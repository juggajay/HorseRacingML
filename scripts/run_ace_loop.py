"""Run the Early Experience + ACE loops end-to-end."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import json

from services.api.ace_runner import run_ace_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Early Experience + ACE loops")
    parser.add_argument("--start-date", type=str, help="Inclusive start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Inclusive end date (YYYY-MM-DD)")
    parser.add_argument("--strategies", type=Path, default=Path("configs/strategies_default.json"), help="Path to strategy JSON config")
    parser.add_argument("--max-races", type=int, default=None, help="Limit number of races to process")
    parser.add_argument("--output-experiences", type=Path, default=Path("data/experiences"))
    parser.add_argument("--playbook-path", type=Path, default=Path("artifacts/playbook/playbook.json"))
    parser.add_argument("--min-bets", type=int, default=30, help="Minimum bets required for context insights")
    parser.add_argument(
        "--pf-schema-dir",
        type=Path,
        default=Path("services/api/data/processed/pf_schema"),
        help="Directory containing PF schema tables",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="Optional explicit model path (defaults to latest betfair_kash_top5 booster)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = date.fromisoformat(args.start_date)
    end = date.fromisoformat(args.end_date)

    result = run_ace_pipeline(
        start,
        end,
        pf_schema_dir=args.pf_schema_dir,
        strategies_path=args.strategies,
        experience_dir=args.output_experiences,
        playbook_path=args.playbook_path,
        model_path=args.model_path,
        max_races=args.max_races,
        min_bets=args.min_bets,
    )

    print("\n=== ACE Summary ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
