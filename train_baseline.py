import os, re, json, numpy as np, pandas as pd
from datetime import datetime
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.model_selection import train_test_split
import lightgbm as lgb

IN_PATH  = r"data/processed/ml/pf_features.csv.gz"
OUT_DIR  = r"artifacts"
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(IN_PATH, low_memory=False)
print("Rows:", len(df), "Cols:", len(df.columns))

# ---- pick columns ----
def pick(cols, patt_list):
    for patt in patt_list:
        for c in cols:
            if re.search(patt, c, flags=re.I): return c
    return None

date_col  = pick(df.columns, [r"^event_date$","meetingdate","daycal","date"])
target    = "target_win"
odds_col  = pick(df.columns, [r"^odds$","last_price_traded","bsp","startingprice"])
priors    = ["horse_rating_2021","runs_life","win_rate_life","model_prob"]

if date_col is None:
    raise SystemExit("No date column detected for time splits.")

# ---- prep data ----
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
df = df[df[date_col].notna()].copy()

# numeric features only; drop leak-prone IDs/text columns
drop_like = ["name","comment","trainer","driver","jockey","sire","_horse","selection_id","market_id"]
X = df.select_dtypes(include=[np.number]).copy()
for c in list(df.columns):
    if any(k in c.lower() for k in drop_like):
        if c in X.columns: X.drop(columns=[c], inplace=True, errors="ignore")

# keep target and odds
y   = df[target].astype(int)
odds= pd.to_numeric(df[odds_col], errors="coerce") if odds_col else pd.Series(np.nan, index=df.index)
dates = df[date_col]

# ---- month keys ----
def month_key(d): return f"{d.year}-{d.month:02d}"
months = sorted(dates.dt.to_period("M").astype(str).unique())
print("Months:", months)

# ---- walk-forward ----
records = []
feat_imp = None

for i in range(6, len(months)):  # start after 6 months of history
    tr_months = months[:i]
    te_month  = months[i]

    tr_idx = dates.dt.to_period("M").astype(str).isin(tr_months)
    te_idx = dates.dt.to_period("M").astype(str).eq(te_month)

    Xtr, ytr = X[tr_idx], y[tr_idx]
    Xte, yte = X[te_idx], y[te_idx]
    odds_te  = odds[te_idx]

    if len(Xtr)==0 or len(Xte)==0: 
        continue

    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=600,
        learning_rate=0.03,
        num_leaves=63,
        subsample=0.9,
        colsample_bytree=0.8,
        random_state=42
    )
    model.fit(Xtr, ytr)

    # calibrate
    calib = CalibratedClassifierCV(model, method="isotonic", cv=3)
    calib.fit(Xtr, ytr)
    p = pd.Series(calib.predict_proba(Xte)[:,1], index=Xte.index)

    # metrics
    try: brier = brier_score_loss(yte, p)
    except: brier = np.nan
    try: ll = log_loss(yte, np.vstack([1-p, p]).T)
    except: ll = np.nan

    # simple value betting: bet when p > 1/odds
    edge = p - (1.0/odds_te.replace(0,np.nan))
    stake = (edge > 0).astype(float)  # flat 1u stake
    ret = (yte*odds_te - 1.0) * stake
    pot = (ret.sum()/stake.sum()) if stake.sum()>0 else np.nan
    n_bets = int(stake.sum())

    # feature importance (first split only)
    if feat_imp is None and hasattr(model, "feature_importances_"):
        feat_imp = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False).head(40)

    records.append({
        "test_month": te_month,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "bets": n_bets,
        "brier": float(brier) if brier==brier else None,
        "logloss": float(ll) if ll==ll else None,
        "pot": float(pot) if pot==pot else None
    })

# save artifacts
metrics = pd.DataFrame(records)
metrics.to_csv(os.path.join(OUT_DIR, "baseline_walkforward_metrics.csv"), index=False)
if isinstance(feat_imp, pd.Series):
    feat_imp.to_csv(os.path.join(OUT_DIR, "baseline_feature_importance.csv"))

print("Saved artifacts:")
print(" -", os.path.join(OUT_DIR, "baseline_walkforward_metrics.csv"))
if isinstance(feat_imp, pd.Series):
    print(" -", os.path.join(OUT_DIR, "baseline_feature_importance.csv"))
print(metrics.tail(5))
