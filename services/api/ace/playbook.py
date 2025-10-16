"""Agentic Context Engineering (ACE) reflection and playbook curation."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class Playbook:
    metadata: Dict[str, object]
    global_stats: Dict[str, object]
    strategy_stats: List[Dict[str, object]]
    track_insights: List[Dict[str, object]]
    context_insights: List[Dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "metadata": self.metadata,
            "global": self.global_stats,
            "strategies": self.strategy_stats,
            "tracks": self.track_insights,
            "contexts": self.context_insights,
        }


class ACEReflector:
    """Transforms experiences into structured playbook insights."""

    def __init__(self, *, min_bets: int = 30) -> None:
        self.min_bets = min_bets

    def build_playbook(
        self,
        experiences: Optional[pd.DataFrame],
        strategy_metrics: Optional[pd.DataFrame],
    ) -> Playbook:
        exp_df = experiences.copy() if experiences is not None else pd.DataFrame()
        strat_df = strategy_metrics.copy() if strategy_metrics is not None else pd.DataFrame()

        metadata = {
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "experience_rows": int(len(exp_df)),
            "strategies_evaluated": int(len(strat_df)),
        }

        global_stats = self._global_stats(exp_df, strat_df)
        strategy_stats = self._strategy_stats(strat_df)
        track_insights = self._track_insights(exp_df)
        context_insights = self._context_insights(exp_df)

        return Playbook(
            metadata=metadata,
            global_stats=global_stats,
            strategy_stats=strategy_stats,
            track_insights=track_insights,
            context_insights=context_insights,
        )

    def _global_stats(self, exp_df: pd.DataFrame, strat_df: pd.DataFrame) -> Dict[str, object]:
        if not exp_df.empty:
            total_bets = int(len(exp_df))
            total_profit = float(exp_df["profit"].sum())
            total_staked = float(exp_df["stake"].sum())
            pot_pct = float((exp_df["profit"].mean() * 100.0) if total_bets else 0.0)
            hit_rate = float(exp_df.get("won_flag", 0).mean()) if "won_flag" in exp_df else np.nan
        else:
            total_bets = int(strat_df.get("bets", pd.Series(dtype=int)).sum()) if not strat_df.empty else 0
            total_profit = float(strat_df.get("total_profit", pd.Series(dtype=float)).sum()) if not strat_df.empty else 0.0
            total_staked = float(strat_df.get("total_staked", pd.Series(dtype=float)).sum()) if not strat_df.empty else 0.0
            pot_pct = float(strat_df.get("pot_pct", pd.Series(dtype=float)).mean()) if not strat_df.empty else 0.0
            hit_rate = float(strat_df.get("hit_rate", pd.Series(dtype=float)).mean()) if not strat_df.empty else np.nan

        return {
            "total_bets": total_bets,
            "total_profit": total_profit,
            "total_staked": total_staked,
            "pot_pct": pot_pct,
            "hit_rate": hit_rate,
        }

    def _strategy_stats(self, strat_df: pd.DataFrame) -> List[Dict[str, object]]:
        if strat_df.empty:
            return []
        df = strat_df.copy()
        if "total_staked" in df.columns:
            with np.errstate(divide="ignore", invalid="ignore"):
                roi = np.where(df["total_staked"] > 0, df["total_profit"] / df["total_staked"] * 100.0, 0.0)
            df["roi_pct"] = roi
        else:
            df["roi_pct"] = df.get("pot_pct", 0.0)
        df = df.sort_values("roi_pct", ascending=False)
        columns = [
            "strategy_id",
            "bets",
            "wins",
            "hit_rate",
            "mean_edge",
            "total_staked",
            "total_profit",
            "pot_pct",
            "roi_pct",
            "params",
        ]
        present_cols = [c for c in columns if c in df.columns]
        return df[present_cols].to_dict(orient="records")

    def _track_insights(self, exp_df: pd.DataFrame) -> List[Dict[str, object]]:
        if exp_df.empty or "track" not in exp_df.columns:
            return []
        grouped = (
            exp_df.groupby("track")
            .agg(
                bets=("profit", "size"),
                profit=("profit", "sum"),
                pot_pct=("profit", lambda s: float(s.mean() * 100.0) if len(s) else 0.0),
                hit_rate=("won_flag", "mean") if "won_flag" in exp_df.columns else ("profit", lambda _: np.nan),
            )
            .reset_index()
        )
        grouped = grouped[grouped["bets"] >= self.min_bets]
        grouped = grouped.sort_values("pot_pct", ascending=False)
        return grouped.to_dict(orient="records")

    def _context_insights(self, exp_df: pd.DataFrame) -> List[Dict[str, object]]:
        if exp_df.empty:
            return []
        df = exp_df.copy()
        if "distance" in df.columns:
            df["distance_band"] = pd.cut(
                df["distance"],
                bins=[0, 1200, 1600, 2000, 2400, 10000],
                labels=["<=1200", "1201-1600", "1601-2000", "2001-2400", "2400+"],
            )
        else:
            df["distance_band"] = "unknown"

        group_cols = [col for col in ["track", "distance_band", "racing_type", "race_type"] if col in df.columns]
        if not group_cols:
            return []

        grouped = (
            df.groupby(group_cols, observed=False)
            .agg(
                bets=("profit", "size"),
                profit=("profit", "sum"),
                pot_pct=("profit", lambda s: float(s.mean() * 100.0) if len(s) else 0.0),
            )
            .reset_index()
        )
        grouped = grouped[grouped["bets"] >= self.min_bets]
        grouped = grouped.sort_values("pot_pct", ascending=False).head(20)
        return grouped.to_dict(orient="records")


class PlaybookCurator:
    """Persists playbook snapshots and maintains a rolling history."""

    def __init__(self, *, output_path: Path = Path("artifacts/playbook/playbook.json"), max_history: int = 10) -> None:
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_history = max_history

    def save(self, playbook: Playbook) -> Path:
        history = self._load_history()
        snapshot = playbook.to_dict()
        history.append(snapshot)
        if len(history) > self.max_history:
            history = history[-self.max_history :]
        payload = {"history": history, "latest": snapshot}
        self.output_path.write_text(json.dumps(payload, indent=2))
        return self.output_path

    def _load_history(self) -> List[Dict[str, object]]:
        if not self.output_path.exists():
            return []
        try:
            data = json.loads(self.output_path.read_text())
            if isinstance(data, dict) and "history" in data:
                history = data["history"]
                if isinstance(history, list):
                    return history
        except json.JSONDecodeError:
            pass
        return []
