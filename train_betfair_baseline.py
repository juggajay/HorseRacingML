# train_betfair_baseline.py — monthly walk-forward on Betfair-only features with POT/ROI
import os, re, numpy as np, pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, log_loss
import lightgbm as lgb

IN_PATH = r"data/processed/ml/betfair_features.csv.gz"
OUT_DIR = r"artifacts"
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(IN_PATH, low_memory=False)
df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
df = df[df["event_date"].notna()].copy()

# keep numeric features
X = df[["odds","implied_prob","matched","odds_rank","overround"]].copy()
y = df["target_win"].astype(int)
dates = df["event_date"]
odds = df["odds"]

months = sorted(dates.dt.to_period("M").astype(str).unique())
print("Months range:", months[:3], "...", months[-3:], "total:", len(months))

records = []
feat_imp = None

for i in range(6, len(months)):  # need 6 months history before first test
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

    # calibration
    calib = CalibratedClassifierCV(model, method="isotonic", cv=3)
    calib.fit(Xtr, ytr)
    p = pd.Series(calib.predict_proba(Xte)[:,1], index=Xte.index)

    # metrics
    try: brier = brier_score_loss(yte, p)
    except: brier = np.nan
    try: ll = log_loss(yte, np.vstack([1-p, p]).T)
    except: ll = np.nan

    # value rule: bet when p > 1/odds
    edge  = p - (1.0/odds_te.replace(0,np.nan))
    stake = (edge > 0).astype(float)   # 1u per positive edge
    ret   = (yte*odds_te - 1.0) * stake
    pot   = (ret.sum()/stake.sum()) if stake.sum()>0 else np.nan
    n_bet = int(stake.sum())

    if feat_imp is None and hasattr(model, "feature_importances_"):
        feat_imp = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)

    records.append({
        "test_month": te_month,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "bets": n_bet,
        "pot": float(pot) if pot==pot else None,
        "brier": float(brier) if brier==brier else None,
        "logloss": float(ll) if ll==ll else None
    })

metrics = pd.DataFrame(records)
metrics.to_csv(os.path.join(OUT_DIR, "betfair_baseline_metrics.csv"), index=False)
if isinstance(feat_imp, pd.Series):
    feat_imp.to_csv(os.path.join(OUT_DIR, "betfair_feature_importance.csv"))

print("Saved:")
print(" -", os.path.join(OUT_DIR, "betfair_baseline_metrics.csv"))
if isinstance(feat_imp, pd.Series):
    print(" -", os.path.join(OUT_DIR, "betfair_feature_importance.csv"))
print(metrics.tail(8))
