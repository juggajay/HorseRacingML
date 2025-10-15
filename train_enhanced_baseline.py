"""
train_enhanced_baseline.py

Train model with the 8 new features and compare to baseline.
Uses same walk-forward validation as original baseline.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score
from sklearn.calibration import CalibratedClassifierCV
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

# LightGBM parameters (same as baseline)
LGBM_PARAMS = {
    'objective': 'binary',
    'n_estimators': 600,
    'learning_rate': 0.03,
    'num_leaves': 63,
    'subsample': 0.9,
    'colsample_bytree': 0.8,
    'random_state': 42,
    'verbose': -1
}

# Enhanced feature set (baseline + 8 new features)
FEATURES = [
    # Baseline features (5)
    'odds',
    'implied_prob',
    'matched',
    'odds_rank',
    'overround',
    
    # Prep cycle features (5)
    'days_since_last_run',
    'is_spell',
    'prep_run_number',
    'is_first_up',
    'is_second_up',
    
    # Market features (3)
    'is_favorite',
    'odds_vs_favorite',
    'volume_rank'
]


def walk_forward_validate(df):
    """
    Monthly walk-forward validation with 6-month warm-up.
    Same methodology as baseline for direct comparison.
    """
    
    print("\n" + "="*70)
    print("WALK-FORWARD VALIDATION")
    print("="*70)
    
    # Sort by date
    df = df.sort_values('event_date').reset_index(drop=True)
    df['event_date'] = pd.to_datetime(df['event_date'])
    df['yearmonth'] = df['event_date'].dt.to_period('M')
    
    # Get unique months
    months = sorted(df['yearmonth'].unique())
    warm_up = 6
    
    print(f"\n📅 Time period: {months[0]} to {months[-1]}")
    print(f"   Total months: {len(months)}")
    print(f"   Warm-up: {warm_up} months")
    print(f"   Testing: {len(months) - warm_up} months")
    
    results = []
    feature_importance_list = []
    
    # Walk forward month by month
    for i in range(warm_up, len(months)):
        test_month = months[i]
        train_months = months[:i]
        
        # Split data
        train = df[df['yearmonth'].isin(train_months)]
        test = df[df['yearmonth'] == test_month]
        
        if len(test) == 0:
            continue
        
        # Prepare data
        X_train = train[FEATURES].fillna(0)
        y_train = train['target_win']
        
        X_test = test[FEATURES].fillna(0)
        y_test = test['target_win']
        
        # Train LightGBM with calibration (same as baseline)
        base_model = lgb.LGBMClassifier(**LGBM_PARAMS)
        calibrated_model = CalibratedClassifierCV(
            base_model,
            method='isotonic',
            cv=3
        )
        
        calibrated_model.fit(X_train, y_train)
        
        # Predict
        probs = calibrated_model.predict_proba(X_test)[:, 1]
        
        # Betting logic (same as baseline)
        # Bet when calibrated probability > implied probability
        test_copy = test.copy()
        test_copy['model_prob'] = probs
        test_copy['value'] = probs > (1 / test_copy['odds'])
        
        bets = test_copy[test_copy['value']].copy()
        
        if len(bets) == 0:
            continue
        
        # Calculate returns (flat 1-unit stakes)
        bets['return'] = np.where(
            bets['target_win'] == 1,
            bets['odds'] - 1,  # Win: return odds-1
            -1  # Lose: -1
        )
        
        # POT calculation
        pot = bets['return'].mean()  # Average return per bet
        
        # Metrics
        brier = brier_score_loss(y_test, probs)
        logloss = log_loss(y_test, probs)
        
        try:
            auc = roc_auc_score(y_test, probs)
        except:
            auc = np.nan
        
        # Store results
        results.append({
            'test_month': str(test_month),
            'n_train': len(train),
            'n_test': len(test),
            'bets': len(bets),
            'pot': pot,
            'brier': brier,
            'logloss': logloss,
            'auc': auc
        })
        
        # Feature importance (from base model before calibration)
        base_estimator = calibrated_model.calibrated_classifiers_[0].estimator
        importance = pd.DataFrame({
            'feature': FEATURES,
            'importance': base_estimator.feature_importances_,
            'month': str(test_month)
        })
        feature_importance_list.append(importance)
        
        # Progress
        if i % 3 == 0:
            print(f"   {test_month}: {len(bets):,} bets, POT: {pot:+.2%}")
    
    return pd.DataFrame(results), pd.concat(feature_importance_list, ignore_index=True)


def compare_to_baseline(metrics_df, feature_importance_df):
    """
    Compare enhanced model to baseline and report improvement.
    """
    
    print("\n" + "="*70)
    print("RESULTS COMPARISON")
    print("="*70)
    
    # Enhanced model POT
    valid_months = metrics_df[metrics_df['pot'].notna()]
    mean_pot = valid_months['pot'].mean()
    median_pot = valid_months['pot'].median()
    
    # Baseline POT (from your results)
    baseline_pot = -0.0176
    
    print(f"\n📈 Profitability:")
    print(f"   Baseline POT:    {baseline_pot:+.2%}")
    print(f"   Enhanced POT:    {mean_pot:+.2%}")
    print(f"   Improvement:     {mean_pot - baseline_pot:+.2%}")
    print(f"   Median POT:      {median_pot:+.2%}")
    
    # Win/loss months
    win_months = (valid_months['pot'] > 0).sum()
    loss_months = (valid_months['pot'] < 0).sum()
    
    print(f"\n📊 Month-by-Month:")
    print(f"   Profitable months: {win_months}/{len(valid_months)} ({win_months/len(valid_months):.1%})")
    print(f"   Loss months: {loss_months}/{len(valid_months)}")
    
    # Best/worst
    best = valid_months.loc[valid_months['pot'].idxmax()]
    worst = valid_months.loc[valid_months['pot'].idxmin()]
    
    print(f"\n🏆 Best month: {best['test_month']}")
    print(f"   POT: {best['pot']:+.2%} ({best['bets']} bets)")
    
    print(f"\n💔 Worst month: {worst['test_month']}")
    print(f"   POT: {worst['pot']:+.2%} ({worst['bets']} bets)")
    
    # Feature importance
    print(f"\n⭐ Top 10 Features:")
    top_features = (
        feature_importance_df
        .groupby('feature')['importance']
        .mean()
        .sort_values(ascending=False)
        .head(10)
    )
    
    for i, (feature, importance) in enumerate(top_features.items(), 1):
        # Mark new features
        is_new = feature in [
            'days_since_last_run', 'is_spell', 'prep_run_number',
            'is_first_up', 'is_second_up', 'is_favorite',
            'odds_vs_favorite', 'volume_rank'
        ]
        marker = "🆕" if is_new else "  "
        print(f"   {i:2d}. {marker} {feature:25s} {importance:8.0f}")
    
    # New features in top 10?
    new_in_top10 = [f for f in top_features.index if f not in [
        'odds', 'implied_prob', 'matched', 'odds_rank', 'overround'
    ]]
    
    print(f"\n🆕 New features in top 10: {len(new_in_top10)}")
    for feat in new_in_top10:
        print(f"   - {feat}")


def main():
    """
    Train enhanced model and compare to baseline.
    """
    
    print("="*70)
    print("ENHANCED BASELINE MODEL TRAINING")
    print("="*70)
    
    # Load enhanced features
    input_path = Path('data/processed/ml/betfair_features_enhanced.csv.gz')
    
    if not input_path.exists():
        print(f"\n❌ ERROR: Input file not found at {input_path}")
        print("\nRun this first: python add_prep_features.py")
        return
    
    print(f"\n📂 Loading: {input_path}")
    df = pd.read_csv(input_path)
    print(f"   Rows: {len(df):,}")
    print(f"   Columns: {len(df.columns)}")
    
    # Verify required features exist
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        print(f"\n❌ ERROR: Missing required features: {missing}")
        return
    
    print(f"\n📊 Using {len(FEATURES)} features:")
    print(f"   Baseline features: 5")
    print(f"   Prep cycle features: 5")
    print(f"   Market features: 3")
    
    # Walk-forward validation
    metrics_df, feature_importance_df = walk_forward_validate(df)
    
    # Compare to baseline
    compare_to_baseline(metrics_df, feature_importance_df)
    
    # Save artifacts
    output_dir = Path('artifacts')
    output_dir.mkdir(exist_ok=True)
    
    metrics_path = output_dir / 'enhanced_baseline_metrics.csv'
    importance_path = output_dir / 'enhanced_feature_importance.csv'
    
    metrics_df.to_csv(metrics_path, index=False)
    feature_importance_df.to_csv(importance_path, index=False)
    
    print(f"\n💾 Saved artifacts:")
    print(f"   - {metrics_path}")
    print(f"   - {importance_path}")
    
    print("\n" + "="*70)
    print("✅ Training complete!")
    print("="*70)
    
    # Final verdict
    mean_pot = metrics_df['pot'].mean()
    baseline_pot = -0.0176
    improvement = mean_pot - baseline_pot
    
    if improvement > 0.02:
        print(f"\n🎉 EXCELLENT! +{improvement:.2%} improvement!")
        print("These 8 features created real edge.")
    elif improvement > 0.01:
        print(f"\n✅ GOOD! +{improvement:.2%} improvement!")
        print("Significant progress toward profitability.")
    elif improvement > 0:
        print(f"\n📈 PROGRESS! +{improvement:.2%} improvement!")
        print("Heading in right direction.")
    else:
        print(f"\n⚠️  No improvement: {improvement:+.2%}")
        print("Features may not be predictive with current data.")
    
    print("\nNext steps:")
    if mean_pot > 0:
        print("1. ✅ Model is profitable! Fix PF integration for more features")
        print("2. Add Australian domain features (WFA, barriers, etc.)")
        print("3. Target: +5% to +10% POT")
    else:
        print("1. Fix Punting Form track name merge (critical!)")
        print("2. Parse PF fields (age, sex, barrier, distance)")
        print("3. Add Australian racing features")
    
    print("="*70)


if __name__ == '__main__':
    main()

