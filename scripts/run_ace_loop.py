"""Run the Early Experience + ACE loops end-to-end.

Example usage:

    python3 scripts/run_ace_loop.py \
        --start-date 2025-07-18 \
        --end-date 2025-09-30 \
        --strategies configs/strategies_default.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import sys

import pandas as pd
from lightgbm import Booster

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from ace.early_experience import EarlyExperienceRunner, ExperienceConfig, ExperienceWriter
from ace.playbook import ACEReflector, PlaybookCurator
from ace.simulator import Simulator
from ace.strategies import StrategyConfig, StrategyGrid
from feature_engineering import engineer_all_features, get_feature_columns
from services.api.pf_schema_loader import load_pf_dataset

MODEL_DIR = Path("artifacts/models")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Early Experience + ACE loops")
    parser.add_argument("--start-date", type=str, help="Inclusive start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Inclusive end date (YYYY-MM-DD)")
    parser.add_argument("--strategies", type=Path, help="Path to strategy JSON config", default=None)
    parser.add_argument("--max-races", type=int, default=None, help="Limit number of races to process")
    parser.add_argument("--output-experiences", type=Path, default=Path("data/experiences"))
    parser.add_argument("--playbook-path", type=Path, default=Path("artifacts/playbook/playbook.json"))
    parser.add_argument("--min-bets", type=int, default=30, help="Minimum bets required for context insights")
    return parser.parse_args()


def load_latest_model(model_dir: Path = MODEL_DIR) -> Booster:
    models = sorted(model_dir.glob("betfair_kash_top5_model_*.txt"))
    if not models:
        raise SystemExit(f"❌ No model artifacts found in {model_dir}")
    return Booster(model_file=str(models[-1]))


def build_dataset(start: str, end: str, max_races: Optional[int]) -> pd.DataFrame:
    df = load_pf_dataset()
    if df is None or df.empty:
        raise SystemExit("❌ PF dataset is empty. Run the schema builder first.")

    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    df = df[(df["event_date"] >= start_dt) & (df["event_date"] <= end_dt)]
    if df.empty:
        raise SystemExit(f"⚠️ No runners found between {start} and {end}")

    df = df.sort_values(["event_date", "race_id"]).reset_index(drop=True)
    if max_races is not None:
        unique_races = df["race_id"].drop_duplicates().head(max_races)
        df = df[df["race_id"].isin(unique_races)]
    return df


def ensure_predictions(df: pd.DataFrame, booster: Booster) -> pd.DataFrame:
    engineered = engineer_all_features(df)
    feature_cols = [c for c in get_feature_columns() if c in engineered.columns]
    if not feature_cols:
        raise SystemExit("❌ No feature columns available for prediction. Check dataset.")
    preds = booster.predict(engineered[feature_cols])
    engineered["model_prob"] = preds
    engineered["implied_prob"] = 1.0 / (engineered["win_odds"].replace(0, pd.NA) + 1e-9)
    return engineered


def load_strategies(path: Optional[Path]) -> List[StrategyConfig]:
    if path is None:
        return StrategyGrid.build(margins=[1.02, 1.05, 1.08], top_ns=[1, 2], stakes=[1.0])
    definition = json.loads(path.read_text())
    if isinstance(definition, list):
        configs: List[StrategyConfig] = []
        for item in definition:
            configs.extend(StrategyGrid.from_dict(item))
        return configs
    if isinstance(definition, dict):
        return StrategyGrid.from_dict(definition)
    raise SystemExit(f"❌ Unsupported strategy definition in {path}")


def read_experiences(path: Optional[Path]) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    if path.suffix.endswith(".gz") or path.suffix == ".gz":
        return pd.read_csv(path)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".csv":
        return pd.read_csv(path)
    raise SystemExit(f"❌ Unsupported experience file format: {path}")


def main() -> None:
    args = parse_args()

    dataset = build_dataset(args.start_date, args.end_date, args.max_races)
    booster = load_latest_model()
    runners = ensure_predictions(dataset, booster)

    strategies = load_strategies(args.strategies)
    print(f"Evaluating {len(strategies)} strategies over {runners['race_id'].nunique()} races")

    simulator = Simulator()
    writer = ExperienceWriter(ExperienceConfig(output_dir=args.output_experiences))
    experience_runner = EarlyExperienceRunner(simulator=simulator, strategies=strategies, writer=writer)
    experience_output = experience_runner.run(runners, label="ace")

    exp_df = read_experiences(experience_output.experience_path)
    reflector = ACEReflector(min_bets=args.min_bets)
    playbook = reflector.build_playbook(exp_df, experience_output.strategy_metrics)

    curator = PlaybookCurator(output_path=args.playbook_path)
    playbook_path = curator.save(playbook)

    print("\n=== Early Experience Summary ===")
    print(experience_output.strategy_metrics)
    print("\n=== Playbook ===")
    print(json.dumps(playbook.to_dict(), indent=2))
    print(f"\nExperience file: {experience_output.experience_path or 'n/a'}")
    print(f"Playbook saved to: {playbook_path}")


if __name__ == "__main__":
    main()
