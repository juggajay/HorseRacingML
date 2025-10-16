"""Fetch live Punting Form data and normalise to runner-level schema."""
from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from puntingform_api import PuntingFormClient

CACHE_DIR = Path("services/api/data/live_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _make_win_market_id(meeting_id: str, race_no: int) -> str:
    key = f"{meeting_id}|{race_no}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"pf_{digest}"


def _coerce_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def load_live_pf_day(target_date: dt.date, *, force: bool = False) -> pd.DataFrame:
    """Fetch all meetings via PF API for the given date and return runner rows."""
    cache_path = CACHE_DIR / f"pf_live_{target_date.isoformat()}.parquet"
    if cache_path.exists() and not force:
        try:
            df_cached = pd.read_parquet(cache_path)
            if not df_cached.empty:
                return df_cached
        except Exception:
            pass

    client = PuntingFormClient()
    meetings = client.get_meetings_list(target_date)
    if not meetings:
        return pd.DataFrame()

    frames = []
    for meeting in meetings:
        meeting_id = str(meeting.get("meetingId") or meeting.get("meeting_id") or "")
        if not meeting_id:
            continue
        meeting_date = meeting.get("meetingDate") or meeting.get("pf_meetingDate") or target_date.isoformat()
        track_info = meeting.get("track") or {}
        track_name = track_info.get("name") if isinstance(track_info, dict) else track_info
        state_code = track_info.get("state") if isinstance(track_info, dict) else None

        form_df = client.get_form(meeting_id, meeting_date)
        if form_df is None or form_df.empty:
            continue

        df = form_df.copy()
        df["meeting_id"] = meeting_id
        df["event_date"] = pd.to_datetime(target_date)
        df["track"] = df.get("track_name") or track_name or track_info
        df["track"].fillna(track_name, inplace=True)
        df["state_code"] = df.get("state_code") or state_code
        df["race_no"] = _coerce_float(df.get("race_number") or df.get("race_no")).astype("Int64")
        df["win_market_id"] = df.apply(
            lambda row: _make_win_market_id(meeting_id, int(row.get("race_no") or 0)), axis=1
        )

        df["selection_name"] = df.get("horse_name")
        df["tab_number"] = _coerce_float(df.get("tab_no") or df.get("tab_number")).astype("Int64")
        df["selection_id"] = (
            df.get("runner_id")
            .fillna(df.get("horse_name"))
            .fillna(df.index.astype(str))
            .apply(lambda val: hashlib.sha1(str(val).encode("utf-8")).hexdigest()[:16])
        )

        # Map PF AI price into odds placeholders used by feature pipeline
        pf_ai_price = _coerce_float(df.get("pf_ai_price")).replace({0: np.nan})
        df["win_preplay_last_price_taken"] = pf_ai_price
        df["win_preplay_max_price_taken"] = pf_ai_price
        df["win_preplay_min_price_taken"] = pf_ai_price
        df["win_last_price_taken"] = pf_ai_price
        df["win_bsp"] = pf_ai_price
        df["win_odds"] = pf_ai_price

        # Ensure columns expected by downstream pipeline exist
        for column in [
            "win_preplay_weighted_average_price_taken",
            "win_preplay_volume",
            "win_inplay_volume",
            "win_inplay_max_price_taken",
            "win_inplay_min_price_taken",
            "value_pct",
            "win_result",
            "place_result",
        ]:
            if column not in df.columns:
                df[column] = np.nan
        if "win_result" in df.columns:
            df["win_result"].fillna("UNKNOWN", inplace=True)

        df["track_name_norm"] = df["track"].astype(str).str.lower()
        df["horse_name_norm"] = df["selection_name"].astype(str).str.lower()

        frames.append(df)

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    result = result.rename(
        columns={
            "race_name": "race_name",
            "distance": "distance",
            "race_time": "race_time",
            "pf_score": "pf_score",
            "neural_rating": "neural_rating",
            "time_rating": "time_rating",
            "early_time_rating": "early_time_rating",
            "late_sectional_rating": "late_sectional_rating",
            "weight_class_rating": "weight_class_rating",
            "pf_ai_score": "pf_ai_score",
            "pf_ai_rank": "pf_ai_rank",
        }
    )

    result.to_parquet(cache_path, index=False)
    return result
