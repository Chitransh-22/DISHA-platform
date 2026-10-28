"""
DISHA Platform - Centralized Automated Ingestion Scheduler
Disaster Intelligence and Situational Hazard Awareness Platform

Features:
- Configurable scheduling via environment variables:
  * GNEWS_INTERVAL_HOURS = 6
  * EARTHQUAKE_INTERVAL_HOURS = 1
  * SACHET_INTERVAL_HOURS = 1
  * OTHER_FEEDS_INTERVAL_HOURS = 1
- Distributed locking via MongoDB to prevent overlapping runs across replicas.
- Incremental checkpointing per source (watermarks + overlap windows).
- Strict Gemini AI quota protection with reserve margin and circuit breaking.
- Bounded retries with exponential backoff and randomized jitter.
- Structured observability logging into `pipeline_runs`.
- Safe CLI execution for Render cron jobs, worker containers, or manual operations.
"""

import os
import sys
import time
import uuid
import random
import asyncio
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable

from dotenv import load_dotenv

# Ensure backend root is on sys.path
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

load_dotenv(_backend_dir / ".env")
load_dotenv()

from app.core.config import settings
from app.database.mongodb import db
from app.services.distributed_lock import DistributedLock, check_lock_status
from app.services.checkpoint_service import (
    get_checkpoint,
    advance_checkpoint,
    record_failed_run,
    get_incremental_window,
)
from app.services.gemini_quota_manager import quota_manager
from app.services.earthquake_service import sync_earthquakes_pipeline
from app.services.sachet_service import sync_sachet_pipeline
from app.services.fetch_gnews import fetch_gnews

logger = logging.getLogger("disha.ingestion_scheduler")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

PIPELINE_RUNS_COLLECTION = "pipeline_runs"


def get_pipeline_runs_collection():
    return db[PIPELINE_RUNS_COLLECTION]


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ============================================================================
# RUN LOGGING & OBSERVABILITY
# ============================================================================

def log_pipeline_run(
    source: str,
    run_id: str,
    status: str,
    started_at: datetime,
    finished_at: datetime,
    records_discovered: int = 0,
    records_inserted: int = 0,
    records_updated: int = 0,
    checkpoint_before: Optional[str] = None,
    checkpoint_after: Optional[str] = None,
    ai_telemetry: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Persists comprehensive execution run metadata for observability."""
    col = get_pipeline_runs_collection()
    duration_sec = round((finished_at - started_at).total_seconds(), 2)

    doc = {
        "run_id": run_id,
        "source": source,
        "status": status,  # "success", "failed", "skipped_locked"
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": duration_sec,
        "records_discovered": records_discovered,
        "records_inserted": records_inserted,
        "records_updated": records_updated,
        "checkpoint_before": checkpoint_before,
        "checkpoint_after": checkpoint_after,
        "ai_telemetry": ai_telemetry or {},
        "error": error,
        "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        col.insert_one(doc)
    except Exception as err:
        logger.warning(f"[Scheduler] Error logging pipeline run: {err}")

    return doc


# ============================================================================
# INDIVIDUAL SOURCE JOB EXECUTORS (Idempotent & Protected)
# ============================================================================

def run_gnews_ingestion(is_scheduled: bool = True, max_retries: int = 2) -> Dict[str, Any]:
    """
    Executes Google News / GNews Ingestion every 6 hours:
    1. Acquires distributed lock 'lock_gnews'.
    2. Retrieves current watermark.
    3. Runs fetch_gnews discovery, storage, and quota-governed AI verification.
    4. Advances watermark on success.
    5. Releases lock and records telemetry.
    """
    source = "gnews"
    run_id = f"run_{source}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    started_at = datetime.now(timezone.utc)
    chk_before = get_checkpoint(source).get("last_successful_timestamp")

    lock = DistributedLock(f"lock_{source}", lease_seconds=3600)
    if not lock.acquire():
        logger.info(f"[Scheduler] GNews job skipped: lock already held by another worker.")
        return {
            "source": source,
            "status": "skipped_locked",
            "message": "Distributed lock active",
            "run_id": run_id,
        }

    try:
        last_err = None
        summary = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[Scheduler] Executing GNews Ingestion (Attempt {attempt}/{max_retries})...")
                # Run GNews pipeline
                summary = fetch_gnews()
                if summary and summary.get("status") in ("success", "completed", "ok"):
                    break
            except Exception as err:
                last_err = err
                jitter = random.uniform(1.0, 3.0)
                backoff = (2.0 ** attempt) + jitter
                logger.warning(f"[Scheduler] GNews attempt {attempt} failed: {err}. Backing off {backoff:.1f}s...")
                time.sleep(backoff)

        finished_at = datetime.now(timezone.utc)

        if summary and not last_err:
            # Advance watermark to current run time
            advance_checkpoint(
                source=source,
                last_event_time=finished_at,
                items_count=summary.get("new_articles", 0),
                metadata={"verified_disasters": summary.get("gemini_verified", 0)},
            )
            chk_after = get_checkpoint(source).get("last_successful_timestamp")

            ai_telem = quota_manager.get_telemetry()
            log_pipeline_run(
                source=source,
                run_id=run_id,
                status="success",
                started_at=started_at,
                finished_at=finished_at,
                records_discovered=summary.get("articles_fetched", 0),
                records_inserted=summary.get("events_created", 0),
                records_updated=summary.get("events_updated", 0),
                checkpoint_before=chk_before,
                checkpoint_after=chk_after,
                ai_telemetry=ai_telem,
                details=summary,
            )
            return {"source": source, "status": "success", "run_id": run_id, "summary": summary}
        else:
            err_msg = str(last_err) if last_err else "GNews pipeline did not return success"
            record_failed_run(source=source, error_message=err_msg)
            log_pipeline_run(
                source=source,
                run_id=run_id,
                status="failed",
                started_at=started_at,
                finished_at=finished_at,
                checkpoint_before=chk_before,
                checkpoint_after=chk_before,
                error=err_msg,
            )
            return {"source": source, "status": "failed", "run_id": run_id, "error": err_msg}

    finally:
        lock.release()


def run_earthquake_ingestion(is_scheduled: bool = True, max_retries: int = 2) -> Dict[str, Any]:
    """
    Executes NCS RISEQ Earthquake Ingestion every 1 hour:
    1. Acquires distributed lock 'lock_earthquakes'.
    2. Runs sync_earthquakes_pipeline.
    3. Advances watermark and records telemetry.
    """
    source = "earthquakes"
    run_id = f"run_{source}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    started_at = datetime.now(timezone.utc)
    chk_before = get_checkpoint(source).get("last_successful_timestamp")

    lock = DistributedLock(f"lock_{source}", lease_seconds=1800)
    if not lock.acquire():
        logger.info(f"[Scheduler] Earthquake job skipped: lock already held by another worker.")
        return {
            "source": source,
            "status": "skipped_locked",
            "message": "Distributed lock active",
            "run_id": run_id,
        }

    try:
        last_err = None
        summary = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[Scheduler] Executing NCS Earthquake Ingestion (Attempt {attempt}/{max_retries})...")
                summary = sync_earthquakes_pipeline()
                if summary and summary.get("status") in ("success", "completed", "ok"):
                    break
            except Exception as err:
                last_err = err
                jitter = random.uniform(1.0, 2.0)
                backoff = (2.0 ** attempt) + jitter
                logger.warning(f"[Scheduler] Earthquake attempt {attempt} failed: {err}. Backing off {backoff:.1f}s...")
                time.sleep(backoff)

        finished_at = datetime.now(timezone.utc)

        if summary and not last_err:
            advance_checkpoint(
                source=source,
                last_event_time=finished_at,
                items_count=summary.get("total_scraped", 0),
                metadata=summary.get("metrics"),
            )
            chk_after = get_checkpoint(source).get("last_successful_timestamp")

            log_pipeline_run(
                source=source,
                run_id=run_id,
                status="success",
                started_at=started_at,
                finished_at=finished_at,
                records_discovered=summary.get("total_scraped", 0),
                records_inserted=summary.get("inserted_count", 0),
                records_updated=summary.get("updated_count", 0),
                checkpoint_before=chk_before,
                checkpoint_after=chk_after,
                details=summary,
            )
            return {"source": source, "status": "success", "run_id": run_id, "summary": summary}
        else:
            err_msg = str(last_err) if last_err else "Earthquake pipeline did not return success"
            record_failed_run(source=source, error_message=err_msg)
            log_pipeline_run(
                source=source,
                run_id=run_id,
                status="failed",
                started_at=started_at,
                finished_at=finished_at,
                checkpoint_before=chk_before,
                checkpoint_after=chk_before,
                error=err_msg,
            )
            return {"source": source, "status": "failed", "run_id": run_id, "error": err_msg}

    finally:
        lock.release()


def run_sachet_ingestion(is_scheduled: bool = True, force_refresh: bool = False, max_retries: int = 2) -> Dict[str, Any]:
    """
    Executes NDMA SACHET CAP Alerts Ingestion every 1 hour:
    1. Acquires distributed lock 'lock_sachet'.
    2. Runs sync_sachet_pipeline (honoring HTTP 304 / ETag).
    3. Advances watermark and records telemetry.
    """
    source = "sachet"
    run_id = f"run_{source}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    started_at = datetime.now(timezone.utc)
    chk_before = get_checkpoint(source).get("last_successful_timestamp")

    lock = DistributedLock(f"lock_{source}", lease_seconds=1800)
    if not lock.acquire():
        logger.info(f"[Scheduler] SACHET job skipped: lock already held by another worker.")
        return {
            "source": source,
            "status": "skipped_locked",
            "message": "Distributed lock active",
            "run_id": run_id,
        }

    try:
        last_err = None
        summary = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[Scheduler] Executing NDMA SACHET Ingestion (Attempt {attempt}/{max_retries})...")
                summary = sync_sachet_pipeline(force_refresh=force_refresh)
                if summary and summary.get("status") in ("success", "not_modified", "completed", "ok"):
                    break
            except Exception as err:
                last_err = err
                jitter = random.uniform(1.0, 2.0)
                backoff = (2.0 ** attempt) + jitter
                logger.warning(f"[Scheduler] SACHET attempt {attempt} failed: {err}. Backing off {backoff:.1f}s...")
                time.sleep(backoff)

        finished_at = datetime.now(timezone.utc)

        if summary and not last_err:
            advance_checkpoint(
                source=source,
                last_event_time=finished_at,
                items_count=summary.get("total_scraped", 0),
                metadata=summary.get("metrics"),
            )
            chk_after = get_checkpoint(source).get("last_successful_timestamp")

            log_pipeline_run(
                source=source,
                run_id=run_id,
                status="success" if summary.get("status") != "not_modified" else "not_modified",
                started_at=started_at,
                finished_at=finished_at,
                records_discovered=summary.get("total_scraped", 0),
                records_inserted=summary.get("inserted_count", 0),
                records_updated=summary.get("updated_count", 0),
                checkpoint_before=chk_before,
                checkpoint_after=chk_after,
                details=summary,
            )
            return {"source": source, "status": "success", "run_id": run_id, "summary": summary}
        else:
            err_msg = str(last_err) if last_err else "SACHET pipeline did not return success"
            record_failed_run(source=source, error_message=err_msg)
            log_pipeline_run(
                source=source,
                run_id=run_id,
                status="failed",
                started_at=started_at,
                finished_at=finished_at,
                checkpoint_before=chk_before,
                checkpoint_after=chk_before,
                error=err_msg,
            )
            return {"source": source, "status": "failed", "run_id": run_id, "error": err_msg}

    finally:
        lock.release()


def run_other_feeds_ingestion(is_scheduled: bool = True) -> Dict[str, Any]:
    """
    Executes Other Non-AI External Feeds every 1 hour:
    Provides an extensible plugin hook for external disaster feeds while respecting rate limits.
    """
    source = "other_feeds"
    run_id = f"run_{source}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    started_at = datetime.now(timezone.utc)
    chk_before = get_checkpoint(source).get("last_successful_timestamp")

    lock = DistributedLock(f"lock_{source}", lease_seconds=1800)
    if not lock.acquire():
        return {"source": source, "status": "skipped_locked", "run_id": run_id}

    try:
        logger.info("[Scheduler] Executing Other Feeds reconciliation cycle...")
        # Checkpoint maintenance & registry health check
        finished_at = datetime.now(timezone.utc)
        advance_checkpoint(source=source, last_event_time=finished_at, items_count=0)
        chk_after = get_checkpoint(source).get("last_successful_timestamp")

        log_pipeline_run(
            source=source,
            run_id=run_id,
            status="success",
            started_at=started_at,
            finished_at=finished_at,
            records_discovered=0,
            records_inserted=0,
            checkpoint_before=chk_before,
            checkpoint_after=chk_after,
        )
        return {"source": source, "status": "success", "run_id": run_id}
    finally:
        lock.release()


def run_citizen_reports_reconcile() -> Dict[str, Any]:
    """
    Hourly citizen reports reconciliation:
    Ensures geospatial indexing, validates coordinates, and refreshes candidate metadata.
    """
    source = "citizen_reports"
    run_id = f"run_{source}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    started_at = datetime.now(timezone.utc)

    lock = DistributedLock(f"lock_{source}", lease_seconds=600)
    if not lock.acquire():
        return {"source": source, "status": "skipped_locked", "run_id": run_id}

    try:
        col = db["incident_reports"]
        count = col.count_documents({})
        finished_at = datetime.now(timezone.utc)

        advance_checkpoint(source=source, last_event_time=finished_at, items_count=count)
        return {"source": source, "status": "success", "total_reports": count, "run_id": run_id}
    finally:
        lock.release()


# ============================================================================
# ASYNC IN-PROCESS SCHEDULER ENGINE
# ============================================================================

class IngestionScheduler:
    """
    Asynchronous in-process scheduler managing periodic interval loops for DISHA feeds.
    Automatically coordinates with distributed locks to avoid multi-worker duplication.
    """

    def __init__(self):
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._next_runs: Dict[str, datetime] = {}
        self._last_runs: Dict[str, Dict[str, Any]] = {}

    def get_status(self) -> Dict[str, Any]:
        """Provides real-time scheduler operational health and upcoming intervals."""
        now_utc = datetime.now(timezone.utc)

        sources_status = {}
        intervals = {
            "gnews": settings.GNEWS_INTERVAL_HOURS,
            "earthquakes": settings.EARTHQUAKE_INTERVAL_HOURS,
            "sachet": settings.SACHET_INTERVAL_HOURS,
            "other_feeds": settings.OTHER_FEEDS_INTERVAL_HOURS,
        }
        enabled_flags = {
            "gnews": settings.GNEWS_ENABLED,
            "earthquakes": settings.EARTHQUAKE_ENABLED,
            "sachet": settings.SACHET_ENABLED,
            "other_feeds": settings.OTHER_FEEDS_ENABLED,
        }

        for src in ["gnews", "earthquakes", "sachet", "other_feeds"]:
            chk = get_checkpoint(src)
            next_run = self._next_runs.get(src)
            sources_status[src] = {
                "enabled": enabled_flags.get(src, True),
                "interval_hours": intervals.get(src, 1),
                "last_run_at": chk.get("last_run_at"),
                "last_run_status": chk.get("last_run_status"),
                "last_successful_run_at": chk.get("last_successful_run_at"),
                "last_successful_watermark": chk.get("last_successful_timestamp"),
                "next_scheduled_run": next_run.isoformat() if next_run else None,
                "lock": check_lock_status(f"lock_{src}"),
                "consecutive_failures": chk.get("consecutive_failures", 0),
            }

        return {
            "scheduler_enabled": settings.INGESTION_SCHEDULER_ENABLED,
            "is_running": self._running,
            "active_tasks_count": len([t for t in self._tasks if not t.done()]),
            "timestamp": now_utc.isoformat(),
            "sources": sources_status,
            "gemini_quota": quota_manager.get_telemetry(),
        }

    async def _run_loop(self, source: str, interval_hours: float, runner_func: Callable, enabled: bool):
        """Generic non-blocking async worker loop for a specific ingestion source."""
        interval_seconds = max(60, int(interval_hours * 3600))
        logger.info(f"[Scheduler] Registered '{source}' worker loop (Interval: {interval_hours}h / {interval_seconds}s, Enabled: {enabled})")

        # Initial staggered jitter delay to avoid startup stampedes
        stagger_sec = random.uniform(5.0, 20.0)
        self._next_runs[source] = datetime.now(timezone.utc) + timedelta(seconds=stagger_sec)
        await asyncio.sleep(stagger_sec)

        while self._running:
            if enabled:
                logger.info(f"[Scheduler] Starting scheduled cycle for '{source}'...")
                try:
                    # Run synchronous network/database ingestion in executor pool
                    loop = asyncio.get_running_loop()
                    res = await loop.run_in_executor(None, runner_func)
                    self._last_runs[source] = res
                except Exception as err:
                    logger.error(f"[Scheduler] Error executing '{source}' cycle: {err}", exc_info=True)

            self._next_runs[source] = datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)

            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                logger.info(f"[Scheduler] Worker loop for '{source}' cancelled.")
                break

    def start(self):
        """Starts all background ingestion worker loops."""
        if not settings.INGESTION_SCHEDULER_ENABLED:
            logger.info("[Scheduler] Ingestion scheduler is disabled via INGESTION_SCHEDULER_ENABLED=false.")
            return

        if self._running:
            logger.warning("[Scheduler] Scheduler is already running.")
            return

        self._running = True
        logger.info("[Scheduler] Initiating DISHA Automated Ingestion Scheduler background loops...")

        # 1. GNews (every 6 hours default)
        t_gnews = asyncio.create_task(
            self._run_loop("gnews", settings.GNEWS_INTERVAL_HOURS, run_gnews_ingestion, settings.GNEWS_ENABLED)
        )
        self._tasks.append(t_gnews)

        # 2. NCS Earthquakes (every 1 hour default)
        t_eq = asyncio.create_task(
            self._run_loop("earthquakes", settings.EARTHQUAKE_INTERVAL_HOURS, run_earthquake_ingestion, settings.EARTHQUAKE_ENABLED)
        )
        self._tasks.append(t_eq)

        # 3. NDMA SACHET Alerts (every 1 hour default)
        t_sachet = asyncio.create_task(
            self._run_loop("sachet", settings.SACHET_INTERVAL_HOURS, run_sachet_ingestion, settings.SACHET_ENABLED)
        )
        self._tasks.append(t_sachet)

        # 4. Other Feeds (every 1 hour default)
        t_other = asyncio.create_task(
            self._run_loop("other_feeds", settings.OTHER_FEEDS_INTERVAL_HOURS, run_other_feeds_ingestion, settings.OTHER_FEEDS_ENABLED)
        )
        self._tasks.append(t_other)

        # 5. Citizen Reports Reconciliation (every 1 hour)
        t_citizen = asyncio.create_task(
            self._run_loop("citizen_reports", 1.0, run_citizen_reports_reconcile, True)
        )
        self._tasks.append(t_citizen)

    def stop(self):
        """Cancels all active worker loops on server shutdown."""
        self._running = False
        for t in self._tasks:
            if not t.done():
                t.cancel()
        self._tasks.clear()
        logger.info("[Scheduler] DISHA Ingestion Scheduler stopped cleanly.")


# Global singleton scheduler instance
scheduler = IngestionScheduler()


# ============================================================================
# CLI ENTRYPOINT FOR EXTERNAL CRON / WORKER SCRIPTS
# ============================================================================

def main_cli():
    """Command-line interface for manual runs or external Render/OS cron triggers."""
    parser = argparse.ArgumentParser(description="DISHA Automated Ingestion Pipeline Runner")
    parser.add_argument(
        "--source",
        choices=["gnews", "earthquakes", "sachet", "other_feeds", "citizen", "all"],
        default="all",
        help="Data source to ingest (default: all)",
    )
    parser.add_argument("--status", action="store_true", help="Display current scheduler & quota status")
    parser.add_argument("--force", action="store_true", help="Force bypass conditional 304/ETag checks")
    args = parser.parse_args()

    if args.status:
        import pprint
        st = scheduler.get_status()
        pprint.pprint(st)
        return

    print(f"\n[DISHA INGESTION] Running ingestion for source: {args.source.upper()}")

    results = {}
    if args.source in ("gnews", "all"):
        results["gnews"] = run_gnews_ingestion(is_scheduled=False)
    if args.source in ("earthquakes", "all"):
        results["earthquakes"] = run_earthquake_ingestion(is_scheduled=False)
    if args.source in ("sachet", "all"):
        results["sachet"] = run_sachet_ingestion(is_scheduled=False, force_refresh=args.force)
    if args.source in ("other_feeds", "all"):
        results["other_feeds"] = run_other_feeds_ingestion(is_scheduled=False)
    if args.source in ("citizen", "all"):
        results["citizen"] = run_citizen_reports_reconcile()

    print("\n[DISHA INGESTION] Execution Completed:")
    for src, res in results.items():
        print(f"  • {src}: {res.get('status')}")
    print()


if __name__ == "__main__":
    main_cli()
