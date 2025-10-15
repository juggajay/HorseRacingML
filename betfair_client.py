"""Betfair API helper for fetching horse racing markets (delayed app key).

Usage example::

    from betfair_client import BetfairClient
    from datetime import datetime, timedelta

    with BetfairClient() as client:
        markets = client.list_market_catalogue(
            country="AU",
            from_time=datetime.utcnow(),
            to_time=datetime.utcnow() + timedelta(days=1),
        )
        print(len(markets))
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

IDENTITY_URL = "https://identitysso.betfair.com"
BETTING_URL = "https://api.betfair.com/exchange/betting/rest/v1.0"
HORSE_EVENT_TYPE_ID = "7"


class BetfairAuthError(RuntimeError):
    """Raised when authentication fails."""


class BetfairClient:
    def __init__(
        self,
        app_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.app_key = app_key or os.getenv("BETFAIR_APP_KEY")
        self.username = username or os.getenv("BETFAIR_USERNAME")
        self.password = password or os.getenv("BETFAIR_PASSWORD")
        if not all([self.app_key, self.username, self.password]):
            raise BetfairAuthError(
                "Betfair credentials missing. Set BETFAIR_APP_KEY, "
                "BETFAIR_USERNAME, BETFAIR_PASSWORD in environment." 
            )
        self.session = session or requests.Session()
        self.session_token: Optional[str] = None

    # ------------------------------------------------------------------
    # Context Manager helpers
    # ------------------------------------------------------------------
    def __enter__(self) -> "BetfairClient":
        self.login()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.logout()
        finally:
            self.session.close()

    # ------------------------------------------------------------------
    # Core auth
    # ------------------------------------------------------------------
    def login(self) -> None:
        url = f"{IDENTITY_URL}/api/login"
        headers = {
            "X-Application": self.app_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        payload = {"username": self.username, "password": self.password}
        resp = self.session.post(url, data=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise BetfairAuthError(f"Login HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        status = data.get("loginStatus") or data.get("status")
        if status != "SUCCESS":
            raise BetfairAuthError(f"Login failed: {status}")
        self.session_token = data.get("token")

    def logout(self) -> None:
        if not self.session_token:
            return
        url = f"{IDENTITY_URL}/api/logout"
        headers = {
            "X-Application": self.app_key,
            "X-Authentication": self.session_token,
            "Accept": "application/json",
        }
        self.session.post(url, headers=headers, timeout=10)
        self.session_token = None

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------
    def _headers(self) -> Dict[str, str]:
        if not self.session_token:
            raise BetfairAuthError("Client not authenticated. Call login() first.")
        return {
            "X-Application": self.app_key,
            "X-Authentication": self.session_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def list_market_catalogue(
        self,
        country: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        max_results: int = 200,
        market_type_codes: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return market catalogue entries for horse racing."""

        market_filter: Dict[str, Any] = {"eventTypeIds": [HORSE_EVENT_TYPE_ID]}
        if country:
            market_filter["marketCountries"] = [country]
        if market_type_codes:
            market_filter["marketTypeCodes"] = list(market_type_codes)
        if from_time or to_time:
            now = datetime.utcnow()
            start = from_time or now
            end = to_time or (now + timedelta(days=1))
            market_filter["marketStartTime"] = {
                "from": start.isoformat(timespec="seconds") + "Z",
                "to": end.isoformat(timespec="seconds") + "Z",
            }

        body = {
            "filter": market_filter,
            "sort": "FIRST_TO_START",
            "marketProjection": [
                "EVENT",
                "MARKET_START_TIME",
                "RUNNER_DESCRIPTION",
                "RUNNER_METADATA",
            ],
            "maxResults": max_results,
        }

        resp = self.session.post(
            f"{BETTING_URL}/listMarketCatalogue/",
            json=body,
            headers=self._headers(),
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"listMarketCatalogue HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def list_market_book(
        self,
        market_ids: Iterable[str],
        price_data: Optional[Iterable[str]] = None,
        max_chunk: int = 25,
    ) -> List[Dict[str, Any]]:
        """Fetch market books (prices) for given market IDs."""

        price_projection = {
            "priceData": list(price_data or ["EX_BEST_OFFERS", "EX_TRADED"]),
            "virtualise": False,
            "rolloverStakes": False,
        }
        market_ids = list(market_ids)
        books: List[Dict[str, Any]] = []
        for idx in range(0, len(market_ids), max_chunk):
            chunk = market_ids[idx : idx + max_chunk]
            body = {
                "marketIds": chunk,
                "priceProjection": price_projection,
            }
            resp = self.session.post(
                f"{BETTING_URL}/listMarketBook/",
                json=body,
                headers=self._headers(),
                timeout=30,
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"listMarketBook HTTP {resp.status_code}: {resp.text[:200]}"
                )
            books.extend(resp.json())
        return books

    # Convenience wrapper used by docs
    def get_todays_races(self, country: str = "AU") -> List[Dict[str, Any]]:
        today = datetime.utcnow()
        tomorrow = today + timedelta(days=1)
        return self.list_market_catalogue(
            country=country,
            from_time=today,
            to_time=tomorrow,
            market_type_codes=["WIN"],
        )
