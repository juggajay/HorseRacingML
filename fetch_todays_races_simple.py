"""
Simple script to fetch today's Betfair race data and prepare it for the ML model.
"""
from datetime import datetime
from pathlib import Path

import pandas as pd

from betfair_client import BetfairClient

OUTPUT_DIR = Path("data/processed/betfair")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 70)
    print("FETCHING TODAY'S BETFAIR RACES")
    print("=" * 70)

    # Login and fetch markets
    client = BetfairClient()
    client.login()
    print("✓ Logged in to Betfair")

    markets = client.get_todays_races(country="AU")
    print(f"✓ Found {len(markets)} markets today")

    if not markets:
        print("⚠ No races found for today")
        return

    # Get market IDs
    market_ids = [m["marketId"] for m in markets]
    print(f"\n✓ Fetching price data for {len(market_ids)} markets...")

    # Fetch market books (prices and runners) - fetch in smaller chunks
    market_books = client.list_market_book(
        market_ids=market_ids,
        price_data=["EX_BEST_OFFERS"],  # Reduced data to avoid TOO_MUCH_DATA error
        max_chunk=10  # Smaller chunks
    )

    print(f"✓ Retrieved {len(market_books)} market books")

    # Build DataFrame
    rows = []
    for market, book in zip(markets, market_books):
        event_name = market.get("event", {}).get("name", "Unknown")
        event_date = market.get("marketStartTime", "")
        market_id = market.get("marketId", "")

        for runner in book.get("runners", []):
            selection_id = runner.get("selectionId")
            status = runner.get("status", "ACTIVE")

            # Get best available price
            ex = runner.get("ex", {})
            available_to_back = ex.get("availableToBack", [])
            best_back_price = available_to_back[0]["price"] if available_to_back else None

            # Find runner name from market catalogue
            runner_name = "Unknown"
            for r in market.get("runners", []):
                if r.get("selectionId") == selection_id:
                    runner_name = r.get("runnerName", "Unknown")
                    break

            rows.append({
                "event_date": event_date,
                "track": event_name,
                "win_market_id": market_id,
                "selection_id": str(selection_id),
                "selection_name": runner_name,
                "win_odds": best_back_price,
                "status": status,
            })

    df = pd.DataFrame(rows)

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"betfair_snapshot_{timestamp}.csv"
    df.to_csv(output_file, index=False)

    print(f"\n✓ Saved {len(df)} runners to: {output_file}")
    print(f"\nSample data:")
    print(df.head(10))

    client.logout()
    print("\n✓ Done!")

if __name__ == "__main__":
    main()
