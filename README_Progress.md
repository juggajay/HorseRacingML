# HorseRacingML Progress Log

## Environment Setup
- Project root normalized to `C:\Users\jayso\Documents\HorseRacingML`.
- Core Python dependencies installed/updated: `pandas`, `numpy`, `scikit-learn`, `lightgbm`, `python-dotenv`, `rapidfuzz`.

## Data Ingestion & Normalisation
- Flattened Punting Form project structure and verified `.env` configuration.
- Updated PF client to v2 API endpoints and scripted weekly updater (Starter-plan safe).
- Generated processed PF form + meetings CSVs for 2025-10.
- Converted monthly Betfair ANZ CSVs (2023-2025) into yearly `betfair_all_raw_20xx.csv.gz` with `unify_betfair_years.py`.

## PF ↔ Betfair Joining
- Implemented `merge_pf_to_betfair.py` with meeting-level fan-out and Starter-plan toggles.
- First pass achieved 0 rows (bench/sectionals locked); after adjustments + form-only strategy, produced `2025_10__form.csv` & `2025_10__meetings.csv`.
- Enhanced merge script to support v2 schemas and adaptive column detection; final merge produced **992 rows** (PF + Betfair) saved to `data/processed/ml/pf_betfair_merged.csv.gz`.

## Kaggle Integration Attempts
- Extracted Kaggle `field.csv` (2021 harness dataset) but direct join to 2025 PF data yielded 0 matches (non-overlapping cohorts).
- Script `merge_kaggle_pf_betfair.py` documented join rate (0%) and outputs empty merged file for transparency.

## Historical Priors
- Created `build_horse_ratings_from_kaggle.py`: trained LightGBM model on ≤2021 Kaggle runners and saved **906** horse ratings to `artifacts/horse_ratings_2021.csv`.
- Applied priors via `apply_horse_ratings_to_pf_betfair.py`; coverage currently 0% because PF runners lack historical Kaggle overlap, but pipeline ready when data overlaps.

## Outputs Snapshot
- `data/processed/puntingform/2025_10/2025_10__form.csv` (9,956 rows)
- `data/processed/puntingform/2025_10/2025_10__meetings.csv` (137 rows)
- `betfair_all_raw_2023.csv.gz`, `betfair_all_raw_2024.csv.gz`, `betfair_all_raw_2025.csv.gz`
- `data/processed/ml/pf_betfair_merged.csv.gz` (992 rows)
- `artifacts/horse_ratings_2021.csv` (906 rows)
- `data/processed/ml/pf_betfair_with_kagglepriors.csv.gz` (992 rows, ratings NA for now)
- `data/processed/ml/betfair_kash_top5.csv.gz` (529,686 rows, 2023-01 → 2025-09)
- `artifacts/models/betfair_kash_top5_model_<timestamp>.txt` (LightGBM boosters)
- `artifacts/walkforward_summary.csv` & `walkforward_results.csv` (monthly backtest metrics)
- `data/processed/live/betfair_live_YYYYMMDD.csv` (exported via Betfair API)

## Next Ideas
- Source modern Kaggle/Betfair runner datasets with overlapping years to increase prior coverage.
- Engineer feature store merging PF (form), Betfair (markets/API), and external priors with consistent track/horse normalization.
- Automate daily pipeline (PF fetch → Betfair API → rating update) via scheduled task.
