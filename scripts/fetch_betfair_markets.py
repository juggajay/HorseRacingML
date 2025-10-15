"""Fetch live Betfair win markets and export to CSV for the current date."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from betfair_live import fetch_live_markets

OUTPUT_DIR = Path("data/processed/live")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Betfair live markets")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD)")
    parser.add_argument("--country", type=str, default="AU", help="Market country code")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else date.today()
    df = fetch_live_markets(target_date, args.country)
    output_path = OUTPUT_DIR / f"betfair_live_{target_date:%Y%m%d}.csv"
    df.to_csv(output_path, index=False)
    print(f"✓ Saved {len(df)} rows to {output_path}")


if __name__ == "__main__":
    main()
