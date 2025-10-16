"""Early Experience loop: explore strategies and capture trajectories."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

from .simulator import SimulationResult, Simulator
from .strategies import StrategyConfig


@dataclass
class ExperienceConfig:
    output_dir: Path = Path("data/experiences")
    partition_by_date: bool = True
    filename_prefix: str = "experiences"


@dataclass
class EarlyExperienceOutput:
    experience_path: Optional[Path]
    strategy_metrics: pd.DataFrame


class ExperienceWriter:
    def __init__(self, config: ExperienceConfig) -> None:
        self.config = config
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, df: pd.DataFrame, label: Optional[str] = None) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        prefix = label or self.config.filename_prefix
        if self.config.partition_by_date and "event_date" in df.columns:
            dates = sorted({str(d) for d in df["event_date"].astype(str)})
            suffix = dates[0].replace("-", "") if len(dates) == 1 else f"{dates[0].replace('-', '')}_{dates[-1].replace('-', '')}"
        else:
            suffix = timestamp
        base = f"{prefix}_{suffix}_{timestamp}"
        parquet_path = self.config.output_dir / f"{base}.parquet"
        try:
            df.to_parquet(parquet_path, index=False)
            return parquet_path
        except Exception:
            csv_path = parquet_path.with_suffix(".csv.gz")
            df.to_csv(csv_path, index=False, compression="gzip")
            return csv_path


class EarlyExperienceRunner:
    """Runs strategies through the simulator and records experiences."""

    def __init__(
        self,
        simulator: Simulator,
        strategies: Iterable[StrategyConfig],
        *,
        writer: Optional[ExperienceWriter] = None,
        context_fields: Optional[Iterable[str]] = None,
    ) -> None:
        self.simulator = simulator
        self.strategies = list(strategies)
        self.writer = writer or ExperienceWriter(ExperienceConfig())
        self.context_fields = tuple(context_fields or ("track", "state_code", "distance", "racing_type", "race_type"))

    def run(self, runners: pd.DataFrame, *, label: Optional[str] = None) -> EarlyExperienceOutput:
        if not self.strategies:
            raise ValueError("No strategies provided to EarlyExperienceRunner")

        experience_frames: List[pd.DataFrame] = []
        metrics_rows: List[Dict[str, float]] = []

        for strategy in self.strategies:
            result = self.simulator.evaluate(runners, strategy)
            metrics_rows.append(result.metrics)
            if result.bets.empty:
                continue
            experience_frames.append(self._build_experiences(result))

        experiences_df = pd.concat(experience_frames, ignore_index=True) if experience_frames else pd.DataFrame()
        metrics_df = pd.DataFrame(metrics_rows)

        path: Optional[Path] = None
        if not experiences_df.empty:
            path = self.writer.write(experiences_df, label=label)

        return EarlyExperienceOutput(experience_path=path, strategy_metrics=metrics_df)

    def _build_experiences(self, result: SimulationResult) -> pd.DataFrame:
        bets = result.bets.copy()
        strategy = result.strategy
        params_json = json.dumps(strategy.to_params(), sort_keys=True)

        experiences = pd.DataFrame(
            {
                "event_date": pd.to_datetime(bets.get("event_date")).dt.date,
                "race_id": bets.get("race_id", bets.get("win_market_id")).astype(str),
                "runner_id": bets.get("runner_id").astype(str),
                "selection_id": bets.get("selection_id").astype("Int64"),
                "strategy_id": strategy.strategy_id,
                "params": params_json,
                "action": "bet",
                "stake": bets["stake"],
                "profit": bets["profit"],
                "model_prob": bets["model_prob"],
                "implied_prob": bets.get("implied_prob"),
                "edge": bets.get("edge"),
                "win_odds": bets["win_odds"],
                "won_flag": bets["won_flag"],
            }
        )

        for field in self.context_fields:
            if field in bets.columns:
                experiences[field] = bets[field]

        experiences["context_hash"] = experiences.apply(self._summarise_context, axis=1)
        experiences["experience_id"] = experiences.apply(self._make_experience_id, axis=1)
        return experiences

    def _summarise_context(self, row: pd.Series) -> str:
        payload = {field: row.get(field) for field in self.context_fields if field in row}
        encoded = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()[:16]

    def _make_experience_id(self, row: pd.Series) -> str:
        key = f"{row['strategy_id']}|{row['race_id']}|{row['runner_id']}|{row['action']}"
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
