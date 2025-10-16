"""ACE/ICE orchestration helpers reusable by the API and CLI."""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Import from local services/api/ace for Railway/container use, fallback to top-level ace for CLI
try:
    from services.api.ace.early_experience import EarlyExperienceRunner, ExperienceConfig, ExperienceWriter
    from services.api.ace.playbook import ACEReflector, PlaybookCurator
    from services.api.ace.simulator import Simulator
    from services.api.ace.strategies import StrategyConfig, StrategyGrid
except ImportError:
    from ace.early_experience import EarlyExperienceRunner, ExperienceConfig, ExperienceWriter
    from ace.playbook import ACEReflector, PlaybookCurator
    from ace.simulator import Simulator
    from ace.strategies import StrategyConfig, StrategyGrid

from feature_engineering import engineer_all_features, get_feature_columns

# Import pf_schema_loader - use relative import for Railway/container, fallback for CLI
try:
    from pf_schema_loader import load_pf_dataset
except ImportError:
    from services.api.pf_schema_loader import load_pf_dataset


def _normalise_track(value: pd.Series) -> pd.Series:
    return (
        value.astype(str)
        .str.lower()
        .str.replace(r"[^a-z0-9\s]", "", regex=True)
        .str.replace(r"\s+", " ", regex=True)
    )


def _make_meeting_id(track_norm: str, event_date: date) -> str:
    import hashlib

    key = f"{track_norm}|{event_date.isoformat()}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return f"pfm_{digest}"


def _make_race_id(win_market_id: str) -> str:
    return f"pfr_{win_market_id}"


def _ensure_schema_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Ensure event_date exists and is valid
    df["event_date"] = pd.to_datetime(df.get("event_date"), errors="coerce")
    df = df.dropna(subset=["event_date"])

    # Ensure track columns exist
    if "track" not in df.columns:
        df["track"] = df.get("track_name", df.get("track_name_norm", "Unknown"))

    df["track_name_norm"] = _normalise_track(df.get("track_name_norm", df.get("track", "")))
    df["state_code"] = df.get("state_code", "")
    df["win_market_name"] = df.get("win_market_name", df.get("race_name", ""))
    df["scheduled_race_time"] = df.get("scheduled_race_time", df.get("race_time"))
    df["actual_off_time"] = df.get("actual_off_time")
    df["racing_type"] = df.get("racing_type", "Thoroughbred")
    df["race_type"] = df.get("race_type", "")
    df["distance"] = pd.to_numeric(df.get("distance"), errors="coerce")

    # Ensure required ID columns exist
    if "win_market_id" not in df.columns:
        raise ValueError("DataFrame missing required column: win_market_id")
    df["win_market_id"] = df["win_market_id"].astype(str)

    df["race_no"] = pd.to_numeric(df.get("race_no"), errors="coerce").astype("Int64")

    if "selection_id" not in df.columns:
        raise ValueError("DataFrame missing required column: selection_id")
    df["selection_id"] = df["selection_id"].astype(str)

    if "selection_name" not in df.columns:
        df["selection_name"] = df.get("horse_name", df["selection_id"])

    # Generate meeting_id after ensuring track_name_norm exists
    df["meeting_id"] = df.apply(
        lambda row: _make_meeting_id(row["track_name_norm"], pd.to_datetime(row["event_date"]).date()), axis=1
    )
    return df


def append_pf_schema_day(live_df: pd.DataFrame, schema_dir: Path) -> dict:
    """Append a single day's PF live data into a schema directory."""

    if live_df is None or live_df.empty:
        return {"meetings": 0, "races": 0, "runners": 0}

    schema_dir.mkdir(parents=True, exist_ok=True)
    live_df = _ensure_schema_columns(live_df)

    meetings_path = schema_dir / "meetings.parquet"
    races_path = schema_dir / "races.parquet"
    runners_path = schema_dir / "runners.parquet"
    manifest_path = schema_dir / "manifest.json"

    # Select columns for meetings, ensuring they exist
    meeting_cols = ["event_date", "track", "track_name_norm", "state_code"]
    missing_cols = [col for col in meeting_cols if col not in live_df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns for meetings: {missing_cols}. Available columns: {list(live_df.columns)}")

    live_meetings = (
        live_df[meeting_cols]
        .drop_duplicates()
        .copy()
    )
    live_meetings["event_date"] = pd.to_datetime(live_meetings["event_date"], errors="coerce").dt.date
    live_meetings["meeting_id"] = live_meetings.apply(
        lambda row: _make_meeting_id(row["track_name_norm"], row["event_date"]), axis=1
    )
    live_meetings["track_abbrev"] = live_meetings["track"].str.slice(stop=5).str.upper()
    live_meetings["country"] = "AUS"
    live_meetings["source"] = "puntingform_live"

    # Select columns for races, ensuring they exist
    race_cols = [
        "event_date",
        "track_name_norm",
        "win_market_id",
        "win_market_name",
        "race_no",
        "racing_type",
        "race_type",
        "distance",
        "scheduled_race_time",
        "actual_off_time",
    ]
    missing_race_cols = [col for col in race_cols if col not in live_df.columns]
    if missing_race_cols:
        raise ValueError(f"Missing required columns for races: {missing_race_cols}. Available columns: {list(live_df.columns)}")

    live_races = (
        live_df[race_cols]
        .drop_duplicates(subset=["win_market_id"])
        .copy()
    )
    live_races["race_id"] = live_races["win_market_id"].apply(_make_race_id)
    live_races["meeting_id"] = live_races.apply(
        lambda row: _make_meeting_id(row["track_name_norm"], pd.to_datetime(row["event_date"]).date()), axis=1
    )
    live_races["scheduled_start"] = pd.to_datetime(
        live_races["event_date"].astype(str)
        + " "
        + live_races["scheduled_race_time"].fillna("00:00:00").astype(str),
        errors="coerce",
    )
    live_races["actual_start"] = pd.to_datetime(
        live_races["event_date"].astype(str)
        + " "
        + live_races["actual_off_time"].fillna("00:00:00").astype(str),
        errors="coerce",
    )

    live_runners = live_df.copy()
    live_runners["race_id"] = live_runners["win_market_id"].apply(_make_race_id)
    live_runners["runner_id"] = live_runners["race_id"] + "_" + live_runners["selection_id"].astype(str)
    live_runners["tab_number"] = pd.to_numeric(live_runners.get("tab_number"), errors="coerce").astype("Int64")
    live_runners["selection_id"] = live_runners["selection_id"].astype(str)
    live_runners["win_odds"] = pd.to_numeric(live_runners.get("win_odds"), errors="coerce")
    if "win_result" in live_runners.columns:
        live_runners["win_result"] = live_runners["win_result"].astype(str)

    # Remove meeting_id from runners - it should come from the races table during merge
    if "meeting_id" in live_runners.columns:
        live_runners = live_runners.drop(columns=["meeting_id"])

    if runners_path.exists():
        # Read just the schema to get column names (read first row then get columns)
        try:
            import pyarrow.parquet as pq
            parquet_file = pq.ParquetFile(runners_path)
            template_cols = parquet_file.schema.names
        except Exception:
            # Fallback: read the file and get columns (less efficient but works)
            template_df = pd.read_parquet(runners_path, engine="pyarrow")
            template_cols = template_df.columns

        for col in template_cols:
            if col not in live_runners.columns:
                live_runners[col] = np.nan
        live_runners = live_runners[[col for col in template_cols]]

    def _combine(path: Path, new_df: pd.DataFrame, subset: list[str]) -> pd.DataFrame:
        if path.exists():
            existing = pd.read_parquet(path)
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=subset)
        else:
            combined = new_df.copy()
        for col in subset:
            combined[col] = combined[col].astype(str)
        for col in combined.columns:
            if col.endswith("_id"):
                combined[col] = combined[col].astype(str)
        combined.to_parquet(path, index=False)
        return combined

    combined_meetings = _combine(meetings_path, live_meetings, ["meeting_id"])
    combined_races = _combine(races_path, live_races, ["race_id"])
    combined_runners = _combine(runners_path, live_runners, ["runner_id"])

    manifest = {
        "source": "services/api/data/processed/ml/betfair_kash_top5.csv.gz",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "total_meetings": len(combined_meetings),
        "total_races": combined_races["race_id"].nunique(),
        "total_runners": len(combined_runners),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return {
        "meetings": len(live_meetings),
        "races": len(live_races),
        "runners": len(live_runners),
    }


def _load_strategies(path: Optional[Path]) -> list[StrategyConfig]:
    if path is None or not path.exists():
        return StrategyGrid.build(margins=[1.02, 1.05, 1.08], top_ns=[1, 2], stakes=[1.0])
    definition = json.loads(path.read_text())
    if isinstance(definition, list):
        configs: list[StrategyConfig] = []
        for item in definition:
            configs.extend(StrategyGrid.from_dict(item))
        return configs
    if isinstance(definition, dict):
        return StrategyGrid.from_dict(definition)
    raise ValueError(f"Unsupported strategy definition in {path}")


def _build_dataset(start: date, end: date, pf_schema_dir: Path, max_races: Optional[int]) -> pd.DataFrame:
    df = load_pf_dataset(pf_schema_dir)
    if df is None or df.empty:
        raise ValueError("PF dataset is empty. Build the schema first.")

    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    subset = df[(df["event_date"] >= start_dt) & (df["event_date"] <= end_dt)].copy()
    if subset.empty:
        raise ValueError(f"No runners found between {start} and {end}")

    subset = subset.sort_values(["event_date", "race_id"]).reset_index(drop=True)
    if max_races is not None:
        keep_ids = subset["race_id"].drop_duplicates().head(max_races)
        subset = subset[subset["race_id"].isin(keep_ids)]
    return subset


def _ensure_predictions(df: pd.DataFrame, booster) -> pd.DataFrame:
    engineered = engineer_all_features(df)
    feature_cols = [c for c in get_feature_columns() if c in engineered.columns]
    if not feature_cols:
        raise ValueError("No feature columns available for prediction.")
    preds = booster.predict(engineered[feature_cols])
    engineered["model_prob"] = preds

    # Fix NULL win_odds by generating from pf_ai_rank or pf_ai_price if available
    if "win_odds" in engineered.columns and engineered["win_odds"].isna().all():
        # Try pf_ai_price first
        if "pf_ai_price" in engineered.columns:
            odds_from_price = pd.to_numeric(engineered["pf_ai_price"], errors="coerce").replace(0, np.nan)
            if not odds_from_price.isna().all():
                engineered["win_odds"] = odds_from_price

        # If still null, try generating from pf_ai_rank
        if engineered["win_odds"].isna().all() and "pf_ai_rank" in engineered.columns:
            ranks = pd.to_numeric(engineered["pf_ai_rank"], errors="coerce")
            engineered["win_odds"] = 2.0 + (ranks * 1.5)

    with np.errstate(divide="ignore", invalid="ignore"):
        engineered["implied_prob"] = 1.0 / engineered["win_odds"].replace(0, np.nan)
    return engineered


def run_ace_pipeline(
    start: date,
    end: date,
    *,
    pf_schema_dir: Path,
    strategies_path: Path,
    experience_dir: Path,
    playbook_path: Path,
    model_path: Optional[Path] = None,
    max_races: Optional[int] = None,
    min_bets: int = 30,
) -> dict:
    from lightgbm import Booster

    if model_path is None:
        model_dir = Path("artifacts/models")
        models = sorted(model_dir.glob("betfair_kash_top5_model_*.txt"))
        if not models:
            raise ValueError("No model artifacts found. Train the model first.")
        model_path = models[-1]

    booster = Booster(model_file=str(model_path))
    dataset = _build_dataset(start, end, pf_schema_dir, max_races)
    runners = _ensure_predictions(dataset, booster)

    strategies = _load_strategies(strategies_path)

    simulator = Simulator()
    experience_dir.mkdir(parents=True, exist_ok=True)
    writer = ExperienceWriter(ExperienceConfig(output_dir=experience_dir))
    experience_runner = EarlyExperienceRunner(simulator=simulator, strategies=strategies, writer=writer)
    experience_output = experience_runner.run(runners, label="ace")

    # Check if experiences were generated
    if experience_output.experience_path is None:
        # Provide diagnostic information
        total_strategies = len(strategies)
        total_bets = experience_output.strategy_metrics["bets"].sum() if not experience_output.strategy_metrics.empty else 0

        diagnostics = {
            "runners_count": len(runners),
            "strategies_evaluated": total_strategies,
            "total_bets_across_strategies": int(total_bets),
            "has_model_prob": "model_prob" in runners.columns,
            "has_win_odds": "win_odds" in runners.columns,
            "has_win_result": "win_result" in runners.columns,
        }

        if "model_prob" in runners.columns:
            diagnostics["model_prob_null_count"] = int(runners["model_prob"].isna().sum())
            diagnostics["model_prob_mean"] = float(runners["model_prob"].mean()) if not runners["model_prob"].isna().all() else None

        if "win_odds" in runners.columns:
            diagnostics["win_odds_null_count"] = int(runners["win_odds"].isna().sum())
            diagnostics["win_odds_mean"] = float(runners["win_odds"].mean()) if not runners["win_odds"].isna().all() else None

        raise ValueError(
            f"No experiences generated. No bets met strategy criteria. Diagnostics: {diagnostics}"
        )

    exp_path = Path(experience_output.experience_path)
    if exp_path.suffix == ".parquet":
        exp_df = pd.read_parquet(exp_path)
    else:
        exp_df = pd.read_csv(exp_path)
    reflector = ACEReflector(min_bets=min_bets)
    playbook = reflector.build_playbook(exp_df, experience_output.strategy_metrics)

    curator = PlaybookCurator(output_path=playbook_path)
    curator.save(playbook)

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "experience_rows": len(exp_df),
        "strategies_evaluated": len(strategies),
        "experience_path": str(exp_path),
        "playbook_path": str(playbook_path),
        "playbook": playbook.to_dict(),
    }


async def run_ace_pipeline_async(**kwargs) -> dict:
    loop = asyncio.get_running_loop()

    def _runner() -> dict:
        return run_ace_pipeline(**kwargs)

    return await loop.run_in_executor(None, _runner)
