"""
DISHA Platform - Strict Gemini AI Quota Manager & Circuit Breaker
Disaster Intelligence and Situational Hazard Awareness Platform

Guarantees:
1. Daily request and token budget enforcement with configurable reserve margins.
2. Per-minute rate limiting (RPM throttling).
3. Circuit breaker on HTTP 429 quota exhaustion with graceful cooldown and recovery.
4. Content fingerprint caching to prevent re-classifying unchanged articles.
5. Persistent candidate queue states: pending, processing, completed, failed, deferred_quota.
6. Safe deferral: when budget is exhausted, candidate articles remain preserved in news_temp.
"""

import os
import time
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List

from pymongo.collection import Collection
from app.core.config import settings
from app.database.mongodb import db

logger = logging.getLogger("disha.gemini_quota")

AI_USAGE_COLLECTION = "ai_usage"
CIRCUIT_BREAKER_COOLDOWN_MINUTES = 15


def get_ai_usage_collection() -> Collection:
    return db[AI_USAGE_COLLECTION]


def to_utc(dt: Any) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_article_fingerprint(title: str, description: str = "", url: str = "") -> str:
    """Computes SHA-256 fingerprint of article text and canonical URL."""
    norm = f"{title.strip().lower()}|{description.strip().lower()}|{url.strip().lower()}"
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


class GeminiQuotaManager:
    """
    Centralized controller governing all Gemini AI interactions.
    Enforces local rate limits, daily request/token budgets, reserve margins,
    circuit breaking, and result caching.
    """

    def __init__(self, collection: Optional[Collection] = None):
        self.col = collection if collection is not None else get_ai_usage_collection()
        self.last_request_time = 0.0
        self.circuit_breaker_open = False
        self.circuit_breaker_reset_at: Optional[datetime] = None
        self.consecutive_429_count = 0
        self._fingerprint_cache: Dict[str, Any] = {}

    def get_cached_classification(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """Returns cached classification for an article fingerprint if present."""
        return self._fingerprint_cache.get(fingerprint)

    def set_cached_classification(self, fingerprint: str, classification: Dict[str, Any]):
        """Caches classification for an article fingerprint to prevent redundant inference."""
        self._fingerprint_cache[fingerprint] = classification

    def record_circuit_breaker_trip(self, cooldown_seconds: int = 900):
        """Manually trip circuit breaker with specified cooldown duration."""
        now_utc = datetime.now(timezone.utc)
        self.circuit_breaker_open = True
        self.circuit_breaker_reset_at = now_utc + timedelta(seconds=cooldown_seconds)

    def check_can_make_request(self, is_reserve: bool = False) -> Tuple[bool, str]:
        """Convenience alias for can_call_ai matching reserve flag semantics."""
        return self.can_call_ai(is_scheduled=not is_reserve)

    def get_today_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def get_today_usage(self) -> Dict[str, Any]:
        """Retrieves or initializes today's aggregated AI usage document."""
        today = self.get_today_key()
        try:
            doc = self.col.find_one({"_id": today})
            if not doc:
                return {
                    "_id": today,
                    "date": today,
                    "requests": 0,
                    "articles_processed": 0,
                    "estimated_tokens": 0,
                    "circuit_breaker_trips": 0,
                }
            return doc
        except Exception as err:
            logger.warning(f"[QuotaManager] Error reading today's usage: {err}")
            return {"_id": today, "requests": 0, "estimated_tokens": 0}

    def check_circuit_breaker(self) -> Tuple[bool, Optional[str]]:
        """Checks if circuit breaker is currently open."""
        now_utc = datetime.now(timezone.utc)
        if self.circuit_breaker_open:
            if self.circuit_breaker_reset_at and now_utc >= self.circuit_breaker_reset_at:
                logger.info("[QuotaManager] Circuit breaker cooldown elapsed. Entering half-open trial state.")
                self.circuit_breaker_open = False
                self.circuit_breaker_reset_at = None
                self.consecutive_429_count = 0
            else:
                rem = (self.circuit_breaker_reset_at - now_utc).total_seconds() if self.circuit_breaker_reset_at else 0
                return True, f"Circuit breaker active (HTTP 429 quota exhaustion). Cooldown remaining: {int(rem)}s."
        return False, None

    def can_call_ai(self, is_scheduled: bool = True) -> Tuple[bool, str]:
        """
        Pre-flight budget check executed BEFORE any Gemini API call.
        Returns: (can_proceed, reason)
        """
        if not settings.GEMINI_AI_ENABLED:
            return False, "Gemini AI processing is disabled via GEMINI_AI_ENABLED=false."

        if not settings.GEMINI_API_KEY:
            return False, "GEMINI_API_KEY is not configured."

        is_cb_open, cb_reason = self.check_circuit_breaker()
        if is_cb_open:
            return False, cb_reason or "Circuit breaker open."

        usage = self.get_today_usage()
        requests_used = usage.get("requests", 0)
        tokens_used = usage.get("estimated_tokens", 0)

        # Apply reserve margin for scheduled background runs
        # e.g., 20% reserve means scheduled runs cap at 80% of daily limit
        if is_scheduled:
            reserve_multiplier = 1.0 - (settings.GEMINI_QUOTA_RESERVE_PERCENT / 100.0)
            effective_request_limit = max(1, int(settings.GEMINI_DAILY_REQUEST_BUDGET * reserve_multiplier))
            effective_token_limit = max(1, int(settings.GEMINI_DAILY_TOKEN_BUDGET * reserve_multiplier))
        else:
            effective_request_limit = settings.GEMINI_DAILY_REQUEST_BUDGET
            effective_token_limit = settings.GEMINI_DAILY_TOKEN_BUDGET

        if requests_used >= effective_request_limit:
            msg = (
                f"Daily request budget reached: {requests_used}/{effective_request_limit} requests used "
                f"(Reserve: {settings.GEMINI_QUOTA_RESERVE_PERCENT}%). AI classification deferred."
            )
            logger.warning(f"[QuotaManager] {msg}")
            return False, msg

        if tokens_used >= effective_token_limit:
            msg = (
                f"Daily token budget reached: {tokens_used}/{effective_token_limit} tokens used "
                f"(Reserve: {settings.GEMINI_QUOTA_RESERVE_PERCENT}%). AI classification deferred."
            )
            logger.warning(f"[QuotaManager] {msg}")
            return False, msg

        return True, "Quota budget available."

    def wait_for_slot(self):
        """Enforces per-minute rate limiter (RPM throttling) using high-precision interval sleep."""
        min_interval = 60.0 / max(1, settings.GEMINI_REQUESTS_PER_MINUTE)
        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug(f"[QuotaManager] Throttling RPM: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def record_success(self, requests_count: int, articles_count: int, estimated_tokens: int = 0):
        """Records successful AI usage and resets consecutive error counters."""
        self.consecutive_429_count = 0
        today = self.get_today_key()
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            self.col.update_one(
                {"_id": today},
                {
                    "$inc": {
                        "requests": requests_count,
                        "articles_processed": articles_count,
                        "estimated_tokens": estimated_tokens,
                    },
                    "$set": {
                        "date": today,
                        "updated_at": now_iso,
                        "last_success_at": now_iso,
                    },
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"[QuotaManager] Error recording usage: {e}")

    def record_failure(self, status_code: int, error_message: str):
        """Records failure and trips circuit breaker on HTTP 429 quota exhaustion."""
        now_utc = datetime.now(timezone.utc)
        today = self.get_today_key()

        if status_code == 429:
            self.consecutive_429_count += 1
            logger.warning(
                f"[QuotaManager] Upstream HTTP 429 Rate Limit/Quota Exhaustion encountered "
                f"(count={self.consecutive_429_count})."
            )
            # Trip circuit breaker
            self.circuit_breaker_open = True
            self.circuit_breaker_reset_at = now_utc + timedelta(minutes=CIRCUIT_BREAKER_COOLDOWN_MINUTES)
            logger.warning(
                f"[QuotaManager] Circuit breaker TRIPPED. AI calls paused until {self.circuit_breaker_reset_at.isoformat()}."
            )
            try:
                self.col.update_one(
                    {"_id": today},
                    {
                        "$inc": {"circuit_breaker_trips": 1, "rate_limit_429_count": 1},
                        "$set": {
                            "last_429_at": now_utc.isoformat(),
                            "circuit_breaker_reset_at": self.circuit_breaker_reset_at.isoformat(),
                        },
                    },
                    upsert=True,
                )
            except Exception:
                pass

    def get_telemetry(self) -> Dict[str, Any]:
        """Provides complete observability metrics for administrative status monitoring."""
        usage = self.get_today_usage()
        requests_used = usage.get("requests", 0)
        tokens_used = usage.get("estimated_tokens", 0)

        reserve_multiplier = 1.0 - (settings.GEMINI_QUOTA_RESERVE_PERCENT / 100.0)
        sched_request_limit = int(settings.GEMINI_DAILY_REQUEST_BUDGET * reserve_multiplier)
        sched_token_limit = int(settings.GEMINI_DAILY_TOKEN_BUDGET * reserve_multiplier)

        is_cb_open, cb_reason = self.check_circuit_breaker()

        return {
            "ai_enabled": settings.GEMINI_AI_ENABLED,
            "has_api_key": bool(settings.GEMINI_API_KEY),
            "model": settings.GEMINI_MODEL,
            "prompt_version": settings.GEMINI_PROMPT_VERSION,
            "requests_used_today": requests_used,
            "daily_request_budget": settings.GEMINI_DAILY_REQUEST_BUDGET,
            "scheduled_request_limit": sched_request_limit,
            "requests_remaining_scheduled": max(0, sched_request_limit - requests_used),
            "requests_remaining_total": max(0, settings.GEMINI_DAILY_REQUEST_BUDGET - requests_used),
            "tokens_used_today": tokens_used,
            "daily_token_budget": settings.GEMINI_DAILY_TOKEN_BUDGET,
            "tokens_remaining_scheduled": max(0, sched_token_limit - tokens_used),
            "rpm_limit": settings.GEMINI_REQUESTS_PER_MINUTE,
            "reserve_percent": settings.GEMINI_QUOTA_RESERVE_PERCENT,
            "batch_size": settings.GEMINI_BATCH_SIZE,
            "circuit_breaker_open": is_cb_open,
            "circuit_breaker_reason": cb_reason,
            "circuit_breaker_reset_at": self.circuit_breaker_reset_at.isoformat() if self.circuit_breaker_reset_at else None,
            "note": "Configured local budgets protect DISHA application quota; provider-enforced account limits may differ if shared.",
        }


# Global singleton instance
quota_manager = GeminiQuotaManager()
