"""Combine enriched Betfair history (with Kash/Top5 signals) into a training-ready table."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import re

ENRICHED_DIR = Path("data/processed/betfair_enriched")
OUTPUT_PATH = Path("data/processed/ml/betfair_kash_top5.csv.gz")
RATINGS_PATH = Path("artifacts/horse_ratings_betfair_2023_2024.csv")

KEEP_COLS = [
    "event_date_merge",
    "local_meeting_date",
    "scheduled_race_time",
    "actual_off_time",
    "track",
    "state_code",
    "race_no",
    "win_market_id",
    "win_market_name",
    "place_market_id",
    "racing_type",
    "distance",
    "race_type",
    "selection_id",
    "tab_number",
    "selection_name",
    "win_result",
    "win_bsp",
    "place_result",
    "place_bsp",
    "win_bsp_volume",
    "win_preplay_max_price_taken",
    "win_preplay_min_price_taken",
    "win_preplay_last_price_taken",
    "win_preplay_weighted_average_price_taken",
    "win_preplay_volume",
    "win_inplay_max_price_taken",
    "win_inplay_min_price_taken",
    "win_last_price_taken",
    "win_inplay_weighted_average_price_taken",
    "win_inplay_volume",
    "place_bsp_volume",
    "place_max_price_taken",
    "place_min_price_taken",
    "place_last_price_taken",
    "place_weighted_average_price_taken",
    "place_preplay_volume",
    "best_avail_back_at_scheduled_off",
    "best_avail_lay_at_scheduled_off",
    "back_market_percentage_at_scheduled_off",
    "lay_market_percentage_at_scheduled_off",
    "runner_name",
    "event_name",
    "market_start_time",
    "track_name_norm",
    "horse_name_norm",
    "race_id",
    "runner_id",
    "rp_rating",
    "win_bsp_kash",
    "win_result_kash",
    "place_bsp_kash",
    "place_result_kash",
    "value_pct",
    "race_speed",
    "speed_category",
    "early_speed",
    "late_speed",
    "model_rank",
    "win_result_top5",
    "win_bsp_top5",
    "place_result_top5",
    "place_bsp_top5",
]


def _norm(text):
    if pd.isna(text):
        return None
    s = str(text).lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s or None


def main() -> None:
    if not ENRICHED_DIR.exists():
        raise SystemExit("❌ Enriched Betfair directory missing. Run scripts/enrich_betfair_with_external_models.py first.")

    frames: list[pd.DataFrame] = []
    for path in sorted(ENRICHED_DIR.glob("betfair_all_raw_enriched_*.csv.gz")):
        df = pd.read_csv(path, low_memory=False)
        missing = [c for c in KEEP_COLS if c not in df.columns]
        for col in missing:
            df[col] = pd.NA
        frames.append(df[KEEP_COLS].copy())
        print(f"Loaded {path.name}: {len(df):,} rows")

    if not frames:
        raise SystemExit("❌ No enriched Betfair files found.")

    combined = pd.concat(frames, ignore_index=True)

    combined["event_date"] = pd.to_datetime(combined["event_date_merge"], errors="coerce")
    combined["event_date"] = combined["event_date"].fillna(pd.to_datetime(combined["local_meeting_date"], errors="coerce"))
    combined = combined.dropna(subset=["event_date"]).copy()

    combined["horse_name_norm"] = combined["horse_name_norm"].where(~combined["horse_name_norm"].isna(), combined["selection_name"])
    combined["horse_name_norm"] = combined["horse_name_norm"].map(_norm)

    combined["track_name_norm"] = combined["track_name_norm"].where(~combined["track_name_norm"].isna(), combined["track"])
    combined["track_name_norm"] = combined["track_name_norm"].map(_norm)

    if RATINGS_PATH.exists():
        ratings = pd.read_csv(RATINGS_PATH)
        ratings["horse_name_norm"] = ratings["horse_name_norm"].astype(str).str.lower().str.strip()
        rating_cols = [
            "betfair_horse_rating",
            "win_rate",
            "place_rate",
            "total_starts",
            "total_wins",
            "avg_odds",
        ]
        cols = [c for c in rating_cols if c in ratings.columns]
        combined = combined.merge(
            ratings[["horse_name_norm", *cols]],
            on="horse_name_norm",
            how="left",
        )
    else:
        combined["betfair_horse_rating"] = np.nan
        combined["win_rate"] = np.nan
        combined["place_rate"] = np.nan
        combined["total_starts"] = np.nan
        if "total_wins" not in combined.columns:
            combined["total_wins"] = np.nan

    combined["betfair_horse_rating"] = pd.to_numeric(combined.get("betfair_horse_rating"), errors="coerce").fillna(50.0)
    combined["win_rate"] = pd.to_numeric(combined.get("win_rate"), errors="coerce").fillna(0.10)
    combined["place_rate"] = pd.to_numeric(combined.get("place_rate"), errors="coerce").fillna(0.30)
    combined["total_starts"] = pd.to_numeric(combined.get("total_starts"), errors="coerce").fillna(5)

    combined["value_pct"] = pd.to_numeric(combined.get("value_pct"), errors="coerce") / 100.0
    combined["race_speed"] = pd.to_numeric(combined.get("race_speed"), errors="coerce")
    combined["early_speed"] = pd.to_numeric(combined.get("early_speed"), errors="coerce")
    combined["late_speed"] = pd.to_numeric(combined.get("late_speed"), errors="coerce")
    combined["model_rank"] = pd.to_numeric(combined.get("model_rank"), errors="coerce")
    combined["win_bsp_kash"] = pd.to_numeric(combined.get("win_bsp_kash"), errors="coerce")
    combined["win_bsp_top5"] = pd.to_numeric(combined.get("win_bsp_top5"), errors="coerce")

    combined["is_experienced"] = (combined["total_starts"] >= 10).astype(int)
    combined["is_novice"] = (combined["total_starts"] <= 3).astype(int)
    combined["is_strong_form"] = (combined["win_rate"] > 0.20).astype(int)
    combined["is_consistent"] = (combined["place_rate"] > 0.50).astype(int)

    combined["event_date"] = combined["event_date"].dt.date
    combined = combined.sort_values(["event_date", "win_market_id", "selection_id"]).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False, compression="gzip")
    print(f"Saved {len(combined):,} rows -> {OUTPUT_PATH}")
    print(f"Date range: {combined['event_date'].min()} to {combined['event_date'].max()}")


if __name__ == "__main__":
    main()
