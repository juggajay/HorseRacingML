# update_weekly_puntingform.py
# Weekly updater:
# - Figures out which months cover the last 7 days.
# - Calls PF endpoints (cached).
# - Writes combined flat CSVs per month under ./data/processed/
# NOTE: Join to Betfair/Kaggle is a separate step; this script only fetches PF data and
#       prepares them into tidy tables you can merge downstream.

from __future__ import annotations
import os, sys, datetime as dt, pandas as pd
from typing import List, Dict, Any
from puntingform_api import PuntingFormClient, month_key, CACHE_ROOT, ensure_dir
from dotenv import load_dotenv
if os.path.exists('.env'):
    load_dotenv('.env')


PROC_ROOT = "./data/processed"
ensure_dir(PROC_ROOT)

def env_flag(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default).strip() not in ("", "0", "false", "False")

FETCH_FORM = env_flag("PF_FETCH_FORM", "1")
FETCH_BENCHMARKS = env_flag("PF_FETCH_BENCHMARKS", "0")
FETCH_SECTIONALS = env_flag("PF_FETCH_SECTIONALS", "0")

def months_covering(days:int=7) -> List[tuple[int,int]]:
    today = dt.date.today()
    start = today - dt.timedelta(days=days)
    months = set()
    d = start
    while d <= today:
        months.add((d.year, d.month))
        d += dt.timedelta(days=1)
    return sorted(months)

def flatten_pf_payload(payload: Dict[str, Any]) -> pd.DataFrame:
    """Make a best-effort DataFrame from a PF response, whether JSON or CSV wrapped."""
    if not payload:
        return pd.DataFrame()
    if isinstance(payload, dict) and "_raw" in payload:
        # Try CSV
        import io
        return pd.read_csv(io.StringIO(payload["_raw"]))
    if isinstance(payload, dict):
        # Try common JSON list field names
        for k in ("payLoad","payload","rows","data","items","sectionals","benchmarks","results"):
            if k in payload and isinstance(payload[k], list):
                return pd.DataFrame(payload[k])
        # Fallback: one-row dict
        return pd.json_normalize(payload)
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    return pd.DataFrame()

def update_week(days:int=7, force:bool=False) -> None:
    client = PuntingFormClient()
    months = months_covering(days)
    for (year, month) in months:
        mk = month_key(year, month)
        # Fetch meetings once per month and reuse downstream
        meetings_resp = client.get_meetings_month(year, month, force=force)
        meetings = meetings_resp.get("payLoad") or []
        if meetings_resp.get("statusCode", 200) not in (None, 200):
            print(f"Warning: meetings list {mk} returned status {meetings_resp.get('statusCode')} -> {meetings_resp.get('error')}")

        datasets: list[tuple[str, pd.DataFrame]] = []
        if meetings:
            df_meetings = pd.DataFrame(meetings)
            if not df_meetings.empty:
                df_meetings["pf_month"] = mk
                datasets.append(("meetings", df_meetings))

        if FETCH_FORM:
            extracted_frames: list[pd.DataFrame] = []
            for meeting in meetings:
                meeting_id = meeting.get("meetingId")
                if not meeting_id:
                    continue
                meeting_date = meeting.get("meetingDate") or meeting.get("pf_meetingDate")
                track = meeting.get("track")
                if isinstance(track, dict):
                    track_name = track.get("name")
                else:
                    track_name = track

                try:
                    form_df = client.get_form(meeting_id, date_str=meeting_date, force=force)
                except Exception as exc:
                    print(f"Warning: meeting {meeting_id} form fetch failed -> {exc}")
                    continue

                if form_df is None or form_df.empty:
                    continue

                form_df["meeting_date"] = meeting_date
                form_df["track_name"] = track_name
                form_df["pf_month"] = mk
                extracted_frames.append(form_df)

            if extracted_frames:
                df_form = pd.concat(extracted_frames, ignore_index=True)
                df_form["pf_endpoint"] = "form"
                datasets.append(("form", df_form))
                print(f"Form extractions: {sum(len(f) for f in extracted_frames)} runners across {len(extracted_frames)} meetings")
            else:
                print("No form runners extracted for this month")

        if FETCH_BENCHMARKS:
            bench = client.get_benchmarks_month(year, month, force=force, meetings=meetings)
            status = bench.get("statusCode")
            if status not in (None, 200):
                print(f"Warning: benchmarks {mk} returned status {status} -> {bench.get('error')}")
            df_bench = flatten_pf_payload(bench)
            if not df_bench.empty:
                df_bench["pf_month"] = mk
                df_bench["pf_endpoint"] = "benchmarks"
                datasets.append(("benchmarks", df_bench))

        if FETCH_SECTIONALS:
            secs = client.get_sectionals_month_bench(year, month, force=force, meetings=meetings)
            status = secs.get("statusCode")
            if status not in (None, 200):
                print(f"Warning: sectionals {mk} returned status {status} -> {secs.get('error')}")
            df_secs = flatten_pf_payload(secs)
            if not df_secs.empty:
                df_secs["pf_month"] = mk
                df_secs["pf_endpoint"] = "sectionals"
                datasets.append(("sectionals", df_secs))

        out_month_dir = os.path.join(PROC_ROOT, "puntingform", mk)
        ensure_dir(out_month_dir)
        for label, df in datasets:
            df.to_csv(os.path.join(out_month_dir, f"{mk}__{label}.csv"), index=False)

        print(f"Saved PF month {mk} → {out_month_dir} ({', '.join(name for name, _ in datasets) or 'no datasets'})")

if __name__ == "__main__":
    days = int(os.environ.get("PF_UPDATE_DAYS", "7"))
    force = os.environ.get("PF_FORCE", "0") == "1"
    update_week(days=days, force=force)
