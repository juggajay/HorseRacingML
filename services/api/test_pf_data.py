"""Test script to see what data PuntingForm API returns."""
import os
from datetime import date
from puntingform_api import PuntingFormClient
import json

# Check if API key is set
api_key = os.getenv("PUNTINGFORM_API_KEY")
if not api_key:
    print("ERROR: PUNTINGFORM_API_KEY environment variable not set")
    exit(1)

print(f"API Key found: {api_key[:10]}...")

# Create client
try:
    client = PuntingFormClient()
    print("✓ PuntingForm client created successfully")
except Exception as e:
    print(f"ERROR creating client: {e}")
    exit(1)

# Get today's meetings
try:
    today = date.today()
    print(f"\nFetching meetings for {today}...")
    meetings = client.get_meetings_list(today)
    print(f"✓ Found {len(meetings)} meetings")

    if not meetings:
        print("No meetings found for today. Try a different date with racing.")
        exit(0)

    # Show first meeting
    print(f"\nFirst meeting: {json.dumps(meetings[0], indent=2, default=str)}")

except Exception as e:
    print(f"ERROR fetching meetings: {e}")
    exit(1)

# Get form data for first meeting
try:
    meeting = meetings[0]
    meeting_id = meeting.get("meetingId") or meeting.get("meeting_id")
    print(f"\nFetching form data for meeting {meeting_id}...")

    form_df = client.get_form(meeting_id, str(today))

    if form_df is None or form_df.empty:
        print("No form data returned")
        exit(1)

    print(f"✓ Got {len(form_df)} runners")
    print(f"\nColumns available: {list(form_df.columns)}")

    # Check for price/odds fields
    print("\nPrice/odds related columns:")
    price_cols = [col for col in form_df.columns if 'price' in col.lower() or 'odds' in col.lower() or 'ai' in col.lower()]
    print(price_cols)

    # Show first runner data
    print(f"\nFirst runner sample:")
    print(form_df.iloc[0].to_dict())

    # Check pf_ai_price specifically
    if 'pf_ai_price' in form_df.columns:
        print(f"\npf_ai_price stats:")
        print(f"  - Null count: {form_df['pf_ai_price'].isna().sum()} / {len(form_df)}")
        print(f"  - Mean: {form_df['pf_ai_price'].mean()}")
        print(f"  - Sample values: {form_df['pf_ai_price'].head(10).tolist()}")
    else:
        print("\n⚠ pf_ai_price column NOT found!")

    # Check pf_ai_rank
    if 'pf_ai_rank' in form_df.columns:
        print(f"\npf_ai_rank stats:")
        print(f"  - Null count: {form_df['pf_ai_rank'].isna().sum()} / {len(form_df)}")
        print(f"  - Sample values: {form_df['pf_ai_rank'].head(10).tolist()}")

except Exception as e:
    print(f"ERROR fetching form: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n✓ Test completed successfully")
