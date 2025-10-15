"""
Fetch today's Betfair market data for Australian horse racing.
Saves data in a format compatible with the existing ML pipeline.
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from betfair_client import BetfairClient

# Output directory
OUTPUT_DIR = Path("data/processed/betfair")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_todays_betfair_data(country: str = "AU", delay_between_markets: float = 0.2):
    """
    Fetch today's horse racing market data from Betfair.

    Args:
        country: Country code (default: AU for Australia)
        delay_between_markets: Seconds to wait between market requests (rate limiting)

    Returns:
        DataFrame with runner-level data
    """
    print("=" * 70)
    print("FETCHING TODAY'S BETFAIR DATA")
    print("=" * 70)

    client = BetfairClient()

    print("\n1. Authenticating with Betfair...")
    try:
        client.login()
        print("   ✓ Authentication successful")
    except Exception as e:
        raise Exception(f"Failed to authenticate with Betfair: {e}")

    print(f"\n2. Fetching today's {country} horse racing markets...")
    markets = client.get_todays_races(country=country)
    print(f"   Found {len(markets)} markets")

    if not markets:
        print("\n   ⚠ No markets found for today")
        print("   This could mean:")
        print("   - No races scheduled")
        print("   - Wrong country code")
        print("   - Markets not yet available (try closer to race time)")
        client.logout()
        return pd.DataFrame()

    print(f"\n3. Fetching price data for {len(markets)} markets...")
    all_data = []
    errors = 0

    for i, market in enumerate(markets, 1):
        market_id = market.get("marketId")
        event = market.get("event", {})
        market_name = market.get("marketName", "")

        try:
            # Get current prices for this market
            market_book = client.get_market_with_prices(market_id)

            if not market_book:
                print(f"   ⚠ [{i}/{len(markets)}] No data for {event.get('venue')} - {market_name}")
                errors += 1
                continue

            # Extract race details from market name (e.g., "R5 1200m Hcp")
            race_no = "0"
            if "R" in market_name:
                parts = market_name.split("R")
                if len(parts) > 1:
                    race_no = parts[1].split()[0] if parts[1].split() else "0"

            # Process each runner in the market
            for runner in market_book.get("runners", []):
                selection_id = runner.get("selectionId")

                # Get runner name from market catalogue
                runner_info = next(
                    (r for r in market.get("runners", []) if r["selectionId"] == selection_id),
                    {},
                )

                # Get best available back price (what you can bet at)
                ex_data = runner.get("ex", {})
                available_to_back = ex_data.get("availableToBack", [])
                best_back_price = available_to_back[0].get("price") if available_to_back else None

                # Get traded volume at this price
                traded = ex_data.get("tradedVolume", [])
                total_traded = sum(t.get("size", 0) for t in traded) if traded else 0

                all_data.append(
                    {
                        "fetch_timestamp": datetime.now(),
                        "event_date": market.get("marketStartTime"),
                        "track": event.get("venue"),
                        "country": event.get("countryCode", country),
                        "race_no": race_no,
                        "market_id": market_id,
                        "market_name": market_name,
                        "selection_id": str(selection_id),
                        "selection_name": runner_info.get("runnerName"),
                        "win_odds": best_back_price,
                        "runner_status": runner.get("status"),  # ACTIVE, REMOVED, WINNER, LOSER
                        "total_matched": market_book.get("totalMatched", 0),
                        "runner_matched": total_traded,
                        "market_status": market_book.get("status"),  # OPEN, SUSPENDED, CLOSED
                        "inplay": market_book.get("inplay", False),
                    }
                )

            print(
                f"   ✓ [{i}/{len(markets)}] {event.get('venue', 'Unknown')} - {market_name}: "
                f"{len(market_book.get('runners', []))} runners"
            )

            # Rate limiting - don't hammer the API
            if i < len(markets):
                time.sleep(delay_between_markets)

        except Exception as e:
            print(
                f"   ✗ [{i}/{len(markets)}] Error fetching {event.get('venue')} - {market_name}: {e}"
            )
            errors += 1
            continue

    print(f"\n4. Logging out...")
    client.logout()

    # Convert to DataFrame
    df = pd.DataFrame(all_data)

    print(f"\n5. Saving results...")
    if df.empty:
        print("   ⚠ No data to save")
        return df

    # Save with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"betfair_snapshot_{timestamp}.csv"
    df.to_csv(output_path, index=False)

    print(f"   ✓ Saved {len(df)} runners from {len(markets)} markets")
    print(f"   ✓ Output: {output_path}")

    if errors > 0:
        print(f"\n   ⚠ {errors} markets had errors")

    # Print summary statistics
    print(f"\n6. Summary:")
    print(f"   Tracks: {df['track'].nunique()}")
    print(f"   Markets: {df['market_id'].nunique()}")
    print(f"   Runners: {len(df)}")
    print(f"   Active runners: {(df['runner_status'] == 'ACTIVE').sum()}")
    print(f"   Open markets: {(df['market_status'] == 'OPEN').sum()}")

    # Show sample data
    if not df.empty:
        print(f"\n7. Sample data (first 5 runners):")
        display_cols = [
            "track",
            "race_no",
            "selection_name",
            "win_odds",
            "runner_status",
            "market_status",
        ]
        print(df[display_cols].head().to_string(index=False))

    print("\n" + "=" * 70)
    print("✓ COMPLETE")
    print("=" * 70)

    return df


def get_live_odds_for_market(market_id: str) -> pd.DataFrame:
    """
    Get current odds for a specific market.

    Args:
        market_id: Betfair market ID

    Returns:
        DataFrame with current odds for all runners
    """
    client = BetfairClient()
    client.login()

    market_book = client.get_market_with_prices(market_id)

    data = []
    for runner in market_book.get("runners", []):
        ex_data = runner.get("ex", {})
        available_to_back = ex_data.get("availableToBack", [])
        best_price = available_to_back[0].get("price") if available_to_back else None

        data.append(
            {
                "selection_id": runner.get("selectionId"),
                "status": runner.get("status"),
                "win_odds": best_price,
                "timestamp": datetime.now(),
            }
        )

    client.logout()

    return pd.DataFrame(data)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch Betfair market data")
    parser.add_argument(
        "--country",
        default="AU",
        help="Country code (AU, GB, IE, US, etc.)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Delay between market requests (seconds)",
    )

    args = parser.parse_args()

    try:
        df = fetch_todays_betfair_data(country=args.country, delay_between_markets=args.delay)

        if not df.empty:
            print(f"\n✓ Successfully fetched data for {len(df)} runners")
        else:
            print("\n⚠ No data fetched")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
