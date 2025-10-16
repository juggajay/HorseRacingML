"""Transform Betfair-derived dataset into PF-style schema tables.

The resulting tables mimic the structure exposed by the Punting Form API so
that downstream training / inference code can swap to real PF data with
minimal changes.

Output artefacts are written under ``services/api/data/processed/pf_schema``:
- meetings.parquet         (one row per meeting)
- races.parquet            (one row per race)
- runners.parquet          (runner-centric flat table of market + results)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd

DEFAULT_SOURCE = Path("services/api/data/processed/ml/betfair_kash_top5.csv.gz")
DEFAULT_OUT = Path("services/api/data/processed/pf_schema")


@dataclass
class DatasetPaths:
    meetings: Path
    races: Path
    runners: Path
    manifest: Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_meeting_id(track: str, event_date: str) -> str:
    """Return a deterministic meeting identifier similar to PF IDs."""
    track = (track or "").strip().lower()
    key = f"{track}|{event_date}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return f"bfm_{digest}"


def _make_race_id(win_market_id: Union[int, float, str]) -> str:
    return f"bfr_{int(float(win_market_id))}"



def _to_datetime(date_series: pd.Series, time_series: pd.Series) -> pd.Series:
    date_str = date_series.astype(str).fillna("")
    time_str = time_series.fillna("00:00:00").astype(str)
    combined = date_str + " " + time_str
    return pd.to_datetime(combined, errors="coerce")


def _to_bool(series: pd.Series) -> pd.Series:
    return series.fillna(False).astype(bool)


def _create_directories(out_dir: Path) -> DatasetPaths:
    out_dir.mkdir(parents=True, exist_ok=True)
    return DatasetPaths(
        meetings=out_dir / "meetings.parquet",
        races=out_dir / "races.parquet",
        runners=out_dir / "runners.parquet",
        manifest=out_dir / "manifest.json",
    )


def _write_table(df: pd.DataFrame, target: Path) -> Path:
    """Write table as parquet when possible, otherwise fallback to gz CSV."""
    try:
        df.to_parquet(target, index=False)
        return target
    except Exception:
        csv_target = target.with_suffix(".csv.gz")
        df.to_csv(csv_target, index=False, compression="gzip")
        return csv_target


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------

def build_meetings(df: pd.DataFrame) -> pd.DataFrame:
    meetings = (
        df[
            [
                "event_date",
                "track",
                "track_name_norm",
                "state_code",
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    meetings["event_date"] = pd.to_datetime(meetings["event_date"], errors="coerce").dt.date
    meetings = meetings.dropna(subset=["event_date"])

    meetings["meeting_id"] = meetings.apply(
        lambda row: _make_meeting_id(row["track_name_norm"], row["event_date"]), axis=1
    )
    meetings["track_abbrev"] = meetings["track"].str.slice(stop=5).str.upper()
    meetings["country"] = "AUS"
    meetings["source"] = "betfair"

    cols = [
        "meeting_id",
        "event_date",
        "track",
        "track_name_norm",
        "track_abbrev",
        "state_code",
        "country",
        "source",
    ]
    meetings = meetings[cols].sort_values(["event_date", "track_name_norm"]).reset_index(drop=True)
    return meetings


def build_races(df: pd.DataFrame, meetings: pd.DataFrame) -> pd.DataFrame:
    races = (
        df[
            [
                "event_date",
                "track_name_norm",
                "win_market_id",
                "win_market_name",
                "scheduled_race_time",
                "actual_off_time",
                "race_no",
                "racing_type",
                "race_type",
                "distance",
            ]
        ]
        .drop_duplicates(subset=["win_market_id"])
        .copy()
    )

    races["race_id"] = races["win_market_id"].map(_make_race_id)
    races["meeting_id"] = races.apply(
        lambda row: _make_meeting_id(row["track_name_norm"], row["event_date"]), axis=1
    )

    races["scheduled_start"] = _to_datetime(races["event_date"], races["scheduled_race_time"])
    races["actual_start"] = _to_datetime(races["event_date"], races["actual_off_time"])
    races["distance"] = pd.to_numeric(races["distance"], errors="coerce")

    cols = [
        "race_id",
        "meeting_id",
        "win_market_id",
        "win_market_name",
        "race_no",
        "racing_type",
        "race_type",
        "distance",
        "scheduled_start",
        "actual_start",
    ]
    races = races[cols].sort_values(["scheduled_start", "race_no"]).reset_index(drop=True)
    return races


def build_runners(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()

    base["race_id"] = base["win_market_id"].map(_make_race_id)
    base["runner_id"] = base["race_id"] + "_" + base["selection_id"].astype(str)

    base["tab_number"] = pd.to_numeric(base["tab_number"], errors="coerce")
    base["selection_id"] = pd.to_numeric(base["selection_id"], errors="coerce")

    scheduled_start = _to_datetime(base["event_date"], base["scheduled_race_time"])
    base["win_odds"] = pd.to_numeric(
        base["win_preplay_last_price_taken"].fillna(base["win_bsp"]), errors="coerce"
    )

    selection_cols = [
        "runner_id",
        "race_id",
        "selection_id",
        "tab_number",
        "selection_name",
        "horse_name_norm",
        "win_odds",
        "win_bsp",
        "win_result",
        "place_bsp",
        "place_result",
        "win_preplay_volume",
        "win_inplay_volume",
        "place_preplay_volume",
        "win_preplay_last_price_taken",
        "win_last_price_taken",
        "win_preplay_weighted_average_price_taken",
        "win_preplay_max_price_taken",
        "win_preplay_min_price_taken",
        "win_inplay_max_price_taken",
        "win_inplay_min_price_taken",
        "value_pct",
        "race_speed",
        "speed_category",
        "early_speed",
        "late_speed",
        "model_rank",
        "betfair_horse_rating",
        "win_rate",
        "place_rate",
        "total_starts",
        "total_wins",
        "avg_odds",
        "is_experienced",
        "is_novice",
        "is_strong_form",
        "is_consistent",
        "place_weighted_average_price_taken",
        "place_max_price_taken",
        "place_min_price_taken",
        "place_last_price_taken",
    ]

    for col in selection_cols:
        if col not in base.columns:
            base[col] = np.nan

    runners = base[selection_cols].assign(_scheduled_start=scheduled_start)
    runners = runners.sort_values(["_scheduled_start", "race_id", "tab_number"]).drop(columns="_scheduled_start").reset_index(drop=True)
    return runners


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(source_path: Path, out_dir: Path) -> DatasetPaths:
    paths = _create_directories(out_dir)
    df = pd.read_csv(source_path)

    meetings = build_meetings(df)
    races = build_races(df, meetings)
    runners = build_runners(df)

    paths.meetings = _write_table(meetings, paths.meetings)
    paths.races = _write_table(races, paths.races)
    paths.runners = _write_table(runners, paths.runners)

    manifest = {
        "source": str(source_path),
        "rows": {
            "meetings": int(len(meetings)),
            "races": int(len(races)),
            "runners": int(len(runners)),
        },
        "outputs": {
            "meetings": str(paths.meetings),
            "races": str(paths.races),
            "runners": str(paths.runners),
        },
    }
    paths.manifest.write_text(json.dumps(manifest, indent=2))

    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Path to Betfair dataset")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output directory root")
    args = parser.parse_args()

    paths = run(args.source, args.out)
    print("PF schema tables written:")
    for name, path in paths.__dict__.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
