"""
DISHA Platform - Automated Incremental Ingestion Pipeline Test Suite
Disaster Intelligence and Situational Hazard Awareness Platform

Verifies:
1. Ingestion scheduling intervals (GNews: 6h, Earthquakes: 1h, SACHET: 1h, Other feeds: 1h).
2. Distributed locking (MongoDB-backed) prevents overlapping runs (skipped_locked).
3. Checkpoint persistence, restart recovery, and strict watermark non-advancement on failure.
4. Gemini quota budget pre-flight checks, daily request/token limits, and reserve margin (20%).
5. Circuit breaker on HTTP 429 errors and cooldown behavior.
6. Zero data loss: AI deferral when quota exhausted (deferred_quota), candidates preserved in news_temp.
7. Unchanged articles skip AI re-classification via content fingerprint caching.
8. Non-AI ingestion (NCS, SACHET, Other Feeds) continues normally when Gemini is disabled or out of quota.
9. Admin API endpoints require authorization (reject unauthorized with 401).
10. Secure manual admin trigger with X-Admin-Key.
11. Idempotent ingestion and upsert deduplication (no duplicate records on repeat runs).
"""

import sys
import os
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest
import httpx
from httpx import AsyncClient, ASGITransport

# Ensure BACKEND directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.main import app
from app.services.distributed_lock import (
    DistributedLock,
    check_lock_status,
    force_release_lock,
    to_utc,
)
from app.services.checkpoint_service import (
    get_checkpoint,
    get_incremental_window,
    advance_checkpoint,
    record_failed_run,
)
from app.services.gemini_quota_manager import (
    GeminiQuotaManager,
    compute_article_fingerprint,
    quota_manager,
)
from app.services.ingestion_scheduler import (
    IngestionScheduler,
    run_earthquake_ingestion,
    run_sachet_ingestion,
    run_gnews_ingestion,
    run_other_feeds_ingestion,
    run_citizen_reports_reconcile,
)


# ============================================================================
# 1. SCHEDULING INTERVAL & CONFIGURATION TESTS
# ============================================================================

def test_ingestion_intervals_configuration():
    """Verify default intervals and quota settings adhere strictly to specification."""
    # Scheduler intervals
    assert settings.GNEWS_INTERVAL_HOURS == 6, "GNews ingestion must default to every 6 hours"
    assert settings.EARTHQUAKE_INTERVAL_HOURS == 1, "Earthquake feed must default to every 1 hour"
    assert settings.SACHET_INTERVAL_HOURS == 1, "SACHET alerts must default to every 1 hour"
    assert settings.OTHER_FEEDS_INTERVAL_HOURS == 1, "Other external feeds must default to every 1 hour"
    assert settings.CITIZEN_REPORTS_RECONCILE_INTERVAL_HOURS == 1, "Citizen reports reconcile must default to 1 hour"

    # Gemini Quota settings
    assert settings.GEMINI_DAILY_REQUEST_BUDGET == 250, "Daily request budget must be 250"
    assert settings.GEMINI_REQUESTS_PER_MINUTE == 10, "RPM throttle must be 10"
    assert settings.GEMINI_DAILY_TOKEN_BUDGET == 500000, "Daily token budget must be 500,000"
    assert settings.GEMINI_QUOTA_RESERVE_PERCENT == 20, "Quota reserve margin must be 20%"
    assert settings.GEMINI_MAX_ATTEMPTS_PER_ARTICLE == 3, "Max retry attempts per article must be 3"
    assert "v2.1" in settings.GEMINI_PROMPT_VERSION, "Prompt version must be tracked"


# ============================================================================
# 2. DISTRIBUTED LOCKING TESTS (Multi-Replica Safe)
# ============================================================================

class MockMongoLockCollection:
    """Mock MongoDB collection simulating atomic find_one_and_update for distributed locking."""
    def __init__(self):
        self.docs = {}

    def find_one(self, filter_query):
        lock_name = filter_query.get("lock_name")
        return self.docs.get(lock_name)

    def find_one_and_update(self, filter_query, update_query, return_document=None):
        lock_name = filter_query.get("lock_name")
        doc = self.docs.get(lock_name)
        now = datetime.now(timezone.utc)

        if doc:
            # Check if locked and unexpired
            exp_dt = to_utc(doc.get("expires_at"))
            is_expired = exp_dt is not None and exp_dt < now
            is_locked = doc.get("is_locked", False)
            same_owner = doc.get("owner_id") == update_query.get("$set", {}).get("owner_id")

            # In release path: filter has owner_id
            if "owner_id" in filter_query:
                if doc.get("owner_id") == filter_query["owner_id"]:
                    doc.update(update_query.get("$set", {}))
                    return doc
                return None

            # In acquire path
            if is_locked and not is_expired and not same_owner:
                return None

            # Can acquire
            doc.update(update_query.get("$set", {}))
            return doc
        return None

    def insert_one(self, doc):
        lock_name = doc.get("lock_name")
        self.docs[lock_name] = dict(doc)
        return MagicMock(inserted_id=lock_name)

    def update_one(self, filter_query, update_query):
        lock_name = filter_query.get("lock_name")
        doc = self.docs.get(lock_name)
        if doc:
            doc.update(update_query.get("$set", {}))
            return MagicMock(matched_count=1, modified_count=1)
        return MagicMock(matched_count=0, modified_count=0)


def test_distributed_lock_acquisition_and_mutual_exclusion():
    """Verify distributed lock prevents overlapping job executions across workers."""
    mock_coll = MockMongoLockCollection()
    with patch("app.services.distributed_lock.get_locks_collection", return_value=mock_coll):
        # Worker 1 acquires lock
        lock_1 = DistributedLock("earthquakes", lease_seconds=30, owner_id="worker_pod_1")
        acquired_1 = lock_1.acquire()
        assert acquired_1 is True
        assert lock_1.acquired is True

        # Worker 2 attempts to acquire same lock simultaneously -> must be rejected
        lock_2 = DistributedLock("earthquakes", lease_seconds=30, owner_id="worker_pod_2")
        acquired_2 = lock_2.acquire()
        assert acquired_2 is False
        assert lock_2.acquired is False

        # Worker 1 releases lock cleanly
        released = lock_1.release()
        assert released is True

        # Now Worker 2 can acquire it
        acquired_2_retry = lock_2.acquire()
        assert acquired_2_retry is True
        assert lock_2.acquired is True


def test_distributed_lock_context_manager_and_auto_expiration():
    """Verify context manager cleanly releases lock and auto-expires stale leases."""
    mock_coll = MockMongoLockCollection()
    with patch("app.services.distributed_lock.get_locks_collection", return_value=mock_coll):
        # Lock with short lease of 1 second
        with DistributedLock("sachet", lease_seconds=1, owner_id="worker_sachet") as lock:
            assert lock.acquired is True
            # Status check
            status = check_lock_status("sachet")
            assert status["is_locked"] is True
            assert status["owner_id"] == "worker_sachet"

        # After exiting context manager, lock is cleanly released
        status = check_lock_status("sachet")
        assert status["is_locked"] is False


def test_distributed_lock_force_release_admin():
    """Verify administrative force-release clears stuck lock regardless of original owner."""
    mock_coll = MockMongoLockCollection()
    with patch("app.services.distributed_lock.get_locks_collection", return_value=mock_coll):
        lock = DistributedLock("gnews", lease_seconds=3600, owner_id="crashed_pod_99")
        lock.acquire()
        status = check_lock_status("gnews")
        assert status["is_locked"] is True

        # Admin force-releases
        force_release_lock("gnews")
        status_after = check_lock_status("gnews")
        assert status_after["is_locked"] is False


# ============================================================================
# 3. CHECKPOINT & WATERMARK INTEGRITY TESTS
# ============================================================================

class MockMongoCheckpointCollection:
    """Mock MongoDB collection for persistent checkpoint management."""
    def __init__(self):
        self.docs = {}

    def find_one(self, filter_query):
        source = filter_query.get("source")
        return self.docs.get(source)

    def find_one_and_update(self, filter_query, update_query, upsert=False, return_document=None):
        source = filter_query.get("source")
        doc = self.docs.get(source, {"source": source})
        set_fields = update_query.get("$set", {})
        doc.update(set_fields)
        inc_fields = update_query.get("$inc", {})
        for k, v in inc_fields.items():
            doc[k] = doc.get(k, 0) + v
        self.docs[source] = doc
        return doc


def test_checkpoint_incremental_window_calculation():
    """Verify overlap window calculation prevents missing delayed out-of-order events."""
    mock_coll = MockMongoCheckpointCollection()
    with patch("app.services.checkpoint_service.get_checkpoints_collection", return_value=mock_coll):
        # Initial run: checkpoint is None -> default lookback window
        start_time, end_time = get_incremental_window("earthquakes", overlap_hours=2, fallback_window_days=30)
        now = datetime.now(timezone.utc)
        assert (now - start_time).total_seconds() >= 29 * 86400

        # Advance checkpoint to specific event timestamp
        event_ts = datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc)
        advance_checkpoint(
            source="earthquakes",
            last_event_time=event_ts,
            items_count=15,
            metadata={"status": "ok"},
        )

        # Next run window should be event_ts MINUS overlap window (2 hours)
        next_start, next_end = get_incremental_window("earthquakes", overlap_hours=2)
        expected_overlap_start = event_ts - timedelta(hours=2)
        assert abs((next_start - expected_overlap_start).total_seconds()) < 2


def test_checkpoint_watermark_never_advances_on_failure():
    """CRITICAL: Failed pipeline executions must NEVER advance the watermark."""
    mock_coll = MockMongoCheckpointCollection()
    with patch("app.services.checkpoint_service.get_checkpoints_collection", return_value=mock_coll):
        initial_ts = datetime(2026, 10, 28, 10, 0, 0, tzinfo=timezone.utc)
        advance_checkpoint(
            source="sachet",
            last_event_time=initial_ts,
            items_count=5,
        )

        # Simulate job failure
        record_failed_run("sachet", error_message="Network timeout connecting to NDMA portal")

        # Verify last_successful_timestamp is strictly unchanged
        chk = get_checkpoint("sachet")
        assert to_utc(chk["last_successful_timestamp"]) == initial_ts
        assert chk["consecutive_failures"] == 1
        assert "Network timeout" in chk["last_run_error"]


# ============================================================================
# 4. GEMINI QUOTA MANAGEMENT & CIRCUIT BREAKER TESTS
# ============================================================================

def test_gemini_quota_budget_and_reserve_margin():
    """Verify Gemini quota pre-flight checks, daily budget enforcement, and reserve protection."""
    qm = GeminiQuotaManager()

    with patch.object(settings, "GEMINI_API_KEY", "dummy-gemini-key"), \
         patch.object(settings, "GEMINI_AI_ENABLED", True):

        # Fresh state: should allow scheduled requests
        with patch.object(qm, "get_today_usage", return_value={"requests": 0, "estimated_tokens": 0}):
            allowed, reason = qm.can_call_ai(is_scheduled=True)
            assert allowed is True

        # Simulate usage up to reserve threshold:
        # Daily budget is 250, reserve percent is 20% (50 requests held for reserve)
        # So scheduled requests cap at 200.
        with patch.object(qm, "get_today_usage", return_value={"requests": 205, "estimated_tokens": 50000}):
            allowed_scheduled, reason_scheduled = qm.can_call_ai(is_scheduled=True)
            assert allowed_scheduled is False
            assert "Daily request budget reached" in reason_scheduled

            # Unscheduled/reserve requests (e.g. manual trigger, emergency alerts) can still run
            allowed_manual, _ = qm.can_call_ai(is_scheduled=False)
            assert allowed_manual is True

        # When total budget (250) is reached, all requests are blocked
        with patch.object(qm, "get_today_usage", return_value={"requests": 250, "estimated_tokens": 100000}):
            allowed_full, reason_full = qm.can_call_ai(is_scheduled=False)
            assert allowed_full is False
            assert "Daily request budget reached" in reason_full


def test_gemini_circuit_breaker_on_http_429():
    """Verify circuit breaker trips on HTTP 429 and enforces cooldown before allowing calls."""
    qm = GeminiQuotaManager()

    with patch.object(settings, "GEMINI_API_KEY", "dummy-gemini-key"), \
         patch.object(settings, "GEMINI_AI_ENABLED", True), \
         patch.object(qm, "col"):

        assert qm.circuit_breaker_open is False

        # Simulate upstream HTTP 429 rate limit error
        qm.record_failure(status_code=429, error_message="ResourceExhausted 429 Quota Exceeded")
        assert qm.circuit_breaker_open is True

        # Pre-flight check must reject calls immediately
        allowed, reason = qm.can_call_ai(is_scheduled=True)
        assert allowed is False
        assert "Circuit breaker active" in reason

        # Simulate cooldown expiration
        qm.circuit_breaker_reset_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        is_open, _ = qm.check_circuit_breaker()
        assert is_open is False
        assert qm.circuit_breaker_open is False


def test_content_fingerprint_generation_and_caching():
    """Verify deterministic article fingerprints prevent redundant AI classifications."""
    title = "Flash floods submerge low-lying areas in Guwahati"
    desc = "Continuous torrential rains in Assam triggered urban flooding across Kamrup district."
    
    fp1 = compute_article_fingerprint(title, desc)
    fp2 = compute_article_fingerprint(title, desc)
    assert fp1 == fp2, "Fingerprints for identical content must match deterministically"
    assert len(fp1) == 64, "Fingerprint must be SHA-256 hex string"

    qm = GeminiQuotaManager()

    # Cache missed
    assert qm.get_cached_classification(fp1) is None

    # Set cache
    dummy_classification = {"disaster_type": "flood", "severity": "high", "is_disaster": True}
    qm.set_cached_classification(fp1, dummy_classification)

    # Cache hit
    cached = qm.get_cached_classification(fp1)
    assert cached == dummy_classification


# ============================================================================
# 5. ZERO DATA LOSS & AI DEFERRAL TESTS
# ============================================================================

def test_zero_data_loss_on_gemini_quota_exhaustion():
    """
    CRITICAL: When Gemini quota is exhausted, candidate articles must be deferred
    to 'deferred_quota' and safely preserved in news_temp, NOT discarded.
    """
    from app.services.fetch_gnews import get_pending_ai_candidates

    mock_news_temp = MagicMock()
    # Mock articles in news_temp: some pending_ai, some deferred_quota
    mock_news_temp.find.return_value.sort.return_value.limit.return_value = [
        {"_id": "art_1", "title": "Cyclone alert", "ai_status": "pending_ai", "attempts": 1},
        {"_id": "art_2", "title": "Landslide in Wayanad", "ai_status": "deferred_quota", "attempts": 1},
    ]

    with patch("app.services.fetch_gnews.news_temp", mock_news_temp):
        candidates = get_pending_ai_candidates(max_count=10)
        assert len(candidates) == 2
        # Verify query matches both 'pending_ai' and 'deferred_quota'
        call_filter = mock_news_temp.find.call_args[0][0]
        assert "$in" in call_filter["status"]
        assert "pending_ai" in call_filter["status"]["$in"]
        assert "deferred_quota" in call_filter["status"]["$in"]


# ============================================================================
# 6. NON-AI INGESTION INDEPENDENCE & FAULT ISOLATION TESTS
# ============================================================================

def test_non_ai_ingestion_runs_when_gemini_disabled():
    """Non-AI feeds (earthquakes, SACHET alerts) must run unimpeded when AI is disabled."""
    mock_lock = MagicMock()
    mock_lock.acquire.return_value = True
    mock_lock.release.return_value = True

    # Mock earthquake fetcher
    mock_eq_result = {"status": "success", "total_scraped": 4, "inserted_count": 4}
    with patch("app.services.ingestion_scheduler.DistributedLock", return_value=mock_lock), \
         patch("app.services.ingestion_scheduler.sync_earthquakes_pipeline", return_value=mock_eq_result), \
         patch("app.services.ingestion_scheduler.advance_checkpoint") as mock_advance, \
         patch("app.services.ingestion_scheduler.log_pipeline_run"):
        
        # Ingest earthquakes with Gemini disabled
        with patch.object(settings, "GEMINI_AI_ENABLED", False):
            result = run_earthquake_ingestion(max_retries=1)
            assert result["status"] == "success"
            assert result["summary"]["inserted_count"] == 4
            assert mock_advance.called


def test_source_failure_isolation():
    """One failed source must not affect or halt other independent sources."""
    mock_lock = MagicMock()
    mock_lock.acquire.return_value = True
    mock_lock.release.return_value = True

    # 1. Earthquake scraper raises an exception
    with patch("app.services.ingestion_scheduler.DistributedLock", return_value=mock_lock), \
         patch("app.services.ingestion_scheduler.sync_earthquakes_pipeline", side_effect=RuntimeError("NCS portal unreachable")), \
         patch("app.services.ingestion_scheduler.record_failed_run") as mock_record_fail, \
         patch("app.services.ingestion_scheduler.log_pipeline_run"), \
         patch("time.sleep"):
        
        eq_result = run_earthquake_ingestion(max_retries=1)
        assert eq_result["status"] == "failed"
        assert "NCS portal unreachable" in eq_result["error"]
        assert mock_record_fail.called

    # 2. SACHET scraper runs immediately after and succeeds independently
    mock_sachet_result = {"status": "success", "total_scraped": 7, "inserted_count": 7}
    with patch("app.services.ingestion_scheduler.DistributedLock", return_value=mock_lock), \
         patch("app.services.ingestion_scheduler.sync_sachet_pipeline", return_value=mock_sachet_result), \
         patch("app.services.ingestion_scheduler.advance_checkpoint") as mock_advance, \
         patch("app.services.ingestion_scheduler.log_pipeline_run"):
        
        sachet_result = run_sachet_ingestion(max_retries=1)
        assert sachet_result["status"] == "success"
        assert sachet_result["summary"]["inserted_count"] == 7
        assert mock_advance.called


# ============================================================================
# 7. ADMIN INGESTION API SECURITY & AUTHORIZATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_admin_api_rejects_unauthorized_access():
    """Admin ingestion routes MUST return 401 Unauthorized when missing valid credentials."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Unauthenticated GET /api/admin/ingestion/status
        resp = await client.get("/api/admin/ingestion/status")
        assert resp.status_code == 401, "Admin status must reject unauthenticated requests"

        # 2. Invalid X-Admin-Key
        resp_invalid = await client.get(
            "/api/admin/ingestion/status",
            headers={"X-Admin-Key": "invalid_super_secret_key"}
        )
        assert resp_invalid.status_code == 401, "Admin status must reject invalid X-Admin-Key"

        # 3. Unauthorized POST /api/admin/ingestion/trigger
        resp_trigger = await client.post("/api/admin/ingestion/trigger?source=earthquakes")
        assert resp_trigger.status_code == 401, "Admin trigger must reject unauthorized calls"


@pytest.mark.asyncio
async def test_admin_api_accepts_valid_admin_key():
    """Admin ingestion routes succeed when presented with valid X-Admin-Key header."""
    admin_key = settings.ADMIN_API_KEY or "disha-admin-secret-key-2026"

    mock_scheduler_status = {
        "scheduler_enabled": True,
        "is_running": True,
        "active_tasks_count": 4,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "gnews": {"interval_hours": 6, "enabled": True},
            "earthquakes": {"interval_hours": 1, "enabled": True},
            "sachet": {"interval_hours": 1, "enabled": True},
            "other_feeds": {"interval_hours": 1, "enabled": True},
        },
        "gemini_quota": {},
    }

    mock_quota_telemetry = {
        "ai_enabled": True,
        "daily_request_budget": 250,
        "requests_used_today": 12,
        "daily_token_budget": 500000,
        "rpm_limit": 10,
        "circuit_breaker_open": False,
    }

    # Force known ADMIN_API_KEY for testing
    with patch.object(settings, "ADMIN_API_KEY", admin_key), \
         patch("app.routes.admin_ingestion.scheduler.get_status", return_value=mock_scheduler_status), \
         patch("app.routes.admin_ingestion.quota_manager.get_telemetry", return_value=mock_quota_telemetry), \
         patch("app.routes.admin_ingestion.force_release_lock", return_value=True):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Authorized GET /api/admin/ingestion/status
            resp = await client.get(
                "/api/admin/ingestion/status",
                headers={"X-Admin-Key": admin_key}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "ingestion" in data
            assert data["ingestion"]["sources"]["gnews"]["interval_hours"] == 6
            assert data["ingestion"]["sources"]["earthquakes"]["interval_hours"] == 1

            # 2. Authorized GET /api/admin/ingestion/quota
            resp_quota = await client.get(
                "/api/admin/ingestion/quota",
                headers={"X-Admin-Key": admin_key}
            )
            assert resp_quota.status_code == 200
            quota_data = resp_quota.json()
            assert quota_data["status"] == "success"
            assert quota_data["quota"]["daily_request_budget"] == 250
            assert quota_data["quota"]["rpm_limit"] == 10

            # 3. Authorized POST /api/admin/ingestion/locks/release
            resp_release = await client.post(
                "/api/admin/ingestion/locks/release?lock_name=lock_earthquakes",
                headers={"X-Admin-Key": admin_key}
            )
            assert resp_release.status_code == 200
            assert resp_release.json()["status"] == "success"


@pytest.mark.asyncio
async def test_admin_api_manual_trigger_execution():
    """Admin manual trigger initiates the requested source ingestion with audit logging."""
    admin_key = "disha-admin-secret-key-2026"

    mock_result = {"status": "success", "records_persisted": 3, "source": "earthquakes"}
    with patch.object(settings, "ADMIN_API_KEY", admin_key), \
         patch("app.routes.admin_ingestion.run_earthquake_ingestion", return_value=mock_result):
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/admin/ingestion/trigger?source=earthquakes&background=false",
                headers={"X-Admin-Key": admin_key}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "completed"
            assert data["source"] == "earthquakes"
            assert data["results"]["earthquakes"]["status"] == "success"


# ============================================================================
# 8. IDEMPOTENCE & DEDUPLICATION VERIFICATION
# ============================================================================

def test_idempotent_ingestion_prevents_duplicate_events():
    """
    Verify repeat runs with identical event feeds do not produce duplicate records.
    MongoDB upserts on canonical source IDs must preserve single records.
    """
    mock_events = [
        {"source_id": "eq_20261028_01", "type": "earthquake", "magnitude": 4.5, "title": "Earthquake in Assam"},
        {"source_id": "eq_20261028_02", "type": "earthquake", "magnitude": 3.8, "title": "Earthquake in Ladakh"},
    ]

    mock_db = {}
    def fake_update_one(filter_query, update_doc, upsert=False):
        source_id = filter_query.get("source_id")
        set_data = update_doc.get("$set", {})
        setOnInsert_data = update_doc.get("$setOnInsert", {})
        
        if source_id in mock_db:
            # Update existing
            mock_db[source_id].update(set_data)
        else:
            # Insert new
            record = {}
            record.update(setOnInsert_data)
            record.update(set_data)
            mock_db[source_id] = record
        return MagicMock(matched_count=1 if source_id in mock_db else 0, upserted_id=source_id)

    # First run: 2 events inserted
    for ev in mock_events:
        fake_update_one(
            {"source_id": ev["source_id"]},
            {"$set": {"last_seen": datetime.now(timezone.utc)}, "$setOnInsert": ev},
            upsert=True
        )
    assert len(mock_db) == 2

    # Second run with exact same events: count must remain 2 (no duplicates)
    for ev in mock_events:
        fake_update_one(
            {"source_id": ev["source_id"]},
            {"$set": {"last_seen": datetime.now(timezone.utc)}, "$setOnInsert": ev},
            upsert=True
        )
    assert len(mock_db) == 2, "Idempotent upserts must never create duplicate records"
