# DISHA Automated Incremental Data Ingestion Pipeline Plan

## 1. Objectives & Overview
Implement an automated, quota-aware, reliable incremental ingestion pipeline for DISHA with:
- Google News (GNews): Every 6 hours (`GNEWS_INTERVAL_HOURS=6`).
- NCS Earthquake Feed: Every 1 hour (`EARTHQUAKE_INTERVAL_HOURS=1`).
- NDMA SACHET Alerts: Every 1 hour (`SACHET_INTERVAL_HOURS=1`).
- Other Feeds / Extensible Feed: Every 1 hour (`OTHER_FEEDS_INTERVAL_HOURS=1`).
- Citizen Incident Reports: Persisted immediately upon submission, reconciled hourly.
- Gemini AI Classification: Only for new, eligible, unprocessed candidates with strict quota controls and reserve margin.

## 2. Key Architecture Components

### A. Centralized Settings (`app/core/config.py`)
- Ingestion intervals: `GNEWS_INTERVAL_HOURS`, `EARTHQUAKE_INTERVAL_HOURS`, `SACHET_INTERVAL_HOURS`, `OTHER_FEEDS_INTERVAL_HOURS`.
- Source enable flags: `GNEWS_ENABLED`, `EARTHQUAKE_ENABLED`, `SACHET_ENABLED`, `OTHER_FEEDS_ENABLED`.
- Global scheduler switch: `INGESTION_SCHEDULER_ENABLED`.
- Gemini Quota configuration:
  - `GEMINI_DAILY_REQUEST_BUDGET` (default: 250)
  - `GEMINI_REQUESTS_PER_MINUTE` (default: 10)
  - `GEMINI_DAILY_TOKEN_BUDGET` (default: 500,000)
  - `GEMINI_QUOTA_RESERVE_PERCENT` (default: 20)
  - `GEMINI_BATCH_SIZE` (default: 10)
  - `GEMINI_MAX_CONCURRENCY` (default: 1)
  - `GEMINI_AI_ENABLED` (default: true)
  - `GEMINI_MAX_ATTEMPTS_PER_ARTICLE` (default: 3)
  - `GEMINI_PROMPT_VERSION` (default: "v2.1-202610")
- Admin authorization: `ADMIN_API_KEY`.

### B. Distributed Locking (`app/services/distributed_lock.py`)
- Backed by MongoDB collection `ingestion_locks`.
- Uses atomic `findOneAndUpdate` with lease expiration (e.g., 30 minutes) to guarantee mutual exclusion across multiple Render web instances or worker processes.
- Automatic release on job completion; graceful recovery if a process dies.

### C. Persistent Checkpointing (`app/services/checkpoint_service.py`)
- Backed by MongoDB collection `ingestion_checkpoints`.
- Stores `last_successful_timestamp`, `last_successful_epoch`, `last_run_at`, `status`, and items count.
- Configurable overlap window (e.g. 2-24 hours depending on source) to handle out-of-order records.
- Checkpoints never advance on job failure.

### D. Strict Gemini Quota Manager (`app/services/gemini_quota_manager.py`)
- Checks budget before EVERY AI call.
- Tracks requests and estimated tokens in `ai_usage`.
- Enforces reserve margin (e.g. 20% reserved for manual/emergency tasks).
- Implements circuit breaker: trips on consecutive HTTP 429s or 5xx errors; enters cooldown period before testing half-open.
- Persistent candidate status: `pending`, `processing`, `completed`, `failed`, `deferred_quota`.
- When quota is reached, articles are marked `deferred_quota` and preserved in `news_temp`. Non-AI ingestion continues uninterrupted.

### E. Separated Discovery, Storage, & AI Classification (`app/services/fetch_gnews.py`)
1. Discover articles from RSS feed queries.
2. Pre-filter and score.
3. Persist new candidate articles into `news_temp` as `pending_ai` (or update existing) BEFORE AI is called.
4. If AI is disabled or quota exhausted, safely defer without data loss.
5. While quota available, batch-evaluate via `gemini_quota_manager`.
6. Verified disaster incidents upserted to `disaster_events`.
7. Preserves source publication time, discovery time, and processing time.

### F. Unified Ingestion Scheduler (`app/services/ingestion_scheduler.py`)
- Single unified scheduler replacing individual ad-hoc loops.
- Manages schedules for all 4 feeds + citizen reports reconciliation.
- Runs non-blocking background async loop in FastAPI lifespan.
- Provides CLI support (`python -m app.services.ingestion_scheduler --source <source>`).
- Logs structured run telemetry to `pipeline_runs`.

### G. Admin Ingestion Route (`app/routes/admin_ingestion.py`)
- `GET /api/admin/ingestion/status`: System health, next run, last success, checkpoints.
- `GET /api/admin/ingestion/quota`: Gemini quota and local budget telemetry.
- `POST /api/admin/ingestion/trigger`: Protected manual trigger.
- `GET /api/admin/ingestion/runs`: Execution history.
- Protected via Bearer token (admin role) or `X-Admin-Key` header.

### H. Verification & Automated Tests
- Test suite in `BACKEND/tests/test_ingestion_pipeline.py`.
- Tests all 13 scenarios with mocks (zero real API calls consumed).
- Verify invariants and run frontend build.
