import os
import re
import zipfile
from pathlib import Path

import pandas as pd
import numpy as np
from rapidfuzz import process, fuzz

PROJECT_ROOT = Path(__file__).resolve().parent
ZIP_PATH = PROJECT_ROOT / "archive.zip"
PF_BETFAIR_PATH = PROJECT_ROOT / "data" / "processed" / "ml" / "pf_betfair_merged.csv.gz"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ml" / "kaggle_pf_betfair_merged.csv.gz"

JOIN_COLS = ["event_date", "track_name_norm", "horse_name_norm"]


def norm(text):
    if pd.isna(text):
        return pd.NA
    cleaned = re.sub(r"[^\w\s]", "", str(text).lower().strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or pd.NA


def find_column(columns, candidates):
    normalized = {re.sub(r"[^a-z0-9]", "", col.lower()): col for col in columns}
    for candidate in candidates:
        token = re.sub(r"[^a-z0-9]", "", candidate.lower())
        if token in normalized:
            return normalized[token]
    for candidate in candidates:
        token = re.sub(r"[^a-z0-9]", "", candidate.lower())
        for normed, original in normalized.items():
            if token in normed:
                return original
    return None


def load_kaggle_runner_data():
    if not ZIP_PATH.exists():
        raise SystemExit("❌ archive.zip not found in project root")

    with zipfile.ZipFile(ZIP_PATH) as zf:
        field_member = None
        for name in zf.namelist():
            lowered = name.lower()
            if lowered.endswith("field.csv") or ("field" in lowered and lowered.endswith(".csv")):
                field_member = name
                break
        if field_member is None:
            raise SystemExit("❌ runner-level CSV (field.csv) not found inside archive.zip")

        with zf.open(field_member) as fp:
            kaggle_raw = pd.read_csv(fp, low_memory=False)

    col_candidates = {
        "RaceDate": ["race_date", "racedate", "race day", "meeting_date", "event_date", "date", "daycalender", "daycalendar"],
        "Venue": ["venue", "track", "course", "meeting", "location", "trackname"],
        "HorseName": ["horse_name", "horsename", "runner_name", "runner", "name"],
        "RaceDistance": ["race_distance", "distance"],
        "Barrier": ["barrier", "draw", "gate", "horse_number", "horsenumber"],
        "Weight": ["weight", "carried_weight", "carrying_weight", "handicap"],
        "FinishingPosition": ["finishing_position", "position", "place", "finishpos", "row"],
        "StartingPrice": ["starting_price", "sp", "odds", "price", "startingodds", "starting_price1"]
    }

    selected = {}
    for logical, candidates in col_candidates.items():
        column = find_column(kaggle_raw.columns, candidates)
        if column is not None:
            selected[logical] = column

    for required in ("RaceDate", "Venue", "HorseName"):
        if required not in selected:
            raise SystemExit(f"❌ Required Kaggle column '{required}' not found in {field_member}")

    kaggle = kaggle_raw[[selected[col] for col in selected]].copy()
    kaggle = kaggle.rename(columns={selected[col]: col for col in selected})

    kaggle["event_date"] = pd.to_datetime(kaggle["RaceDate"], errors="coerce").dt.strftime("%Y-%m-%d")
    kaggle["track_name_norm"] = kaggle["Venue"].map(norm)
    kaggle["horse_name_norm"] = kaggle["HorseName"].map(norm)

    kaggle["event_date"] = kaggle["event_date"].replace("NaT", pd.NA)
    kaggle_clean = kaggle.dropna(subset=JOIN_COLS).copy()

    rename_map = {col: f"kaggle_{col}" for col in kaggle_clean.columns if col not in JOIN_COLS}
    kaggle_ready = kaggle_clean.rename(columns=rename_map)

    kaggle_ready = kaggle_ready.reset_index(drop=True)
    kaggle_ready["kaggle_index"] = kaggle_ready.index

    kaggle_added_cols = [rename_map[col] for col in rename_map if col not in JOIN_COLS]

    return kaggle_ready, kaggle_added_cols


def load_pf_betfair():
    if not PF_BETFAIR_PATH.exists():
        raise SystemExit("❌ Punting Form + Betfair merged file not found")

    pf_df = pd.read_csv(PF_BETFAIR_PATH, low_memory=False)

    pf_df["event_date"] = pd.to_datetime(pf_df.get("event_date"), errors="coerce").dt.strftime("%Y-%m-%d")
    pf_df["event_date"] = pf_df["event_date"].replace("NaT", pd.NA)

    track_col = "track_name_norm" if "track_name_norm" in pf_df.columns else find_column(pf_df.columns, [
        "track_name", "venue", "track", "course", "meeting"
    ])
    horse_col = "horse_name_norm" if "horse_name_norm" in pf_df.columns else find_column(pf_df.columns, [
        "runner_name", "horse", "name"
    ])

    if track_col is None or horse_col is None:
        raise SystemExit("❌ Could not locate track/horse columns in pf_betfair_merged.csv.gz")

    pf_df["track_name_norm"] = pf_df[track_col].map(norm)
    pf_df["horse_name_norm"] = pf_df[horse_col].map(norm)

    pf_ready = pf_df.dropna(subset=JOIN_COLS).copy()

    rename_map = {col: f"pf_{col}" for col in pf_ready.columns if col not in JOIN_COLS}
    pf_ready = pf_ready.rename(columns=rename_map)

    pf_ready = pf_ready.reset_index(drop=True)
    pf_ready["pf_index"] = pf_ready.index

    return pf_ready


def fuzzy_match(kaggle_unmatched, pf_unmatched):
    matches = []
    if kaggle_unmatched.empty or pf_unmatched.empty:
        return matches

    combos_by_date = {}
    for date, subset in pf_unmatched.groupby("event_date"):
        combos_by_date[date] = {row["pf_index"]: f"{row['track_name_norm']}||{row['horse_name_norm']}" for _, row in subset.iterrows()}

    for _, row in kaggle_unmatched.iterrows():
        date = row["event_date"]
        if pd.isna(date) or date not in combos_by_date:
            continue
        track = row["track_name_norm"]
        horse = row["horse_name_norm"]
        if pd.isna(track) or pd.isna(horse):
            continue
        query = f"{track}||{horse}"
        choices = combos_by_date[date]
        if not choices:
            continue
        value, score, pf_index = process.extractOne(query, choices, scorer=fuzz.token_sort_ratio)
        if score >= 90:
            matches.append((row["kaggle_index"], pf_index, score))
            del choices[pf_index]

    return matches


def main():
    kaggle_ready, kaggle_added_cols = load_kaggle_runner_data()
    pf_ready = load_pf_betfair()

    kaggle_count = len(kaggle_ready)
    pf_count = len(pf_ready)

    initial_merge = kaggle_ready.merge(pf_ready, on=JOIN_COLS, how="inner")
    matched_kaggle = set(initial_merge.get("kaggle_index", []))
    matched_pf = set(initial_merge.get("pf_index", []))

    initial_join_rows = len(initial_merge)
    join_rate = (initial_join_rows / kaggle_count) if kaggle_count else 0

    kaggle_unmatched = kaggle_ready[~kaggle_ready["kaggle_index"].isin(matched_kaggle)]
    pf_unmatched = pf_ready[~pf_ready["pf_index"].isin(matched_pf)]

    fuzzy_matches = []
    if join_rate < 0.7:
        fuzzy_matches = fuzzy_match(kaggle_unmatched, pf_unmatched)

    if fuzzy_matches:
        fuzzy_df = pd.DataFrame(fuzzy_matches, columns=["kaggle_index", "pf_index", "match_score"])
        fuzzy_merge = fuzzy_df.merge(kaggle_ready, on="kaggle_index").merge(pf_ready, on="pf_index")
        combined = pd.concat([initial_merge, fuzzy_merge.drop(columns=["match_score"])], ignore_index=True)
    else:
        combined = initial_merge

    combined = combined.sort_values("kaggle_index").drop_duplicates(subset=["kaggle_index"], keep="first")
    final_rows = len(combined)
    final_join_rate = (final_rows / kaggle_count) if kaggle_count else 0

    combined = combined.drop(columns=[c for c in ["kaggle_index", "pf_index"] if c in combined.columns])
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False, compression="gzip")

    print(f"Kaggle rows: {kaggle_count}")
    print(f"PF+Betfair rows: {pf_count}")
    print(f"Joined rows: {final_rows}")
    print(f"Join rate: {final_join_rate * 100:.2f}%")
    print(f"Kaggle columns added: {', '.join(kaggle_added_cols) if kaggle_added_cols else 'None'}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
