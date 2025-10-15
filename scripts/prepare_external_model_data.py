"""Consolidate Kash and Top5 historical model outputs into canonical tables."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

RAW_KASH_DIR = Path("data/raw/kash")
RAW_TOP5_DIR = Path("data/raw/top5")
OUT_DIR = Path("data/processed/external_models")

KASH_REQUIRED = [
    "event_date",
    "track_name",
    "race_name",
    "race_number",
    "betfair_market_id",
    "betfair_selection_id",
    "runner_number",
    "horse_name",
    "rp_rating",
    "win_bsp",
    "win_result",
    "place_bsp",
    "place_result",
    "value_pct",
    "race_speed",
    "speed_category",
    "early_speed",
    "late_speed",
]

TOP5_REQUIRED = [
    "event_date",
    "track_name",
    "race_name",
    "race_number",
    "betfair_market_id",
    "betfair_selection_id",
    "runner_number",
    "horse_name",
    "model_rank",
    "win_result",
    "win_bsp",
    "place_result",
    "place_bsp",
]


def _resolve_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _normalise_percentage(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace('%', '', regex=False)
        .str.replace('−', '-', regex=False)
        .str.replace('\u2212', '-', regex=False)
    )
    cleaned = cleaned.replace({'nan': None, 'None': None, '': None})
    return pd.to_numeric(cleaned, errors='coerce')


def load_kash_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    alias_map = {
        "event_date": ["Date"],
        "track_name": ["Track"],
        "race_name": ["Race Name", "Race_Name"],
        "race_number": ["Race"],
        "betfair_market_id": ["Market", "MarketID"],
        "betfair_selection_id": ["Selection", "SelectionID"],
        "runner_number": ["Number"],
        "horse_name": ["Horse"],
        "rp_rating": ["RP"],
        "win_bsp": ["WIN_BSP", "Win_BSP"],
        "win_result": ["WIN_RESULT", "Win_Result"],
        "place_bsp": ["PLACE_BSP", "Place_BSP"],
        "place_result": ["PLACE_RESULT", "Place_Result"],
        "value_pct": ["VALUE", "Value"],
        "race_speed": ["Race_Speed"],
        "speed_category": ["Speed_Category", "Speed_Cat"],
        "early_speed": ["Early_Speed"],
        "late_speed": ["Late_Speed"],
    }

    rename_map: dict[str, str] = {}
    for target, candidates in alias_map.items():
        resolved = _resolve_column(df, candidates)
        if resolved:
            rename_map[resolved] = target

    df = df.rename(columns=rename_map)

    for col in KASH_REQUIRED:
        if col not in df.columns:
            df[col] = pd.NA

    df["event_date"] = pd.to_datetime(df["event_date"], dayfirst=True, errors="coerce")
    df["race_number"] = pd.to_numeric(df["race_number"], errors="coerce")
    df["runner_number"] = pd.to_numeric(df["runner_number"], errors="coerce")
    df["win_bsp"] = pd.to_numeric(df["win_bsp"], errors="coerce")
    df["place_bsp"] = pd.to_numeric(df["place_bsp"], errors="coerce")
    df["win_result"] = pd.to_numeric(df["win_result"], errors="coerce").fillna(0).astype("Int64")
    df["place_result"] = pd.to_numeric(df["place_result"], errors="coerce").fillna(0).astype("Int64")
    df["rp_rating"] = pd.to_numeric(df["rp_rating"], errors="coerce")
    df["value_pct"] = _normalise_percentage(df["value_pct"])
    df["race_speed"] = pd.to_numeric(df["race_speed"], errors="coerce")
    df["early_speed"] = pd.to_numeric(df["early_speed"], errors="coerce")
    df["late_speed"] = pd.to_numeric(df["late_speed"], errors="coerce")
    df["speed_category"] = df["speed_category"].astype("string")

    df["betfair_market_id"] = df["betfair_market_id"].astype("string").str.strip()
    df["betfair_selection_id"] = df["betfair_selection_id"].astype("string").str.strip()
    df["track_name"] = df["track_name"].astype("string").str.strip()
    df["race_name"] = df["race_name"].astype("string").str.strip()
    df["horse_name"] = df["horse_name"].astype("string").str.strip()

    df["source_file"] = path.name

    columns = KASH_REQUIRED + ["source_file"]
    return df[columns]


def load_top5_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)

    alias_map = {
        "event_date": ["Date"],
        "track_name": ["Track"],
        "race_name": ["Race Name", "Race_Name"],
        "race_number": ["Race"],
        "betfair_market_id": ["MarketID", "Market"],
        "betfair_selection_id": ["SelectionID", "Selection"],
        "runner_number": ["Number"],
        "horse_name": ["Horse"],
        "model_rank": ["Rank"],
        "win_result": ["WIN_RESULT", "Win_Result"],
        "win_bsp": ["WIN_BSP", "Win_BSP"],
        "place_result": ["PLACE_RESULT", "Place_Result"],
        "place_bsp": ["PLACE_BSP", "Place_BSP"],
    }

    rename_map: dict[str, str] = {}
    for target, candidates in alias_map.items():
        resolved = _resolve_column(df, candidates)
        if resolved:
            rename_map[resolved] = target

    df = df.rename(columns=rename_map)

    for col in TOP5_REQUIRED:
        if col not in df.columns:
            df[col] = pd.NA

    df["event_date"] = pd.to_datetime(df["event_date"], dayfirst=True, errors="coerce")
    df["race_number"] = pd.to_numeric(df["race_number"], errors="coerce")
    df["runner_number"] = pd.to_numeric(df["runner_number"], errors="coerce")
    df["model_rank"] = pd.to_numeric(df["model_rank"], errors="coerce")
    df["win_bsp"] = pd.to_numeric(df["win_bsp"], errors="coerce")
    df["place_bsp"] = pd.to_numeric(df["place_bsp"], errors="coerce")
    df["win_result"] = pd.to_numeric(df["win_result"], errors="coerce").fillna(0).astype("Int64")
    df["place_result"] = pd.to_numeric(df["place_result"], errors="coerce").fillna(0).astype("Int64")

    df["betfair_market_id"] = df["betfair_market_id"].astype("string").str.strip()
    df["betfair_selection_id"] = df["betfair_selection_id"].astype("string").str.strip()
    df["track_name"] = df["track_name"].astype("string").str.strip()
    df["race_name"] = df["race_name"].astype("string").str.strip()
    df["horse_name"] = df["horse_name"].astype("string").str.strip()

    df["source_file"] = path.name

    columns = TOP5_REQUIRED + ["source_file"]
    return df[columns]


def consolidate_frames(paths: list[Path], loader) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        frames.append(loader(path))
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["event_date", "betfair_market_id", "betfair_selection_id"])
    combined = combined.drop_duplicates(
        subset=["event_date", "betfair_market_id", "betfair_selection_id", "source_file"],
        keep="last",
    )
    return combined.reset_index(drop=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    kash_paths = sorted(RAW_KASH_DIR.glob("Kash_Model_Results_*.csv"))
    top5_paths = sorted(RAW_TOP5_DIR.glob("Top5_Model_Results_*.csv"))

    if kash_paths:
        kash_df = consolidate_frames(kash_paths, load_kash_file)
        kash_df.to_csv(OUT_DIR / "kash_model_results.csv.gz", index=False, compression="gzip")
        print(f"Wrote {len(kash_df):,} Kash rows")
    else:
        print("No Kash files found")

    if top5_paths:
        top5_df = consolidate_frames(top5_paths, load_top5_file)
        top5_df.to_csv(OUT_DIR / "top5_model_results.csv.gz", index=False, compression="gzip")
        print(f"Wrote {len(top5_df):,} Top5 rows")
    else:
        print("No Top5 files found")


if __name__ == "__main__":
    main()
