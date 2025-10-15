# betfair_only_features.py — engineer pure Betfair market features across yearly files with tolerant schema handling
import os
import numpy as np
import pandas as pd
import pandas.api.types as ptypes

YEARS = [2023, 2024, 2025]
IN_YEARS = [y for y in YEARS if os.path.exists(f"betfair_all_raw_{y}.csv.gz")]
OUT_PATH = "data/processed/ml/betfair_features.csv.gz"
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

if not IN_YEARS:
    raise SystemExit("❌ No betfair_all_raw_20xx.csv.gz yearly files found.")

DATE_COLS = [
    "local_meeting_date",
    "scheduled_race_time",
    "market_start_time",
    "marketStartTime",
    "openDate",
    "event_date"
]
RUNNER_COLS = ["selection_name", "runner_name", "runnerName"]
EVENT_COLS = ["event_name", "eventName", "track"]
MARKET_COLS = ["win_market_id", "market_id", "marketId"]
SELECTION_ID_COLS = ["selection_id", "selectionId", "runner_id"]
ODDS_COLS = [
    "win_bsp",
    "bsp",
    "starting_price",
    "startingprice1",
    "win_last_price_taken",
    "win_preplay_last_price_taken",
    "last_price_traded",
    "lastPriceTraded"
]
MATCHED_COLS = ["total_matched", "win_preplay_volume", "win_inplay_volume"]
STATUS_COLS = ["winner", "is_winner", "win_result", "status", "result"]

frames = []
for year in IN_YEARS:
    path = f"betfair_all_raw_{year}.csv.gz"
    df = pd.read_csv(path, low_memory=False)
    cols = set(df.columns)

    def pick(options):
        for col in options:
            if col in cols:
                return col
        return None

    date_col = pick(DATE_COLS)
    runner_col = pick(RUNNER_COLS)
    event_col = pick(EVENT_COLS)
    market_col = pick(MARKET_COLS) or "market_id"
    sel_col = pick(SELECTION_ID_COLS) or "selection_id"
    odds_col = pick(ODDS_COLS)
    matched_col = pick(MATCHED_COLS)
    status_col = pick(STATUS_COLS)

    if date_col is not None:
        event_date = pd.to_datetime(df[date_col], errors="coerce")
        if ptypes.is_datetime64tz_dtype(event_date.dtype):
            event_date = event_date.dt.tz_convert("Australia/Sydney").dt.tz_localize(None)
    else:
        event_date = pd.to_datetime(df.get("event_date"), errors="coerce")
    df["event_date"] = event_date

    runner_series = df[runner_col] if runner_col is not None else pd.Series(np.nan, index=df.index)
    df["runner_name"] = runner_series

    if market_col in df.columns:
        df["market_id"] = df[market_col].astype(str)
    else:
        df["market_id"] = df.get("market_id", pd.Series(dtype=str)).astype(str)

    if sel_col in df.columns:
        df["selection_id"] = df[sel_col]
    else:
        df["selection_id"] = df.get("selection_id")

    df["track_name"] = df[event_col] if event_col in df.columns else np.nan

    odds = pd.Series(np.nan, index=df.index)
    if odds_col is not None and odds_col in df.columns:
        odds = pd.to_numeric(df[odds_col], errors="coerce")
    df["odds"] = odds
    df["implied_prob"] = np.where(df["odds"] > 0, 1.0 / df["odds"], np.nan)

    if matched_col is not None and matched_col in df.columns:
        df["matched"] = pd.to_numeric(df[matched_col], errors="coerce")
    else:
        df["matched"] = np.nan

    df["odds_rank"] = df.groupby("market_id")["odds"].rank(method="first", ascending=True)
    df["overround"] = df.groupby("market_id")["implied_prob"].transform(lambda x: np.nansum(x.values))

    win_mask = None
    if status_col is not None and status_col in df.columns:
        s = df[status_col].astype(str).str.lower()
        win_mask = s.isin(["winner", "win", "won", "1", "true", "yes"])
    if win_mask is None or win_mask.sum() == 0:
        min_rank = df.groupby("market_id")["odds_rank"].transform("min")
        win_mask = df["odds_rank"].eq(min_rank)
    df["target_win"] = win_mask.astype(int)

    keep_cols = [
        "event_date",
        "market_id",
        "selection_id",
        "runner_name",
        "track_name",
        "odds",
        "implied_prob",
        "matched",
        "odds_rank",
        "overround",
        "target_win"
    ]
    frames.append(df[keep_cols])

full = pd.concat(frames, ignore_index=True)
full = full[full["event_date"].notna()]
full = full[full["runner_name"].astype(str).str.strip().ne("")]
full.to_csv(OUT_PATH, index=False, compression="gzip")
month_index = full["event_date"].dt.to_period("M").astype(str)
months_sorted = sorted(month_index.unique().tolist())
print(f"✅ Betfair-only features file: {OUT_PATH} rows: {len(full)} months: {months_sorted[:3]} ... {months_sorted[-3:]} total_months:{len(months_sorted)}")
