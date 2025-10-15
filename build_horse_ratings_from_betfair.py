"""
Build horse ability ratings from Betfair historical exports.
Automatically ingests every `betfair_all_raw_*.csv.gz` file found in the
project root so new seasons are picked up without code changes.

These ratings replace the legacy Kaggle priors that had negligible overlap.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings("ignore")

print("=" * 70)
print("BUILDING HORSE RATINGS FROM BETFAIR HISTORICAL DATA")
print("=" * 70)

# ========================================================================
# 1. LOAD BETFAIR HISTORICAL DATA
# ========================================================================
print("\n1. Loading Betfair historical data...")

raw_paths = sorted(Path(".").glob("betfair_all_raw_*.csv.gz"))
if not raw_paths:
    print("   ✗ No betfair_all_raw_*.csv.gz files found")
    exit(1)

frames: list[pd.DataFrame] = []
for raw_path in raw_paths:
    try:
        frame = pd.read_csv(raw_path, low_memory=False)
        print(f"   ✓ Loaded {raw_path.name}: {len(frame):,} rows")
        frames.append(frame)
    except FileNotFoundError:
        print(f"   ✗ Missing file: {raw_path}")

if not frames:
    print("\nERROR: Unable to load any Betfair raw exports")
    exit(1)

historical = pd.concat(frames, ignore_index=True)
print(f"\n   Total historical rows: {len(historical):,}")

# ========================================================================
# 2. PREPARE DATA
# ========================================================================
print("\n2. Preparing data...")

# Ensure required columns exist
required_cols = ['horse_name_norm', 'won', 'win_odds']
missing_cols = [col for col in required_cols if col not in historical.columns]

if missing_cols:
    print(f"\n   ✗ Missing required columns: {missing_cols}")
    print(f"   Available columns: {historical.columns.tolist()[:20]}...")
    
    # Try to infer columns
    if 'horse' in historical.columns and 'horse_name_norm' not in historical.columns:
        print("   → Using 'horse' column, normalizing...")
        historical['horse_name_norm'] = historical['horse']
    
    if 'selection_name' in historical.columns and 'horse_name_norm' not in historical.columns:
        print("   → Using 'selection_name' column, normalizing...")
        historical['horse_name_norm'] = historical['selection_name']

# If horse_name_norm exists but is empty/null, backfill from selection_name
if 'horse_name_norm' in historical.columns:
    non_null = historical['horse_name_norm'].notna().sum()
    if non_null == 0 and 'selection_name' in historical.columns:
        print("   → Filling 'horse_name_norm' from 'selection_name' column...")
        historical['horse_name_norm'] = historical['selection_name']

    historical['horse_name_norm'] = (
        historical['horse_name_norm']
        .astype(str)
        .str.lower()
        .str.strip()
    )
    historical['horse_name_norm'] = historical['horse_name_norm'].replace({'nan': pd.NA, 'none': pd.NA, '': pd.NA})

# Check if 'won' column exists
if 'won' not in historical.columns:
    # Try to derive it
    if 'result' in historical.columns:
        print("   → Deriving 'won' from 'result' column...")
        historical['won'] = (historical['result'] == 1).astype(int)
    elif 'win_lose' in historical.columns:
        print("   → Deriving 'won' from 'win_lose' column...")
        historical['won'] = (historical['win_lose'].astype(str).str.upper() == 'WIN').astype(int)
    elif 'win_result' in historical.columns:
        print("   → Deriving 'won' from 'win_result' column...")
        historical['won'] = (historical['win_result'].astype(str).str.upper() == 'WINNER').astype(int)
    else:
        print("\n   ✗ Cannot find 'won' or 'result' column!")
        print("   Available columns:")
        print(f"   {historical.columns.tolist()}")
        exit(1)

# Check odds column
if 'win_odds' not in historical.columns:
    odds_candidates = [
        'win_bsp',
        'win_last_price_taken',
        'win_preplay_weighted_average_price_taken',
        'win_preplay_max_price_taken',
        'win_preplay_min_price_taken',
        'odds',
        'last_price_traded',
        'bsp',
        'starting_price'
    ]
    for candidate in odds_candidates:
        if candidate in historical.columns:
            print(f"   → Using '{candidate}' as win_odds...")
            historical['win_odds'] = historical[candidate]
            break
    
    if 'win_odds' not in historical.columns:
        print("\n   ✗ Cannot find odds column!")
        exit(1)

# Filter valid data
historical = historical[historical['horse_name_norm'].notna()].copy()
historical = historical[historical['win_odds'].notna()].copy()
historical = historical[historical['win_odds'] > 1.0].copy()  # Valid odds

print(f"   ✓ Valid rows after filtering: {len(historical):,}")
print(f"   ✓ Unique horses: {historical['horse_name_norm'].nunique():,}")

# Add 'placed' if not exists (top 3)
if 'placed' not in historical.columns:
    if 'finishing_position' in historical.columns:
        historical['placed'] = (historical['finishing_position'] <= 3).astype(int)
    elif 'final_position' in historical.columns:
        historical['placed'] = (historical['final_position'] <= 3).astype(int)
    else:
        # Estimate from odds - horses under 5.0 considered placed more often
        historical['placed'] = ((historical['won'] == 1) | 
                               (historical['win_odds'] < 5.0)).astype(int)

# ========================================================================
# 3. BUILD PER-HORSE STATISTICS
# ========================================================================
print("\n3. Calculating per-horse statistics...")

volume_candidates = [
    'win_bsp_volume',
    'win_preplay_volume',
    'win_inplay_volume',
    'total_matched'
]
volume_col = next((col for col in volume_candidates if col in historical.columns), None)

agg_dict = {
    'won': ['sum', 'mean', 'count'],  # Total wins, win rate, total starts
    'placed': 'mean',                 # Place rate (top 3)
    'win_odds': 'mean'                # Average odds (inverse = market rating)
}

if volume_col:
    agg_dict[volume_col] = 'mean'

horse_stats = historical.groupby('horse_name_norm').agg(agg_dict).reset_index()

column_names = ['horse_name_norm', 'total_wins', 'win_rate', 'total_starts',
                'place_rate', 'avg_odds']
if volume_col:
    column_names.append('avg_volume')

horse_stats.columns = column_names

if not volume_col:
    horse_stats['avg_volume'] = horse_stats['total_starts']

# Filter horses with at least 3 starts (reliability threshold)
horse_stats = horse_stats[horse_stats['total_starts'] >= 3].copy()

print(f"   ✓ Horses with 3+ starts: {len(horse_stats):,}")

# ========================================================================
# 4. CALCULATE COMPOSITE RATING (0-100 scale)
# ========================================================================
print("\n4. Calculating composite ratings...")

# Multiple rating components
horse_stats['rating_win_rate'] = horse_stats['win_rate'] * 100  # 0-100

# Inverse odds as market rating (normalize)
horse_stats['rating_market'] = 1 / horse_stats['avg_odds']
horse_stats['rating_market'] = horse_stats['rating_market'] * 100 / horse_stats['rating_market'].max()

# Place rate
horse_stats['rating_consistency'] = horse_stats['place_rate'] * 100

# Experience factor (horses with more starts slightly boosted)
horse_stats['rating_experience'] = np.log1p(horse_stats['total_starts']) * 5

# Volume/liquidity (indicates confidence)
horse_stats['rating_liquidity'] = np.log1p(horse_stats['avg_volume']) * 3

# ========================================================================
# 5. WEIGHTED COMPOSITE RATING
# ========================================================================
print("\n5. Creating weighted composite...")

# Weights based on importance
horse_stats['betfair_horse_rating_raw'] = (
    horse_stats['rating_win_rate'] * 0.35 +      # Win rate most important
    horse_stats['rating_market'] * 0.30 +        # Market opinion
    horse_stats['rating_consistency'] * 0.20 +   # Consistency
    horse_stats['rating_experience'] * 0.10 +    # Experience
    horse_stats['rating_liquidity'] * 0.05       # Liquidity
)

# Normalize to 20-100 scale (never below 20 = poor horse)
scaler = MinMaxScaler(feature_range=(20, 100))
horse_stats['betfair_horse_rating'] = scaler.fit_transform(
    horse_stats[['betfair_horse_rating_raw']]
)

# Round to 1 decimal
horse_stats['betfair_horse_rating'] = horse_stats['betfair_horse_rating'].round(1)

# ========================================================================
# 6. SAVE OUTPUT
# ========================================================================
print("\n6. Saving results...")

# Select final columns
output_cols = [
    'horse_name_norm',
    'betfair_horse_rating',
    'win_rate',
    'place_rate',
    'total_wins',
    'total_starts',
    'avg_odds'
]

output = horse_stats[output_cols].copy()

# Sort by rating
output = output.sort_values('betfair_horse_rating', ascending=False)

# Save
output_file = 'artifacts/horse_ratings_betfair_2023_2024.csv'
output.to_csv(output_file, index=False)

print(f"\n   ✓ Saved to: {output_file}")
print(f"   ✓ Total horses rated: {len(output):,}")

# ========================================================================
# 7. SUMMARY STATISTICS
# ========================================================================
print("\n" + "="*70)
print("RATING DISTRIBUTION")
print("="*70)

print(f"\nRating statistics:")
print(f"  Min:    {output['betfair_horse_rating'].min():.1f}")
print(f"  25%:    {output['betfair_horse_rating'].quantile(0.25):.1f}")
print(f"  Median: {output['betfair_horse_rating'].median():.1f}")
print(f"  75%:    {output['betfair_horse_rating'].quantile(0.75):.1f}")
print(f"  Max:    {output['betfair_horse_rating'].max():.1f}")

print(f"\nTop 10 rated horses:")
print(output.head(10)[['horse_name_norm', 'betfair_horse_rating', 
                       'win_rate', 'total_starts']].to_string(index=False))

print(f"\nBottom 10 rated horses:")
print(output.tail(10)[['horse_name_norm', 'betfair_horse_rating', 
                       'win_rate', 'total_starts']].to_string(index=False))

print("\n" + "="*70)
print("✓ COMPLETE - Horse ratings built from Betfair historical data")
print("="*70)
print(f"\nNext step: Run apply_betfair_ratings_to_current.py")
