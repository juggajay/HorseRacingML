"""Test PF API feature extraction outputs."""
from __future__ import annotations
import os
import sys
from pathlib import Path

from puntingform_api import PuntingFormAPI

ENV_PATH = Path('.env')
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        if line.strip().startswith('PUNTINGFORM_API_KEY=') and 'PUNTINGFORM_API_KEY' not in os.environ:
            os.environ['PUNTINGFORM_API_KEY'] = line.split('=', 1)[1].strip().strip('"')
            break

api_key = os.environ.get('PUNTINGFORM_API_KEY')
if not api_key:
    print("ERROR: PUNTINGFORM_API_KEY not configured in environment or .env")
    sys.exit(1)

print("=" * 70)
print("TESTING PUNTING FORM API EXTRACTION")
print("=" * 70)

api = PuntingFormAPI()

print("\nFetching meetings list...")
meetings = api.get_meetings_list()
if not meetings:
    print("ERROR: No meetings returned from API")
    sys.exit(1)

print(f"Found {len(meetings)} meetings")
first_meeting = meetings[0]
meeting_id = first_meeting.get('meetingId')
track = first_meeting.get('track', {}).get('name') if isinstance(first_meeting.get('track'), dict) else first_meeting.get('track')
date = first_meeting.get('meetingDate') or first_meeting.get('pf_meetingDate')

print(f"\nTesting with meeting {meeting_id} ({track}) on {date}")
print("\nFetching form data...")
form_df = api.get_form(meeting_id, date_str=date)

if form_df is None or form_df.empty:
    print("ERROR: No runner data returned")
    sys.exit(1)

print("\n" + "=" * 70)
print("EXTRACTION RESULTS")
print("=" * 70)

print(f"\nTotal runners extracted: {len(form_df)}")
if 'race_number' in form_df.columns:
    print(f"Total races: {form_df['race_number'].nunique(dropna=True)}")

print("\n=== COLUMN LIST ===")
for idx, col in enumerate(sorted(form_df.columns), 1):
    print(f"{idx:2d}. {col}")

KEY_FEATURES = [
    'pf_score',
    'neural_rating',
    'time_rating',
    'early_time_rating',
    'late_sectional_rating',
    'weight_class_rating',
    'pf_ai_rank',
    'pf_ai_score',
    'pf_ai_price',
]

print("\n=== KEY FEATURES: POPULATION ===")
for feature in KEY_FEATURES:
    if feature not in form_df.columns:
        print(f"✗ {feature:25s}: missing column")
        continue
    non_null = form_df[feature].notna().sum()
    pct = 100 * non_null / len(form_df)
    status = "✓" if pct >= 50 else "⚠" if pct > 0 else "✗"
    print(f"{status} {feature:25s}: {non_null:4d} / {len(form_df)} ({pct:5.1f}%)")

sample_cols = [c for c in ['horse_name', 'tab_no', 'pf_ai_rank', 'pf_ai_score', 'neural_rating', 'time_rating'] if c in form_df.columns]
if sample_cols:
    print("\n=== SAMPLE DATA (First 5 rows) ===")
    print(form_df[sample_cols].head().to_string(index=False))

stats_cols = [c for c in ['pf_score', 'neural_rating', 'time_rating', 'pf_ai_score'] if c in form_df.columns]
if stats_cols:
    print("\n=== RATING STATS ===")
    for col in stats_cols:
        series = form_df[col].dropna()
        if series.empty:
            continue
        print(f"\n{col}:")
        print(f"  Min:  {series.min():.2f}")
        print(f"  Mean: {series.mean():.2f}")
        print(f"  Max:  {series.max():.2f}")
        print(f"  Std:  {series.std():.2f}")

print("\n" + "=" * 70)
if any(col in form_df.columns and form_df[col].notna().sum() > 0 for col in KEY_FEATURES):
    print("✅ SUCCESS: PF columns extracted (coverage shown above)")
else:
    print("⚠️  WARNING: PF rating fields are missing or zero coverage")
    print("   Confirm Starter tier includes AI + ratings fields for this account")
print("=" * 70)
