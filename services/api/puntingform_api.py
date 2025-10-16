# puntingform_api.py
# Lightweight client + cache layer for Punting Form API.
# - Set your API key as an environment variable:  export PUNTINGFORM_API_KEY="..."
# - All requests respect a 1 req/sec throttle and include retries.
# - Responses are cached under ./data/raw/puntingform/YYYY_MM/ as JSON.

from __future__ import annotations
import os, time, json, hashlib, pathlib, datetime as dt, calendar
from typing import Any, Dict, Optional, Tuple, Iterable
import pandas as pd
import requests

DEFAULT_BASE_URL = "https://api.puntingform.com.au"  # v2 API host
CACHE_ROOT = os.environ.get("PF_CACHE_ROOT", "./data/raw/puntingform")

def month_key(year: int, month: int) -> str:
    return f"{year:04d}_{month:02d}"

def ensure_dir(p: str) -> None:
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)

class PuntingFormClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = DEFAULT_BASE_URL, req_per_sec: float = 1.0, timeout: int = 60):
        self.api_key = api_key or os.environ.get("PUNTINGFORM_API_KEY")
        if not self.api_key:
            raise ValueError("Missing API key. Set PUNTINGFORM_API_KEY env var or pass api_key=...")
        self.base_url = base_url.rstrip("/")
        self.req_interval = 1.0 / max(0.0001, req_per_sec)
        self.timeout = timeout
        self._last_req_ts = 0.0

    # ---- Core HTTP with throttle + retry ----
    def _throttle(self) -> None:
        delta = time.time() - self._last_req_ts
        if delta < self.req_interval:
            time.sleep(self.req_interval - delta)

    def _get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._throttle()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers: Dict[str, str] = {}
        req_params = dict(params or {})
        req_params.setdefault("apiKey", self.api_key)
        # Basic 3-try retry with backoff
        backoff = 1.5
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=headers, params=req_params, timeout=self.timeout)
                self._last_req_ts = time.time()
                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except Exception:
                        # Some endpoints may return CSV; if so, wrap as {"_raw": text}
                        return {"_raw": resp.text}
                if resp.status_code in (429, 502, 503):
                    time.sleep((attempt + 1) * backoff)
                    continue
                try:
                    data = resp.json()
                except Exception:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                data.setdefault("statusCode", resp.status_code)
                if "error" not in data or not data["error"]:
                    data["error"] = f"HTTP {resp.status_code}"
                return data
            except requests.RequestException as e:
                if attempt == 2:
                    raise
                time.sleep((attempt + 1) * backoff)
        raise RuntimeError("Unreachable: retries exhausted")

    # ---- Cache helpers ----
    def _cache_path(self, endpoint: str, year: int, month: int, extra: Optional[Dict[str, Any]] = None) -> str:
        mk = month_key(year, month)
        base = f"{endpoint.strip('/').replace('/', '_')}"
        key = json.dumps(extra or {}, sort_keys=True)
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
        folder = os.path.join(CACHE_ROOT, mk)
        ensure_dir(folder)
        return os.path.join(folder, f"{base}__{digest}.json")

    def _cached_get(self, endpoint: str, year: int, month: int, params: Dict[str, Any], force: bool=False) -> Dict[str, Any]:
        path = self._cache_path(endpoint, year, month, params)
        if (not force) and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        data = self._get(endpoint, params)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return data

    def _make_request(self, endpoint: str, params: Dict[str, Any], *, date_hint: Optional[str | dt.date] = None, force: bool = False) -> Dict[str, Any]:
        """Wrapper that prefers cached responses when a date hint is available."""
        date_obj: Optional[dt.date] = None
        if isinstance(date_hint, dt.date):
            date_obj = date_hint
        elif isinstance(date_hint, str) and date_hint:
            try:
                date_obj = dt.date.fromisoformat(date_hint)
            except ValueError:
                pass

        if date_obj is None:
            return self._get(endpoint, params)

        return self._cached_get(endpoint, date_obj.year, date_obj.month, params, force=force)

    # ---- Runner feature extraction helpers ----
    @staticmethod
    def _key_variants(key: str) -> Iterable[str]:
        base = str(key)
        lowered = base.lower()
        snake = ''.join(['_' + c.lower() if c.isupper() else c for c in base]).lstrip('_')
        collapsed = lowered.replace('_', '')
        yield base
        yield lowered
        yield snake
        yield snake.replace('_', '')
        yield collapsed

    @staticmethod
    def _maybe_from_mapping(value: Any) -> Any:
        if isinstance(value, dict):
            for nested_key in ("fullName", "name", "value", "display", "runnerName"):
                if nested_key in value:
                    return value[nested_key]
        return value

    def extract_runner_features(self, runner_json: Dict[str, Any]) -> Dict[str, Any]:
        """Extract flat starter-level features from a PF runner payload."""

        def safe_get(data: Dict[str, Any], keys: Iterable[str]) -> Any:
            for key in keys:
                for variant in self._key_variants(key):
                    if variant in data:
                        return self._maybe_from_mapping(data[variant])
            return None

        def safe_number(value: Any) -> Any:
            if value in (None, "", "NaN"):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return value

        features = {
            # Identification
            "horse_name": safe_get(runner_json, ["horse_name", "horseName", "name"]),
            "tab_no": safe_get(runner_json, ["tabNo", "tab_no", "number"]),
            "barrier": safe_get(runner_json, ["barrier", "barrierNumber", "originalBarrier"]),
            "age": safe_get(runner_json, ["age"]),
            "sex": safe_get(runner_json, ["sex", "gender"]),
            "weight": safe_get(runner_json, ["weight", "handicapWeight", "allocatedWeight"]),
            "jockey": safe_get(runner_json, ["jockey", "jockeyName"]),
            "trainer": safe_get(runner_json, ["trainer", "trainerName"]),

            # Base Starter ratings (Starter tier expectations)
            "pf_score": safe_number(safe_get(runner_json, ["pfscore", "pfScore", "pf_score"])),
            "neural_rating": safe_number(safe_get(runner_json, ["neuralRating", "neural_rating"])),
            "time_rating": safe_number(safe_get(runner_json, ["timeRating", "time_rating"])),
            "early_time_rating": safe_number(safe_get(runner_json, ["earlyTimeRating", "early_time_rating"])),
            "late_sectional_rating": safe_number(safe_get(runner_json, ["lateSectionalRating", "late_sectional_rating"])),
            "weight_class_rating": safe_number(safe_get(runner_json, ["weightClassRating", "weight_class_rating"])),
            "combined_weight_time": safe_number(safe_get(runner_json, ["combinedWeightTime", "combined_weight_time"])),

            # AI derived fields
            "pf_ai_rank": safe_number(safe_get(runner_json, ["pfAIRank", "pf_ai_rank", "aiRank"])),
            "pf_ai_score": safe_number(safe_get(runner_json, ["pfAIScore", "pf_ai_score", "aiScore"])),
            "pf_ai_price": safe_number(safe_get(runner_json, ["pfAIPrice", "pf_ai_price", "aiPrice"])),

            # Form indicators
            "days_since_last": safe_number(safe_get(runner_json, ["daysSinceLastRun", "days_since_last_run"])),
            "career_wins": safe_number(safe_get(runner_json, ["careerWins", "career_wins"])),
            "career_starts": safe_number(safe_get(runner_json, ["careerStarts", "career_starts"])),
            "career_seconds": safe_number(safe_get(runner_json, ["careerSeconds", "career_seconds"])),
            "career_thirds": safe_number(safe_get(runner_json, ["careerThirds", "career_thirds"])),
            "prize_money": safe_number(safe_get(runner_json, ["prizeMoney", "prize_money", "prizemoney"])),
        }

        if features["jockey"] and isinstance(features["jockey"], dict):
            features["jockey"] = self._maybe_from_mapping(features["jockey"])
        if features["trainer"] and isinstance(features["trainer"], dict):
            features["trainer"] = self._maybe_from_mapping(features["trainer"])

        return features

    # ---- Public helpers ----
    def get_meetings_list(self, meeting_date: Optional[str | dt.date] = None, *, force: bool = False) -> list[Dict[str, Any]]:
        meeting_date = meeting_date or dt.date.today()
        if isinstance(meeting_date, str):
            meeting_date = dt.date.fromisoformat(meeting_date)
        response = self.meetings_list(meeting_date, force=force)
        payload = response.get("payLoad") or response.get("payload") or []
        return payload

    def get_form(self, meeting_id: Any, date_str: Optional[str] = None, *, force: bool = False) -> Optional[pd.DataFrame]:
        """Return a flat DataFrame of runners for a meeting."""

        if meeting_id is None:
            return None

        params = {"meetingId": meeting_id}
        date_hint = None
        if date_str:
            try:
                date_hint = dt.date.fromisoformat(str(date_str)[:10])
            except ValueError:
                pass
        response = self._make_request("v2/form/form", params, date_hint=date_hint, force=force)

        if not response:
            return None

        if response.get("statusCode", 200) not in (200, None):
            return None

        # Some responses nest runners under races; others return a flat payload list.
        runners: list[Dict[str, Any]] = []

        if "races" in response:
            races = response.get("races") or []
            for race in races:
                race_meta = {
                    "meeting_id": meeting_id,
                    "race_number": race.get("raceNumber"),
                    "race_name": race.get("raceName"),
                    "distance": race.get("distance"),
                    "race_time": race.get("raceTime") or race.get("raceStartTime"),
                    "track_condition": race.get("trackCondition"),
                    "rail_position": race.get("railPosition"),
                }
                for runner in race.get("runners", []):
                    runner_features = self.extract_runner_features(runner)
                    runners.append({**race_meta, **runner_features})

        payload = response.get("payLoad") or response.get("payload")
        if isinstance(payload, list) and payload:
            for runner in payload:
                race_meta = {
                    "meeting_id": meeting_id,
                    "race_id": runner.get("raceId"),
                    "race_number": runner.get("raceNumber") or runner.get("raceNo"),
                    "race_name": runner.get("raceName"),
                    "distance": runner.get("distance"),
                    "race_time": runner.get("raceTime") or runner.get("raceStartTime"),
                    "track_condition": runner.get("trackCondition"),
                    "rail_position": runner.get("railPosition"),
                }
                runner_features = self.extract_runner_features(runner)
                runners.append({**race_meta, **runner_features})

        if not runners:
            return None

        df = pd.DataFrame(runners)
        return df

    # ---- Helpers for v2 API ----
    def _parsed_meeting_date(self, meeting: Dict[str, Any], fallback: Tuple[int, int]) -> Tuple[int, int, str]:
        raw = meeting.get("meetingDate") or meeting.get("pf_meetingDate")
        if raw:
            try:
                dt_obj = dt.datetime.fromisoformat(str(raw).replace("Z", ""))
                return dt_obj.year, dt_obj.month, dt_obj.date().isoformat()
            except ValueError:
                pass
        year, month = fallback
        reference = dt.date(year, month, 1)
        return year, month, reference.isoformat()

    def _month_day_iter(self, year: int, month: int) -> Tuple[dt.date, ...]:
        days = calendar.monthrange(year, month)[1]
        return tuple(dt.date(year, month, day) for day in range(1, days + 1))

    def meetings_list(self, meeting_date: dt.date | str, *, force: bool = False) -> Dict[str, Any]:
        if isinstance(meeting_date, str):
            meeting_date = dt.date.fromisoformat(meeting_date)
        params = {"meetingDate": meeting_date.isoformat()}
        return self._cached_get("v2/form/meetingslist", meeting_date.year, meeting_date.month, params, force=force)

    def get_meetings_month(self, year: int, month: int, *, force: bool = False) -> Dict[str, Any]:
        meetings: list[Dict[str, Any]] = []
        for day in self._month_day_iter(year, month):
            resp = self.meetings_list(day, force=force)
            if resp.get("statusCode", 200) != 200:
                continue
            payload = resp.get("payLoad") or []
            for meeting in payload:
                meeting.setdefault("pf_meetingDate", day.isoformat())
            meetings.extend(payload)
        return {"payLoad": meetings}

    def _collect_meeting_payload(
        self,
        meetings: list[Dict[str, Any]],
        endpoint: str,
        *,
        params_extra: Optional[Dict[str, Any]] = None,
        force: bool = False,
        year_month: Tuple[int, int] | None = None,
    ) -> list[Dict[str, Any]]:
        aggregated: list[Dict[str, Any]] = []
        year_hint, month_hint = (year_month or (dt.date.today().year, dt.date.today().month))
        for meeting in meetings:
            meeting_id = meeting.get("meetingId") or meeting.get("meeting_id")
            if not meeting_id:
                continue
            year_val, month_val, meeting_date_iso = self._parsed_meeting_date(meeting, (year_hint, month_hint))
            params = {"meetingId": meeting_id}
            if params_extra:
                params.update(params_extra)
            resp = self._cached_get(endpoint, year_val, month_val, params, force=force)
            status = resp.get("statusCode", 200)
            if status != 200:
                aggregated.append({
                    "meetingId": meeting_id,
                    "pf_meetingDate": meeting_date_iso,
                    "statusCode": status,
                    "error": resp.get("error"),
                })
                if status in (401, 403):
                    # Account not entitled for this endpoint; avoid hammering the API.
                    break
                continue
            payload = resp.get("payLoad") or []
            for item in payload:
                item.setdefault("pf_meetingId", meeting_id)
                item.setdefault("pf_meetingDate", meeting_date_iso)
            aggregated.extend(payload)
        return aggregated

    # ---- Domain endpoints (adjust names/params to your PF contract) ----
    def get_southcoast_data(self, year: int, month: int, *, force: bool = False, meetings: Optional[list[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Meeting form (replaces legacy Southcoast data)."""
        meetings_data = meetings or self.get_meetings_month(year, month, force=force).get("payLoad", [])
        payload = self._collect_meeting_payload(
            meetings_data,
            "v2/form/form",
            params_extra={"raceNumber": 0},
            force=force,
            year_month=(year, month),
        )
        return {"payLoad": payload}

    def get_benchmarks_month(self, year: int, month: int, *, force: bool = False, meetings: Optional[list[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Benchmark data aggregated by month (meeting-level under the hood)."""
        meetings_data = meetings or self.get_meetings_month(year, month, force=force).get("payLoad", [])
        payload = self._collect_meeting_payload(
            meetings_data,
            "v2/Ratings/MeetingBenchmarks",
            force=force,
            year_month=(year, month),
        )
        return {"payLoad": payload}

    def get_sectionals_month_bench(self, year: int, month: int, *, force: bool = False, meetings: Optional[list[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Sectional times aggregated by month (meeting-level under the hood)."""
        meetings_data = meetings or self.get_meetings_month(year, month, force=force).get("payLoad", [])
        payload = self._collect_meeting_payload(
            meetings_data,
            "v2/Ratings/MeetingSectionals",
            force=force,
            year_month=(year, month),
        )
        return {"payLoad": payload}

# ---- Normalisers for joining with Kaggle/Betfair ----
import re
def norm_txt(s: str | None) -> str | None:
    if s is None:
        return None
    s = str(s).lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def to_event_date(dt_str: str | None, tz: str = "Australia/Sydney") -> str | None:
    if not dt_str:
        return None
    try:
        import pandas as pd
        t = pd.to_datetime(dt_str, errors="coerce", utc=True)
        if getattr(t, "tz", None) is None:
            return str(pd.to_datetime(dt_str, errors="coerce").date())
        return str(t.tz_convert(tz).date())
    except Exception:
        try:
            return str(dt_str.split("T")[0])
        except Exception:
            return None


# Backwards-compatible alias expected by newer scripts/instructions
PuntingFormAPI = PuntingFormClient
