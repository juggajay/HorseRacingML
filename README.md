# HorseRacingML - AI-Powered Horse Racing Predictions

Machine learning system for predicting horse racing outcomes using Betfair market data and PuntingForm ratings.

## Features

- **LightGBM ML Model** - Trained on 529K+ races (2023-2025)
- **Test AUC**: 0.868
- **Profit on Turnover (POT)**: 68.18%
- **Real-time Betfair API Integration** - FREE delayed data access
- **PuntingForm API Integration** - Professional form ratings
- **Docker Deployment** - Production-ready containerized services
- **FastAPI Backend** - High-performance REST API
- **Next.js Frontend** - Modern web interface

## Architecture

```
┌─────────────────┐     ┌──────────────────┐
│  PuntingForm    │────▶│                  │
│      API        │     │  Feature         │
└─────────────────┘     │  Engineering     │
                        │                  │
┌─────────────────┐     │                  │
│  Betfair API    │────▶│  (45 features)   │
│  (Delayed Key)  │     │                  │
└─────────────────┘     └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  LightGBM Model  │
                        │  (500 trees)     │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  FastAPI + UI    │
                        │  (Docker)        │
                        └──────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Betfair account (FREE delayed API key)
- PuntingForm account (optional)

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd HorseRacingML
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:
```bash
BETFAIR_APP_KEY=your_delayed_app_key
BETFAIR_USERNAME=your_username
BETFAIR_PASSWORD=your_password
PUNTINGFORM_API_KEY=your_key (optional)
```

### 3. Start Services

```bash
docker-compose up -d
```

Services:
- **API**: http://localhost:8000
- **UI**: http://localhost:3000

## Data Pipeline

### Fetch Live Betfair Data

```bash
python fetch_betfair_todays_data.py
```

Output: `data/processed/betfair/betfair_snapshot_YYYYMMDD_HHMMSS.csv`

### Train Model

```bash
python train_model_pf.py
```

Output: `artifacts/models/betfair_kash_top5_model_TIMESTAMP.txt`

## API Endpoints

### Health Check
```bash
GET /health
```

### Get Today's Races
```bash
GET /races?date_str=2025-10-15
```

### Get Value Selections
```bash
GET /selections?date_str=2025-10-15&margin=1.05&top=3
```

## Model Features (45 total)

### Market Features (6)
- `win_odds`, `total_matched`, `is_favorite`, `odds_vs_favorite`, `volume_rank`, `is_high_volume`

### Form Cycle (6)
- `days_since_last_run`, `is_spell`, `prep_run_number`, `is_first_up`, `is_second_up`, `is_third_up`

### Historical Performance (9)
- `betfair_horse_rating`, `win_rate`, `place_rate`, `total_starts`, `betfair_rating_advantage`, `is_experienced`, `is_novice`, `is_strong_form`, `is_consistent`

### PuntingForm Features (15)
- Various ratings and AI scores (when available)

### Interaction Features (9)
- Combined and derived features

## Performance Metrics

### Model Performance
- **Train AUC**: 0.885
- **Test AUC**: 0.868
- **Train LogLoss**: 0.221
- **Test LogLoss**: 0.230

### Betting Simulation (Test Set)
- **Total Bets**: 48,405
- **Profit on Turnover**: 68.18%
- **Test Period**: March 2025 - September 2025

## Project Structure

```
HorseRacingML/
├── services/
│   └── api/
│       ├── Dockerfile
│       └── main.py              # FastAPI application
├── web/
│   ├── Dockerfile
│   ├── pages/
│   ├── components/
│   └── package.json             # Next.js UI
├── data/
│   ├── raw/                     # Raw data (gitignored)
│   └── processed/               # Processed data (gitignored)
├── artifacts/
│   └── models/                  # Trained models (gitignored)
├── docs/
│   ├── BETFAIR_QUICKSTART.md
│   ├── BETFAIR_API_SETUP.md
│   └── BETFAIR_README.md
├── betfair_client.py            # Betfair API wrapper
├── feature_engineering.py       # Feature pipeline
├── train_model_pf.py           # Model training
├── fetch_betfair_todays_data.py # Data fetching
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Run API
cd services/api
uvicorn main:app --reload --port 8000

# Run UI (separate terminal)
cd web
npm install
npm run dev
```

### Run Tests

```bash
python betfair_client.py  # Test Betfair connection
```

## Deployment

### Production Environment Variables

Create `.env.production`:
```bash
BETFAIR_APP_KEY=your_live_key (£299 activation)
BETFAIR_USERNAME=your_username
BETFAIR_PASSWORD=your_password
```

### Docker Production Build

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Cloud Deployment Options

- **AWS ECS/Fargate** - Container orchestration
- **Google Cloud Run** - Serverless containers
- **DigitalOcean App Platform** - Simple deployment
- **Heroku** - Easy setup with containers

## Betfair API Setup

### Get FREE Delayed API Key

1. **Create Betfair account**: https://register.betfair.com/account/registration
2. **Login**: https://www.betfair.com
3. **Get SSOID token from browser console**:
   ```javascript
   document.cookie.split(';').find(c=>c.includes('ssoid'))
   ```
4. **Create app key**: Run `python create_betfair_appkey.py`
5. **Update .env** with your Delayed App Key

**Full instructions**: See `docs/BETFAIR_QUICKSTART.md`

### Upgrade to Live Key (Optional)

- **Cost**: £299 one-time fee
- **Benefits**: Real-time data, no delay
- **Contact**: automation@betfair.com.au

## Data Sources

### Betfair Exchange API
- **Type**: Delayed (FREE) or Live (£299)
- **Coverage**: Australian & International racing
- **Data**: Market odds, volumes, runner metadata

### PuntingForm API
- **Tiers**: Starter (FREE) or Professional
- **Coverage**: Australian racing
- **Data**: Form ratings, sectionals, benchmarks

## Security

- **Never commit `.env`** - Contains API credentials
- **Use environment variables** - All sensitive config
- **Rotate credentials** - Regularly update passwords
- **HTTPS only** - Production deployments

## Roadmap

- [ ] Automated daily data pipeline
- [ ] Live odds monitoring dashboard
- [ ] SMS/Email alerts for value bets
- [ ] Multi-model ensemble predictions
- [ ] Historical performance tracking
- [ ] Bankroll management tools
- [ ] Live in-play betting integration

## License

MIT License - See LICENSE file

## Disclaimer

This software is for educational and research purposes only.

**Gambling involves risk.** Past performance does not guarantee future results. Always gamble responsibly and within your means. Check your local laws regarding sports betting.

The authors are not responsible for any financial losses incurred through use of this software.

## Support

- **Documentation**: `docs/` directory
- **Issues**: GitHub Issues
- **Betfair Support**: automation@betfair.com.au
- **PuntingForm Support**: support@puntingform.com.au

## Acknowledgments

- Betfair Exchange API
- PuntingForm Racing Data
- LightGBM Framework
- FastAPI & Next.js Communities

---

**Built with ❤️ for horse racing enthusiasts and data scientists**

Version: 1.0.0 | Last Updated: October 2025
