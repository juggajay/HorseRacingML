#!/usr/bin/env python3
"""Test script to debug PuntingForm API responses"""
import os
import json
from datetime import date
from puntingform_api import PuntingFormClient

def test_form_endpoint():
    """Test the form endpoint with and without meetingDate parameter"""
    client = PuntingFormClient()

    # Get meetings for today
    meetings_resp = client.meetings_list(date.today())
    print(f"\n=== Meetings for {date.today()} ===")
    print(f"Found {len(meetings_resp)} meetings")

    if not meetings_resp:
        print("No meetings found!")
        return

    # Test first meeting
    meeting = meetings_resp[0]
    meeting_id = meeting.get("meetingId")
    meeting_date = meeting.get("meetingDate")
    track = meeting.get("track", {}).get("name", "Unknown")

    print(f"\nTesting meeting: {track}")
    print(f"Meeting ID: {meeting_id}")
    print(f"Meeting Date: {meeting_date}")

    # Test WITHOUT meetingDate parameter (old way)
    print("\n--- Test 1: WITHOUT meetingDate parameter ---")
    form_df_old = client.get_form(meeting_id, date_str=None)
    if form_df_old is not None:
        print(f"Runners returned: {len(form_df_old)}")
        print(f"Columns: {list(form_df_old.columns)}")
        if len(form_df_old) > 0:
            print(f"\nFirst runner:")
            print(form_df_old.iloc[0].to_dict())
    else:
        print("No data returned")

    # Test WITH meetingDate parameter (new way)
    print("\n--- Test 2: WITH meetingDate parameter ---")
    form_df_new = client.get_form(meeting_id, date_str=meeting_date, force=True)
    if form_df_new is not None:
        print(f"Runners returned: {len(form_df_new)}")
        print(f"Columns: {list(form_df_new.columns)}")
        if len(form_df_new) > 0:
            print(f"\nFirst runner:")
            print(form_df_new.iloc[0].to_dict())
    else:
        print("No data returned")

    # Compare
    if form_df_old is not None and form_df_new is not None:
        print(f"\n=== COMPARISON ===")
        print(f"Old way (no meetingDate): {len(form_df_old)} runners")
        print(f"New way (with meetingDate): {len(form_df_new)} runners")
        print(f"Difference: {len(form_df_new) - len(form_df_old)} runners")

if __name__ == "__main__":
    test_form_endpoint()
