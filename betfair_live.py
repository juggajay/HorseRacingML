"""Helpers for retrieving Betfair live market data and shaping it for scoring."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from betfair_client import BetfairClient

RATINGS_PATH = Path("artifacts/horse_ratings_betfair_2023_2024.csv")


def _parse_race_number(name: Optional[str]) -> float:
    if not name:
        return np.nan
    parts = name.split()
    if parts and parts[0].startswith("R"):
        digits = ''.join(ch for ch in parts[0] if ch.isdigit())
        if digits.isdigit():
            return float(digits)
    return np.nan


def _norm(text: Optional[str]) -> Optional[str]:
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return None
    import re
    s = str(text).lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s or None


def fetch_live_markets(
    target_date: date,
    country: str = "AU",
    market_type_codes: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    start = datetime.combine(target_date, datetime.min.time())
    end = start + timedelta(days=1)

    with BetfairClient() as client:
        catalogues = client.list_market_catalogue(
            country=country,
            from_time=start,
            to_time=end,
            market_type_codes=market_type_codes or ["WIN"],
            max_results=400,
        )
        if not catalogues:
            raise SystemExit(f"⚠️ No Betfair markets returned for {target_date} ({country})")
        market_ids = [c["marketId"] for c in catalogues]
        books = client.list_market_book(market_ids)

    book_map: Dict[str, Dict] = {book["marketId"]: book for book in books}
    rows: List[Dict] = []
    for market in catalogues:
        market_id = market["marketId"]
        book = book_map.get(market_id)
        if not book:
            continue
        event = market.get("event", {})
        venue = event.get("venue") or event.get("name")
        market_start = pd.to_datetime(market.get("marketStartTime"))
        runner_names = {
            runner["selectionId"]: runner.get("runnerName")
            for runner in market.get("runners", [])
        }

        for runner in book.get("runners", []):
            selection_id = runner.get("selectionId")
            ex = runner.get("ex", {})
            best_back = ex.get("availableToBack", [{}])
            best_price = best_back[0].get("price") if best_back else None
            last_price = runner.get("lastPriceTraded")
            odds = best_price or last_price or np.nan
            row = {
                "event_date_merge": market_start.isoformat(),
                "local_meeting_date": market_start.date().isoformat(),
                "scheduled_race_time": market_start.strftime("%H:%M:%S"),
                "track": venue,
                "state_code": event.get("countryCode"),
                "race_no": _parse_race_number(market.get("marketName")),
                "win_market_id": market_id,
                "win_market_name": market.get("marketName"),
                "selection_id": str(selection_id),
                "selection_name": runner_names.get(selection_id, str(selection_id)),
                "win_market_start_time": market_start.isoformat(),
                "win_odds": odds,
                "win_bsp": runner.get("sp", {}).get("actualSP"),
                "win_result": np.nan,
                "place_result": np.nan,
                "win_bsp_volume": np.nan,
                "win_preplay_volume": np.nan,
                "win_inplay_volume": np.nan,
                "place_bsp": np.nan,
                "runner_name": runner_names.get(selection_id, str(selection_id)),
                "event_name": event.get("name"),
                "market_start_time": market_start.isoformat(),
                "track_name_norm": venue,
                "horse_name_norm": runner_names.get(selection_id, str(selection_id)),
                "race_id": market_id,
                "runner_id": f"{market_id}_{selection_id}",
            }
            rows.append(row)

    if not rows:
        raise SystemExit("⚠️ No runner rows generated from Betfair API response")

    df = pd.DataFrame(rows)

    # Normalise names for joining
    df["horse_name_norm"] = df["horse_name_norm"].map(_norm)

    if RATINGS_PATH.exists():
        ratings = pd.read_csv(RATINGS_PATH)
        ratings["horse_name_norm"] = ratings["horse_name_norm"].map(_norm)
        rating_cols = [
            "betfair_horse_rating",
            "win_rate",
            "place_rate",
            "total_starts",
        ]
        df = df.merge(ratings[["horse_name_norm", *rating_cols]], on="horse_name_norm", how="left")
    else:
        df["betfair_horse_rating"] = np.nan
        df["win_rate"] = np.nan
        df["place_rate"] = np.nan
        df["total_starts"] = np.nan

    df["betfair_horse_rating"] = pd.to_numeric(df["betfair_horse_rating"], errors="coerce").fillna(50.0)
    df["win_rate"] = pd.to_numeric(df["win_rate"], errors="coerce").fillna(0.10)
    df["place_rate"] = pd.to_numeric(df["place_rate"], errors="coerce").fillna(0.30)
    df["total_starts"] = pd.to_numeric(df["total_starts"], errors="coerce").fillna(5)

    df["value_pct"] = np.nan
    df["race_speed"] = np.nan
    df["early_speed"] = np.nan
    df["late_speed"] = np.nan
    df["speed_category"] = np.nan
    df["model_rank"] = np.nan
    df["win_bsp_kash"] = np.nan
    df["win_bsp_top5"] = np.nan

    df["event_date"] = pd.to_datetime(df["event_date_merge"], errors="coerce")
    return df
