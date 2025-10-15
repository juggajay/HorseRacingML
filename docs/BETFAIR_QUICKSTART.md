# Betfair API Quick Start Guide

Get up and running with Betfair API in 10 minutes.

## Prerequisites

- Betfair account (create at https://register.betfair.com/account/registration)
- Python 3.10+
- Project dependencies installed

## Step-by-Step Setup

### 1. Install Dependencies

```bash
pip install requests
# or
pip install -r requirements.txt
```

### 2. Get Your Betfair Delayed App Key (FREE)

#### Option A: Using API Demo Tool (Easiest)

1. **Login to Betfair**: Open https://www.betfair.com and login
2. **Open Demo Tool**: Visit https://docs.developer.betfair.com/visualisers/api-ng-account-operations/
3. **Select Operation**: Choose `createDeveloperAppKeys` from dropdown
4. **Enter App Name**: Type a unique name (e.g., "HorseRacingML-Dev-2025")
5. **Click Execute**: Your keys will be generated instantly

**Response Example:**
```json
[
  {
    "appName": "HorseRacingML-Dev-2025",
    "appId": 12345,
    "appVersions": [
      {
        "owner": "yourUsername",
        "versionId": 1,
        "version": "1.0",
        "applicationKey": "aBcDeFgHiJkLmNoPqRsTuVwXyZ12345=",  // ← DELAYED KEY (use this)
        "delayData": true,
        "subscriptionRequired": false,
        "ownerManaged": false,
        "active": true
      },
      {
        "owner": "yourUsername",
        "versionId": 2,
        "version": "1.0",
        "applicationKey": "XyZaBcDeFgHiJkLmNoPqRsTuVw67890=",  // ← LIVE KEY (inactive)
        "delayData": false,
        "subscriptionRequired": true,
        "ownerManaged": true,
        "active": false  // ← Requires £299 to activate
      }
    ]
  }
]
```

**Copy the DELAYED KEY** (the one with `"delayData": true`)

#### Option B: Via My Account

1. Login to https://myaccount.betfair.com/
2. Click "Developer Program" → "My Application Keys"
3. Click "Create New App Key"
4. Enter application name
5. Copy your Delayed App Key

### 3. Update .env File

Open `.env` and add your credentials:

```bash
# Betfair API Credentials (Delayed App Key - FREE)
BETFAIR_APP_KEY=aBcDeFgHiJkLmNoPqRsTuVwXyZ12345=
BETFAIR_USERNAME=your_betfair_username
BETFAIR_PASSWORD=your_betfair_password
```

**Important**:
- Use your actual Betfair login username/password
- Keep this file secret (already in `.gitignore`)

### 4. Test Connection

Run the test script:

```bash
python betfair_client.py
```

**Expected Output:**
```
======================================================================
BETFAIR API CONNECTION TEST
======================================================================

1. Credentials loaded:
   App Key: aBcDeFgHiJ...
   Username: your_username

2. Authenticating...
✓ Logged in to Betfair successfully at 2025-10-15 17:30:45.123456

3. Fetching today's horse racing markets...
   Found 45 markets

4. Sample market details:
   Event: Randwick (AUS) 15th Oct
   Market: R1 1200m Hcp
   Start Time: 2025-10-15T05:30:00.000Z
   Runners: 12

5. Fetching prices for first market...
   Market Status: OPEN
   Runners with prices: 12

   Top 3 runners by price:
   1. Speedy Star: $2.5
   2. Lightning Bolt: $4.2
   3. Thunder Road: $6.0

6. Logging out...
✓ Logged out from Betfair

======================================================================
✓ CONNECTION TEST SUCCESSFUL
======================================================================
```

### 5. Basic Usage Examples

#### Get Today's Races

```python
from betfair_client import BetfairClient

client = BetfairClient()
client.login()

# Get all today's Australian horse racing
markets = client.get_todays_races(country="AU")

for market in markets:
    event = market.get("event", {})
    print(f"{event.get('name')} - {market.get('marketName')}")

client.logout()
```

#### Get Market Prices

```python
from betfair_client import BetfairClient

client = BetfairClient()
client.login()

# Get market with prices
market_id = "1.234567890"  # Replace with real market ID
market_book = client.get_market_with_prices(market_id)

for runner in market_book.get("runners", []):
    selection_id = runner.get("selectionId")
    best_price = runner.get("ex", {}).get("availableToBack", [{}])[0].get("price", "N/A")
    print(f"Selection {selection_id}: ${best_price}")

client.logout()
```

#### Using Context Manager (Auto Login/Logout)

```python
from betfair_client import BetfairClient

# This will be implemented in the next version
with BetfairClient() as client:
    markets = client.get_todays_races()
    # ... your code ...
# Automatically logs out when done
```

## Common Issues & Solutions

### "Missing credentials"
**Solution**: Check your `.env` file has all three values set correctly

### "Login failed: INVALID_USERNAME_OR_PASSWORD"
**Solution**:
- Verify username/password are correct
- Try logging into www.betfair.com to confirm credentials work

### "INVALID_APP_KEY"
**Solution**:
- Make sure you copied the DELAYED key (not Live key)
- Check for extra spaces in `.env` file
- Ensure the key is the full string including any `=` at the end

### "No markets found"
**Solution**:
- Check the date - may not be races scheduled for today
- Try different country codes: `AU`, `GB`, `IE`, `US`
- Markets appear ~24 hours before race time

### "CERT_REQUIRED"
**Solution**:
- This is for non-interactive login (not needed for this setup)
- Ignore if using username/password authentication

## Rate Limits

Betfair has built-in rate limiting:
- **Default**: ~100 requests per second
- **Recommendation**: Stay well below 10 requests per second during development
- **Best Practice**: Add delays between batch requests

```python
import time

for market_id in market_ids:
    data = client.get_market_with_prices(market_id)
    # Process data...
    time.sleep(0.2)  # 200ms delay = max 5 requests/second
```

## Next Steps

✅ Test connection successful?

Now you can:

1. **Integrate with Pipeline**: Fetch live Betfair data to complement PuntingForm data
2. **Build Real-Time Predictions**: Use current market odds with your ML model
3. **Backtest Strategies**: Compare model predictions against actual Betfair prices
4. **Monitor Value Bets**: Alert when model finds odds discrepancies

## Advanced Topics

For more advanced usage, see:
- **Full Setup Guide**: `docs/BETFAIR_API_SETUP.md`
- **API Documentation**: https://docs.developer.betfair.com/
- **Market Types**: https://docs.developer.betfair.com/pages/viewpage.action?pageId=3834909

## Getting Help

- **Betfair Support**: https://support.developer.betfair.com/
- **Developer Forum**: https://forum.developer.betfair.com/
- **API Visualizer**: https://docs.developer.betfair.com/visualisers/

---

**Remember**: This is using the FREE Delayed App Key. Data is delayed by a few seconds.
Upgrade to Live Key (£299) when ready for real-time production use.
