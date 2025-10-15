"""
Get or create Betfair app keys using SSOID token
"""
import requests
import json

# Your SSOID token from browser
SSOID_TOKEN = "+4bKhcV2CTEw5Mipan+8uAt2e21t/fUqivMB9rWscQc="

ACCOUNT_API_URL = "https://api.betfair.com/exchange/account/rest/v1.0"

print("=" * 70)
print("BETFAIR APP KEY RETRIEVAL")
print("=" * 70)
print(f"\nUsing SSOID Token: {SSOID_TOKEN[:20]}...")

def get_existing_keys(session_token):
    """Check if app keys already exist."""
    print("\n1. Checking for existing app keys...")
    url = f"{ACCOUNT_API_URL}/getDeveloperAppKeys/"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Authentication": session_token
    }

    try:
        response = requests.post(url, headers=headers, json={}, timeout=15)

        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            keys = response.json()
            if keys and len(keys) > 0:
                print(f"   ✓ Found existing keys!")
                return keys
            else:
                print("   → No existing keys found")
                return None
        else:
            print(f"   Response: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return None

def create_app_keys(session_token, app_name):
    """Create new app keys."""
    print(f"\n2. Creating new app keys with name: '{app_name}'...")
    url = f"{ACCOUNT_API_URL}/createDeveloperAppKeys/"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Authentication": session_token
    }
    data = {
        "appName": app_name
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)

        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ App keys created successfully!")
            return result
        else:
            error_text = response.text
            print(f"   ✗ Failed: {error_text[:300]}")

            if "INVALID_SESSION" in error_text:
                print("\n   → Session expired. Get a fresh SSOID token from browser.")
            elif "APP_KEY_CREATION_FAILED" in error_text or "DUPLICATE" in error_text:
                print("\n   → Keys already exist or app name not unique.")
                print("   → Try getDeveloperAppKeys instead")

            return None

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return None

def display_keys(keys_data):
    """Display app keys in readable format."""
    print("\n" + "=" * 70)
    print("YOUR BETFAIR APP KEYS")
    print("=" * 70)

    if isinstance(keys_data, list) and len(keys_data) > 0:
        for app in keys_data:
            app_name = app.get("appName", "Unknown")
            print(f"\nApplication Name: {app_name}")

            versions = app.get("appVersions", [])
            for version in versions:
                app_key = version.get("applicationKey", "N/A")
                delay_data = version.get("delayData", False)
                active = version.get("active", False)

                if delay_data:
                    print(f"\n  🔑 DELAYED KEY (FREE - USE THIS):")
                    print(f"     {app_key}")
                    print(f"     Active: {active}")
                    print(f"     Delay: Yes")

                    # This is the one to save
                    delayed_key = app_key
                else:
                    print(f"\n  🔐 LIVE KEY (Requires activation):")
                    print(f"     {app_key}")
                    print(f"     Active: {active}")
                    print(f"     Delay: No")

    print("\n" + "=" * 70)
    return delayed_key if 'delayed_key' in locals() else None

# Try to get existing keys first
existing_keys = get_existing_keys(SSOID_TOKEN)

if existing_keys:
    delayed_key = display_keys(existing_keys)

    if delayed_key:
        print("\n✓ DONE! Copy the DELAYED KEY above.")
        print("\nUpdate your .env file:")
        print(f"BETFAIR_APP_KEY={delayed_key}")

else:
    # No existing keys, create new ones
    app_name = "HorseRacingML2025"
    print(f"\nNo existing keys found. Creating new ones...")

    new_keys = create_app_keys(SSOID_TOKEN, app_name)

    if new_keys:
        delayed_key = display_keys([new_keys])

        if delayed_key:
            print("\n✓ DONE! Copy the DELAYED KEY above.")
            print("\nUpdate your .env file:")
            print(f"BETFAIR_APP_KEY={delayed_key}")
    else:
        print("\n✗ Failed to create or retrieve keys")
        print("\nTry these app names instead:")
        for i in range(1, 6):
            print(f"  - HorseRacingML{2025 + i}")
            print(f"  - RacingML{i}")

print("\n" + "=" * 70)
