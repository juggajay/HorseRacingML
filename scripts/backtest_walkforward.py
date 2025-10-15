"""Walk-forward evaluation for Betfair+Kash+Top5 model.

Trains sequentially by month and evaluates multiple betting thresholds."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import log_loss, roc_auc_score

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from feature_engineering import engineer_all_features, get_feature_columns

DATA_PATH = Path("data/processed/ml/betfair_kash_top5.csv.gz")
OUTPUT_PATH = Path("artifacts/walkforward_results.csv")
SUMMARY_PATH = Path("artifacts/walkforward_summary.csv")

# Require model probability to exceed implied_prob * margin_factor before betting
MARGIN_FACTORS: Iterable[float] = (1.00, 1.02, 1.05, 1.10, 1.20)
MIN_TRAIN_ROWS = 50_000  # skip very early months if not enough history

MODEL_PARAMS = dict(
    objective="binary",
    n_estimators=500,
    learning_rate=0.03,
    num_leaves=63,
    subsample=0.9,
    colsample_bytree=0.8,
    random_state=42,
)


def compute_metrics(df: pd.DataFrame, margins: Iterable[float]) -> list[dict[str, float]]:
    results: list[dict[str, float]] = []
    implied = 1.0 / (df["win_odds"] + 1e-9)
    won = df["won"].values

    for margin in margins:
        edge_mask = df["model_prob"] > implied * margin
        bets = df[edge_mask]
        num_bets = int(edge_mask.sum())
        if num_bets == 0:
            pot = 0.0
            profit = 0.0
        else:
            profits = np.where(bets["won"] == 1, bets["win_odds"] - 1.0, -1.0)
            profit = float(profits.sum())
            pot = float(profits.mean())
        results.append(
            dict(
                margin=margin,
                bets=num_bets,
                pot_pct=pot * 100.0,
                profit=profit,
            )
        )
    return results


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"❌ Dataset missing: {DATA_PATH}")

    df_raw = pd.read_csv(DATA_PATH)
    df = engineer_all_features(df_raw)

    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df = df.dropna(subset=["event_date"]).sort_values("event_date").reset_index(drop=True)

    feature_cols = [c for c in get_feature_columns() if c in df.columns]

    df["won"] = df["win_result"].astype(str).str.lower().eq("winner").astype(int)

    df["month"] = df["event_date"].dt.to_period("M")
    months = sorted(df["month"].dropna().unique())

    rows: list[dict[str, float]] = []

    for month in months:
        test_mask = df["month"] == month
        train_mask = df["event_date"] < month.to_timestamp()

        X_train = df.loc[train_mask, feature_cols]
        y_train = df.loc[train_mask, "won"]
        X_test = df.loc[test_mask, feature_cols]
        y_test = df.loc[test_mask, "won"]

        if len(X_train) < MIN_TRAIN_ROWS or len(X_test) == 0:
            continue

        model = LGBMClassifier(**MODEL_PARAMS)
        model.fit(X_train, y_train)

        train_pred = model.predict_proba(X_train)[:, 1]
        test_pred = model.predict_proba(X_test)[:, 1]

        train_logloss = log_loss(y_train, train_pred)
        test_logloss = log_loss(y_test, test_pred)
        train_auc = roc_auc_score(y_train, train_pred)
        test_auc = roc_auc_score(y_test, test_pred)

        test_frame = df.loc[test_mask, ["win_odds", "won"]].copy()
        test_frame["model_prob"] = test_pred

        bet_metrics = compute_metrics(test_frame, MARGIN_FACTORS)
        for bm in bet_metrics:
            rows.append(
                dict(
                    month=str(month),
                    train_rows=len(X_train),
                    test_rows=len(X_test),
                    train_logloss=train_logloss,
                    test_logloss=test_logloss,
                    train_auc=train_auc,
                    test_auc=test_auc,
                    margin=bm["margin"],
                    bets=bm["bets"],
                    pot_pct=bm["pot_pct"],
                    profit=bm["profit"],
                )
            )

    if not rows:
        raise SystemExit("❌ No walk-forward folds produced results. Check dataset/date coverage.")

    results_df = pd.DataFrame(rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUT_PATH, index=False)

    summary = results_df.groupby("margin").agg(
        folds=("month", "nunique"),
        total_bets=("bets", "sum"),
        avg_pot=("pot_pct", "mean"),
        median_pot=("pot_pct", "median"),
        total_profit=("profit", "sum"),
        mean_test_auc=("test_auc", "mean"),
    ).reset_index()
    summary.to_csv(SUMMARY_PATH, index=False)

    print("Saved walk-forward detail ->", OUTPUT_PATH)
    print("Saved walk-forward summary ->", SUMMARY_PATH)
    print(summary)


if __name__ == "__main__":
    main()
