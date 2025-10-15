"""
Get SSOID token from Betfair for manual entry into visualizer
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("BETFAIR_USERNAME")
password = os.getenv("BETFAIR_PASSWORD")

print("=" * 70)
print("GET BETFAIR SSOID TOKEN")
print("=" * 70)

if not username or not password:
    print("\n✗ Missing credentials in .env file")
    exit(1)

print(f"\nUsername: {username}")
print(f"Password: {'*' * len(password)}")

# Try both Australian and international endpoints
endpoints = [
    ("Australian", "https://identitysso.betfair.com.au/api/login"),
    ("International", "https://identitysso.betfair.com/api/login"),
]

for endpoint_name, url in endpoints:
    print(f"\n{'='*70}")
    print(f"Trying {endpoint_name} endpoint...")
    print(f"{'='*70}")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "username": username,
        "password": password
    }

    try:
        response = requests.post(url, headers=headers, data=data, timeout=15)

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result}")

            # Check different possible keys for the token
            token = (result.get("sessionToken") or
                    result.get("token") or
                    result.get("ssoid"))

            status = result.get("loginStatus") or result.get("status")

            if status == "SUCCESS" and token:
                print("\n" + "=" * 70)
                print("✓ LOGIN SUCCESSFUL!")
                print("=" * 70)
                print(f"\nYour SSOID Token:")
                print(f">>> {token} <<<")
                print("\n" + "=" * 70)
                print("NEXT STEPS:")
                print("=" * 70)
                print("1. Copy the token above (the long string)")
                print("2. Go to: https://apps.betfair.com/visualisers/api-ng-account-operations/")
                print("3. Find the 'Session Token (ssoid)' field")
                print("4. Paste your token there")
                print("5. Select 'getDeveloperAppKeys' or 'createDeveloperAppKeys'")
                print("6. Click 'Execute'")
                print("=" * 70)
                exit(0)
            else:
                print(f"✗ Login failed: {status}")
                print(f"Error: {result.get('error', 'Unknown')}")
        else:
            print(f"✗ HTTP Error: {response.text[:200]}")

    except Exception as e:
        print(f"✗ Exception: {e}")

print("\n" + "=" * 70)
print("✗ FAILED TO GET TOKEN")
print("=" * 70)
print("\nPossible issues:")
print("1. Incorrect username/password")
print("2. Account needs verification")
print("3. Account locked or restricted")
print("\nRecommendation:")
print("→ Email automation@betfair.com.au to request your app key manually")
print("=" * 70)
