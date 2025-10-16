# HorseRacingML – Context & Deployment Plan

This document captures the state of the HorseRacingML project as of October 2025 and lays out the path to a production‑grade system with a professional UI that surfaces live racing selections. Everything referenced here runs on free‑tier tooling by default.

---

## 1. Vision Snapshot

| Layer | Current Status | Target Outcome |
| --- | --- | --- |
| **Data** | 2019‑09 → 2025‑09 Betfair runners, Kash & Top5 priors | Automated daily ingestion + PF Pro when available |
| **Model** | LightGBM, AUC ≈ 0.86, walk‑forward POT > 70% (needs leakage checks) | Scheduled retraining with guardrails, versioned artifacts |
| **Delivery** | CLI scripts for scoring/backtests | FastAPI scoring service + React UI on Vercel |
| **Ops** | Manual shell commands | CI/CD, observability, paper‑trading dashboard |

---

## 2. Tech Stack (Free Tier Friendly)

| Domain | Tooling |
| --- | --- |
| Web UI | **Next.js on Vercel** (Hobby tier) |
| Backend API | FastAPI + Uvicorn (Vercel Edge Functions or small VPS) |
| Worker Jobs | GitHub Actions / Vercel Cron for light tasks |
| Storage | PostgreSQL (Supabase free tier) or PlanetScale MySQL (Hobby) for metadata; S3‑compatible bucket (Wasabi free trial/MinIO) for large artifacts |
| Caching | Upstash Redis (free tier) for live cards |
| Auth | Vercel JWT or Clerk.dev free tier |
| Monitoring | Logtail/BetterStack free tier + Grafana Cloud Free |

All selections rely on **PUNTINGFORM_API_KEY**—store this in Vercel “Environment Variables” and in local `.env`. No paid subscriptions are required to reach MVP.

---

## 3. Data & Model Pipeline

### 3.1 Ingestion Scripts

| Script | Description |
| --- | --- |
| `unify_betfair_years.py` | Consolidates monthly `ANZ_Thoroughbreds_YYYY_MM.csv` into yearly `betfair_all_raw_YYYY.csv.gz`. Source roots via `MONTH_SRC`. |
| `scripts/enrich_betfair_with_external_models.py` | Left-joins Kash & Top5 priors onto Betfair rows (IDs + event date). |
| `scripts/prepare_betfair_training_dataset.py` | Normalises names, injects Betfair horse ratings, converts Kash metrics, outputs `data/processed/ml/betfair_kash_top5.csv.gz`. |
| `scripts/build_pf_schema_from_betfair.py` | Reshapes the Betfair slice into PF-style `meetings/ races/ runners` tables under `services/api/data/processed/pf_schema/`. |
| `scripts/pf_smoke_test.py` | Confirms the PF API key works and returns live meetings/starters. |
| `betfair_client.py` | Handles login and API calls using the free delayed app key. |
| `betfair_live.py` | Shapes Betfair API responses into runner-level data ready for scoring. |
| `scripts/fetch_betfair_markets.py` | CLI to export live markets to `data/processed/live/betfair_live_<date>.csv`. |

When PF Pro is enabled, re‑enable `merge_pf_to_betfair.py` to fold PF ratings into the dataset (the feature pipeline already handles those columns).

### 3.2 Training & Backtesting

| Script | Purpose |
| --- | --- |
| `train_model_pf.py` | Trains LightGBM, writes metrics, and should be extended to save booster models under `artifacts/models/`. |
| `scripts/backtest_walkforward.py` | Month‑by‑month walk‑forward evaluation with configurable staking margins. Outputs detailed and aggregated CSVs under `artifacts/`. |

**Guardrails to add before production:**
1. Verify no leakage from Kash/Top5 (audit the source calculations).
2. Add odds/liquidity filters (cap BSP, require min matched volume).
3. Fail a CI check if walk‑forward POT falls below threshold.

---

## 4. Environment Configuration

Create `.env` (not committed) and or `.env.local` for Vercel:

```env
# Required for PF API usage
PUNTINGFORM_API_KEY=sk_live_...

# Optional toggles
PF_MODE=starter   # or "pro" when PF form data is available
BETTING_MARGIN=1.05
DATABASE_URL=postgresql://...
REDIS_URL=...

# Betfair API (delayed) credentials
BETFAIR_APP_KEY=your_delayed_app_key
BETFAIR_USERNAME=your_betfair_username
BETFAIR_PASSWORD=your_betfair_password
```

Vercel deployment → Settings → Environment Variables → add the same keys (`PUNTINGFORM_API_KEY`, `PF_MODE`, etc.).

---

## 5. Implementation Roadmap

### Phase 1 – Automate Pipeline
1. **Data drop**: nightly GitHub Action moves new Betfair/Kash/Top5 CSVs into S3 + local cache.
2. **Run ingestion trio**: `unify_betfair_years.py`, `enrich_betfair_with_external_models.py`, `prepare_betfair_training_dataset.py`.
3. **Smoke check**: `PF_DATE=$(date +%F)` `python3 scripts/pf_smoke_test.py`.
4. **Log**: insert record into `pipeline_runs` table (status, rows processed, checksum).

### Phase 2 – Model Service
1. Update `train_model_pf.py` to persist to `artifacts/models/model_<date>.txt`. ✅
2. Build `scripts/score_today.py` (loads latest model, scores races, applies staking rule). ✅ (`--source betfair` hits live API)
3. Wrap scoring in FastAPI microservice (deployed as Vercel Serverless Function): ✅
   - `GET /races/:date` → raw runners + probabilities.
   - `POST /bets` → returns filtered selections according to margin.
4. Store selections in DB with status fields (`open`, `settled`, POT).

### Phase 3 – UI on Vercel
1. Next.js app (TypeScript) scaffolded under `web/` (SWR + API client). ✅
2. Current page: `/` dashboard with date + margin selectors and selections table. Future enhancements can add race detail/settings pages.
3. UI consumes API via `NEXT_PUBLIC_API_BASE` (ready for Vercel deployment).
4. Deploy on Vercel Hobby once API endpoint is hosted.

### Phase 4 – Monitoring & Ops
1. Instrument FastAPI with structured JSON logs (ship to Logtail free tier).
2. Nightly report (GitHub Action) summarising POT, bet counts, AUC.
3. Alert (email/Slack) if pipeline fails, PF API smoke test fails, or model metrics dip below target.

---

## 6. Daily Runbook (Starter Mode)

1. **Option A: Historical dataset refresh**
   ```bash
   MONTH_SRC="/mnt/c/Users/jayso/OneDrive/ML data" python3 unify_betfair_years.py
   python3 scripts/prepare_external_model_data.py
   python3 scripts/enrich_betfair_with_external_models.py
   python3 scripts/prepare_betfair_training_dataset.py
   LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH python3 train_model_pf.py
   LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH python3 scripts/backtest_walkforward.py
   ```
   Review `artifacts/walkforward_summary.csv` and `artifacts/models/` for the latest booster.

2. **Option B: Live scoring straight from Betfair API**
   ```bash
   python3 scripts/score_today.py --source betfair --date $(date +%F) --margin 1.05 --top 3
   ```
   (Requires `BETFAIR_APP_KEY`, `BETFAIR_USERNAME`, `BETFAIR_PASSWORD`.)

3. **Save selections**: `artifacts/selections_YYYYMMDD.csv` contains the output; UI & API reflect the same data.

Switch to **Pro mode** once PF ratings are included:
- Set `PF_MODE=pro` and use the PF API client to populate `data/processed/puntingform/YYYY_MM/*`.
- Rerun merge and dataset prep to incorporate PF features.

---

## 7. Outstanding Tasks Before “Professional UI”

- [x] Implement `scripts/score_today.py` & persist model boosters.
- [x] Build FastAPI service with routes for scoring & health checks.
- [x] Scaffold Next.js UI on Vercel (Starter plan) with basic dashboard.
- [ ] Integrate PF API smoke test into pipeline; fail job if no meetings returned.
- [ ] Add data-leakage diagnostics (ablation without Kash/Top5).
- [ ] Create test suite (pytest) for key scripts & feature pipeline.
- [ ] Document downtime/rollback strategy in `docs/runbook.md` (future work).

---

## 8. References

- Betfair data source: `OneDrive/ML data/ANZ_Thoroughbreds_*.csv`
- External priors: `data/processed/external_models/kash_model_results.csv.gz`, `.../top5_model_results.csv.gz`
- Primary dataset: `services/api/data/processed/pf_schema/` (PF-aligned tables built from `betfair_kash_top5.csv.gz`)
- Walk-forward details: `artifacts/walkforward_results.csv`
- Model summary: `artifacts/pf_feature_importance.csv`, `artifacts/pf_enhanced_results.csv`

For any new collaborator, `docs/context.md` is the launch pad. Combine it with the main README for onboarding and keep it updated as PF Pro features become available.
