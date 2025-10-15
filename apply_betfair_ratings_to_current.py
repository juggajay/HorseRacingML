"""
Apply Betfair historical horse ratings to current 2025 data.

This joins the ratings built from 2023-2024 data to your current
PF+Betfair merged dataset, replacing the Kaggle priors that had 0% overlap.
"""
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("APPLYING BETFAIR HORSE RATINGS TO CURRENT DATA")
print("="*70)

# ========================================================================
# 1. LOAD CURRENT DATA
# ========================================================================
print("\n1. Loading current PF+Betfair data...")

current_file = 'data/processed/ml/pf_betfair_merged.csv.gz'
try:
    current = pd.read_csv(current_file, low_memory=False)
    print(f"   ✓ Loaded: {len(current):,} rows")
except FileNotFoundError:
    print(f"   ✗ File not found: {current_file}")
    print("   Make sure merge_pf_to_betfair.py has been run")
    exit(1)

# ========================================================================
# 2. LOAD BETFAIR RATINGS
# ========================================================================
print("\n2. Loading Betfair horse ratings...")

ratings_file = 'artifacts/horse_ratings_betfair_2023_2024.csv'
try:
    ratings = pd.read_csv(ratings_file)
    print(f"   ✓ Loaded: {len(ratings):,} rated horses")
except FileNotFoundError:
    print(f"   ✗ File not found: {ratings_file}")
    print("   Run build_horse_ratings_from_betfair.py first")
    exit(1)

# ========================================================================
# 3. CHECK OVERLAP
# ========================================================================
print("\n3. Checking horse name overlap...")

current_horses = set(current['horse_name_norm'].dropna().unique())
rated_horses = set(ratings['horse_name_norm'].unique())
overlap = current_horses & rated_horses

print(f"   Current dataset horses: {len(current_horses):,}")
print(f"   Rated horses:           {len(rated_horses):,}")
print(f"   Overlap:                {len(overlap):,} horses")
print(f"   Expected join rate:     {100*len(overlap)/len(current_horses):.1f}%")

if len(overlap) == 0:
    print("\n   ⚠️  WARNING: 0% overlap!")
    print("   Possible issues:")
    print("   - Horse name normalization differs between files")
    print("   - Different time periods (no overlapping horses)")
    print("   - Column name mismatch")
    
    print("\n   Sample current horses:")
    print("   ", list(current_horses)[:5])
    print("\n   Sample rated horses:")
    print("   ", list(rated_horses)[:5])
    
    # Continue anyway with median fillna

# ========================================================================
# 4. JOIN RATINGS
# ========================================================================
print("\n4. Joining ratings to current data...")

# Merge on horse_name_norm
current = current.merge(
    ratings[['horse_name_norm', 'betfair_horse_rating', 'win_rate', 
             'place_rate', 'total_starts', 'avg_odds']],
    on='horse_name_norm',
    how='left',
    suffixes=('', '_betfair_prior')
)

# Count successful joins
joined = current['betfair_horse_rating'].notna().sum()
join_rate = 100 * joined / len(current)

print(f"   ✓ Rows with ratings: {joined:,} / {len(current):,} ({join_rate:.1f}%)")

# ========================================================================
# 5. FILL MISSING RATINGS
# ========================================================================
print("\n5. Filling missing ratings...")

# For horses without historical ratings, use median
median_rating = ratings['betfair_horse_rating'].median()
print(f"   Median rating: {median_rating:.1f}")

current['betfair_horse_rating'] = current['betfair_horse_rating'].fillna(median_rating)
current['win_rate'] = current['win_rate'].fillna(0.10)  # Default 10% win rate
current['place_rate'] = current['place_rate'].fillna(0.30)  # Default 30% place rate
current['total_starts'] = current['total_starts'].fillna(5)  # Default experience

print(f"   ✓ Filled {len(current) - joined:,} missing values with defaults")

# ========================================================================
# 6. CREATE DERIVED FEATURES
# ========================================================================
print("\n6. Creating derived features from ratings...")

# Rating advantage vs field
race_id_candidates = ['race_id', 'race_id_pf', 'race_id_bf', 'meeting_id']
race_id_col = next((col for col in race_id_candidates if col in current.columns), None)

if race_id_col is None:
    raise KeyError("No race identifier column found for rating advantage calculation")

current['betfair_rating_advantage'] = current.groupby(race_id_col)['betfair_horse_rating'].transform(
    lambda x: x - x.mean()
)
print(f"   ✓ Using '{race_id_col}' for within-race calculations")

# Experience categories
current['is_experienced'] = (current['total_starts'] >= 10).astype(int)
current['is_novice'] = (current['total_starts'] <= 3).astype(int)

# Form categories based on win rate
current['is_strong_form'] = (current['win_rate'] > 0.20).astype(int)  # 20%+ win rate
current['is_consistent'] = (current['place_rate'] > 0.50).astype(int)  # 50%+ place rate

print(f"   ✓ Created 5 derived features")

# ========================================================================
# 7. SAVE OUTPUT
# ========================================================================
print("\n7. Saving enriched dataset...")

output_file = 'data/processed/ml/pf_betfair_with_betfair_priors.csv.gz'
current.to_csv(output_file, index=False, compression='gzip')

print(f"   ✓ Saved to: {output_file}")

# ========================================================================
# 8. SUMMARY
# ========================================================================
print("\n" + "="*70)
print("SUMMARY")
print("="*70)

print(f"\nDataset size: {len(current):,} rows")
print(f"Unique horses: {current['horse_name_norm'].nunique():,}")
print(f"Horses with historical ratings: {joined:,} ({join_rate:.1f}%)")
print(f"Horses using median rating: {len(current) - joined:,}")

print(f"\nNew features added:")
print(f"  - betfair_horse_rating (20-100 scale)")
print(f"  - win_rate (historical)")
print(f"  - place_rate (historical)")
print(f"  - total_starts (experience)")
print(f"  - betfair_rating_advantage (vs field)")
print(f"  - is_experienced, is_novice, is_strong_form, is_consistent")

# Show rating distribution
print(f"\nRating distribution in current data:")
print(f"  Min:    {current['betfair_horse_rating'].min():.1f}")
print(f"  25%:    {current['betfair_horse_rating'].quantile(0.25):.1f}")
print(f"  Median: {current['betfair_horse_rating'].median():.1f}")
print(f"  75%:    {current['betfair_horse_rating'].quantile(0.75):.1f}")
print(f"  Max:    {current['betfair_horse_rating'].max():.1f}")

print("\n" + "="*70)
print("✓ COMPLETE - Betfair ratings applied to current data")
print("="*70)
print(f"\nNext step: Update feature_engineering.py to use betfair_horse_rating")
print(f"           instead of kaggle_horse_rating, then retrain model")
