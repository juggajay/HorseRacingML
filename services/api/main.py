from __future__ import annotations

import json
import asyncio
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from lightgbm import Booster
from pydantic import BaseModel
from zoneinfo import ZoneInfo

from feature_engineering import engineer_all_features, get_feature_columns
try:
    from .pf_schema_loader import load_pf_dataset
except ImportError:  # Fallback for environments running as top-level module
    from pf_schema_loader import load_pf_dataset

try:
    from .pf_live_loader import load_live_pf_day
except ImportError:
    from pf_live_loader import load_live_pf_day

try:
    from .ace_runner import append_pf_schema_day, run_ace_pipeline_async
except ImportError:
    from ace_runner import append_pf_schema_day, run_ace_pipeline_async

DATA_PATH = Path("data/processed/ml/betfair_kash_top5.csv.gz")
MODEL_DIR = Path("artifacts/models")
PLAYBOOK_PATH = Path("artifacts/playbook/playbook.json")
ACE_SCHEMA_DIR = Path("data/processed/pf_schema_full")
ACE_STRATEGIES_PATH = Path("configs/strategies_default.json")
ACE_EXPERIENCE_DIR = Path("data/experiences")
ACE_MIN_BETS = 30
SYDNEY_TZ = ZoneInfo("Australia/Sydney")

app = FastAPI(title="HorseRacingML API", version="0.1.0")

# Add CORS middleware to allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache model and dataset at startup
_cached_model: Optional[Booster] = None
_cached_data: Optional[pd.DataFrame] = None
_ace_lock = asyncio.Lock()


@app.on_event("startup")
async def startup_event():
    """Pre-load model and dataset on startup to avoid first-request timeout"""
    global _cached_model, _cached_data
    print("Loading dataset and model at startup...")
    try:
        # Pre-load dataset
        _load_full_dataset()
        print("Dataset loaded successfully!")
    except Exception as e:
        print(f"Warning: Could not pre-load dataset at startup: {e}")
        print("Dataset will be loaded on first request instead.")

    try:
        # Pre-load model
        _latest_model()
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Warning: Could not pre-load model at startup: {e}")
        print("Model will be loaded on first request instead.")


def _latest_model() -> Booster:
    global _cached_model
    if _cached_model is None:
        models = sorted(MODEL_DIR.glob("betfair_kash_top5_model_*.txt"))
        if not models:
            raise HTTPException(status_code=500, detail="Model artifact not found. Train the model first.")
        _cached_model = Booster(model_file=str(models[-1]))
    return _cached_model


def _load_full_dataset() -> pd.DataFrame:
    global _cached_data
    if _cached_data is None:
        pf_df = load_pf_dataset()
        if pf_df is not None and not pf_df.empty:
            _cached_data = pf_df
        else:
            if not DATA_PATH.exists():
                raise HTTPException(status_code=500, detail="Training dataset missing. Run data prep pipeline first.")
            _cached_data = pd.read_csv(DATA_PATH, low_memory=False)
            _cached_data["event_date"] = pd.to_datetime(_cached_data["event_date"], errors="coerce")
            _cached_data = _cached_data.dropna(subset=["event_date"]).copy()
    return _cached_data


def _load_dataset(target_date: date) -> pd.DataFrame:
    df = _load_full_dataset()
    mask = df["event_date"].dt.date == target_date
    subset = df.loc[mask]
    if subset.empty:
        live_df = load_live_pf_day(target_date)
        if live_df is None or live_df.empty:
            raise HTTPException(status_code=404, detail=f"No runners found on {target_date}")
        live_df = live_df.copy()
        live_df["event_date"] = pd.to_datetime(live_df["event_date"], errors="coerce")
        return live_df
    return subset


def _load_playbook() -> dict:
    if not PLAYBOOK_PATH.exists():
        raise HTTPException(status_code=404, detail="Playbook artifact not found")
    try:
        return json.loads(PLAYBOOK_PATH.read_text())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Playbook artifact is invalid JSON") from exc


class AceRunRequest(BaseModel):
    force_refresh: bool = False


class AceRunResponse(BaseModel):
    status: str
    message: str
    target_date: str
    started_at: str
    finished_at: str
    duration_seconds: float
    experience_rows: int
    strategies_evaluated: int
    global_pot_pct: Optional[float]
    global_total_bets: Optional[int]
    playbook_generated_at: Optional[str]
    schema_meetings_added: int
    schema_races_added: int
    schema_runners_added: int


def _score(df_raw: pd.DataFrame, booster: Booster) -> pd.DataFrame:
    df_feat = engineer_all_features(df_raw)
    feature_cols = [c for c in get_feature_columns() if c in df_feat.columns]
    predictions = booster.predict(df_feat[feature_cols])
    df_feat["model_prob"] = predictions
    df_feat["win_odds"] = pd.to_numeric(df_feat.get("win_odds"), errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        df_feat["implied_prob"] = 1.0 / df_feat["win_odds"]
    df_feat.loc[~np.isfinite(df_feat["implied_prob"]), "implied_prob"] = np.nan

    missing_implied = df_feat["implied_prob"].isna()
    if missing_implied.any():
        field_sizes = df_feat.groupby(["event_date", "win_market_id"])['selection_id'].transform("count")
        uniform_probs = 1.0 / field_sizes.replace(0, 1)
        df_feat.loc[missing_implied, "implied_prob"] = uniform_probs[missing_implied]
        df_feat.loc[missing_implied, "win_odds"] = 1.0 / df_feat.loc[missing_implied, "implied_prob"].replace(0, np.nan)

    df_feat["edge"] = df_feat["model_prob"] - df_feat["implied_prob"]
    return df_feat


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/races")
def get_races(date_str: Optional[str] = Query(None, description="YYYY-MM-DD")) -> dict:
    target_date = date.fromisoformat(date_str) if date_str else date.today()
    subset = _load_dataset(target_date)
    booster = _latest_model()
    scored = _score(subset, booster)
    cols = [
        "event_date",
        "track",
        "race_no",
        "win_market_id",
        "selection_id",
        "selection_name",
        "win_odds",
        "model_prob",
        "implied_prob",
        "edge",
        "value_pct",
        "betfair_horse_rating",
        "win_rate",
        "model_rank",
    ]
    data = scored[cols].to_dict(orient="records")
    return {"date": target_date.isoformat(), "runners": data}


@app.get("/selections")
def get_selections(
    date_str: Optional[str] = Query(None, description="YYYY-MM-DD or YYYY-MM-DD:YYYY-MM-DD for date range"),
    margin: float = Query(1.05, ge=1.0),
    top: Optional[int] = Query(None, ge=1),
    limit: int = Query(5000, ge=1, le=50000, description="Max total selections to return"),
) -> dict:
    # Handle date range (e.g., "2025-10-16:2025-10-22" for a week)
    if date_str and ":" in date_str:
        start_str, end_str = date_str.split(":")
        start_date = date.fromisoformat(start_str)
        end_date = date.fromisoformat(end_str)
        df = _load_full_dataset()
        subset = df[(df["event_date"].dt.date >= start_date) & (df["event_date"].dt.date <= end_date)].copy()
        if subset.empty:
            raise HTTPException(status_code=404, detail=f"No runners found between {start_date} and {end_date}")
    else:
        target_date = date.fromisoformat(date_str) if date_str else date.today()
        subset = _load_dataset(target_date)

    booster = _latest_model()
    scored = _score(subset, booster)

    scored["edge_margin"] = scored["model_prob"] - scored["implied_prob"] * margin
    filtered = scored[scored["edge_margin"] > 0].copy()
    filtered = filtered.sort_values(["event_date", "edge_margin"], ascending=[True, False])
    if top:
        filtered = filtered.groupby(["event_date", "win_market_id"]).head(top).reset_index(drop=True)

    # Apply limit to prevent response size issues
    limited = len(filtered) > limit
    filtered = filtered.head(limit)

    # Select only columns that exist in the dataframe
    desired_cols = [
        "event_date",
        "track",
        "race_no",
        "win_market_id",
        "selection_id",
        "selection_name",
        "win_odds",
        "model_prob",
        "implied_prob",
        "edge_margin",
        "value_pct",
        "betfair_horse_rating",
        "win_rate",
        "model_rank",
    ]
    cols = [c for c in desired_cols if c in filtered.columns]
    data = filtered[cols].to_dict(orient="records")

    # Prepare response with date info
    if date_str and ":" in date_str:
        date_info = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
    else:
        date_info = {"date": target_date.isoformat()}

    return {
        **date_info,
        "margin": margin,
        "selections": data,
        "total": len(data),
        "limited": limited,
    }


@app.get("/playbook")
def get_playbook() -> dict:
    """Return the latest ACE playbook snapshot."""
    return _load_playbook()


@app.get("/ace/status")
def get_ace_status() -> dict:
    """Check ACE system readiness and configuration."""
    status = {
        "playbook_exists": PLAYBOOK_PATH.exists(),
        "strategies_config_exists": ACE_STRATEGIES_PATH.exists(),
        "schema_dir_exists": ACE_SCHEMA_DIR.exists(),
        "experience_dir_exists": ACE_EXPERIENCE_DIR.exists(),
        "model_available": False,
        "pf_credentials_configured": False,
    }

    # Check model availability
    try:
        models = list(MODEL_DIR.glob("betfair_kash_top5_model_*.txt"))
        status["model_available"] = len(models) > 0
        if models:
            status["latest_model"] = str(models[-1].name)
    except Exception:
        pass

    # Check PuntingForm credentials
    import os
    status["pf_credentials_configured"] = bool(os.getenv("PUNTINGFORM_API_KEY"))

    # Check if ACE is ready to run
    status["ready"] = (
        status["model_available"]
        and status["pf_credentials_configured"]
    )

    return status


@app.post("/ace/run", response_model=AceRunResponse)
async def run_ace_endpoint(payload: AceRunRequest) -> AceRunResponse:
    if _ace_lock.locked():
        raise HTTPException(status_code=409, detail="ACE run already in progress")

    async with _ace_lock:
        started_at = datetime.utcnow()
        target_date = datetime.now(tz=SYDNEY_TZ).date()

        try:
            # Always force refresh to get latest data with current odds
            live_df = load_live_pf_day(target_date, force=True)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch PuntingForm data: {str(e)}. Check API credentials."
            ) from e

        if live_df is None or live_df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No PF live data available for {target_date}. Meetings may not be published yet."
            )

        ACE_SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
        ACE_EXPERIENCE_DIR.mkdir(parents=True, exist_ok=True)

        try:
            schema_stats = append_pf_schema_day(live_df, ACE_SCHEMA_DIR)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to append schema data: {str(e)}"
            ) from e

        try:
            result = await run_ace_pipeline_async(
                start=target_date,
                end=target_date,
                pf_schema_dir=ACE_SCHEMA_DIR,
                strategies_path=ACE_STRATEGIES_PATH,
                experience_dir=ACE_EXPERIENCE_DIR,
                playbook_path=PLAYBOOK_PATH,
                max_races=None,
                min_bets=ACE_MIN_BETS,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"ACE pipeline failed: {str(e)}. Check model artifacts and config files."
            ) from e

        finished_at = datetime.utcnow()
        duration = (finished_at - started_at).total_seconds()

        playbook_dict = result.get("playbook", {})
        latest = playbook_dict.get("latest", playbook_dict)
        metadata = latest.get("metadata", {})
        global_stats = latest.get("global", {})

        return AceRunResponse(
            status="completed",
            message="ACE run finished successfully",
            target_date=target_date.isoformat(),
            started_at=started_at.isoformat() + "Z",
            finished_at=finished_at.isoformat() + "Z",
            duration_seconds=duration,
            experience_rows=result.get("experience_rows", 0),
            strategies_evaluated=result.get("strategies_evaluated", 0),
            global_pot_pct=global_stats.get("pot_pct"),
            global_total_bets=global_stats.get("total_bets"),
            playbook_generated_at=metadata.get("generated_at"),
            schema_meetings_added=schema_stats.get("meetings", 0),
            schema_races_added=schema_stats.get("races", 0),
            schema_runners_added=schema_stats.get("runners", 0),
        )
