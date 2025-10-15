from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from lightgbm import Booster

from feature_engineering import engineer_all_features, get_feature_columns

DATA_PATH = Path("data/processed/ml/betfair_kash_top5.csv.gz")
MODEL_DIR = Path("artifacts/models")

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
        raise HTTPException(status_code=404, detail=f"No runners found on {target_date}")
    return subset


def _score(df_raw: pd.DataFrame, booster: Booster) -> pd.DataFrame:
    df_feat = engineer_all_features(df_raw)
    feature_cols = [c for c in get_feature_columns() if c in df_feat.columns]
    predictions = booster.predict(df_feat[feature_cols])
    df_feat["model_prob"] = predictions
    df_feat["implied_prob"] = 1.0 / (df_feat["win_odds"] + 1e-9)
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
    date_str: Optional[str] = Query(None, description="YYYY-MM-DD"),
    margin: float = Query(1.05, ge=1.0),
    top: Optional[int] = Query(None, ge=1),
) -> dict:
    target_date = date.fromisoformat(date_str) if date_str else date.today()
    subset = _load_dataset(target_date)
    booster = _latest_model()
    scored = _score(subset, booster)

    scored["edge_margin"] = scored["model_prob"] - scored["implied_prob"] * margin
    filtered = scored[scored["edge_margin"] > 0].copy()
    filtered = filtered.sort_values(["event_date", "edge_margin"], ascending=[True, False])
    if top:
        filtered = filtered.groupby(["event_date", "win_market_id"]).head(top).reset_index(drop=True)

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
        "edge_margin",
        "value_pct",
        "betfair_horse_rating",
        "win_rate",
        "model_rank",
    ]
    data = filtered[cols].to_dict(orient="records")
    return {"date": target_date.isoformat(), "margin": margin, "selections": data}
