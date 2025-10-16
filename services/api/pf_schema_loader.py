"""Helpers for reading PF-style schema tables produced from Betfair data."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

# Determine base directory - works in both development and Docker container
_current_file = Path(__file__).resolve()
if _current_file.parent.name == "api":  # Development: services/api/
    REPO_ROOT = _current_file.parents[2]
    PF_SCHEMA_DIR = REPO_ROOT / "services" / "api" / "data" / "processed" / "pf_schema"
else:  # Docker container: /app/
    PF_SCHEMA_DIR = _current_file.parent / "data" / "processed" / "pf_schema"

_TABLE_EXTS = (".parquet", ".csv.gz", ".csv")


def _resolve_column(frame: pd.DataFrame, base_name: str) -> None:
    if base_name in frame.columns:
        return
    candidates = [f"{base_name}_x", f"{base_name}_y"]
    values = [frame[c] for c in candidates if c in frame.columns]
    if not values:
        return
    combined = values[0]
    for extra in values[1:]:
        combined = combined.fillna(extra)
    frame[base_name] = combined
    frame.drop(columns=[c for c in candidates if c in frame.columns], inplace=True)


def _convert_to_int_or_str(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        return series.astype(str)
    return numeric.astype("Int64")


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

    for base in [
        "event_date",
        "meeting_id",
        "track_name_norm",
        "win_market_id",
        "race_no",
        "selection_id",
        "tab_number",
    ]:
        _resolve_column(merged, base)

    merged["event_date"] = pd.to_datetime(merged["event_date"], errors="coerce")
    merged = merged.dropna(subset=["event_date"]).copy()

    if "track" not in merged.columns:
        merged["track"] = merged["track_name_norm"].str.title()
    else:
        merged["track"] = merged["track"].fillna(merged["track_name_norm"].str.title())

    merged["win_market_id"] = _convert_to_int_or_str(merged.get("win_market_id"))
    merged["race_no"] = pd.to_numeric(merged.get("race_no"), errors="coerce").astype("Int64")
    if "selection_id" in merged.columns:
        merged["selection_id"] = _convert_to_int_or_str(merged["selection_id"])
    if "tab_number" in merged.columns:
        merged["tab_number"] = pd.to_numeric(merged.get("tab_number"), errors="coerce").astype("Int64")
    if "scheduled_start" in merged.columns:
        merged["scheduled_start"] = pd.to_datetime(merged["scheduled_start"], errors="coerce")

    return merged
