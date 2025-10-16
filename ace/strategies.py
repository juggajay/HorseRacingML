"""Strategy definitions for the Early Experience loop."""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


@dataclass(frozen=True)
class StrategyConfig:
    """Declarative description of a betting strategy to be evaluated."""

    strategy_id: str
    margin: float = 1.05
    top_n: int = 1
    stake: float = 1.0
    min_model_prob: Optional[float] = None
    max_win_odds: Optional[float] = None
    filters: Mapping[str, Any] = field(default_factory=dict)

    def to_params(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "margin": self.margin,
            "top_n": self.top_n,
            "stake": self.stake,
            "min_model_prob": self.min_model_prob,
            "max_win_odds": self.max_win_odds,
            "filters": dict(self.filters),
        }


class StrategyGrid:
    """Utility for generating grids of strategy configs."""

    @staticmethod
    def build(
        margins: Sequence[float],
        top_ns: Sequence[int],
        stakes: Sequence[float] = (1.0,),
        min_model_probs: Sequence[Optional[float]] = (None,),
        max_win_odds: Sequence[Optional[float]] = (None,),
        base_filters: Optional[Mapping[str, Any]] = None,
    ) -> List[StrategyConfig]:
        configs: List[StrategyConfig] = []
        for margin, top_n, stake, min_prob, max_odds in product(
            margins, top_ns, stakes, min_model_probs, max_win_odds
        ):
            strategy_id = (
                f"margin_{margin:.2f}_top{top_n}_stake{stake:.2f}"
                + (f"_minprob{min_prob:.2f}" if min_prob is not None else "")
                + (f"_maxodds{max_odds:.2f}" if max_odds is not None else "")
            )
            configs.append(
                StrategyConfig(
                    strategy_id=strategy_id,
                    margin=margin,
                    top_n=top_n,
                    stake=stake,
                    min_model_prob=min_prob,
                    max_win_odds=max_odds,
                    filters=base_filters or {},
                )
            )
        return configs

    @staticmethod
    def from_dict(definition: Mapping[str, Any]) -> List[StrategyConfig]:
        """Create configs from a JSON-like definition.

        Example definition::

            {
                "margins": [1.02, 1.05, 1.08],
                "top_ns": [1, 2],
                "stakes": [0.5, 1.0],
                "min_model_probs": [0.2, 0.25],
                "max_win_odds": [10.0, null],
                "filters": {"state_code": ["VIC", "NSW"]}
            }
        """

        filters = definition.get("filters", {})
        base_filters = filters if isinstance(filters, Mapping) else {}
        configs = StrategyGrid.build(
            margins=definition.get("margins", [1.05]),
            top_ns=definition.get("top_ns", [1]),
            stakes=definition.get("stakes", [1.0]),
            min_model_probs=definition.get("min_model_probs", [None]),
            max_win_odds=definition.get("max_win_odds", [None]),
            base_filters=base_filters,
        )

        # If filters supply lists, expand per value
        expanded: List[StrategyConfig] = []
        for cfg in configs:
            if not base_filters:
                expanded.append(cfg)
                continue
            filter_items = list(base_filters.items())
            # If any filter values are iterables, create combinations
            keys = [k for k, _ in filter_items]
            values = [v if isinstance(v, Iterable) and not isinstance(v, (str, bytes)) else [v] for _, v in filter_items]
            for combo in product(*values):
                combo_filters = dict(zip(keys, combo))
                suffix = "".join(f"_{k}{val}" for k, val in combo_filters.items())
                expanded.append(
                    StrategyConfig(
                        strategy_id=f"{cfg.strategy_id}{suffix}",
                        margin=cfg.margin,
                        top_n=cfg.top_n,
                        stake=cfg.stake,
                        min_model_prob=cfg.min_model_prob,
                        max_win_odds=cfg.max_win_odds,
                        filters=combo_filters,
                    )
                )
        return expanded or configs
