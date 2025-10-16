# HorseRacingML - Project Status & Developer Guide

**Last Updated**: October 15, 2025
**Status**: ✅ **PRODUCTION DEPLOYED**

---

## 🎯 What This Project Does

HorseRacingML is a **machine learning system** that predicts horse racing outcomes and identifies **value betting opportunities** using:
- **Betfair Exchange API** (delayed, FREE tier)
- **PuntingForm API** (form ratings)
- **LightGBM ML Model** (529K training samples)

The system analyzes odds vs model predictions to find horses where the market is undervaluing the true win probability.

---

## 🚀 Current Deployment

### **Production URLs**
- **Frontend (Vercel)**: https://horse-racing-ml.vercel.app (or your custom domain)
- **Backend API (Railway)**: https://horseracingml-production.up.railway.app
- **GitHub Repository**: https://github.com/juggajay/HorseRacingML

### **Deployment Architecture**

```
┌─────────────────────────────────────────┐
│  FRONTEND (Vercel - Next.js)            │
│  https://horse-racing-ml.vercel.app     │
│                                          │
│  Features:                               │
│  - Date picker                           │
│  - Track filter dropdown                 │
│  - Race filter dropdown                  │
│  - Margin slider                         │
│  - Value selections table                │
└────────────────┬────────────────────────┘
                 │
                 │ HTTPS API Calls
                 │ (CORS enabled)
                 ▼
┌─────────────────────────────────────────┐
│  BACKEND (Railway - FastAPI)            │
│  https://horseracingml-production...    │
│                                          │
│  Endpoints:                              │
│  - GET /health                           │
│  - GET /races?date_str=YYYY-MM-DD        │
│  - GET /selections?date_str=...&margin=  │
│                                          │
│  Data:                                   │
│  - ML model (LightGBM, 3.3MB)            │
│  - Training dataset (37K races, cached)  │
│  - Feature engineering pipeline          │
└─────────────────────────────────────────┘
```

---

## 📊 Current Data Status

### **Dataset in Production**
- **PF Schema Root**: `services/api/data/processed/pf_schema/`
  - `meetings.csv.gz` – 495 AU meetings (2025-07-18 → 2025-09-30)
  - `races.csv.gz` – 3,814 races (scheduled start + metadata)
  - `runners.csv.gz` – 36,956 starters (Betfair markets aligned to PF-style rows)
- **Source**: reshaped from `services/api/data/processed/ml/betfair_kash_top5.csv.gz`
- **Why limited**: Railway cold-start limits still require a ~4 MB slice; full archive lives outside production build

#### **PF Schema Transform**
- Run `python3 scripts/build_pf_schema_from_betfair.py` to regenerate PF-aligned tables from the latest Betfair slice
- Loader utility `services/api/pf_schema_loader.py` merges the `meetings → races → runners` tables for training, scoring, and backtesting
- API (`services/api/main.py`) and training scripts now prefer the PF schema automatically, falling back to the legacy CSV only if the transform is missing

### **Model in Production**
- **Location**: `services/api/artifacts/models/betfair_kash_top5_model_20251015T060239Z.txt`
- **Size**: 3.3MB
- **Type**: LightGBM Booster
- **Training Set**: 529,686 races (2023-2025)
- **Test AUC**: 0.868
- **Profit on Turnover**: 68.18%
- **Features**: 45 (market, form cycle, historical, PuntingForm, interactions)

---

## 🔑 API Credentials & Environment Variables

### **Betfair API (Delayed - FREE)**
- **App Key**: `qkXksbzX9pMJfLCp` (Delayed Application Key)
- **Username**: `jryan1810`
- **Password**: `Kn2Y9s3aRh.h8q!`
- **Type**: Delayed (1-180 second delay, no cost)
- **Upgrade Option**: Live key available for £299 (real-time data)

### **PuntingForm API**
- **API Key**: `5b0df8bf-da9a-4d1e-995d-9b7a002aa836`
- **Tier**: Starter (FREE)
- **Coverage**: Australian racing only

### **Environment Files**

**`.env` (Local Development - NOT in git):**
```bash
BETFAIR_APP_KEY=qkXksbzX9pMJfLCp
BETFAIR_USERNAME=jryan1810
BETFAIR_PASSWORD=Kn2Y9s3aRh.h8q!
PUNTINGFORM_API_KEY=5b0df8bf-da9a-4d1e-995d-9b7a002aa836
PF_MODE=starter
```

**`.env.vercel` (Frontend Only - SAFE to commit):**
```bash
NEXT_PUBLIC_API_BASE=https://horseracingml-production.up.railway.app
```

### **Where Secrets Are Stored**

| Environment | Where | Variables |
|-------------|-------|-----------|
| **Local Development** | `.env` file | All credentials |
| **Railway (Backend)** | Railway Dashboard → Variables | All backend credentials |
| **Vercel (Frontend)** | Vercel Dashboard → Environment Variables | `NEXT_PUBLIC_API_BASE` only |

---

## 🏗️ Project Structure

```
HorseRacingML/
├── services/
│   └── api/                          # FastAPI backend
│       ├── main.py                   # API endpoints, CORS, caching
│       ├── feature_engineering.py    # ML feature pipeline
│       ├── betfair_client.py         # Betfair API wrapper
│       ├── requirements.txt          # Python dependencies
│       ├── Dockerfile                # Docker build for Railway
│       ├── data/                     # Training data (in production)
│       │   └── processed/ml/
│       │       └── betfair_kash_top5.csv.gz
│       └── artifacts/                # ML models (in production)
│           └── models/
│               └── betfair_kash_top5_model_*.txt
│
├── web/                              # Next.js frontend
│   ├── pages/
│   │   ├── index.tsx                 # Main dashboard (filtering UI)
│   │   └── _app.tsx                  # App wrapper
│   ├── components/
│   │   └── SelectionTable.tsx        # Results table component
│   ├── lib/
│   │   └── api.ts                    # API client, types
│   ├── styles/
│   │   └── globals.css               # Global styles
│   ├── package.json                  # Node dependencies
│   ├── next.config.js                # Next.js config
│   └── Dockerfile                    # Docker build (not used in production)
│
├── data/                             # Local data (gitignored)
│   ├── raw/                          # Original Betfair snapshots
│   └── processed/
│       ├── betfair/                  # Fetched Betfair data
│       └── ml/                       # Prepared ML datasets
│
├── artifacts/                        # Local models (gitignored)
│   └── models/                       # Trained model files
│
├── docs/                             # Documentation
│   ├── BETFAIR_QUICKSTART.md
│   ├── BETFAIR_API_SETUP.md
│   └── BETFAIR_README.md
│
├── betfair_client.py                 # Betfair API client (root copy)
├── feature_engineering.py            # Feature pipeline (root copy)
├── train_model_pf.py                 # Model training script
├── fetch_betfair_todays_data.py      # Original data fetcher (has issues)
├── fetch_todays_races_simple.py      # ✅ WORKING data fetcher
├── create_betfair_appkey.py          # Script to create Betfair app keys
├── requirements.txt                  # Python dependencies
├── .env                              # Local secrets (NOT in git)
├── .env.example                      # Template for .env
├── .env.vercel                       # Frontend-only env vars (safe)
├── .gitignore                        # Git ignore rules
├── docker-compose.yml                # Local Docker setup
├── README.md                         # Main readme
├── DEPLOYMENT_GUIDE.md               # General deployment guide
├── VERCEL_DEPLOYMENT.md              # Vercel + Railway guide
└── PROJECT_STATUS.md                 # 👈 THIS FILE
```

---

## 🔧 How to Run Locally

### **Prerequisites**
- Python 3.10+
- Node.js 20+
- Docker (optional)

### **1. Clone Repository**
```bash
git clone https://github.com/juggajay/HorseRacingML.git
cd HorseRacingML
```

### **2. Set Up Environment**
```bash
# Copy example env file
cp .env.example .env

# Edit .env with actual credentials (already populated)
# BETFAIR_APP_KEY=qkXksbzX9pMJfLCp
# BETFAIR_USERNAME=jryan1810
# BETFAIR_PASSWORD=Kn2Y9s3aRh.h8q!
# PUNTINGFORM_API_KEY=5b0df8bf-da9a-4d1e-995d-9b7a002aa836
```

### **3. Run Backend API**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run API locally
cd services/api
uvicorn main:app --reload --port 8000

# Test: http://localhost:8000/health
```

### **4. Run Frontend**
```bash
# Install Node dependencies
cd web
npm install

# Set API URL for local dev
export NEXT_PUBLIC_API_BASE=http://localhost:8000

# Run Next.js dev server
npm run dev

# Open: http://localhost:3000
```

### **5. Using Docker (Alternative)**
```bash
# Start both API and UI
docker-compose up -d

# API: http://localhost:8000
# UI: http://localhost:3000
```

---

## 📡 How to Fetch Fresh Betfair Data

### **Working Script: `fetch_todays_races_simple.py`**

This script fetches today's Australian horse racing data from Betfair's delayed API:

```bash
python3 fetch_todays_races_simple.py
```

**What it does:**
1. Authenticates with Betfair using credentials from `.env`
2. Fetches all Australian horse racing markets for today
3. Gets current odds and runner information
4. Saves to: `data/processed/betfair/betfair_snapshot_YYYYMMDD_HHMMSS.csv`

**Output Example:**
```
Found 49 markets today
Retrieved 49 market books
Saved 500 runners to: data/processed/betfair/betfair_snapshot_20251015_211453.csv
```

**Important Notes:**
- ⚠️ `fetch_betfair_todays_data.py` (original script) has bugs - use `fetch_todays_races_simple.py` instead
- Data is delayed by 1-180 seconds (FREE tier limitation)
- Rate limited - script fetches in chunks of 10 markets
- Only fetches Australian racing (country="AU")

---

## 🧠 How to Retrain the Model

### **Training Script: `train_model_pf.py`**

```bash
python3 train_model_pf.py
```

**What it does:**
1. Loads data from `data/processed/ml/betfair_kash_top5.csv.gz`
2. Engineers 45 features
3. Trains LightGBM model with 500 trees
4. Saves model to `artifacts/models/betfair_kash_top5_model_TIMESTAMP.txt`
5. Prints performance metrics (AUC, LogLoss, POT)

**To deploy new model to production:**
```bash
# After training locally
cp artifacts/models/betfair_kash_top5_model_*.txt services/api/artifacts/models/

# Commit and push
git add services/api/artifacts/models/
git commit -m "Update ML model"
git push origin master

# Railway will auto-deploy
```

---

## 🚢 Deployment Process

### **Backend (Railway)**

**Auto-deploys on git push to master**

1. Push code: `git push origin master`
2. Railway detects changes
3. Builds Docker image from `services/api/Dockerfile`
4. Loads environment variables from Railway dashboard
5. Starts FastAPI server on port 8000
6. **Startup process**:
   - Loads dataset into memory (~2-3 seconds)
   - Loads ML model
   - Prints "Dataset and model loaded successfully!"
   - Ready to serve requests

**Manual Re-deploy:**
- Go to Railway dashboard → Deployments → Click "Deploy"

### **Frontend (Vercel)**

**Auto-deploys on git push to master**

1. Push code: `git push origin master`
2. Vercel detects changes
3. Builds Next.js from `web/` directory
4. Deploys to edge network
5. Live in ~60 seconds

**Manual Re-deploy:**
- Go to Vercel dashboard → Deployments → Click redeploy

### **Environment Variables in Production**

**Railway (Backend):**
```bash
BETFAIR_APP_KEY=qkXksbzX9pMJfLCp
BETFAIR_USERNAME=jryan1810
BETFAIR_PASSWORD=Kn2Y9s3aRh.h8q!
PUNTINGFORM_API_KEY=5b0df8bf-da9a-4d1e-995d-9b7a002aa836
PF_MODE=starter
```

**Vercel (Frontend):**
```bash
NEXT_PUBLIC_API_BASE=https://horseracingml-production.up.railway.app
```

---

## 📝 API Endpoints

### **Health Check**
```bash
GET /health

Response:
{
  "status": "ok"
}
```

### **Get All Races for a Date**
```bash
GET /races?date_str=2025-09-15

Response:
{
  "date": "2025-09-15",
  "runners": [
    {
      "event_date": "2025-09-15T00:00:00",
      "track": "Hamilton",
      "race_no": 1,
      "selection_name": "Morisu Ojo",
      "win_odds": 3.15,
      "model_prob": 0.939,
      "implied_prob": 0.317,
      "edge": 0.622,
      ...
    }
  ]
}
```

### **Get Value Selections (Filtered)**
```bash
GET /selections?date_str=2025-09-15&margin=1.05&top=3

Parameters:
- date_str: Race date (YYYY-MM-DD)
- margin: Edge margin filter (default 1.05 = 5%)
- top: Optional - only return top N selections per race

Response:
{
  "date": "2025-09-15",
  "margin": 1.05,
  "selections": [
    {
      "event_date": "2025-09-15T00:00:00",
      "track": "Hamilton",
      "race_no": 1,
      "selection_name": "Morisu Ojo",
      "win_odds": 3.15,
      "model_prob": 0.939,
      "implied_prob": 0.317,
      "edge": 0.622,
      "betfair_horse_rating": 35.7,
      "win_rate": 0.25
    }
  ]
}
```

---

## 🎨 Frontend Features

### **Current Filters**
1. **Date Picker**: Select race date (currently limited to July-September 2025 dataset)
2. **Margin Slider**: Filter by edge margin (default 1.05 = 5% edge required)
3. **Track Dropdown**: Filter to specific track (e.g., "Hamilton", "Muswellbrook")
4. **Race Dropdown**: Filter to specific race number (only shows when track selected)
5. **Results Counter**: Shows "X of Y selections" based on active filters

### **Table Columns**
- **DATE**: Race date
- **TRACK**: Racetrack name
- **RACE**: Race number
- **RUNNER**: Horse name
- **ODDS**: Current Betfair odds
- **PROB%**: Model's predicted win probability
- **IMP%**: Implied probability from odds (1/odds)
- **EDGE%**: Value edge (PROB% - IMP% × Margin)
- **VALUE%**: Additional value metric

---

## 🔥 Known Issues & Limitations

### **1. Limited Dataset in Production**
- **Issue**: Only has data from July 18 - September 30, 2025
- **Why**: Full 58MB dataset caused Railway startup timeouts
- **Solution**: Fetch fresh data using `fetch_todays_races_simple.py` and update

### **2. Original Data Fetcher Broken**
- **Issue**: `fetch_betfair_todays_data.py` calls `get_market_with_prices()` which doesn't exist
- **Workaround**: Use `fetch_todays_races_simple.py` instead
- **TODO**: Fix or deprecate original script

### **3. No Automated Daily Updates**
- **Issue**: Data doesn't refresh automatically
- **Solution**: Need to run fetch script manually or set up cron job
- **Future**: Add scheduled GitHub Action or Railway cron job

### **4. Betfair Delayed API Limitations**
- **Delay**: 1-180 seconds (not real-time)
- **Upgrade**: £299 one-time fee for live key
- **Rate Limits**: Max 10 markets per request, need chunking

### **5. Missing PuntingForm Integration**
- **Status**: API key exists but not actively fetching PuntingForm data
- **Why**: Model was trained with PuntingForm features but current fetch script doesn't include them
- **Impact**: Model may underperform vs training performance
- **TODO**: Integrate PuntingForm API into data fetching pipeline

---

## 🛠️ Common Tasks

### **Update Production Dataset**

```bash
# 1. Fetch fresh data
python3 fetch_todays_races_simple.py

# 2. Process and combine with existing data (optional)
# ... add your data processing steps ...

# 3. Create smaller dataset for production
python3 << 'EOF'
import pandas as pd
from datetime import datetime, timedelta

df = pd.read_csv("data/processed/ml/betfair_kash_top5.csv.gz")
df["event_date"] = pd.to_datetime(df["event_date"])

# Keep last 90 days
cutoff = datetime.now() - timedelta(days=90)
recent = df[df["event_date"] >= cutoff]

# Save to production location
recent.to_csv("services/api/data/processed/ml/betfair_kash_top5.csv.gz", index=False, compression="gzip")
print(f"Saved {len(recent)} races")
EOF

# 4. Deploy
git add services/api/data/
git commit -m "Update production dataset"
git push origin master
```

### **View Railway Logs**

```bash
# Option 1: Railway Dashboard
# Go to: https://railway.app → Your Project → Deployments → Click deployment → View logs

# Option 2: Railway CLI (if installed)
railway logs
```

### **Test API Locally**

```bash
# Health check
curl http://localhost:8000/health

# Get today's races
curl "http://localhost:8000/races?date_str=2025-09-15"

# Get value selections
curl "http://localhost:8000/selections?date_str=2025-09-15&margin=1.05"
```

### **Test API in Production**

```bash
# Health check
curl https://horseracingml-production.up.railway.app/health

# Get selections
curl "https://horseracingml-production.up.railway.app/selections?date_str=2025-09-15&margin=1.05"
```

---

## 🔐 Security Notes

### **What's Safe to Commit**
- ✅ `.env.example` (template with placeholder values)
- ✅ `.env.vercel` (only contains public API URL)
- ✅ `web/` directory (no secrets)
- ✅ Documentation files

### **NEVER Commit**
- ❌ `.env` (contains real credentials)
- ❌ `data/raw/` (large files, API responses)
- ❌ `data/processed/` (except production dataset in `services/api/data/`)
- ❌ `artifacts/models/` (except production model in `services/api/artifacts/`)
- ❌ Any file with actual API keys in code

### **Credential Rotation**
If credentials are compromised:
1. **Betfair**: Login to Betfair → Account → API → Revoke app key → Create new
2. **PuntingForm**: Contact support@puntingform.com.au
3. Update `.env`, Railway variables, and this documentation

---

## 📈 Performance Metrics

### **Model Performance (Test Set)**
- **AUC**: 0.868 (excellent discrimination)
- **Train/Test AUC Gap**: 0.017 (minimal overfitting)
- **LogLoss**: 0.230 (well-calibrated)
- **Profit on Turnover**: 68.18% (on test set, March-Sept 2025)

### **API Performance**
- **Cold Start**: ~5 seconds (dataset + model loading)
- **Request Latency**: <100ms (after startup)
- **Dataset Size**: 37K races cached in memory
- **Uptime**: Railway free tier (generous, ~99% uptime)

### **Frontend Performance**
- **Build Time**: ~60 seconds
- **First Load**: <2 seconds
- **Interactive**: <1 second
- **CDN**: Vercel Edge (global)

---

## 🔮 Future Improvements

### **High Priority**
1. **Automated Data Updates**: GitHub Action or Railway cron to fetch daily data
2. **Fix PuntingForm Integration**: Include form ratings in data fetch
3. **Expand Dataset**: Add more recent data to production
4. **Real-time Updates**: Consider upgrading to Betfair Live API (£299)

### **Medium Priority**
5. **Database Integration**: Move from CSV to PostgreSQL for better performance
6. **Historical Performance Tracking**: Track model predictions vs actual results
7. **Backtesting Dashboard**: Visualize historical performance
8. **SMS/Email Alerts**: Notify when high-value bets appear
9. **Multi-model Ensemble**: Combine multiple models for better predictions

### **Low Priority**
10. **User Authentication**: Add login system
11. **Bet Tracking**: Log bets and calculate ROI
12. **Mobile App**: React Native version
13. **Live In-Play Betting**: Real-time odds monitoring during races

---

## 🆘 Troubleshooting

### **Frontend shows "Failed to fetch"**
1. Check Railway API is running: `curl https://horseracingml-production.up.railway.app/health`
2. Check CORS is enabled in `services/api/main.py` (should be)
3. Check Vercel environment variable `NEXT_PUBLIC_API_BASE` is set correctly
4. Check browser console for detailed error

### **API returns 404 "No runners found"**
- Dataset only has July 18 - September 30, 2025
- Try date: `2025-09-15` instead of current date
- Or fetch fresh data and update production dataset

### **API returns 500 "Model artifact not found"**
- Model file is missing from Railway
- Check `services/api/artifacts/models/` has a model file
- Redeploy if needed

### **Railway deployment fails**
- Check Railway logs for errors
- Common issues:
  - Missing environment variables
  - Dockerfile errors
  - Out of memory (dataset too large)
  - Build timeout (reduce dataset size)

### **Betfair login fails**
- Check credentials in `.env` are correct
- Password has special characters - make sure properly escaped
- Test login: `python3 -c "from betfair_client import BetfairClient; c=BetfairClient(); c.login(); print('Success')"`

---

## 📞 Support & Resources

### **Documentation**
- **This File**: `PROJECT_STATUS.md` (most comprehensive)
- **Main README**: `README.md` (overview)
- **Deployment Guide**: `VERCEL_DEPLOYMENT.md` (step-by-step deployment)
- **Betfair Setup**: `docs/BETFAIR_QUICKSTART.md`

### **External Resources**
- **Betfair API Docs**: https://docs.developer.betfair.com/
- **PuntingForm API**: https://www.puntingform.com.au/api
- **Railway Docs**: https://docs.railway.app/
- **Vercel Docs**: https://vercel.com/docs
- **LightGBM Docs**: https://lightgbm.readthedocs.io/

### **GitHub Repository**
- **Issues**: https://github.com/juggajay/HorseRacingML/issues
- **Code**: https://github.com/juggajay/HorseRacingML

### **Contact**
- **GitHub**: @juggajay
- **Email**: jryan1810@gmail.com
- **Betfair Support**: automation@betfair.com.au
- **PuntingForm Support**: support@puntingform.com.au

---

## ✅ Quick Reference

### **Most Important Files**
1. `services/api/main.py` - Backend API logic
2. `web/pages/index.tsx` - Frontend UI
3. `services/api/data/processed/pf_schema/` - Production dataset (meetings/races/runners)
4. `services/api/artifacts/models/betfair_kash_top5_model_*.txt` - Production model
5. `.env` - Local credentials (not in git)
6. `fetch_todays_races_simple.py` - Data fetching script

### **Most Important Commands**
```bash
# Run locally
cd services/api && uvicorn main:app --reload --port 8000
cd web && npm run dev

# Fetch fresh data
python3 fetch_todays_races_simple.py

# Train model
python3 train_model_pf.py

# Deploy
git push origin master

# Test API
curl https://horseracingml-production.up.railway.app/health
```

### **Most Important URLs**
- **Production Frontend**: https://horse-racing-ml.vercel.app
- **Production API**: https://horseracingml-production.up.railway.app
- **Railway Dashboard**: https://railway.app
- **Vercel Dashboard**: https://vercel.com
- **GitHub Repo**: https://github.com/juggajay/HorseRacingML

---

## 🎉 You're All Set!

This project is **production-ready** and **fully deployed**. The system successfully:
- ✅ Fetches live horse racing data from Betfair
- ✅ Makes ML predictions with 86.8% AUC
- ✅ Identifies value betting opportunities
- ✅ Serves predictions via REST API
- ✅ Displays results in beautiful web UI
- ✅ Auto-deploys on git push

**Welcome aboard!** 🚀🐴

---

**Last Updated**: October 15, 2025
**Version**: 1.0.0
**Status**: Production
**Maintained By**: @juggajay
