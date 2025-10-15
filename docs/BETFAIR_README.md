# Betfair API Integration - Documentation Index

Complete guide to integrating Betfair Exchange API with HorseRacingML project.

## Quick Links

- **🚀 Quick Start** (10 minutes): [`BETFAIR_QUICKSTART.md`](BETFAIR_QUICKSTART.md)
- **📖 Full Setup Guide**: [`BETFAIR_API_SETUP.md`](BETFAIR_API_SETUP.md)
- **🐍 Python Client**: [`../betfair_client.py`](../betfair_client.py)

## What You Get

### FREE Delayed App Key
- ✅ No cost - completely free
- ✅ Access to all markets and prices
- ✅ Data delayed by a few seconds
- ✅ Perfect for development and backtesting
- ✅ Immediate activation

### Paid Live App Key (Optional)
- 💰 £299 one-time fee
- ✅ Real-time data (no delay)
- ✅ Required for live production trading
- ⏳ Requires application process

## What's Included

### 1. Documentation

| File | Description |
|------|-------------|
| `BETFAIR_QUICKSTART.md` | 10-minute setup guide |
| `BETFAIR_API_SETUP.md` | Comprehensive technical documentation |
| `BETFAIR_README.md` | This file - overview and index |

### 2. Python Client

**File**: `betfair_client.py`

Full-featured client with:
- ✅ Authentication handling (login/logout/keep-alive)
- ✅ Auto session management
- ✅ Market catalogue retrieval
- ✅ Price data fetching
- ✅ Today's races helper
- ✅ Error handling
- ✅ Built-in test function

### 3. Environment Setup

**File**: `.env` (updated)

Added Betfair credentials:
```bash
BETFAIR_APP_KEY=your_delayed_app_key_here
BETFAIR_USERNAME=your_betfair_username
BETFAIR_PASSWORD=your_betfair_password
```

## Getting Started

### Prerequisites

1. **Betfair Account**
   - Register at https://register.betfair.com/account/registration
   - Complete KYC verification

2. **Python Environment**
   - Python 3.10+
   - Dependencies: `requests`, `python-dotenv` (already in `requirements.txt`)

### Setup Steps

1. **Get Your App Key** (5 minutes)
   ```
   → Visit: https://docs.developer.betfair.com/visualisers/api-ng-account-operations/
   → Select: createDeveloperAppKeys
   → Enter: Your app name (e.g., "HorseRacingML-Dev")
   → Copy: Your DELAYED App Key
   ```

2. **Update `.env`** (1 minute)
   ```bash
   BETFAIR_APP_KEY=your_actual_key_here
   BETFAIR_USERNAME=your_betfair_username
   BETFAIR_PASSWORD=your_betfair_password
   ```

3. **Test Connection** (2 minutes)
   ```bash
   python betfair_client.py
   ```

4. **Start Building** 🚀
   ```python
   from betfair_client import BetfairClient

   client = BetfairClient()
   client.login()
   markets = client.get_todays_races()
   client.logout()
   ```

## Use Cases for Your ML Project

### 1. Real-Time Odds Integration
Combine Betfair market odds with your ML predictions:
```python
# Get current market odds
market_book = client.get_market_with_prices(market_id)

# Compare with ML model predictions
# Find value bets where model_prob > implied_prob
```

### 2. Data Pipeline Enhancement
Augment PuntingForm data with Betfair market data:
```python
# Existing: PuntingForm ratings + historical data
# Add: Live Betfair odds + market volume
# Result: More features for ML model
```

### 3. Backtesting
Historical comparison of model predictions vs actual Betfair prices:
```python
# For each historical race:
# - Model predicted win probability
# - Actual Betfair closing odds
# - Calculate ROI if bet at predicted edges
```

### 4. Live Monitoring
Alert when model finds value bets:
```python
# If model_prob > (1 / betfair_odds) + margin:
#   → Send alert
#   → Log opportunity
#   → Track performance
```

## API Capabilities

### Market Data
- ✅ List available markets (today, tomorrow, date range)
- ✅ Filter by country (AU, GB, IE, US, etc.)
- ✅ Filter by event type (Horse Racing, Greyhounds, etc.)
- ✅ Get market details (event, venue, start time)

### Price Data
- ✅ Best available odds (back/lay)
- ✅ Price depth (multiple price levels)
- ✅ Traded volume
- ✅ Market status (OPEN, SUSPENDED, CLOSED)
- ✅ Runner status (ACTIVE, WITHDRAWN, etc.)

### Authentication
- ✅ Session token management
- ✅ Auto re-login on expiry
- ✅ Keep-alive handling
- ✅ Secure credential storage

## Example Integration

Here's how to integrate with your existing pipeline:

```python
# fetch_betfair_data.py
from datetime import datetime
import pandas as pd
from betfair_client import BetfairClient

def fetch_todays_betfair_data():
    """Fetch today's horse racing odds from Betfair."""
    client = BetfairClient()
    client.login()

    # Get today's Australian horse racing markets
    markets = client.get_todays_races(country="AU")

    data = []
    for market in markets:
        market_id = market.get("marketId")
        event = market.get("event", {})

        # Get current prices
        market_book = client.get_market_with_prices(market_id)

        for runner in market_book.get("runners", []):
            # Extract runner details
            selection_id = runner.get("selectionId")

            # Get runner name from market catalogue
            runner_info = next(
                (r for r in market.get("runners", [])
                 if r["selectionId"] == selection_id),
                {}
            )

            # Get best back price
            best_back = runner.get("ex", {}).get("availableToBack", [{}])[0]

            data.append({
                "event_date": market.get("marketStartTime"),
                "track": event.get("venue"),
                "race_no": market.get("marketName", "").split("R")[-1].split()[0],
                "market_id": market_id,
                "selection_id": selection_id,
                "selection_name": runner_info.get("runnerName"),
                "win_odds": best_back.get("price"),
                "total_matched": market_book.get("totalMatched", 0),
                "status": runner.get("status"),
            })

    client.logout()

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Save to processed data
    output_path = f"data/processed/betfair/betfair_{datetime.now().strftime('%Y%m%d')}.csv"
    df.to_csv(output_path, index=False)
    print(f"✓ Saved {len(df)} runners to {output_path}")

    return df

if __name__ == "__main__":
    fetch_todays_betfair_data()
```

## Cost Comparison

| Feature | Delayed Key | Live Key |
|---------|------------|----------|
| **Cost** | FREE ✅ | £299 (one-time) |
| **Data Delay** | ~5 seconds | Real-time |
| **Market Access** | All markets ✅ | All markets ✅ |
| **Price Data** | All prices ✅ | All prices ✅ |
| **Volume Data** | Yes ✅ | Yes ✅ |
| **Historical Data** | Yes ✅ | Yes ✅ |
| **Best For** | Development, Testing, Backtesting | Live Trading, Production |
| **Activation** | Instant ✅ | Application required |

**Recommendation**: Start with Delayed Key. Only upgrade to Live Key when:
- Your model is proven profitable
- You're ready for live production deployment
- You need real-time data (not backtesting)

## Support & Resources

### Official Betfair Resources
- **API Docs**: https://docs.developer.betfair.com/
- **Support**: https://support.developer.betfair.com/
- **Forum**: https://forum.developer.betfair.com/
- **API Visualizer**: https://docs.developer.betfair.com/visualisers/

### Project Files
- **Client Code**: `betfair_client.py`
- **Quick Start**: `docs/BETFAIR_QUICKSTART.md`
- **Full Guide**: `docs/BETFAIR_API_SETUP.md`
- **Environment**: `.env`

### Getting Help

1. **Test Connection First**:
   ```bash
   python betfair_client.py
   ```

2. **Check Logs**: Look for error messages in output

3. **Common Issues**: See troubleshooting in `BETFAIR_QUICKSTART.md`

4. **Betfair Support**: https://support.developer.betfair.com/hc/en-us/requests/new

## Next Steps

After setup, consider:

1. **Fetch Historical Data**: Use Betfair API to backfill historical odds
2. **Real-Time Monitoring**: Build a service to fetch odds every 5 minutes
3. **Model Enhancement**: Add Betfair odds as features to your ML model
4. **Value Detection**: Compare model predictions with market prices
5. **Automation**: Schedule data fetching with cron/systemd

## License Note

This integration uses Betfair's official public API. By using it, you agree to:
- Betfair's Terms & Conditions
- API Terms of Use
- Responsible gambling guidelines

Always comply with Betfair's policies and your local gambling regulations.

---

**Questions?** Check the quick start guide or full setup documentation.

**Ready to start?** → [`BETFAIR_QUICKSTART.md`](BETFAIR_QUICKSTART.md)
