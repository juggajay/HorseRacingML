"""Quick smoke test for the Punting Form API integration.

Usage:
    PF_DATE=2025-10-17 python3 scripts/pf_smoke_test.py

Requires the PUNTINGFORM_API_KEY environment variable to be set.
"""
from __future__ import annotations

import os
import datetime as dt
from puntingform_api import PuntingFormClient


def main() -> None:
    api_key = os.environ.get("PUNTINGFORM_API_KEY")
    if not api_key:
        raise SystemExit("❌ Set PUNTINGFORM_API_KEY before running the smoke test.")

    date_str = os.environ.get("PF_DATE")
    if date_str:
        target_date = dt.date.fromisoformat(date_str)
    else:
        target_date = dt.date.today()

    client = PuntingFormClient(api_key=api_key)
    meetings = client.get_meetings_list(target_date)
    print(f"Meetings on {target_date:%Y-%m-%d}: {len(meetings)}")
    for meeting in meetings[:5]:
        meeting_id = meeting.get("meetingId") or meeting.get("meeting_id")
        track = meeting.get("track") or meeting.get("meetingVenue")
        print(f"  - Meeting {meeting_id}: {track}")

    if meetings:
        first_meeting = meetings[0]
        meeting_id = first_meeting.get("meetingId") or first_meeting.get("meeting_id")
        df = client.get_form(meeting_id, date_str=str(target_date))
        if df is None:
            print("⚠️ No form data returned for the first meeting")
        else:
            print(f"Retrieved {len(df)} starters for meeting {meeting_id}")
            print(df.head())


if __name__ == "__main__":
    main()
