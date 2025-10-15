"""
Backfill existing PF JSON caches into flat feature CSVs using the new extractor.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

import pandas as pd

from puntingform_api import PuntingFormAPI

print("=" * 70)
print("BACKFILLING PF FEATURES FROM EXISTING JSON FILES")
print("=" * 70)

# Ensure API key available for extractor (cached requests only)
if 'PUNTINGFORM_API_KEY' not in os.environ and Path('.env').exists():
    for line in Path('.env').read_text().splitlines():
        if line.strip().startswith('PUNTINGFORM_API_KEY='):
            os.environ['PUNTINGFORM_API_KEY'] = line.split('=', 1)[1].strip().strip('"')
            break

api = PuntingFormAPI(os.environ.get('PUNTINGFORM_API_KEY'))

raw_dir = Path('data/raw/puntingform')
processed_dir = Path('data/processed/puntingform')

if not raw_dir.exists():
    print(f"\nERROR: {raw_dir} does not exist. Run update_weekly_puntingform.py first.")
    raise SystemExit(1)

month_dirs: List[Path] = sorted([p for p in raw_dir.iterdir() if p.is_dir()])
print(f"\nFound {len(month_dirs)} month directories")

total_meetings = 0
total_runners = 0
errors = 0

for month_dir in month_dirs:
    month_name = month_dir.name
    try:
        year, month = map(int, month_name.split('_'))
    except ValueError:
        print(f"\nSkipping malformed directory name: {month_name}")
        continue

    print("\n" + "=" * 70)
    print(f"Processing {month_name}...")
    print("=" * 70)

    try:
        meetings_resp = api.get_meetings_month(year, month, force=False)
        meetings = meetings_resp.get('payLoad') or meetings_resp.get('payload') or []
    except Exception as exc:
        errors += 1
        print(f"  ✗ Failed to load meetings for {month_name}: {exc}")
        continue

    if not meetings:
        print("  No meetings found in cache for this month")
        continue

    month_frames: List[pd.DataFrame] = []

    for meeting in meetings:
        meeting_id = meeting.get('meetingId') or meeting.get('meeting_id')
        if not meeting_id:
            continue

        meeting_date = meeting.get('meetingDate') or meeting.get('pf_meetingDate')
        track = meeting.get('track')
        track_name = track.get('name') if isinstance(track, dict) else track

        try:
            form_df = api.get_form(meeting_id, date_str=meeting_date, force=False)
        except Exception as exc:
            errors += 1
            print(f"  ✗ Meeting {meeting_id} form fetch failed: {exc}")
            continue

        if form_df is None or form_df.empty:
            continue

        total_meetings += 1
        form_df['meeting_id'] = meeting_id
        form_df['meeting_date'] = meeting_date
        form_df['event_date'] = (str(meeting_date)[:10]) if meeting_date else None
        form_df['track_name'] = track_name
        form_df['pf_month'] = month_name
        month_frames.append(form_df)
        total_runners += len(form_df)
        print(f"  ✓ Meeting {meeting_id}: {len(form_df)} runners")

    if not month_frames:
        print("  ✗ No runner data extracted for this month")
        continue

    month_df = pd.concat(month_frames, ignore_index=True)
    out_dir = processed_dir / month_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{month_name}__form.csv"
    month_df.to_csv(out_path, index=False)
    print(f"  → Saved {len(month_df)} runners to {out_path}")

print("\n" + "=" * 70)
print("BACKFILL COMPLETE")
print("=" * 70)
print(f"Meetings processed: {total_meetings}")
print(f"Total runners:     {total_runners}")
print(f"Errors:            {errors}")
print("=" * 70)
