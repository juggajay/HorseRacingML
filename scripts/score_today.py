"""Score upcoming races and output selections based on margin rules.

Usage:
    python3 scripts/score_today.py --date 2025-09-30 --margin 1.05 --top 3

Defaults:
    - date: today (UTC)
    - margin: 1.05 (model probability must exceed implied probability * margin)
    - top: None (no limit)

Outputs selections to artifacts/selections_<date>.csv and prints a summary table.
"""
from __future__ import annotations

import argparse
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from lightgbm import Booster

from feature_engineering import engineer_all_features, get_feature_columns
from betfair_live import fetch_live_markets

DATA_PATH = Path("data/processed/ml/betfair_kash_top5.csv.gz")
MODEL_DIR = Path("artifacts/models")
OUTPUT_DIR = Path("artifacts/selections")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def latest_model_path() -> Path:
    models = sorted(MODEL_DIR.glob("betfair_kash_top5_model_*.txt"))
    if not models:
        raise SystemExit("❌ No model artifacts found. Run train_model_pf.py first.")
    return models[-1]


def load_dataset(target_date: date) -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise SystemExit(f"❌ Dataset missing: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df = df.dropna(subset=["event_date"]).copy()
    mask = df["event_date"].dt.date == target_date
    upcoming = df.loc[mask].reset_index(drop=True)
    if upcoming.empty:
        raise SystemExit(f"⚠️ No runners found on {target_date}")
    return upcoming


def load_live_dataset(target_date: date, country: str) -> pd.DataFrame:
    df = fetch_live_markets(target_date, country=country)
    if df.empty:
        raise SystemExit(f"⚠️ Betfair returned no live markets for {target_date}")
    return df


def score(df_raw: pd.DataFrame, model_path: Path) -> pd.DataFrame:
    df_feat = engineer_all_features(df_raw)
    feature_cols = [col for col in get_feature_columns() if col in df_feat.columns]
    missing_cols = set(get_feature_columns()) - set(feature_cols)
    if missing_cols:
        print(f"⚠️ Missing feature columns: {sorted(missing_cols)}")
    booster = Booster(model_file=str(model_path))
    preds = booster.predict(df_feat[feature_cols])
    df_out = df_feat.copy()
    df_out["model_prob"] = preds
    df_out["implied_prob"] = 1.0 / (df_out["win_odds"] + 1e-9)
    return df_out


def filter_selections(df: pd.DataFrame, margin: float, top: Optional[int]) -> pd.DataFrame:
    df = df.copy()
    df["edge"] = df["model_prob"] - df["implied_prob"] * margin
    df = df[df["edge"] > 0]
    df = df.sort_values(["event_date", "edge"], ascending=[True, False])
    if top:
        df = df.groupby(["event_date", "win_market_id"]) \
               .head(top) \
               .reset_index(drop=True)
    return df


def output(df: pd.DataFrame, target_date: date) -> Path:
    output_path = OUTPUT_DIR / f"selections_{target_date:%Y%m%d}.csv"
    columns = [
        "event_date",
        "track",
        "race_no",
        "win_market_id",
        "selection_id",
        "selection_name",
        "win_odds",
        "model_prob",
        "implied_prob",
        "edge",
        "value_pct",
        "betfair_horse_rating",
        "win_rate",
        "model_rank",
    ]
    available = [c for c in columns if c in df.columns]
    df[available].to_csv(output_path, index=False)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score live races and output selections")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD); default today", default=None)
    parser.add_argument("--margin", type=float, default=1.05, help="Margin factor for betting edge")
    parser.add_argument("--top", type=int, default=None, help="Max runners per race to keep")
    parser.add_argument("--source", choices=["dataset", "betfair"], default="dataset", help="Data source")
    parser.add_argument("--country", type=str, default="AU", help="Betfair country code when using live source")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    if args.source == "betfair":
        df_raw = load_live_dataset(target_date, args.country)
    else:
        df_raw = load_dataset(target_date)
    model_path = latest_model_path()
    scored = score(df_raw, model_path)
    selections = filter_selections(scored, args.margin, args.top)
    if selections.empty:
        print(f"⚠️ No selections found with margin {args.margin}")
        return
    out_path = output(selections, target_date)
    print(f"✓ Selections saved -> {out_path}")
    display_cols = [
        "event_date",
        "track",
        "race_no",
        "selection_name",
        "win_odds",
        "model_prob",
        "implied_prob",
        "edge",
    ]
    print(selections[display_cols].head(20))


if __name__ == "__main__":
    main()
