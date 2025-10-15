"""
Helper script to guide you through getting your Betfair App Key.
Run this if you haven't generated your app key yet.
"""
import webbrowser
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("BETFAIR APP KEY SETUP HELPER")
print("=" * 70)

# Check current credentials
username = os.getenv("BETFAIR_USERNAME")
password = os.getenv("BETFAIR_PASSWORD")
app_key = os.getenv("BETFAIR_APP_KEY")

print("\n1. Current credentials in .env:")
print(f"   Username: {username}")
print(f"   Password: {'*' * len(password) if password else 'NOT SET'}")
print(f"   App Key:  {app_key}")

if app_key and len(app_key) > 20 and '=' in app_key:
    print("\n✓ Your app key looks valid!")
    print("  Run: python betfair_client.py")
    exit(0)

print("\n⚠ Your app key doesn't look valid yet.")
print("  App keys are typically 30+ characters and end with '='")

print("\n" + "=" * 70)
print("STEPS TO GET YOUR APP KEY:")
print("=" * 70)

print("\n1. First, login to Betfair in your browser:")
print("   → https://www.betfair.com")
print("   → Username: " + (username or "your_username"))
print("   → Password: " + ("(use your password)" if password else "your_password"))

response = input("\n   Press ENTER when you're logged in to Betfair.com... ")

print("\n2. Now open the App Key Generator:")
print("   → Opening: https://docs.developer.betfair.com/visualisers/api-ng-account-operations/")

# Open browser
try:
    webbrowser.open("https://docs.developer.betfair.com/visualisers/api-ng-account-operations/")
    print("   ✓ Browser opened")
except:
    print("   ⚠ Could not open browser automatically")
    print("   → Manually visit: https://docs.developer.betfair.com/visualisers/api-ng-account-operations/")

print("\n3. On the API page:")
print("   → Select operation: createDeveloperAppKeys (from dropdown)")
print("   → Enter App Name: HorseRacingML-Dev-2025 (or any unique name)")
print("   → Click 'Execute'")

print("\n4. Look for the response JSON:")
print("   You'll see TWO keys:")
print("   ")
print("   Key 1 (DELAYED): \"delayData\": true, \"active\": true  ← USE THIS ONE")
print("   Key 2 (LIVE):    \"delayData\": false, \"active\": false")
print("   ")
print("   Copy the 'applicationKey' from Key 1 (the DELAYED key)")

print("\n5. Update your .env file:")
print("   → Open: .env")
print("   → Find: BETFAIR_APP_KEY=betfair")
print("   → Replace 'betfair' with your actual key")
print("   → Example: BETFAIR_APP_KEY=aBcDeFgHiJkLmNoPqRsTuVwXyZ12345=")

print("\n6. Test your setup:")
print("   → Run: python betfair_client.py")
print("   → You should see: ✓ CONNECTION TEST SUCCESSFUL")

print("\n" + "=" * 70)
print("EXAMPLE RESPONSE (what you're looking for):")
print("=" * 70)
print("""
[
  {
    "appName": "HorseRacingML-Dev-2025",
    "appVersions": [
      {
        "applicationKey": "aBcDeFgHiJkLmNoPqRsTuVwXyZ12345=",  ← COPY THIS
        "delayData": true,                                    ← DELAYED KEY
        "active": true
      },
      {
        "applicationKey": "XyZaBcDeFgHiJkLmNoPqRsTuVw67890=",
        "delayData": false,
        "active": false                                       ← LIVE KEY (ignore)
      }
    ]
  }
]
""")

print("\n" + "=" * 70)
print("NEED HELP?")
print("=" * 70)
print("→ Quick Start Guide: docs/BETFAIR_QUICKSTART.md")
print("→ Full Setup Guide:  docs/BETFAIR_API_SETUP.md")
print("→ Betfair Support:   https://support.developer.betfair.com/")
print("=" * 70)
