# Betfair API Integration - Summary for Developers

## What's Been Added

Complete Betfair Exchange API integration for your HorseRacingML project with FREE Delayed App Key access.

---

## 📁 New Files Created

### Documentation (in `docs/`)
1. **`BETFAIR_README.md`** - Overview and index of all Betfair docs
2. **`BETFAIR_QUICKSTART.md`** - 10-minute quick start guide
3. **`BETFAIR_API_SETUP.md`** - Comprehensive technical documentation

### Code (in project root)
1. **`betfair_client.py`** - Full-featured Betfair API client
2. **`fetch_betfair_todays_data.py`** - Script to fetch today's race data

### Updated Files
1. **`.env`** - Added Betfair credential placeholders
2. **`requirements.txt`** - Added `requests` dependency

---

## 🚀 Quick Start for Developers

### Step 1: Get Betfair Credentials (5 minutes)

1. Create account: https://register.betfair.com/account/registration
2. Get FREE Delayed App Key:
   - Visit: https://docs.developer.betfair.com/visualisers/api-ng-account-operations/
   - Select: `createDeveloperAppKeys`
   - Enter: App name (e.g., "HorseRacingML-Dev")
   - Copy: Your DELAYED key (the one with `"delayData": true`)

### Step 2: Update Environment

Edit `.env` file:
```bash
BETFAIR_APP_KEY=your_actual_delayed_key_here
BETFAIR_USERNAME=your_betfair_username
BETFAIR_PASSWORD=your_betfair_password
```

### Step 3: Test Connection

```bash
# Install requests if not already installed
pip install requests

# Run test
python betfair_client.py
```

Expected output:
```
✓ Logged in to Betfair successfully
✓ Found 45 markets
✓ CONNECTION TEST SUCCESSFUL
```

### Step 4: Fetch Today's Data

```bash
# Fetch today's Australian horse racing data
python fetch_betfair_todays_data.py

# For other countries
python fetch_betfair_todays_data.py --country GB  # Great Britain
python fetch_betfair_todays_data.py --country IE  # Ireland
```

---

## 💻 Code Examples

### Basic Usage

```python
from betfair_client import BetfairClient

# Create client (reads from .env automatically)
client = BetfairClient()

# Login
client.login()

# Get today's races
markets = client.get_todays_races(country="AU")
print(f"Found {len(markets)} markets")

# Get prices for a specific market
market_id = markets[0]["marketId"]
market_book = client.get_market_with_prices(market_id)

# Always logout when done
client.logout()
```

### Integration Example

```python
from betfair_client import BetfairClient
import pandas as pd

def get_current_odds(market_id: str) -> pd.DataFrame:
    """Get current odds for a market."""
    client = BetfairClient()
    client.login()

    market_book = client.get_market_with_prices(market_id)

    data = []
    for runner in market_book["runners"]:
        best_price = runner["ex"]["availableToBack"][0]["price"]
        data.append({
            "selection_id": runner["selectionId"],
            "odds": best_price,
            "status": runner["status"]
        })

    client.logout()
    return pd.DataFrame(data)
```

---

## 📊 Integration with Existing Pipeline

### Current Pipeline
```
PuntingForm API → Raw Data → Feature Engineering → ML Model → Predictions
```

### Enhanced Pipeline
```
PuntingForm API ──┐
                  ├→ Merge → Feature Engineering → ML Model → Predictions
Betfair API ──────┘                                              │
                                                                 ↓
                                                    Compare with Market Odds
                                                                 ↓
                                                          Find Value Bets
```

### Example Merge Script

```python
import pandas as pd
from fetch_betfair_todays_data import fetch_todays_betfair_data
# Your existing PuntingForm code
from puntingform_api import fetch_pf_data

# Get Betfair odds
betfair_df = fetch_todays_betfair_data()

# Get PuntingForm ratings (your existing code)
pf_df = fetch_pf_data()

# Merge on horse name + race
merged = pd.merge(
    pf_df,
    betfair_df,
    left_on=["horse_name", "track", "race_no"],
    right_on=["selection_name", "track", "race_no"],
    how="left"
)

# Now you have both PF ratings AND Betfair odds
# Use this for your ML model
```

---

## 🎯 Use Cases

### 1. Real-Time Predictions
Fetch current odds and compare with model predictions:
```python
# Get model prediction
model_prob = model.predict_proba(features)

# Get current Betfair odds
betfair_odds = get_current_odds(market_id)
implied_prob = 1 / betfair_odds

# Find value
edge = model_prob - implied_prob
if edge > 0.1:  # 10% edge
    print("VALUE BET FOUND!")
```

### 2. Backtesting
Compare historical predictions with actual Betfair prices:
```python
# For each past race:
#   - Your model's predicted probability
#   - Actual Betfair closing odds
#   - Calculate what ROI would have been
```

### 3. Data Enrichment
Add Betfair market features to your ML model:
- `win_odds` - Current market price
- `total_matched` - Market liquidity
- `implied_prob` - Market's probability estimate
- `odds_rank` - Runner's rank by odds

### 4. Live Monitoring
Schedule data fetching:
```bash
# In crontab (fetch every 10 minutes during race hours)
*/10 8-18 * * * cd /path/to/project && python fetch_betfair_todays_data.py
```

---

## 💰 Costs

| Item | Cost | Notes |
|------|------|-------|
| **Betfair Account** | FREE | Registration is free |
| **Delayed App Key** | FREE | For development & testing |
| **Live App Key** | £299 one-time | Only if you need real-time data |

**Recommendation**: Start with FREE Delayed Key. Only upgrade to Live when:
- Model is proven profitable
- Ready for production deployment
- Need real-time (not backtesting)

---

## 📚 Documentation Structure

```
docs/
├── BETFAIR_README.md          # Overview & index
├── BETFAIR_QUICKSTART.md      # 10-min quick start
└── BETFAIR_API_SETUP.md       # Comprehensive guide

Root:
├── betfair_client.py                    # API client library
├── fetch_betfair_todays_data.py         # Data fetching script
└── .env                                 # Credentials (updated)
```

---

## 🔧 API Client Features

The `BetfairClient` class provides:

### Authentication
- ✅ `login()` - Authenticate with Betfair
- ✅ `logout()` - End session
- ✅ `keep_alive()` - Maintain session
- ✅ `ensure_authenticated()` - Auto re-login if expired

### Market Data
- ✅ `list_market_catalogue()` - Get available markets
- ✅ `list_market_book()` - Get market prices
- ✅ `get_todays_races()` - Helper for today's races
- ✅ `get_market_with_prices()` - Get single market with odds

### Error Handling
- ✅ Automatic session management
- ✅ Connection timeout handling
- ✅ Rate limiting friendly
- ✅ Clear error messages

---

## ⚠️ Important Notes

### Rate Limits
- Betfair limits: ~100 requests/second
- **Best practice**: Stay under 10 requests/second
- Add delays between requests: `time.sleep(0.2)`

### Session Management
- Sessions expire after 24 hours of inactivity
- Call `keep_alive()` or the client handles it automatically
- Re-login automatically on expiry

### Data Delay
- FREE Delayed Key: ~5 seconds delay
- Sufficient for development and backtesting
- Upgrade to Live Key for real-time trading

### Security
- ✅ `.env` already in `.gitignore`
- ✅ Never commit credentials
- ✅ Use environment variables only

---

## 🐛 Troubleshooting

### "Missing credentials"
→ Check `.env` has all three values set

### "Login failed"
→ Verify username/password on www.betfair.com first

### "INVALID_APP_KEY"
→ Make sure you copied the DELAYED key (not Live)

### "No markets found"
→ Races appear ~24 hours before start time
→ Try different country codes

### "Connection timeout"
→ Check internet connection
→ Betfair may be down (rare)

**Full troubleshooting**: See `docs/BETFAIR_QUICKSTART.md`

---

## 🎓 Learning Resources

### Official Betfair
- **API Docs**: https://docs.developer.betfair.com/
- **API Visualizer**: https://docs.developer.betfair.com/visualisers/
- **Support**: https://support.developer.betfair.com/
- **Forum**: https://forum.developer.betfair.com/

### Your Project Docs
- **Quick Start**: `docs/BETFAIR_QUICKSTART.md` - Start here!
- **Full Guide**: `docs/BETFAIR_API_SETUP.md` - All the details
- **Overview**: `docs/BETFAIR_README.md` - What's included

---

## ✅ Next Steps

1. **Setup** (10 min)
   - [ ] Create Betfair account
   - [ ] Get Delayed App Key
   - [ ] Update `.env`
   - [ ] Run test: `python betfair_client.py`

2. **Explore** (30 min)
   - [ ] Fetch today's data: `python fetch_betfair_todays_data.py`
   - [ ] Review output CSV
   - [ ] Explore API with `betfair_client.py` examples

3. **Integrate** (variable)
   - [ ] Merge with PuntingForm data
   - [ ] Add Betfair features to ML model
   - [ ] Build value bet detector
   - [ ] Set up automated data fetching

4. **Production** (when ready)
   - [ ] Backtest strategy thoroughly
   - [ ] Consider upgrading to Live Key (£299)
   - [ ] Deploy automated monitoring
   - [ ] Track performance

---

## 🤝 Support

**Questions?** Check these resources in order:
1. `docs/BETFAIR_QUICKSTART.md` - Quick answers
2. `docs/BETFAIR_API_SETUP.md` - Detailed explanations
3. Official Betfair support - For API-specific issues

**Issues with the integration code?** Review:
- `betfair_client.py` - Well-commented
- `fetch_betfair_todays_data.py` - Usage examples

---

## 📝 Summary

You now have:
✅ FREE Betfair API access (Delayed App Key)
✅ Python client library (`betfair_client.py`)
✅ Data fetching scripts
✅ Complete documentation
✅ Integration examples
✅ Test scripts

**Total setup time**: ~10 minutes
**Total cost**: £0 (FREE)

**Get started**: `docs/BETFAIR_QUICKSTART.md`

---

**Happy coding! 🏇📊**
