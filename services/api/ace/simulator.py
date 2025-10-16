"""Simulation environment for evaluating betting strategies over PF data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import numpy as np
import pandas as pd

from .strategies import StrategyConfig


@dataclass
class SimulationResult:
    """Container for per-strategy simulation outcomes."""

    strategy: StrategyConfig
    bets: pd.DataFrame
    metrics: Dict[str, float]
    by_track: Optional[pd.DataFrame] = None


class Simulator:
    """Runs strategy evaluations against historical runner features."""

    def __init__(self, *, win_result_col: str = "win_result", race_id_col: str = "race_id") -> None:
        self.win_result_col = win_result_col
        self.race_id_col = race_id_col

    def evaluate(self, runners: pd.DataFrame, strategy: StrategyConfig) -> SimulationResult:
        df = runners.copy()
        required = {"model_prob", "win_odds", self.win_result_col}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns in runners dataset: {sorted(missing)}")

        if "implied_prob" not in df.columns:
            df["implied_prob"] = 1.0 / (df["win_odds"].replace(0, np.nan) + 1e-9)
        df["edge"] = df["model_prob"] - df["implied_prob"] * strategy.margin

        if strategy.min_model_prob is not None:
            df = df[df["model_prob"] >= strategy.min_model_prob]
        if strategy.max_win_odds is not None:
            df = df[df["win_odds"] <= strategy.max_win_odds]

        for key, value in strategy.filters.items():
            if key not in df.columns:
                continue
            if isinstance(value, (list, tuple, set)):
                df = df[df[key].isin(value)]
            else:
                df = df[df[key] == value]

        if df.empty:
            return SimulationResult(
                strategy=strategy,
                bets=df.assign(stake=0.0, profit=0.0, won_flag=0),
                metrics=self._empty_metrics(strategy),
                by_track=None,
            )

        race_col = self._resolve_race_id(df)
        df = df.sort_values([race_col, "edge"], ascending=[True, False])
        df = df[df["edge"] > 0]
        if strategy.top_n:
            df = df.groupby(race_col).head(strategy.top_n).reset_index(drop=True)

        if df.empty:
            return SimulationResult(
                strategy=strategy,
                bets=df.assign(stake=0.0, profit=0.0, won_flag=0),
                metrics=self._empty_metrics(strategy),
                by_track=None,
            )

        win_flags = df[self.win_result_col].astype(str).str.upper().eq("WINNER").astype(int)
        stake = strategy.stake
        profits = np.where(win_flags == 1, stake * (df["win_odds"] - 1.0), -stake)

        df = df.copy()
        df["stake"] = stake
        df["won_flag"] = win_flags
        df["profit"] = profits

        metrics = {
            "strategy_id": strategy.strategy_id,
            "bets": int(len(df)),
            "wins": int(win_flags.sum()),
            "hit_rate": float(win_flags.mean()),
            "mean_edge": float(df["edge"].mean()),
            "total_staked": float(stake * len(df)),
            "total_profit": float(profits.sum()),
            "pot_pct": float(profits.mean() * 100.0),
            "params": strategy.to_params(),
        }

        by_track = None
        if "track" in df.columns:
            agg = (
                df.groupby("track", as_index=False)
                .agg(
                    bets=("profit", "size"),
                    profit=("profit", "sum"),
                    pot_pct=("profit", lambda s: float(s.mean() * 100.0) if len(s) else 0.0),
                )
            )
            by_track = agg.sort_values("pot_pct", ascending=False)

        return SimulationResult(strategy=strategy, bets=df, metrics=metrics, by_track=by_track)

    def _resolve_race_id(self, df: pd.DataFrame) -> str:
        if self.race_id_col in df.columns:
            return self.race_id_col
        if "win_market_id" in df.columns:
            return "win_market_id"
        raise ValueError("No race identifier column found (expected 'race_id' or 'win_market_id').")

    def _empty_metrics(self, strategy: StrategyConfig) -> Dict[str, Any]:
        return {
            "strategy_id": strategy.strategy_id,
            "bets": 0,
            "wins": 0,
            "hit_rate": 0.0,
            "mean_edge": 0.0,
            "total_staked": 0.0,
            "total_profit": 0.0,
            "pot_pct": 0.0,
            "params": strategy.to_params(),
        }
