# merge_pf_to_betfair_bulk.py — merge PF Starter (form) with Betfair for all months
import os, re, glob, json, ast, numpy as np, pandas as pd

def norm(s):
    if pd.isna(s): return s
    s = str(s).lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

PROC = os.path.join("data","processed","puntingform")
OUT  = os.path.join("data","processed","ml","pf_betfair_merged.csv.gz")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# 1) Load all PF form CSVs (Starter)
pf_files = sorted(glob.glob(os.path.join(PROC, "*", "*__form.csv")))
if not pf_files:
    raise SystemExit("❌ No PF form CSVs found; run backfill_pf_starter.py first.")

pf = pd.concat((pd.read_csv(p, low_memory=False) for p in pf_files), ignore_index=True)

# detect key columns from PF
def pick(cols, patterns):
    for patt in patterns:
        for c in cols:
            if re.search(patt, c, flags=re.I):
                return c
    return None

date_col  = pick(pf.columns, [
    r"pf_meeting_date",
    r"pf_meetingdate",
    r"local_meeting_date",
    r"meetingdate",
    r"daycal",
    r"race_date",
    r"racedate",
    r"event_date",
    r"date$",
])
venue_col = pick(pf.columns, [
    r"pf_meetingname",
    r"meetingname",
    r"venue",
    r"^track$",
    r"course",
])
horse_col = pick(pf.columns, [r"horse.?name", r"runner.?name", r"name"])
dist_col  = pick(pf.columns, [r"race.?distance", r"distance", r"metres", r"meters"])

def extract_track_from_forms(raw):
    if not isinstance(raw, (str, list, dict)):
        return None
    data = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            try:
                data = ast.literal_eval(raw)
            except Exception:
                return None
    if isinstance(data, dict):
        data = [data]
    for item in data or []:
        if not isinstance(item, dict):
            continue
        track = item.get("track")
        if isinstance(track, dict):
            name = track.get("name") or track.get("meeting")
            if name:
                return name
    return None

if not (date_col and horse_col):
    raise SystemExit(f"❌ PF columns not found (date/horse). Found date={date_col}, horse={horse_col}")

if not venue_col and "forms" in pf.columns:
    pf["__track_from_forms"] = pf["forms"].apply(extract_track_from_forms)
    venue_col = "__track_from_forms"

if not venue_col:
    raise SystemExit(f"❌ PF track column not found. Evaluated columns: {list(pf.columns)[:10]}")

pf["event_date"] = pd.to_datetime(pf[date_col], errors="coerce")
pf["track_name_norm"] = pf[venue_col].map(norm)
if "forms" in pf.columns:
    pf["_track_from_forms_norm"] = pf["forms"].apply(extract_track_from_forms).map(norm)
    pf["track_name_norm"] = pf["track_name_norm"].fillna(pf["_track_from_forms_norm"])
    pf.drop(columns=["_track_from_forms_norm"], inplace=True)
pf["horse_name_norm"] = pf[horse_col].map(norm)
if dist_col:
    pf["distance"] = pd.to_numeric(pf[dist_col], errors="coerce")

pf_key = pf[["event_date","track_name_norm","horse_name_norm"]].copy()
pf_keep = [c for c in pf.columns if c not in pf_key.columns]
pf_small = pd.concat([pf_key, pf[pf_keep]], axis=1)
pf_small["event_date"] = pd.to_datetime(pf_small["event_date"], errors="coerce").dt.normalize()

# 2) Load Betfair yearly files
years = [y for y in (2023,2024,2025) if os.path.exists(f"betfair_all_raw_{y}.csv.gz")]
if not years:
    raise SystemExit("❌ No Betfair yearly files present in project root.")

frames=[]
for y in years:
    bf = pd.read_csv(f"betfair_all_raw_{y}.csv.gz", low_memory=False)

    def find(cols, t):
        T = re.sub(r"[^a-z0-9]", "", t.lower())
        for c in cols:
            if re.sub(r"[^a-z0-9]", "", c.lower()) == T: return c
        for c in cols:
            if T in re.sub(r"[^a-z0-9]", "", c.lower()): return c
        return None

    mkt_time  = find(bf.columns, "market_start_time") or find(bf.columns, "scheduled_race_time") or find(bf.columns, "opendate") or "event_date"
    ev_name   = find(bf.columns, "event_name") or find(bf.columns, "track") or "event_name"
    run_name  = find(bf.columns, "selection_name") or find(bf.columns, "runner_name") or "runner_name"
    market_id = find(bf.columns, "market_id") or "market_id"
    sel_id    = find(bf.columns, "selection_id") or "selection_id"
    lpt       = find(bf.columns, "last_price_traded") or "last_price_traded"
    bsp       = find(bf.columns, "bsp") or find(bf.columns, "startingprice1")

    # event_date (AU)
    if mkt_time in bf.columns and mkt_time != "event_date":
        dt = pd.to_datetime(bf[mkt_time], errors="coerce", utc=True)
        try:
            bf["event_date"] = dt.dt.tz_convert("Australia/Sydney").dt.tz_localize(None).dt.normalize()
        except Exception:
            bf["event_date"] = pd.to_datetime(dt, errors="coerce").dt.normalize()

    bf["track_name_norm"] = bf[ev_name].map(norm) if ev_name in bf.columns else np.nan
    if "track" in bf.columns:
        bf["track_name_norm"] = bf["track_name_norm"].fillna(bf["track"].map(norm))
    bf["horse_name_norm"] = bf[run_name].map(norm) if run_name in bf.columns else np.nan
    # choose odds (bsp preferred)
    bf["odds"] = pd.to_numeric(bf[bsp], errors="coerce") if bsp in bf.columns else pd.to_numeric(bf[lpt], errors="coerce")

    frames.append(bf[["event_date","track_name_norm","horse_name_norm","odds",str(market_id),str(sel_id)]])

betfair = pd.concat(frames, ignore_index=True)
betfair["event_date"] = pd.to_datetime(betfair["event_date"], errors="coerce").dt.normalize()

# 3) Strict join (can upgrade to fuzzy/time window later)
merged = pd.merge(
    pf_small,
    betfair,
    on=["event_date","track_name_norm","horse_name_norm"],
    how="inner",
    suffixes=("_pf","_bf")
).drop_duplicates()

merged.to_csv(OUT, index=False, compression="gzip")
print("✅ Merged PF+Betfair:", OUT, "rows:", len(merged))
