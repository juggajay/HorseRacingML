# unify_betfair_years.py — build yearly Betfair files from monthly ANZ_Thoroughbreds_YYYY_MM.csv
import os, re, glob
import pandas as pd
import numpy as np

def to_snake(name: str) -> str:
    n = re.sub(r"[\s\-]+", "_", name.strip())
    n = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", n)
    n = n.replace("__", "_").lower()
    return n

def find_col(cols, target):
    t = re.sub(r"[^a-z0-9]", "", target.lower())
    for c in cols:
        if re.sub(r"[^a-z0-9]", "", c.lower()) == t:
            return c
    for c in cols:
        if t in re.sub(r"[^a-z0-9]", "", c.lower()):
            return c
    return None

def norm_txt(s):
    if pd.isna(s):
        return s
    s = str(s).lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def load_month(path):
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception:
        df = pd.read_csv(path, low_memory=False, encoding="latin1")
    df.columns = [to_snake(c) for c in df.columns]
    cols = list(df.columns)
    col_market_id = find_col(cols, "market_id") or "market_id"
    col_selection_id = find_col(cols, "selection_id") or "selection_id"
    col_runner_name = find_col(cols, "runner_name") or "runner_name"
    col_event_name = find_col(cols, "event_name") or "event_name"
    col_track = find_col(cols, "track") or col_event_name
    col_mkt_start = find_col(cols, "market_start_time") or "market_start_time"
    for need in [col_market_id, col_selection_id, col_runner_name, col_event_name, col_mkt_start, col_track]:
        if need not in df.columns:
            df[need] = np.nan
    dt = pd.to_datetime(df[col_mkt_start], errors="coerce", utc=True)
    try:
        df["event_date"] = dt.dt.tz_convert("Australia/Sydney").dt.date
    except Exception:
        df["event_date"] = pd.to_datetime(dt).dt.date
    track_source = df[col_track]
    df["track_name_norm"] = track_source.map(norm_txt)
    df["horse_name_norm"] = df[col_runner_name].map(norm_txt)
    df["race_id"] = df[col_market_id].astype("string")
    df["runner_id"] = df[col_market_id].astype("string") + "_" + df[col_selection_id].astype("string")
    return df

def build_year(files, year, out_dir="."):
    parts = [load_month(f) for f in sorted(files)]
    if not parts:
        return None
    full = pd.concat(parts, ignore_index=True)
    out_path = os.path.join(out_dir, f"betfair_all_raw_{year}.csv.gz")
    full.to_csv(out_path, index=False, compression="gzip")
    full_dates = pd.to_datetime(full["event_date"], errors="coerce")
    return (
        out_path,
        len(full),
        full["race_id"].nunique(),
        full["runner_id"].nunique(),
        str(full_dates.min()),
        str(full_dates.max()),
    )

if __name__ == "__main__":
    roots = os.environ.get("MONTH_SRC", "").split(";")
    roots = [r for r in roots if r] or ["."]
    files_by_year = {}
    pattern = re.compile(r"ANZ_Thoroughbreds_(\d{4})_(\d{2})\.csv$", re.IGNORECASE)
    for root in roots:
        for p in glob.glob(os.path.join(root, "**", "ANZ_Thoroughbreds_*.csv"), recursive=True):
            m = pattern.search(os.path.basename(p))
            if m:
                year = int(m.group(1))
                files_by_year.setdefault(year, []).append(p)
    if not files_by_year:
        print("❌ No monthly files found via MONTH_SRC roots:", roots)
        raise SystemExit(1)
    results = []
    for year, files in sorted(files_by_year.items()):
        out = build_year(files, year, ".")
        if out:
            out_path, nrows, nmkts, nruns, dmin, dmax = out
            results.append({
                "year": year,
                "path": out_path,
                "rows": nrows,
                "unique_markets": nmkts,
                "unique_runners": nruns,
                "date_min": dmin,
                "date_max": dmax,
            })
    import json
    print(json.dumps({"built": results}, indent=2))
