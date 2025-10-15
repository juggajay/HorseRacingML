"""
Create Betfair App Key via API (for when web visualizer doesn't work)
This script will login and create your app keys programmatically.
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Australian Betfair endpoints
IDENTITY_URL = "https://identitysso.betfair.com.au"
ACCOUNT_API_URL = "https://api.betfair.com/exchange/account/rest/v1.0"

def login(username, password):
    """Login to Betfair and get session token."""
    print("=" * 70)
    print("BETFAIR APP KEY CREATOR")
    print("=" * 70)

    print("\n1. Logging in to Betfair...")
    url = f"{IDENTITY_URL}/api/login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "username": username,
        "password": password
    }

    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get("loginStatus") == "SUCCESS":
                token = result.get("sessionToken") or result.get("token")
                print(f"   ✓ Login successful!")
                print(f"   Session Token: {token[:20]}...")
                return token
            else:
                print(f"   ✗ Login failed: {result.get('loginStatus')}")
                return None
        else:
            print(f"   ✗ HTTP Error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return None

def get_existing_keys(session_token):
    """Check if app keys already exist."""
    print("\n2. Checking for existing app keys...")
    url = f"{ACCOUNT_API_URL}/getDeveloperAppKeys/"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Authentication": session_token
    }

    try:
        response = requests.post(url, headers=headers, json={}, timeout=10)

        if response.status_code == 200:
            keys = response.json()
            if keys:
                print(f"   ✓ Found existing keys!")
                return keys
            else:
                print("   → No existing keys found")
                return None
        else:
            print(f"   → No keys found (this is normal for first time)")
            return None

    except Exception as e:
        print(f"   → No existing keys: {e}")
        return None

def create_app_keys(session_token, app_name):
    """Create new app keys."""
    print(f"\n3. Creating new app keys with name: '{app_name}'...")
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
        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ App keys created successfully!")
            return result
        else:
            error_text = response.text
            print(f"   ✗ Failed to create keys: {error_text}")

            if "APP_KEY_CREATION_FAILED" in error_text:
                print("\n   Possible reasons:")
                print("   - App name not unique (try a different name)")
                print("   - App name contains your username")
                print("   - You already have keys (check with getDeveloperAppKeys)")

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
                else:
                    print(f"\n  🔐 LIVE KEY (Requires £299 activation):")
                    print(f"     {app_key}")
                    print(f"     Active: {active}")
                    print(f"     Delay: No")

    print("\n" + "=" * 70)

def save_to_env(delayed_key):
    """Update .env file with the delayed key."""
    print("\n4. Updating .env file...")

    env_path = ".env"

    try:
        # Read current .env
        with open(env_path, 'r') as f:
            lines = f.readlines()

        # Update the BETFAIR_APP_KEY line
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("BETFAIR_APP_KEY="):
                lines[i] = f"BETFAIR_APP_KEY={delayed_key}\n"
                updated = True
                break

        # Write back
        with open(env_path, 'w') as f:
            f.writelines(lines)

        if updated:
            print(f"   ✓ Updated .env with your DELAYED key")
            print(f"   Key: {delayed_key[:20]}...")
        else:
            print("   ⚠ Could not find BETFAIR_APP_KEY in .env")
            print(f"   Please manually add: BETFAIR_APP_KEY={delayed_key}")

    except Exception as e:
        print(f"   ✗ Error updating .env: {e}")
        print(f"   Please manually add to .env: BETFAIR_APP_KEY={delayed_key}")

def main():
    # Get credentials from .env
    username = os.getenv("BETFAIR_USERNAME")
    password = os.getenv("BETFAIR_PASSWORD")

    if not username or not password:
        print("✗ Missing credentials in .env file")
        print("  Please set BETFAIR_USERNAME and BETFAIR_PASSWORD")
        return

    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")

    # Login
    session_token = login(username, password)
    if not session_token:
        print("\n✗ Failed to login. Please check your credentials.")
        return

    # Check for existing keys first
    existing_keys = get_existing_keys(session_token)

    if existing_keys:
        display_keys(existing_keys)

        # Extract delayed key
        for app in existing_keys:
            for version in app.get("appVersions", []):
                if version.get("delayData"):
                    delayed_key = version.get("applicationKey")
                    save_to_env(delayed_key)
                    break

        print("\n✓ DONE! You already had keys. Check output above.")
        return

    # Create new keys
    app_name = input("\n   Enter a unique app name (e.g., HorseRacingML2025): ").strip()

    if not app_name:
        app_name = "HorseRacingML2025"
        print(f"   Using default: {app_name}")

    keys_data = create_app_keys(session_token, app_name)

    if keys_data:
        display_keys([keys_data])

        # Extract and save delayed key
        for version in keys_data.get("appVersions", []):
            if version.get("delayData"):
                delayed_key = version.get("applicationKey")
                save_to_env(delayed_key)
                break

        print("\n✓ DONE! Your app keys have been created and saved.")
        print("\nNext step: Run 'python betfair_client.py' to test connection")
    else:
        print("\n✗ Failed to create app keys.")
        print("\nAlternative: Email automation@betfair.com.au and request keys manually")

if __name__ == "__main__":
    main()
