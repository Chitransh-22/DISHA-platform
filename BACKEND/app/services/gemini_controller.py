"""
DISHA Gemini Quota Controller & AI Classification Service
Enforces strict rate-limiting, daily quota preservation, backoff retries, and high-precision extraction.
"""

import os
import re
import time
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_RPM_LIMIT = int(os.getenv("GEMINI_RPM_LIMIT", "12"))
DAILY_REQUEST_LIMIT = int(os.getenv("DAILY_REQUEST_LIMIT", "450"))

GEMINI_SYSTEM_PROMPT = """You are the DISHA Real-Time Disaster Intelligence Classifier for India.
Your mission is high-precision verification of physical disaster and emergency incidents in India.

Evaluate EVERY article independently.

CRITICAL DISASTER CRITERIA (Set is_disaster = true):
1. Must describe an actual, physical disaster or emergency that has occurred or is actively ongoing.
2. Must be located in India (or directly causing impact/damage on Indian territory).
3. Must involve ground impact: casualties, injuries, trapped persons, evacuations, submersion, or infrastructure damage.

ACCEPTED DISASTER TYPES:
- flood (flooding, flash flood, river overflow, waterlogging, submersion)
- earthquake (earthquake, tremors felt, aftershocks)
- landslide (landslide, mudslide, rockslide, hill collapse)
- cyclone (cyclone, tropical storm, severe cyclonic storm)
- cloudburst
- lightning (lightning deaths, injuries, strikes)
- heavy_rain (extreme downpour causing actual damage/flooding)
- heatwave (extreme heat causing recorded deaths/illnesses)
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
- Sports, cricket, tournaments, scores, entertainment, movies, celebrities, box office
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

Return ONLY a valid JSON object matching this schema:
{
  "results": [
    {
      "id": "<matching input article id>",
      "is_disaster": true,
      "confidence": 0.95,
      "disaster_type": "<flood|earthquake|landslide|cyclone|cloudburst|lightning|heavy_rain|heatwave|cold_wave|wildfire|avalanche|tsunami|drought|dam_failure|building_collapse|fire_accident|industrial_accident|explosion|transport_accident|other>",
      "severity": "<critical|high|medium|low|unknown>",
      "country": "India",
      "state": "<Indian State/UT name, or null>",
      "city": "<City or district name, or null>",
      "incident_date": "<YYYY-MM-DD or null>",
      "reason": "<1 clear sentence stating the exact ground event>",
      "evidence": [
        "<Key factual observation 1>",
        "<Key factual observation 2>"
      ],
      "is_forecast": false,
      "is_historical": false,
      "is_metaphorical": false
    }
  ]
}

Every input article must have exactly one corresponding item in the "results" array. No markdown fences outside the JSON.
"""


class QuotaController:
    """Controls and monitors Gemini rate limits and daily quota usage."""

    def __init__(self, ai_usage_collection):
        self.collection = ai_usage_collection
        self.last_request_time = 0.0
        self.min_interval = 60.0 / max(1, GEMINI_RPM_LIMIT)

    def can_make_request(self) -> bool:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        doc = self.collection.find_one({"_id": today})
        if doc and doc.get("requests", 0) >= DAILY_REQUEST_LIMIT:
            print(f"[QUOTA WARNING] Daily limit of {DAILY_REQUEST_LIMIT} requests reached for {today}.")
            return False
        return True

    def wait_for_slot(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def record_usage(self, requests_count: int, articles_count: int, estimated_tokens: int = 0):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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


def call_gemini_api(payload: Dict[str, Any], max_retries: int = 3) -> Optional[str]:
    """
    Sends request to Gemini REST endpoint with exponential backoff retries.
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
    backoff = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=request_body, timeout=60)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return None
                parts = candidates[0].get("content", {}).get("parts", [])
                raw_text = "".join(part.get("text", "") for part in parts).strip()
                return raw_text

            if response.status_code in (429, 500, 503):
                print(f"[GEMINI RETRY] HTTP {response.status_code} on attempt {attempt}/{max_retries}. Backing off {backoff:.1f}s...")
                time.sleep(backoff)
                backoff *= 2.0
                continue

            print(f"[GEMINI ERROR] HTTP {response.status_code}: {response.text[:200]}")
            return None

        except (requests.RequestException, TimeoutError) as e:
            print(f"[GEMINI TIMEOUT/NET ERROR] {e} on attempt {attempt}/{max_retries}.")
            time.sleep(backoff)
            backoff *= 2.0

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
            return parsed
        if isinstance(parsed, dict):
            return (
                parsed.get("results")
                or parsed.get("articles")
                or parsed.get("data")
                or []
            )
    except json.JSONDecodeError as e:
        print(f"[GEMINI JSON PARSE ERROR] {e} on text: {cleaned[:150]}")

    return []
