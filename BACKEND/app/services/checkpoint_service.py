"""
DISHA Platform - Ingestion Checkpoint & Watermark Service
Disaster Intelligence and Situational Hazard Awareness Platform

Persists incremental watermarks and configurable overlap windows per ingestion source
in MongoDB (`ingestion_checkpoints`). Guarantees that checkpoints only advance
upon verified successful persistence, and preserves historical data without duplicates.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any

from pymongo.collection import Collection
from pymongo import ReturnDocument
from app.database.mongodb import db

logger = logging.getLogger("disha.checkpoint_service")

CHECKPOINTS_COLLECTION = "ingestion_checkpoints"


def get_checkpoints_collection() -> Collection:
    return db[CHECKPOINTS_COLLECTION]


def to_utc(dt: Any) -> Optional[datetime]:
    """Ensures datetime is offset-aware in UTC. Accepts datetime, ISO string, or None."""
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


def init_checkpoint_indexes():
    """Ensure indexes on checkpoints collection."""
    try:
        col = get_checkpoints_collection()
        col.create_index("source", unique=True)
    except Exception as e:
        logger.warning(f"[CheckpointService] Notice initializing indexes: {e}")


def get_checkpoint(source: str) -> Dict[str, Any]:
    """
    Retrieves the persisted watermark and status for a source.
    Returns a default record if the source has never run.
    """
    col = get_checkpoints_collection()
    doc = col.find_one({"source": source})
    if not doc:
        return {
            "source": source,
            "last_successful_timestamp": None,
            "last_successful_epoch": None,
            "last_successful_run_at": None,
            "last_run_at": None,
            "last_run_status": "never_run",
            "items_processed": 0,
            "total_runs": 0,
            "consecutive_failures": 0,
        }
    return doc


def get_incremental_window(
    source: str,
    overlap_hours: int = 2,
    fallback_window_days: int = 30,
) -> Tuple[datetime, datetime]:
    """
    Computes (start_time_utc, end_time_utc) for incremental polling.
    Applies a configurable overlap window behind the watermark to catch delayed or out-of-order records.
    If no prior watermark exists, defaults to fallback_window_days ago.
    """
    now_utc = datetime.now(timezone.utc)
    chk = get_checkpoint(source)
    last_ts_raw = chk.get("last_successful_timestamp")

    if last_ts_raw:
        if isinstance(last_ts_raw, datetime):
            watermark = to_utc(last_ts_raw)
        else:
            try:
                watermark = datetime.fromisoformat(str(last_ts_raw).replace("Z", "+00:00"))
                watermark = to_utc(watermark)
            except Exception:
                watermark = now_utc - timedelta(days=fallback_window_days)
        # Apply safety overlap window
        start_time = watermark - timedelta(hours=overlap_hours)
    else:
        # Initial run: full window
        start_time = now_utc - timedelta(days=fallback_window_days)

    return start_time, now_utc


def advance_checkpoint(
    source: str,
    last_event_time: Optional[datetime],
    items_count: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Advances the source watermark to the latest successfully persisted event timestamp.
    NEVER advances watermark past unpersisted or failed records.
    """
    col = get_checkpoints_collection()
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.isoformat()

    prev_doc = get_checkpoint(source)
    prev_watermark = to_utc(prev_doc.get("last_successful_timestamp"))

    # Only advance watermark forward in time
    new_watermark = prev_watermark
    new_epoch = prev_doc.get("last_successful_epoch")

    if last_event_time is not None:
        cand_utc = to_utc(last_event_time)
        if prev_watermark is None or cand_utc > prev_watermark:
            new_watermark = cand_utc
            new_epoch = cand_utc.timestamp()

    update_fields = {
        "source": source,
        "last_successful_timestamp": new_watermark.isoformat() if new_watermark else None,
        "last_successful_epoch": new_epoch,
        "last_successful_run_at": now_iso,
        "last_run_at": now_iso,
        "last_run_status": "success",
        "last_run_error": None,
        "consecutive_failures": 0,
        "updated_at": now_iso,
    }

    if metadata:
        update_fields["metadata"] = metadata

    doc = col.find_one_and_update(
        {"source": source},
        {
            "$set": update_fields,
            "$inc": {
                "items_processed": items_count,
                "total_runs": 1,
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    logger.info(f"[CheckpointService] Advanced watermark for '{source}' to {new_watermark}")
    return doc


def record_failed_run(
    source: str,
    error_message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Records a pipeline execution failure.
    CRITICAL: Preserves the previous watermark without advancing it, guaranteeing safe retry.
    """
    col = get_checkpoints_collection()
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.isoformat()

    update_fields = {
        "source": source,
        "last_run_at": now_iso,
        "last_run_status": "failed",
        "last_run_error": error_message[:500],
        "updated_at": now_iso,
    }

    if metadata:
        update_fields["metadata"] = metadata

    doc = col.find_one_and_update(
        {"source": source},
        {
            "$set": update_fields,
            "$inc": {
                "total_runs": 1,
                "consecutive_failures": 1,
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    logger.warning(f"[CheckpointService] Recorded failed run for '{source}'. Watermark preserved.")
    return doc
