"""Attach Kash and Top5 external model outputs to Betfair raw exports."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

EXTERNAL_DIR = Path("data/processed/external_models")
BETFAIR_RAW_PATTERN = "betfair_all_raw_*.csv.gz"
BETFAIR_RAW_DIR = Path(".")
OUT_DIR = Path("data/processed/betfair_enriched")

KASH_PATH = EXTERNAL_DIR / "kash_model_results.csv.gz"
TOP5_PATH = EXTERNAL_DIR / "top5_model_results.csv.gz"


def _normalise_id(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.astype("Int64").astype(str).replace({"<NA>": pd.NA})


def load_external_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"External table missing: {path}")
    df = pd.read_csv(path, parse_dates=["event_date"], low_memory=False)
    df["betfair_market_id"] = _normalise_id(df["betfair_market_id"])
    df["betfair_selection_id"] = _normalise_id(df["betfair_selection_id"])
    return df


def _derive_event_date(df: pd.DataFrame) -> pd.Series:
    event_date = pd.to_datetime(df.get("event_date"), errors="coerce")
    if "local_meeting_date" in df.columns:
        event_date = event_date.fillna(pd.to_datetime(df["local_meeting_date"], errors="coerce"))
    if event_date.isna().all() and "market_start_time" in df.columns:
        market_dt = pd.to_datetime(df["market_start_time"], errors="coerce")
        if getattr(market_dt.dt, "tz", None) is not None:
            event_date = market_dt.dt.tz_convert("Australia/Sydney").dt.date
        else:
            event_date = market_dt.dt.date
        event_date = pd.to_datetime(event_date, errors="coerce")
    return event_date


def enrich_file(raw_path: Path, kash: pd.DataFrame, top5: pd.DataFrame) -> Path:
    df = pd.read_csv(raw_path, low_memory=False)

    df["event_date_merge"] = _derive_event_date(df)
    df["win_market_id"] = _normalise_id(df["win_market_id"])
    df["selection_id"] = _normalise_id(df["selection_id"])

    merge_keys = ["event_date_merge", "win_market_id", "selection_id"]

    kash_subset = kash.rename(
        columns={
            "betfair_market_id": "win_market_id",
            "betfair_selection_id": "selection_id",
        }
    ).copy()
    kash_subset["event_date_merge"] = kash_subset["event_date"]
    kash_subset = kash_subset.drop(columns=["event_date"])

    df = df.merge(
        kash_subset,
        on=merge_keys,
        how="left",
        suffixes=("", "_kash"),
    )

    top5_subset = top5.rename(
        columns={
            "betfair_market_id": "win_market_id",
            "betfair_selection_id": "selection_id",
        }
    ).copy()
    top5_subset["event_date_merge"] = top5_subset["event_date"]
    top5_subset = top5_subset.drop(columns=["event_date"])

    df = df.merge(
        top5_subset,
        on=merge_keys,
        how="left",
        suffixes=("", "_top5"),
    )

    out_path = OUT_DIR / raw_path.name.replace("betfair_all_raw", "betfair_all_raw_enriched")
    df.to_csv(out_path, index=False, compression="gzip")
    return out_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    kash = load_external_table(KASH_PATH)
    top5 = load_external_table(TOP5_PATH)

    raw_files = sorted(BETFAIR_RAW_DIR.glob(BETFAIR_RAW_PATTERN))
    if not raw_files:
        raise FileNotFoundError("No betfair_all_raw_*.csv.gz files found in project root")

    for raw in raw_files:
        out_path = enrich_file(raw, kash, top5)
        print(f"Enriched {raw.name} -> {out_path.name}")


if __name__ == "__main__":
    main()
