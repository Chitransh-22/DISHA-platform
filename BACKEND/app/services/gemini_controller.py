"""
DISHA Gemini Quota Controller & AI Verification Service
Enforces strict rate-limiting, daily quota preservation, backoff retries,
full batch response validation, and selective missing-ID retry handling.
"""

import os
import re
import time
import json
import random
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple

import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_RPM_LIMIT = int(os.getenv("GEMINI_RPM_LIMIT", "12"))
DAILY_REQUEST_LIMIT = int(os.getenv("DAILY_REQUEST_LIMIT", "450"))
GEMINI_BATCH_SIZE = int(os.getenv("GEMINI_BATCH_SIZE", "10"))
GEMINI_CONNECT_TIMEOUT = float(os.getenv("GEMINI_CONNECT_TIMEOUT", "15"))
GEMINI_READ_TIMEOUT = float(os.getenv("GEMINI_READ_TIMEOUT", "120"))

GEMINI_SYSTEM_PROMPT = """You are the DISHA Real-Time Disaster Intelligence Classifier for India.
Your mission is high-precision verification of physical disaster and emergency incidents in India.

Evaluate EVERY article independently.

CRITICAL DISASTER & TRUE RECENCY CRITERIA:
1. is_disaster = true ONLY IF the article describes an actual physical disaster or emergency with real-world ground impact (casualties, missing/trapped persons, injuries, evacuations, submersion, collapsed structures, physical damage).
2. is_current = true ONLY IF the incident occurred recently (within the last 24-72 hours) or is an active ongoing emergency.
3. is_historical = true IF the article discusses past disasters (e.g. from 2024, 2023, last year, years ago), retrospectives, memorials, or anniversaries.
4. is_forecast_only = true IF the article is ONLY a weather forecast, rain warning, or alert without reported physical damage/ground impact.
5. is_india = true ONLY IF the disaster occurred in India (or directly impacted Indian territory). Exclude foreign-exclusive disasters.

ACCEPTED DISASTER TYPES:
- flood (flash flood, river overflow, waterlogging, submersion)
- earthquake (earthquake, tremors, aftershocks)
- landslide (landslide, mudslide, rockslide, hill collapse)
- cyclone (cyclone, tropical storm, super cyclone, landfall)
- cloudburst
- lightning (lightning deaths, injuries, strikes)
- heavy_rain (extreme downpour causing actual damage/flooding)
- heatwave (extreme heat causing recorded deaths/hospitalizations)
- cold_wave (severe cold causing recorded deaths/disruption)
- wildfire (forest fire, bushfire)
- avalanche (snowslide)
- tsunami
- drought (acute drinking water/agricultural crisis)
- dam_failure (dam breach, collapse, burst, overflow)
- building_collapse (building, bridge, roof, wall, or tunnel collapse)
- fire_accident (major hotel, hospital, industrial, commercial, residential fire)
- industrial_accident (gas leak, chemical leak, boiler blast, factory explosion)
- explosion (bomb blast, IED blast, detonation)
- transport_accident (train derailment, bus falling into gorge, boat capsize, plane crash)

STRICT REJECTION CRITERIA (Set is_disaster = false):
- Metaphorical / Figurative usage ("landslide victory", "election landslide", "sports drought", "sales explosion", "market collapse")
- Sports, cricket, tournaments, entertainment, movies, celebrities, box office
- Pure weather forecasts/alerts without reported actual ground emergency / damage
- Pure political statements, policy meetings, relief packages without a current incident
- Historical disaster retrospectives or anniversaries
- Incidents exclusively in foreign countries with no impact in India
- Academic / Exam paper leaks, cyber data leaks

SEVERITY LEVELS:
- "critical": 10+ fatalities, massive displacement, extreme catastrophic destruction.
- "high": 1-9 fatalities, major hospitalizations, severe infrastructure damage.
- "medium": Significant property damage, evacuations/rescues, no reported fatalities.
- "low": Localized disruption, quickly brought under control, minor damage.
- "unknown": Severity not ascertainable from article.

Return ONLY a valid JSON object matching this exact schema:
{
  "results": [
    {
      "id": "<matching input article id>",
      "is_disaster": true,
      "is_current": true,
      "is_ongoing": false,
      "is_forecast_only": false,
      "is_historical": false,
      "is_india": true,
      "article_type": "<CURRENT_INCIDENT|ONGOING_INCIDENT|FORECAST_ONLY|HISTORICAL|ANALYSIS|POLICY|FUNDING|FOREIGN_INCIDENT|UNKNOWN>",
      "confidence": 0.95,
      "disaster_type": "<flood|earthquake|landslide|cyclone|cloudburst|lightning|heavy_rain|heatwave|cold_wave|wildfire|avalanche|tsunami|drought|dam_failure|building_collapse|fire_accident|industrial_accident|explosion|transport_accident|other>",
      "severity": "<critical|high|medium|low|unknown>",
      "country": "India",
      "state": "<Indian State/UT name, or null>",
      "district": "<District name, or null>",
      "city": "<City or town name, or null>",
      "incident_date": "<YYYY-MM-DD or null>",
      "reason": "<1 clear sentence stating the exact ground event>",
      "evidence": [
        "<Key factual observation 1>",
        "<Key factual observation 2>"
      ]
    }
  ]
}

Every input article must have exactly one corresponding item in the "results" array.
"""


class QuotaController:
    """Controls and monitors Gemini rate limits and daily quota usage."""

    def __init__(self, ai_usage_collection):
        self.collection = ai_usage_collection
        self.last_request_time = 0.0
        self.min_interval = 60.0 / max(1, GEMINI_RPM_LIMIT)

    def can_make_request(self) -> bool:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            doc = self.collection.find_one({"_id": today})
            if doc and doc.get("requests", 0) >= DAILY_REQUEST_LIMIT:
                print(f"[QUOTA WARNING] Daily limit of {DAILY_REQUEST_LIMIT} requests reached for {today}.")
                return False
        except Exception:
            pass
        return True

    def wait_for_slot(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def record_usage(self, requests_count: int, articles_count: int, estimated_tokens: int = 0):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            self.collection.update_one(
                {"_id": today},
                {
                    "$inc": {
                        "requests": requests_count,
                        "articles_processed": articles_count,
                        "estimated_tokens": estimated_tokens,
                    },
                    "$set": {
                        "date": today,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                },
                upsert=True,
            )
        except Exception as e:
            print(f"[USAGE RECORD NOTICE] {e}")


def call_gemini_api(payload: Dict[str, Any], max_retries: int = 3) -> Optional[str]:
    """
    Sends request to Gemini REST endpoint with separate connect/read timeouts,
    fine-grained error classification, and exponential backoff with jitter.
    """
    if not GEMINI_API_KEY:
        print("[GEMINI WARNING] GEMINI_API_KEY is not configured.")
        return None

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

    request_body = {
        "system_instruction": {
            "parts": [{"text": GEMINI_SYSTEM_PROMPT}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": json.dumps(payload, ensure_ascii=False)}],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    headers = {"Content-Type": "application/json"}
    timeouts = (GEMINI_CONNECT_TIMEOUT, GEMINI_READ_TIMEOUT)

    for attempt in range(1, max_retries + 1):
        # Calculate exponential backoff with randomized jitter
        jitter = random.uniform(0.5, 1.5)
        backoff_sec = (2.0 ** attempt) + jitter

        try:
            response = requests.post(url, headers=headers, json=request_body, timeout=timeouts)

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception as json_err:
                    print(f"[GEMINI INVALID RESPONSE] Failed to parse HTTP 200 JSON on attempt {attempt}/{max_retries}: {json_err}")
                    return None

                candidates = data.get("candidates", [])
                if not candidates:
                    print(f"[GEMINI INVALID RESPONSE] Response HTTP 200 but 'candidates' is empty: {data}")
                    return None

                parts = candidates[0].get("content", {}).get("parts", [])
                raw_text = "".join(part.get("text", "") for part in parts).strip()
                if not raw_text:
                    print(f"[GEMINI INVALID RESPONSE] Empty text returned in candidate parts on attempt {attempt}/{max_retries}.")
                    return None

                return raw_text

            if response.status_code == 503:
                print(f"[GEMINI HTTP 503] Attempt {attempt}/{max_retries}: Service Unavailable (Overloaded). Backing off {backoff_sec:.2f}s...")
                time.sleep(backoff_sec)
                continue

            if response.status_code == 429:
                rate_backoff = max(5.0, (2.0 ** attempt) + random.uniform(1.0, 3.0))
                print(f"[GEMINI RATE LIMIT] Attempt {attempt}/{max_retries}: Rate limit reached. Backing off {rate_backoff:.2f}s...")
                time.sleep(rate_backoff)
                continue

            if response.status_code in (500, 502, 504):
                print(f"[GEMINI HTTP {response.status_code}] Attempt {attempt}/{max_retries}: Server error. Backing off {backoff_sec:.2f}s...")
                time.sleep(backoff_sec)
                continue

            print(f"[GEMINI INVALID RESPONSE] HTTP {response.status_code}: {response.text[:250]}")
            return None

        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException, TimeoutError) as net_err:
            print(f"[GEMINI NETWORK ERROR] Attempt {attempt}/{max_retries}: {type(net_err).__name__} - {net_err}. Backing off {backoff_sec:.2f}s...")
            time.sleep(backoff_sec)

    return None


def parse_gemini_response(raw_text: str) -> List[Dict[str, Any]]:
    """
    Safely parses JSON and extracts classification results list.
    """
    if not raw_text:
        return []

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict):
            items = (
                parsed.get("results")
                or parsed.get("articles")
                or parsed.get("data")
                or []
            )
        else:
            items = []

        valid_items = []
        for it in items:
            if isinstance(it, dict) and it.get("id"):
                valid_items.append(it)
        return valid_items

    except json.JSONDecodeError as e:
        print(f"[GEMINI INVALID RESPONSE] JSON decode error: {e} on text: {cleaned[:150]}")

    return []


def validate_and_retry_gemini_batch(
    compact_articles: List[Dict[str, Any]],
    quota_controller: QuotaController,
    max_missing_retries: int = 2,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Validates that all input article IDs are present in the Gemini response.
    Selectively retries ONLY the missing or malformed articles with the smaller batch size.
    Returns: (validated_results, gemini_api_calls_made)
    """
    if not compact_articles:
        return [], 0

    api_calls_made = 0
    expected_ids = {a["id"] for a in compact_articles}
    articles_by_id = {a["id"]: a for a in compact_articles}
    collected_results: Dict[str, Dict[str, Any]] = {}

    current_batch = compact_articles

    for attempt in range(max_missing_retries + 1):
        if not current_batch:
            break

        if not quota_controller.can_make_request():
            print("[GEMINI] Daily quota reached during batch processing.")
            break

        quota_controller.wait_for_slot()
        payload = {"articles": current_batch}
        raw_resp = call_gemini_api(payload)
        api_calls_made += 1

        quota_controller.record_usage(
            requests_count=1,
            articles_count=len(current_batch),
            estimated_tokens=len(str(payload)) // 4,
        )

        if raw_resp is None:
            print(f"[GEMINI INVALID RESPONSE] Entire request failed for sub-batch of {len(current_batch)} articles.")
        else:
            parsed_items = parse_gemini_response(raw_resp)
            if not parsed_items:
                print(f"[GEMINI INVALID RESPONSE] No valid result items parsed from response.")

            for item in parsed_items:
                item_id = item.get("id")
                if item_id and item_id in expected_ids:
                    collected_results[item_id] = item

        missing_ids = expected_ids - set(collected_results.keys())
        if not missing_ids:
            print(f"[GEMINI SUCCESS] Verified all {len(collected_results)}/{len(expected_ids)} articles in batch.")
            break

        print(f"[GEMINI MISSING IDS] Resolved {len(collected_results)}/{len(expected_ids)} articles. Missing {len(missing_ids)} IDs: {list(missing_ids)}")

        if attempt < max_missing_retries:
            current_batch = [articles_by_id[mid] for mid in missing_ids if mid in articles_by_id]
            print(f"[GEMINI RETRY] Retrying ONLY {len(current_batch)} missing articles (attempt {attempt + 1}/{max_missing_retries})...")
            time.sleep(2.0)
        else:
            print(f"[GEMINI MISSING IDS] {len(missing_ids)} IDs remained unverified after all missing-ID retries.")

    return list(collected_results.values()), api_calls_made
