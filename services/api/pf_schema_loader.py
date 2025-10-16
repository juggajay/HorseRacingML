"""Helpers for reading PF-style schema tables produced from Betfair data."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PF_SCHEMA_DIR = REPO_ROOT / "services" / "api" / "data" / "processed" / "pf_schema"
_TABLE_EXTS = (".parquet", ".csv.gz", ".csv")


def read_table(name: str, base_dir: Path = PF_SCHEMA_DIR) -> pd.DataFrame:
    """Read a PF schema table with flexible extension support."""
    for ext in _TABLE_EXTS:
        path = base_dir / f"{name}{ext}"
        if path.exists():
            if ext == ".parquet":
                return pd.read_parquet(path)
            return pd.read_csv(path, low_memory=False)
    raise FileNotFoundError(f"Table {name} not found under {base_dir}")


def load_pf_dataset(base_dir: Path = PF_SCHEMA_DIR) -> Optional[pd.DataFrame]:
    """Return merged runner-level dataset aligned to original Betfair schema."""
    if not base_dir.exists():
        return None
    try:
        runners = read_table("runners", base_dir)
        races = read_table("races", base_dir)
        meetings = read_table("meetings", base_dir)
    except FileNotFoundError:
        return None

    merged = (
        runners.merge(
            races[
                [
                    "race_id",
                    "meeting_id",
                    "win_market_id",
                    "win_market_name",
                    "race_no",
                    "racing_type",
                    "race_type",
                    "distance",
                    "scheduled_start",
                ]
            ],
            on="race_id",
            how="left",
        )
        .merge(
            meetings[["meeting_id", "event_date", "track", "track_name_norm", "state_code"]],
            on="meeting_id",
            how="left",
        )
    )

    merged["event_date"] = pd.to_datetime(merged["event_date"], errors="coerce")
    merged = merged.dropna(subset=["event_date"]).copy()

    if "track" not in merged.columns:
        merged["track"] = merged["track_name_norm"].str.title()
    else:
        merged["track"] = merged["track"].fillna(merged["track_name_norm"].str.title())
    merged["win_market_id"] = pd.to_numeric(merged["win_market_id"], errors="coerce").astype("Int64")
    merged["race_no"] = pd.to_numeric(merged["race_no"], errors="coerce").astype("Int64")
    merged["selection_id"] = pd.to_numeric(merged.get("selection_id"), errors="coerce").astype("Int64")
    merged["tab_number"] = pd.to_numeric(merged.get("tab_number"), errors="coerce").astype("Int64")
    if "scheduled_start" in merged.columns:
        merged["scheduled_start"] = pd.to_datetime(merged["scheduled_start"], errors="coerce")

    return merged
