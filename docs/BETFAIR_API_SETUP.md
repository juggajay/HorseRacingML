# Betfair API Setup Guide - Delayed App Key (FREE)

This guide will help you set up Betfair API access using the **Delayed App Key** (free for development).

## Overview

- **Cost**: FREE
- **Purpose**: Development and testing with delayed data
- **Upgrade Path**: £299 one-time fee for Live App Key (real-time data)

---

## Step 1: Create a Betfair Account

1. Go to https://register.betfair.com/account/registration
2. Complete the registration process
3. Verify your email address
4. **Important**: Complete KYC (Know Your Customer) verification for full access

---

## Step 2: Generate Your Application Keys

### Method A: Using the Accounts API Demo Tool (Recommended)

1. Visit the **Accounts API Demo Tool**: https://docs.developer.betfair.com/visualisers/api-ng-account-operations/
2. Select the operation: **`createDeveloperAppKeys`**
3. In a separate browser tab, login to https://www.betfair.com
4. Return to the Demo Tool
5. Enter a **unique Application Name** (e.g., "HorseRacingML-Dev")
6. Click **Execute**

You'll receive:
- **Delayed Key (Active)** - Use this for development (FREE)
- **Live Key (Inactive)** - Requires £299 activation fee

### Method B: Via Developer Portal

1. Login to https://myaccount.betfair.com/
2. Navigate to "Developer Program" section
3. Click "Get an Application Key"
4. Enter your application name
5. Submit the form

---

## Step 3: Authentication Methods

Betfair offers three login methods. For automated data collection, we recommend **Interactive Login - API Endpoint**.

### Interactive Login - API Endpoint (Recommended for this project)

This method uses username/password authentication via API.

#### Request Format

```bash
curl -k -i \
  -H "Accept: application/json" \
  -H "X-Application: YOUR_DELAYED_APP_KEY" \
  -X POST \
  -d 'username=YOUR_USERNAME&password=YOUR_PASSWORD' \
  https://identitysso.betfair.com/api/login
```

#### Response Example

```json
{
  "token": "xxxxxxxxxxxxx",
  "product": "exchange",
  "status": "SUCCESS",
  "error": ""
}
```

The `token` value is your **session token** (also called `ssoid`).

#### With 2FA Enabled

If you have two-factor authentication enabled:

```bash
curl -k -i \
  -H "Accept: application/json" \
  -H "X-Application: YOUR_DELAYED_APP_KEY" \
  -X POST \
  -d 'username=YOUR_USERNAME&password=YOUR_PASSWORD&code=123456' \
  https://identitysso.betfair.com/api/login
```

---

## Step 4: Making API Requests

Once authenticated, include these headers in all API requests:

```
X-Application: YOUR_DELAYED_APP_KEY
X-Authentication: YOUR_SESSION_TOKEN
```

### Example: List Market Catalogue (Horse Racing)

```bash
curl -X POST \
  -H "X-Application: YOUR_DELAYED_APP_KEY" \
  -H "X-Authentication: YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "eventTypeIds": ["7"],
      "marketCountries": ["AU"],
      "marketTypeCodes": ["WIN"]
    },
    "maxResults": "10",
    "marketProjection": ["RUNNER_DESCRIPTION", "EVENT", "MARKET_START_TIME"]
  }' \
  https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/
```

**Note**: Event Type ID `7` = Horse Racing

---

## Step 5: Session Management

### Keep Alive

Session tokens expire if not used. Call the Keep Alive endpoint at least once every 24 hours:

```bash
curl -X POST \
  -H "X-Application: YOUR_DELAYED_APP_KEY" \
  -H "X-Authentication: YOUR_SESSION_TOKEN" \
  -H "Accept: application/json" \
  https://identitysso.betfair.com/api/keepAlive
```

### Logout

To explicitly logout:

```bash
curl -X POST \
  -H "X-Application: YOUR_DELAYED_APP_KEY" \
  -H "X-Authentication: YOUR_SESSION_TOKEN" \
  -H "Accept: application/json" \
  https://identitysso.betfair.com/api/logout
```

---

## Step 6: Python Implementation

Here's a Python class to handle Betfair authentication:

```python
import requests
from typing import Optional

class BetfairClient:
    """Betfair API client with authentication."""

    LOGIN_URL = "https://identitysso.betfair.com/api/login"
    KEEP_ALIVE_URL = "https://identitysso.betfair.com/api/keepAlive"
    LOGOUT_URL = "https://identitysso.betfair.com/api/logout"
    API_BASE = "https://api.betfair.com/exchange/betting/rest/v1.0"

    def __init__(self, app_key: str, username: str, password: str):
        self.app_key = app_key
        self.username = username
        self.password = password
        self.session_token: Optional[str] = None

    def login(self) -> bool:
        """Login and obtain session token."""
        headers = {
            "Accept": "application/json",
            "X-Application": self.app_key
        }
        data = {
            "username": self.username,
            "password": self.password
        }

        response = requests.post(self.LOGIN_URL, headers=headers, data=data)

        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "SUCCESS":
                self.session_token = result.get("token")
                print(f"✓ Logged in successfully")
                return True

        print(f"✗ Login failed: {response.text}")
        return False

    def keep_alive(self) -> bool:
        """Keep session alive."""
        if not self.session_token:
            return False

        headers = {
            "Accept": "application/json",
            "X-Application": self.app_key,
            "X-Authentication": self.session_token
        }

        response = requests.post(self.KEEP_ALIVE_URL, headers=headers)
        return response.status_code == 200

    def logout(self):
        """Logout and invalidate session."""
        if not self.session_token:
            return

        headers = {
            "Accept": "application/json",
            "X-Application": self.app_key,
            "X-Authentication": self.session_token
        }

        requests.post(self.LOGOUT_URL, headers=headers)
        self.session_token = None
        print("✓ Logged out")

    def call_api(self, endpoint: str, params: dict) -> dict:
        """Make authenticated API call."""
        if not self.session_token:
            raise Exception("Not authenticated. Call login() first.")

        headers = {
            "X-Application": self.app_key,
            "X-Authentication": self.session_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        url = f"{self.API_BASE}/{endpoint}/"
        response = requests.post(url, headers=headers, json=params)
        response.raise_for_status()
        return response.json()

    def list_market_catalogue(self, event_type_ids=["7"], max_results=100):
        """List available markets (default: Horse Racing)."""
        params = {
            "filter": {
                "eventTypeIds": event_type_ids,
                "marketCountries": ["AU"],
                "marketTypeCodes": ["WIN"]
            },
            "maxResults": str(max_results),
            "marketProjection": [
                "RUNNER_DESCRIPTION",
                "EVENT",
                "MARKET_START_TIME",
                "MARKET_DESCRIPTION"
            ]
        }

        return self.call_api("listMarketCatalogue", params)

    def list_market_book(self, market_ids: list):
        """Get market prices and runner data."""
        params = {
            "marketIds": market_ids,
            "priceProjection": {
                "priceData": ["EX_BEST_OFFERS", "EX_TRADED"],
                "virtualise": True
            }
        }

        return self.call_api("listMarketBook", params)


# Usage Example
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    client = BetfairClient(
        app_key=os.getenv("BETFAIR_APP_KEY"),
        username=os.getenv("BETFAIR_USERNAME"),
        password=os.getenv("BETFAIR_PASSWORD")
    )

    # Login
    if client.login():
        # Get today's horse racing markets
        markets = client.list_market_catalogue(max_results=10)
        print(f"Found {len(markets)} markets")

        # Logout when done
        client.logout()
```

---

## Step 7: Update .env File

Add these credentials to your `.env` file:

```bash
# Betfair API Credentials
BETFAIR_APP_KEY=your_delayed_app_key_here
BETFAIR_USERNAME=your_betfair_username
BETFAIR_PASSWORD=your_betfair_password
```

**Security Note**: Never commit `.env` to version control. Ensure `.env` is in `.gitignore`.

---

## Important Notes

### Delayed vs Live Data

- **Delayed App Key**: Data is delayed by a few seconds
- **Live App Key**: Real-time data, requires £299 fee
- For development and backtesting, the delayed key is sufficient

### API Rate Limits

Betfair has rate limits to prevent abuse:
- Default: ~100 requests per second
- Stay well below limits during development
- Implement exponential backoff for retries

### Event Type IDs

Common sport IDs:
- `1` = Soccer
- `2` = Tennis
- `4` = Cricket
- `7` = Horse Racing (Australia)
- `4339` = Greyhound Racing

---

## Troubleshooting

### "Invalid session token"
- Session expired - call `login()` again
- Implement auto-refresh logic in production

### "INVALID_APP_KEY"
- Check your app key is correct
- Ensure you're using the Delayed key, not Live key (if not activated)

### "LOGIN_RESTRICTED"
- Account may be restricted
- Contact Betfair support

### "CERT_REQUIRED"
- Some operations require SSL certificate
- Use username/password login for basic access

---

## Next Steps

1. ✅ Create Betfair account
2. ✅ Generate Delayed App Key
3. ✅ Test authentication with Python script
4. ✅ Update `.env` with credentials
5. ✅ Integrate with existing data pipeline
6. 📊 Fetch live market data
7. 🤖 Enhance ML model with real-time odds

---

## Useful Resources

- **API Documentation**: https://docs.developer.betfair.com/
- **API Visualizer**: https://docs.developer.betfair.com/visualisers/
- **Developer Forum**: https://forum.developer.betfair.com/
- **Support**: https://support.developer.betfair.com/

---

## Cost Summary

| Feature | Delayed Key | Live Key |
|---------|------------|----------|
| **Cost** | FREE | £299 (one-time) |
| **Data Delay** | Few seconds | Real-time |
| **Use Case** | Development/Testing | Production |
| **Activation** | Immediate | Requires application |

---

**Questions?** Check the Betfair Developer Support or contact their team at https://support.developer.betfair.com/
