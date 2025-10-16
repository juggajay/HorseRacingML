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


def _coerce_float(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype="float64")
    return pd.to_numeric(series, errors="coerce")


def _pick_column(frame: pd.DataFrame, *candidates: str) -> Optional[pd.Series]:
    for column in candidates:
        if column in frame.columns:
            return frame[column]
    return None


def _safe_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


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

        track_series = _pick_column(df, "track", "track_name")
        if track_series is not None:
            df["track"] = track_series.fillna(track_name).fillna(track_info)
        else:
            fallback_track = track_name or track_info
            df["track"] = fallback_track if fallback_track is not None else ""

        state_series = _pick_column(df, "state_code")
        if state_series is not None:
            df["state_code"] = state_series.fillna(state_code)
        else:
            df["state_code"] = state_code

        race_no_series = _pick_column(df, "race_number", "race_no")
        if race_no_series is not None:
            df["race_no"] = _coerce_float(race_no_series).astype("Int64", copy=False)
        else:
            df["race_no"] = pd.Series(pd.NA, index=df.index, dtype="Int64")

        if df["race_no"].isna().all() and "race_id" in df.columns:
            race_times = pd.to_datetime(df.get("race_time"), errors="coerce") if "race_time" in df.columns else None
            race_lookup = pd.DataFrame({
                "race_id": df["race_id"],
                "race_time": race_times,
            }).dropna(subset=["race_id"]).drop_duplicates(subset=["race_id"])
            if "race_time" in race_lookup.columns:
                race_lookup = race_lookup.sort_values("race_time", na_position="last")
            mapping = {rid: idx + 1 for idx, rid in enumerate(race_lookup["race_id"].astype(str))}
            df["race_no"] = df["race_id"].astype(str).map(mapping).astype("Int64")

        df["win_market_id"] = df.apply(
            lambda row: _make_win_market_id(meeting_id, _safe_int(row.get("race_no"))), axis=1
        )

        selection_name_series = _pick_column(df, "horse_name", "runnerName", "runner_name")
        if selection_name_series is not None:
            df["selection_name"] = selection_name_series
        else:
            df["selection_name"] = df.index.astype(str)

        tab_series = _pick_column(df, "tab_no", "tab_number")
        if tab_series is not None:
            df["tab_number"] = _coerce_float(tab_series).astype("Int64", copy=False)
        else:
            df["tab_number"] = pd.Series(pd.NA, index=df.index, dtype="Int64")

        runner_ids = _pick_column(df, "runner_id")
        if runner_ids is None:
            runner_ids = pd.Series([None] * len(df), index=df.index)
        else:
            runner_ids = runner_ids.copy()

        horse_names = _pick_column(df, "horse_name")
        if horse_names is None:
            horse_names = pd.Series([None] * len(df), index=df.index)

        index_fallback = pd.Series(df.index.astype(str), index=df.index)
        df["selection_id"] = (
            runner_ids.fillna(horse_names)
            .fillna(index_fallback)
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
            "place_result",
        ]:
            if column not in df.columns:
                df[column] = np.nan
        if "win_result" in df.columns:
            df["win_result"] = df["win_result"].astype("string").fillna("UNKNOWN")
        else:
            df["win_result"] = "UNKNOWN"

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
