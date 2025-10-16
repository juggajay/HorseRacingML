"""Train PF-enhanced LightGBM model and log betting metrics."""
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import log_loss, roc_auc_score

from feature_engineering import engineer_all_features, get_feature_columns, print_feature_summary
from services.api.pf_schema_loader import load_pf_dataset

DATA_PATH = Path("data/processed/ml/betfair_kash_top5.csv.gz")
ARTIFACT_DIR = Path("artifacts")
ARTIFACT_DIR.mkdir(exist_ok=True)
MODEL_DIR = ARTIFACT_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

print("=" * 70)
print("TRAINING MODEL WITH PF FEATURES")
print("=" * 70)

print("1. Loading data...")
df_raw = load_pf_dataset()
source = "pf_schema"
if df_raw is None or df_raw.empty:
    if not DATA_PATH.exists():
        raise SystemExit(f"❌ Data not found: {DATA_PATH}")
    df_raw = pd.read_csv(DATA_PATH)
    source = DATA_PATH.name
print(f"   Source: {source}")
pf_fallback_cols = [
    "pf_score",
    "neural_rating",
    "time_rating",
    "early_time_rating",
    "late_sectional_rating",
    "weight_class_rating",
    "combined_weight_time",
    "pf_ai_rank",
    "pf_ai_score",
    "pf_ai_price",
]
for col in pf_fallback_cols:
    if col not in df_raw.columns:
        df_raw[col] = np.nan
print(f"   Rows: {len(df_raw)}")

print("\n2. Engineering features...")
df = engineer_all_features(df_raw)

feature_cols = [col for col in get_feature_columns() if col in df.columns]
print(f"   Features available: {len(feature_cols)}")
print_feature_summary(df, feature_cols)

print("\n3. Preparing dataset...")
# Target based on Betfair win_result column
if "win_result" in df.columns:
    target = df["win_result"].astype(str).str.lower().eq("winner").astype(int)
else:
    raise SystemExit("❌ win_result column missing; cannot derive target")

df = df.copy()
df["won"] = target

rows_with_target = df["won"].notna().sum()
print(f"   Rows with target: {rows_with_target}")

print("\n4. Temporal train/test split...")
df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
df = df.sort_values("event_date").reset_index(drop=True)

split_date = df["event_date"].quantile(0.8)
print(f"   Split date: {split_date.date() if pd.notna(split_date) else 'N/A'}")

train_mask = df["event_date"] < split_date
test_mask = df["event_date"] >= split_date

X = df[feature_cols]
y = df["won"]

X_train = X[train_mask]
y_train = y[train_mask]
X_test = X[test_mask]
y_test = y[test_mask]

print(f"   Train rows: {len(X_train)}")
print(f"   Test rows:  {len(X_test)}")

if len(X_test) == 0 or len(X_train) == 0:
    raise SystemExit("❌ Not enough data after temporal split")

print("\n5. Training LightGBM...")
model = LGBMClassifier(
    objective="binary",
    n_estimators=500,
    learning_rate=0.03,
    num_leaves=63,
    subsample=0.9,
    colsample_bytree=0.8,
    random_state=42,
)
model.fit(X_train, y_train)
print("   ✓ Training complete")

timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
model_path = MODEL_DIR / f"betfair_kash_top5_model_{timestamp}.txt"
model.booster_.save_model(model_path)
print(f"   ✓ Model saved -> {model_path}")

print("\n6. Evaluating model...")
train_pred = model.predict_proba(X_train)[:, 1]
test_pred = model.predict_proba(X_test)[:, 1]

train_logloss = log_loss(y_train, train_pred)
test_logloss = log_loss(y_test, test_pred)

try:
    train_auc = roc_auc_score(y_train, train_pred)
    test_auc = roc_auc_score(y_test, test_pred)
except ValueError:
    train_auc = np.nan
    test_auc = np.nan

print(f"   Train LogLoss: {train_logloss:.4f}")
print(f"   Test LogLoss:  {test_logloss:.4f}")
print(f"   Train AUC:     {train_auc:.4f}")
print(f"   Test AUC:      {test_auc:.4f}")

print("\n7. Betting simulation (test set)...")
results = df.loc[test_mask].copy()
results["model_prob"] = test_pred
results["implied_prob"] = 1.0 / (results["win_odds"] + 1e-9)

results["bet"] = results["model_prob"] > results["implied_prob"]
bets = results[results["bet"]].copy()
results["profit"] = 0.0
print(f"   Bets placed: {len(bets)}")

if len(bets):
    bets["profit"] = np.where(bets["won"] == 1, bets["win_odds"] - 1, -1)
    pot = bets["profit"].mean()
    print(f"   POT: {pot * 100:.2f}%")
    results.loc[bets.index, "profit"] = bets["profit"]
else:
    pot = 0.0
    print("   No bets triggered")

print("\n8. Monthly aggregation...")
results["month"] = results["event_date"].dt.to_period("M").astype(str)
summary = (
    results.groupby("month")
    .apply(
        lambda grp: pd.Series(
            {
                "bets": int(grp["bet"].sum()),
                "wins": int((grp["bet"] & (grp["won"] == 1)).sum()),
                "pot_pct": grp.loc[grp["bet"], "profit"].mean() * 100 if grp["bet"].any() else 0.0,
                "total_staked": float(grp["bet"].sum()),
                "total_return": float(grp.loc[grp["bet"], "profit"].sum()),
            }
        )
    )
    .reset_index()
)
summary["pot_pct"] = summary["pot_pct"].fillna(0)

art_path = ARTIFACT_DIR / "pf_enhanced_results.csv"
summary.to_csv(art_path, index=False)
print(f"   Saved monthly results -> {art_path}")

feature_importances = pd.DataFrame(
    {
        "feature": feature_cols,
        "importance": model.feature_importances_,
    }
).sort_values("importance", ascending=False)
fi_path = ARTIFACT_DIR / "pf_feature_importance.csv"
feature_importances.to_csv(fi_path, index=False)
print(f"   Feature importance saved -> {fi_path}")

print("\n9. Overall summary")
print("=" * 70)
print(f"Train AUC: {train_auc:.3f} | Test AUC: {test_auc:.3f}")
print(f"Train LogLoss: {train_logloss:.3f} | Test LogLoss: {test_logloss:.3f}")
print(f"Bets placed: {len(bets)} | POT: {pot * 100:.2f}%")
print("=" * 70)
