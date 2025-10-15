# build_horse_ratings_from_kaggle.py
# Pretrain horse ratings from Kaggle field.csv inside archive.zip (no overlap with 2023-2025 needed).
import os, re, zipfile, io, pandas as pd, numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
import lightgbm as lgb

ARCH = "archive.zip"
OUT_PATH = os.path.join("artifacts", "horse_ratings_2021.csv")
os.makedirs("artifacts", exist_ok=True)

def norm(s):
    if pd.isna(s): return s
    s = str(s).lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

# 1) Find a runner-level Kaggle CSV (usually field.csv) inside archive.zip
with zipfile.ZipFile(ARCH, "r") as z:
    candidates = [i for i in z.infolist() if i.filename.lower().endswith(".csv")]
    file_hit = None
    need_any = {"Venue","HorseName"}  # minimal schema for this script
    for info in candidates:
        try:
            with z.open(info.filename) as f:
                head = pd.read_csv(f, nrows=1, low_memory=False)
            cols = set(map(str, head.columns))
            if need_any.issubset(cols):
                file_hit = info.filename
                break
        except Exception:
            pass
    if not file_hit:
        raise SystemExit("❌ Could not locate Kaggle runner-level CSV (need Venue, HorseName).")

    with z.open(file_hit) as f:
        kg = pd.read_csv(f, low_memory=False)

# 2) Column detection (Starter-friendly names you shared earlier)
def pick(cols, patterns):
    cl = [c.lower() for c in cols]
    for patt in patterns:
        for i,c in enumerate(cl):
            if re.search(patt, c):
                return cols[i]
    return None

date_col   = pick(kg.columns, [r"daycalender|daycalendar|date|meetingdate|racedate"])
venue_col  = pick(kg.columns, [r"venue|track|course|meetingname"])
horse_col  = pick(kg.columns, [r"horse.?name|runner.?name|name"])
dist_col   = pick(kg.columns, [r"race.?distance|distance|metres|meters"])
bar_col    = pick(kg.columns, [r"barrier|draw|gate"])
wt_col     = pick(kg.columns, [r"weight|carried"])
pos_col    = pick(kg.columns, [r"^place$|finish|position|result"])
sp_col     = pick(kg.columns, [r"starting.?price|sp|bsp|odds"])

if not (venue_col and horse_col and date_col):
    raise SystemExit(f"❌ Missing core columns. Found date={date_col}, venue={venue_col}, horse={horse_col}")

# 3) Clean & restrict to <= 2021 to avoid leakage
kg["event_date"] = pd.to_datetime(kg[date_col], errors="coerce")
kg = kg[kg["event_date"].notna()]
kg_year = kg["event_date"].dt.year
kg = kg[kg_year <= 2021].copy()
if len(kg) == 0:
    raise SystemExit("❌ No Kaggle rows ≤ 2021 after filtering.")

kg["horse_name_norm"] = kg[horse_col].map(norm)

# 4) Create simple targets & features
# Target: win (place==1) if available; otherwise use finishing position proxy
if pos_col and pos_col in kg.columns:
    y = (kg[pos_col].astype(str).str.strip().str.upper().isin(["1","1.0","WIN","WON"])).astype(int)
else:
    # fall back to inverse SP if no finishing pos; use >median as 'win' proxy
    sp = pd.to_numeric(kg[sp_col], errors="coerce") if sp_col else pd.Series(np.nan, index=kg.index)
    y = (sp.rank(pct=True) < 0.1).astype(int)  # top-10% by price as pseudo-winners

# Base features
X = pd.DataFrame(index=kg.index)
if dist_col: X["distance"] = pd.to_numeric(kg[dist_col], errors="coerce")
if bar_col:  X["barrier"]  = pd.to_numeric(kg[bar_col], errors="coerce")
if wt_col:   X["weight"]   = pd.to_numeric(kg[wt_col], errors="coerce")

# Rolling horse stats (lifetime/ recent)
kg = kg.sort_values(["horse_name_norm","event_date"])
grp = kg.groupby("horse_name_norm")
# Lifetime counts
X["runs_life"]  = grp.cumcount() + 1
# Rolling win/placings if we have a target; else zeros
if isinstance(y, pd.Series):
    wins_hist = grp[y.name].transform(lambda s: s.shift().rolling(9999, min_periods=1).sum())
else:
    wins_hist = 0.0
X["wins_life"] = wins_hist
X["win_rate_life"] = wins_hist / X["runs_life"]

# 5) Train LightGBM on historic data (simple, robust)
mask = y.notna() & X.notna().any(axis=1)
Xtr, Xte, ytr, yte = train_test_split(X[mask], y[mask], test_size=0.2, random_state=42, stratify=y[mask])
model = lgb.LGBMClassifier(
    objective="binary",
    n_estimators=500,
    learning_rate=0.03,
    num_leaves=63,
    subsample=0.9,
    colsample_bytree=0.8,
    random_state=42
)
model.fit(Xtr, ytr)
try:
    auc = roc_auc_score(yte, model.predict_proba(Xte)[:,1])
except Exception:
    auc = float("nan")
print("AUC (historic proxy):", auc)

# 6) Produce per-horse rating = smoothed win_rate_life blended with model avg prob
probs = pd.Series(model.predict_proba(X)[:,1], index=X.index)
rating_df = pd.DataFrame({
    "horse_name_norm": kg["horse_name_norm"],
    "last_event_date": kg["event_date"],
    "runs_life": X["runs_life"],
    "win_rate_life": X["win_rate_life"].fillna(0.0),
    "model_prob": probs.fillna(probs.median()),
})
# Aggregate to per-horse
agg = rating_df.groupby("horse_name_norm").agg(
    last_event_date=("last_event_date","max"),
    runs_life=("runs_life","max"),
    win_rate_life=("win_rate_life","max"),
    model_prob=("model_prob","mean")
).reset_index()
# Blend rating
agg["horse_rating_2021"] = 0.6*agg["model_prob"] + 0.4*agg["win_rate_life"]

agg.sort_values("horse_rating_2021", ascending=False).to_csv(OUT_PATH, index=False)
print("Saved ratings:", OUT_PATH, "rows:", len(agg))
