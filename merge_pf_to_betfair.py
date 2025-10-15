# merge_pf_to_betfair.py — PF Starter merge (no raceNumber)

import os
import re
import glob
import ast
from pathlib import Path

import pandas as pd

def norm(text):
    if pd.isna(text):
        return pd.NA
    cleaned = re.sub(r"[^\w\s]", "", str(text).lower().strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or pd.NA

def pick_col(columns, candidates):
    lowered = [c.lower() for c in columns]
    for pattern in candidates:
        for idx, col in enumerate(lowered):
            if re.fullmatch(pattern, col) or re.search(pattern, col):
                return columns[idx]
    return None

def parse_track(value):
    if isinstance(value, dict):
        return value.get("name")
    if isinstance(value, str):
        try:
            data = ast.literal_eval(value)
            if isinstance(data, dict):
                return data.get("name")
        except Exception:
            pass
    return None

def load_pf_form():
    pf_files = sorted(glob.glob(os.path.join("data", "processed", "puntingform", "*", "*__form.csv")))
    if not pf_files:
        raise SystemExit("❌ No PF form CSVs found under data/processed/puntingform/. Run update_weekly_puntingform.py first.")
    pf = pd.concat((pd.read_csv(path, low_memory=False) for path in pf_files), ignore_index=True)
    return pf

def load_pf_meetings():
    meeting_files = sorted(glob.glob(os.path.join("data", "processed", "puntingform", "*", "*__meetings.csv")))
    if not meeting_files:
        raise SystemExit("❌ PF meetings CSVs missing. Ensure update_weekly_puntingform.py generated meetings output.")
    meetings = pd.concat((pd.read_csv(path, low_memory=False) for path in meeting_files), ignore_index=True)
    meetings["meetingId"] = pd.to_numeric(meetings["meetingId"], errors="coerce").astype("Int64")
    meetings["event_date_meeting"] = pd.to_datetime(meetings["meetingDate"], errors="coerce").dt.strftime("%Y-%m-%d")
    meetings["track_name_meeting"] = meetings["track"].apply(parse_track)
    meetings["track_name_norm_meeting"] = meetings["track_name_meeting"].map(norm)
    return meetings[["meetingId", "event_date_meeting", "track_name_meeting", "track_name_norm_meeting"]]

def prepare_pf(pf, meetings):
    date_col = pick_col(pf.columns, [r"pf_meetingdate", r"meeting.*date", r"daycalender", r"daycalendar", r"start.*time", r"date"])
    horse_col = pick_col(pf.columns, [r"^name$", r"horse.?name", r"runner.?name", r"horse", r"runner"])
    meeting_col = pick_col(pf.columns, [r"pf_meetingid", r"meetingid", r"meeting_id"])

    if not horse_col or not meeting_col or not date_col:
        raise SystemExit(f"❌ Unable to identify PF columns. Found -> date: {date_col}, meeting: {meeting_col}, horse: {horse_col}")

    pf = pf.copy()
    pf[meeting_col] = pd.to_numeric(pf[meeting_col], errors="coerce").astype("Int64")
    pf["horse_name_norm"] = pf[horse_col].map(norm)
    pf["event_date_pf"] = pd.to_datetime(pf[date_col], errors="coerce").dt.strftime("%Y-%m-%d")

    pf_merged = pf.merge(meetings, left_on=meeting_col, right_on="meetingId", how="left")
    pf_merged["event_date"] = pf_merged["event_date_meeting"].fillna(pf_merged["event_date_pf"])
    pf_merged["track_name_norm"] = pf_merged["track_name_norm_meeting"]
    if "trackRecord" in pf_merged.columns:
        pf_merged["track_name_norm"] = pf_merged["track_name_norm"].fillna(pf_merged["trackRecord"].map(norm))
    pf_merged["track_name_norm"] = pf_merged["track_name_norm"].fillna(pd.NA)

    keep_cols = [c for c in pf_merged.columns if c not in {"event_date_pf", "event_date_meeting", "track_name_norm_meeting", "track_name_meeting"}]
    pf_small = pf_merged[["event_date", "track_name_norm", "horse_name_norm"] + [c for c in keep_cols if c not in {"event_date", "track_name_norm", "horse_name_norm"}]].copy()

    pf_small["event_date"] = pf_small["event_date"].astype("string")
    pf_small["track_name_norm"] = pf_small["track_name_norm"].astype("string")
    pf_small["horse_name_norm"] = pf_small["horse_name_norm"].astype("string")

    return pf_small, {"date": date_col, "horse": horse_col, "meeting": meeting_col}

def load_betfair_years():
    enriched_dir = Path("data/processed/betfair_enriched")
    enriched_files = sorted(enriched_dir.glob("betfair_all_raw_enriched_*.csv.gz"))

    if enriched_files:
        year_paths = enriched_files
    else:
        year_paths = sorted(Path(".").glob("betfair_all_raw_*.csv.gz"))

    if not year_paths:
        raise SystemExit("❌ Betfair yearly files not found. Run unify_betfair_years.py or place betfair_all_raw_*.csv.gz in project root.")

    def find_column(df, candidates):
        columns = list(df.columns)
        normalized = {re.sub(r"[^a-z0-9]", "", col.lower()): col for col in columns}
        for candidate in candidates:
            token = re.sub(r"[^a-z0-9]", "", candidate.lower())
            if token in normalized:
                col = normalized[token]
                series = df[col]
                if getattr(series, "notna", None) is None or series.notna().any():
                    return col
        for candidate in candidates:
            token = re.sub(r"[^a-z0-9]", "", candidate.lower())
            for normed, original in normalized.items():
                if token in normed:
                    series = df[original]
                    if getattr(series, "notna", None) is None or series.notna().any():
                        return original
        return None

    frames = []
    column_usage = []
    for path in year_paths:
        df = pd.read_csv(path, low_memory=False)
        mkt_start = find_column(df, ["market_start_time", "marketstarttime", "scheduled_race_time", "local_meeting_date"])
        event_col = find_column(df, ["event_name", "track", "venue", "win_market_name", "market_name"])
        runner_col = find_column(df, ["runner_name", "selection_name", "runner", "horse_name", "selection"])

        if not event_col or not runner_col:
            raise SystemExit(f"❌ Could not locate event/runner columns in {path}")

        if "event_date_merge" in df.columns:
            df["event_date"] = pd.to_datetime(df["event_date_merge"], errors="coerce").dt.strftime("%Y-%m-%d")
        elif mkt_start and mkt_start in df.columns:
            dt = pd.to_datetime(df[mkt_start], errors="coerce", utc=True)
            try:
                df["event_date"] = dt.dt.tz_convert("Australia/Sydney").dt.strftime("%Y-%m-%d")
            except Exception:
                df["event_date"] = pd.to_datetime(dt).dt.strftime("%Y-%m-%d")
        elif "event_date" in df.columns:
            df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        else:
            raise SystemExit(f"❌ {path}: missing market_start_time or event_date column")

        df["track_name_norm"] = df[event_col].map(norm)
        df["horse_name_norm"] = df[runner_col].map(norm)
        frames.append(df[["event_date", "track_name_norm", "horse_name_norm"] + [c for c in df.columns if c not in {"event_date", "track_name_norm", "horse_name_norm"}]])
        column_usage.append({"file": str(path), "event": event_col, "runner": runner_col, "time": mkt_start or "event_date_merge"})

    betfair = pd.concat(frames, ignore_index=True)
    betfair["event_date"] = betfair["event_date"].astype("string")
    betfair["track_name_norm"] = betfair["track_name_norm"].astype("string")
    betfair["horse_name_norm"] = betfair["horse_name_norm"].astype("string")
    return betfair, [str(p) for p in year_paths], column_usage


def main():
    pf = load_pf_form()
    meetings = load_pf_meetings()
    pf_small, pf_meta = prepare_pf(pf, meetings)
    betfair, year_files, column_usage = load_betfair_years()

    merged = pd.merge(
        pf_small,
        betfair,
        on=["event_date", "track_name_norm", "horse_name_norm"],
        how="inner",
        suffixes=("_pf", "_bf"),
    ).drop_duplicates()

    os.makedirs(os.path.join("data", "processed", "ml"), exist_ok=True)
    out_path = os.path.join("data", "processed", "ml", "pf_betfair_merged.csv.gz")
    merged.to_csv(out_path, index=False, compression="gzip")

    print("✅ Merge complete")
    print("Rows merged:", len(merged))
    print("Saved:", out_path)
    print("PF mappings -> date:", pf_meta["date"], "| meeting:", pf_meta["meeting"], "| horse:", pf_meta["horse"])
    print("Betfair files used:", ", ".join(year_files))
    for info in column_usage:
        print("  -", info)


if __name__ == "__main__":
    main()
