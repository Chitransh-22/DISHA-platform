"""
DISHA Platform - NDMA SACHET Alert Pipeline Service
Manages synchronization, deduplication, rolling 30-day retention, database upserts,
and querying for NDMA SACHET CAP disaster alerts.
"""

import os
import sys
import logging
import threading
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set

from dotenv import load_dotenv

# Ensure backend root in sys.path
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

load_dotenv(_backend_dir / ".env")
load_dotenv()

from pymongo.collection import Collection
from pymongo import UpdateOne
from pymongo.errors import PyMongoError

from app.database.mongodb import db
from app.sources.sachet import (
    scrape_sachet_alerts,
    generate_sachet_event_id,
    SACHET_RSS_URL,
    SACHET_TIMEOUT,
)

logger = logging.getLogger("disha.services.sachet")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

sachet_collection: Collection = db["sachet_alerts"]
sync_state_collection: Collection = db["sync_state"]
pipeline_runs_collection: Collection = db["pipeline_runs"]

# Concurrency lock to prevent simultaneous overlapping sync executions
_sync_lock = threading.Lock()
_last_sync_info: Dict[str, Any] = {
    "status": "idle",
    "last_run_at": None,
    "last_run_duration": None,
    "last_run_metrics": None,
}


def get_last_sync_metrics() -> Dict[str, Any]:
    """Returns the metrics and status of the latest pipeline execution."""
    return dict(_last_sync_info)


def sync_sachet_pipeline(
    force_refresh: bool = False,
    timeout: int = SACHET_TIMEOUT,
    reference_now: Optional[datetime] = None,
    target_collection: Optional[Collection] = None,
    target_sync_state: Optional[Collection] = None,
) -> Dict[str, Any]:
    """
    Executes a complete on-demand synchronization of the NDMA SACHET CAP pipeline:
    1. Reads cached ETag and Last-Modified from sync_state collection.
    2. Fetches SACHET RSS XML (honoring 304 Not Modified if feed is unchanged).
    3. Concurrently resolves and parses underlying CAP XML documents for new/updated alerts.
    4. Identifies new, updated, and unchanged events using deterministic event_id.
    5. Handles CAP Update and Cancel lifecycle semantics.
    6. Performs atomic MongoDB upserts with first_seen_at/last_seen_at tracking.
    7. Automatically purges records older than 30 days.
    8. Records execution metrics for observability and synchronizes the map dashboard.
    """
    global _last_sync_info

    # Non-blocking lock check: if already running, skip safely
    if not _sync_lock.acquire(blocking=False):
        logger.warning("[SACHET] Synchronization already in progress. Skipping concurrent request.")
        return {
            "source": "NDMA_SACHET",
            "status": "skipped",
            "message": "Another synchronization is currently running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    start_time = time.time()
    now_utc = reference_now if reference_now is not None else datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    now_iso = now_utc.isoformat()

    col = target_collection if target_collection is not None else sachet_collection
    sync_state_col = target_sync_state if target_sync_state is not None else sync_state_collection

    logger.info("[SACHET] Fetching India CAP RSS feed")

    try:
        # Step 1: Check cached ETag
        cached_state = None
        cached_etag = None
        cached_last_mod = None

        if not force_refresh:
            try:
                cached_state = sync_state_col.find_one({"pipeline": "NDMA_SACHET"})
                if cached_state:
                    cached_etag = cached_state.get("etag")
                    cached_last_mod = cached_state.get("last_modified")
            except Exception as e:
                logger.debug(f"[SACHET] Could not read sync_state: {e}")

        # Step 2: Fetch and scrape feed
        scrape_res = scrape_sachet_alerts(
            rss_url=SACHET_RSS_URL,
            timeout=timeout,
            cached_etag=cached_etag,
            cached_last_modified=cached_last_mod,
            force_refresh=force_refresh,
            reference_now=now_utc,
        )

        duration = round(time.time() - start_time, 2)

        # Handle 304 Not Modified
        if scrape_res.get("status") == "not_modified":
            logger.info("[SACHET] HTTP 304 Not Modified")
            logger.info("[SACHET] No new source data")
            logger.info(f"[SACHET] Sync skipped ({duration}s)")

            summary = {
                "source": "NDMA_SACHET",
                "status": "not_modified",
                "message": "Feed not modified on server (ETag matched)",
                "etag": cached_etag,
                "fetched": 0,
                "within_30_days": 0,
                "new": 0,
                "updated": 0,
                "unchanged": 0,
                "invalid": 0,
                "expired_removed": 0,
                "etag_changed": False,
                "duration_seconds": duration,
                "timestamp": now_iso,
            }
            _last_sync_info = {
                "status": "not_modified",
                "last_run_at": now_iso,
                "last_run_duration": duration,
                "last_run_metrics": summary,
            }
            return summary

        # Handle Error
        if scrape_res.get("status") != "success":
            err_msg = scrape_res.get("error", "Unknown SACHET ingestion error")
            logger.error(f"[SACHET] Fetch failed: {err_msg}")

            summary = {
                "source": "NDMA_SACHET",
                "status": "error",
                "error": err_msg,
                "fetched": 0,
                "within_30_days": 0,
                "new": 0,
                "updated": 0,
                "unchanged": 0,
                "invalid": 0,
                "expired_removed": 0,
                "etag_changed": False,
                "duration_seconds": duration,
                "timestamp": now_iso,
            }
            _last_sync_info = {
                "status": "error",
                "last_run_at": now_iso,
                "last_run_duration": duration,
                "last_run_metrics": summary,
            }
            return summary

        events: List[Dict[str, Any]] = scrape_res.get("events", [])
        total_scraped = scrape_res.get("total_items", len(events))
        within_30d = scrape_res.get("within_30_days", len(events))
        new_etag = scrape_res.get("etag")
        new_last_mod = scrape_res.get("last_modified")

        logger.info(f"[SACHET] Items found: {total_scraped}")
        logger.info(f"[SACHET] Within 30 days: {within_30d}")

        # Step 3: Query existing active records for in-memory comparison
        cutoff_30d = now_utc - timedelta(days=30)
        cutoff_30d_iso = cutoff_30d.isoformat()

        existing_cursor = col.find(
            {"event_time": {"$gte": cutoff_30d_iso}},
            {
                "_id": 0,
                "event_id": 1,
                "alert_id": 1,
                "guid": 1,
                "severity": 1,
                "urgency": 1,
                "certainty": 1,
                "status": 1,
                "message_type": 1,
                "effective_at": 1,
                "onset_at": 1,
                "expires_at": 1,
                "area_description": 1,
                "description": 1,
                "headline": 1,
                "instruction": 1,
                "latitude": 1,
                "longitude": 1,
                "polygon": 1,
                "is_active": 1,
                "is_cancelled": 1,
            },
        )
        existing_map: Dict[str, Dict[str, Any]] = {
            doc["event_id"]: doc for doc in existing_cursor if "event_id" in doc
        }

        new_count = 0
        updated_count = 0
        unchanged_count = 0
        invalid_count = 0

        bulk_ops = []

        # Step 4: Compare and upsert records
        for event in events:
            ev_id = event.get("event_id")
            if not ev_id:
                invalid_count += 1
                continue

            if ev_id in existing_map:
                existing_doc = existing_map[ev_id]

                # Check if fields changed
                fields_changed = (
                    existing_doc.get("severity") != event.get("severity")
                    or existing_doc.get("urgency") != event.get("urgency")
                    or existing_doc.get("certainty") != event.get("certainty")
                    or existing_doc.get("status") != event.get("status")
                    or existing_doc.get("message_type") != event.get("message_type")
                    or existing_doc.get("effective_at") != event.get("effective_at")
                    or existing_doc.get("onset_at") != event.get("onset_at")
                    or existing_doc.get("expires_at") != event.get("expires_at")
                    or existing_doc.get("area_description") != event.get("area_description")
                    or existing_doc.get("description") != event.get("description")
                    or existing_doc.get("headline") != event.get("headline")
                    or existing_doc.get("instruction") != event.get("instruction")
                    or existing_doc.get("polygon") != event.get("polygon")
                    or existing_doc.get("is_active") != event.get("is_active")
                    or existing_doc.get("is_cancelled") != event.get("is_cancelled")
                    or abs((existing_doc.get("latitude") or 0.0) - (event.get("latitude") or 0.0)) > 1e-4
                    or abs((existing_doc.get("longitude") or 0.0) - (event.get("longitude") or 0.0)) > 1e-4
                )

                if fields_changed:
                    update_data = {
                        "severity": event.get("severity"),
                        "urgency": event.get("urgency"),
                        "certainty": event.get("certainty"),
                        "status": event.get("status"),
                        "message_type": event.get("message_type"),
                        "effective_at": event.get("effective_at"),
                        "onset_at": event.get("onset_at"),
                        "expires_at": event.get("expires_at"),
                        "sent_at": event.get("sent_at"),
                        "area_description": event.get("area_description"),
                        "headline": event.get("headline"),
                        "description": event.get("description"),
                        "instruction": event.get("instruction"),
                        "latitude": event.get("latitude"),
                        "longitude": event.get("longitude"),
                        "polygon": event.get("polygon"),
                        "circle": event.get("circle"),
                        "location": event.get("location"),
                        "is_active": event.get("is_active"),
                        "is_cancelled": event.get("is_cancelled"),
                        "metadata": event.get("metadata", {}),
                        "updated_at": now_iso,
                        "last_seen_at": now_iso,
                    }
                    if hasattr(col, "bulk_write"):
                        bulk_ops.append(UpdateOne({"event_id": ev_id}, {"$set": update_data}))
                    else:
                        col.update_one({"event_id": ev_id}, {"$set": update_data})
                    updated_count += 1
                else:
                    # Refresh last_seen_at & is_active
                    refresh_data = {
                        "last_seen_at": now_iso,
                        "is_active": event.get("is_active", True),
                    }
                    if hasattr(col, "bulk_write"):
                        bulk_ops.append(UpdateOne({"event_id": ev_id}, {"$set": refresh_data}))
                    else:
                        col.update_one({"event_id": ev_id}, {"$set": refresh_data})
                    unchanged_count += 1

            else:
                # Brand new alert
                set_fields = {k: v for k, v in event.items() if k not in ("first_seen_at", "created_at")}
                set_fields["last_seen_at"] = now_iso
                set_fields["updated_at"] = now_iso

                if hasattr(col, "bulk_write"):
                    bulk_ops.append(
                        UpdateOne(
                            {"event_id": ev_id},
                            {
                                "$setOnInsert": {
                                    "first_seen_at": now_iso,
                                    "created_at": now_iso,
                                },
                                "$set": set_fields,
                            },
                            upsert=True,
                        )
                    )
                else:
                    try:
                        col.update_one(
                            {"event_id": ev_id},
                            {
                                "$setOnInsert": {
                                    "first_seen_at": now_iso,
                                    "created_at": now_iso,
                                },
                                "$set": set_fields,
                            },
                            upsert=True,
                        )
                    except Exception:
                        pass
                new_count += 1

            # Step 4b: Handle CAP Cancel or Update references
            references_str = event.get("references", "")
            if references_str:
                # References format: sender,identifier,sent
                ref_parts = references_str.split(",")
                if len(ref_parts) >= 2:
                    ref_id = ref_parts[1].strip()
                    ref_event_id = generate_sachet_event_id(ref_id)
                    if event.get("is_cancelled"):
                        col.update_one(
                            {"event_id": ref_event_id},
                            {"$set": {"is_cancelled": True, "status": "Cancelled", "updated_at": now_iso}},
                        )

        # Execute bulk operations
        if bulk_ops and hasattr(col, "bulk_write"):
            try:
                col.bulk_write(bulk_ops, ordered=False)
            except PyMongoError as bulk_err:
                logger.warning(f"[SACHET] Bulk write notice: {bulk_err}")

        # Step 5: Rolling 30-day retention cleanup
        removed_expired_count = 0
        try:
            del_result = col.delete_many({"event_time": {"$lt": cutoff_30d_iso}})
            removed_expired_count = del_result.deleted_count if del_result else 0
        except Exception as del_err:
            logger.warning(f"[SACHET] 30-day retention cleanup notice: {del_err}")

        # Step 6: Persist updated ETag
        try:
            sync_state_col.update_one(
                {"pipeline": "NDMA_SACHET"},
                {
                    "$set": {
                        "pipeline": "NDMA_SACHET",
                        "etag": new_etag,
                        "last_modified": new_last_mod,
                        "last_successful_sync_at": now_iso,
                        "updated_at": now_iso,
                    }
                },
                upsert=True,
            )
        except Exception as e:
            logger.debug(f"[SACHET] Could not update sync_state: {e}")

        duration = round(time.time() - start_time, 2)

        # Log formatted summary
        logger.info(f"[SACHET] New: {new_count}")
        logger.info(f"[SACHET] Updated: {updated_count}")
        logger.info(f"[SACHET] Unchanged: {unchanged_count}")
        logger.info(f"[SACHET] Invalid: {invalid_count}")
        logger.info(f"[SACHET] Expired removed: {removed_expired_count}")
        logger.info(f"[SACHET] Sync completed in {duration}s")

        summary = {
            "source": "NDMA_SACHET",
            "status": "success",
            "fetched": total_scraped,
            "within_30_days": within_30d,
            "new": new_count,
            "updated": updated_count,
            "unchanged": unchanged_count,
            "invalid": invalid_count,
            "expired_removed": removed_expired_count,
            "etag_changed": True,
            "duration_seconds": duration,
            "timestamp": now_iso,
        }

        _last_sync_info = {
            "status": "success",
            "last_run_at": now_iso,
            "last_run_duration": duration,
            "last_run_metrics": summary,
        }

        # Auto-refresh map UI if available
        try:
            from tests.generate_temp_map_ui import generate_map
            generate_map(open_browser=False)
            logger.info("[DISHA MAP] Synchronized latest SACHET alerts to map UI.")
        except Exception:
            pass

        return summary

    finally:
        _sync_lock.release()


# ============================================================
# READ / QUERY SERVICES
# ============================================================

def query_sachet_alerts(
    severity: Optional[str] = None,
    urgency: Optional[str] = None,
    certainty: Optional[str] = None,
    disaster_type: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    active_only: bool = False,
    status_filter: Optional[str] = None,
    message_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    last_30_days_only: bool = True,
    target_collection: Optional[Collection] = None,
) -> Dict[str, Any]:
    """
    Queries stored SACHET disaster alerts with multi-criteria filtering and pagination.
    """
    col = target_collection if target_collection is not None else sachet_collection
    query: Dict[str, Any] = {}

    if last_30_days_only:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        query["event_time"] = {"$gte": cutoff}

    if severity:
        query["severity"] = {"$regex": f"^{re.escape(severity.strip())}$", "$options": "i"}

    if urgency:
        query["urgency"] = {"$regex": f"^{re.escape(urgency.strip())}$", "$options": "i"}

    if certainty:
        query["certainty"] = {"$regex": f"^{re.escape(certainty.strip())}$", "$options": "i"}

    if disaster_type:
        query["disaster_type"] = disaster_type.lower().strip()

    if state:
        query["location.state"] = {"$regex": re.escape(state.strip()), "$options": "i"}

    if district:
        query["location.district"] = {"$regex": re.escape(district.strip()), "$options": "i"}

    if active_only:
        now_iso = datetime.now(timezone.utc).isoformat()
        query["$and"] = [
            {"is_cancelled": {"$ne": True}},
            {
                "$or": [
                    {"expires_at": {"$gte": now_iso}},
                    {"expires_at": None},
                ]
            },
        ]

    if status_filter:
        query["status"] = {"$regex": f"^{re.escape(status_filter.strip())}$", "$options": "i"}

    if message_type:
        query["message_type"] = {"$regex": f"^{re.escape(message_type.strip())}$", "$options": "i"}

    if start_date or end_date:
        time_q = query.get("event_time", {})
        if not isinstance(time_q, dict):
            time_q = {"$gte": time_q}
        if start_date:
            time_q["$gte"] = start_date
        if end_date:
            time_q["$lte"] = end_date
        query["event_time"] = time_q

    lim = max(1, min(500, int(limit)))
    skp = max(0, int(skip))

    try:
        cursor = col.find(query, {"_id": 0}).sort("event_time", -1).skip(skp).limit(lim)
        alerts = list(cursor)
        total = col.count_documents(query)
    except Exception as e:
        logger.error(f"[SACHET] Database query error: {e}")
        return {"total": 0, "count": 0, "limit": lim, "skip": skp, "alerts": []}

    return {
        "total": total,
        "count": len(alerts),
        "limit": lim,
        "skip": skp,
        "alerts": alerts,
    }


def get_latest_sachet_alerts(
    limit: int = 10,
    severity: Optional[str] = None,
    state: Optional[str] = None,
    active_only: bool = True,
    target_collection: Optional[Collection] = None,
) -> Dict[str, Any]:
    """Retrieves the most recent alerts ordered by event time descending."""
    return query_sachet_alerts(
        limit=limit,
        severity=severity,
        state=state,
        active_only=active_only,
        target_collection=target_collection,
    )


def get_sachet_alert_by_id(event_id: str, target_collection: Optional[Collection] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single SACHET alert by its event_id or alert_id."""
    col = target_collection if target_collection is not None else sachet_collection
    try:
        doc = col.find_one(
            {"$or": [{"event_id": event_id}, {"alert_id": event_id}, {"guid": event_id}]},
            {"_id": 0},
        )
        return doc
    except Exception as e:
        logger.error(f"[SACHET] Lookup error for {event_id}: {e}")
        return None


def get_sachet_statistics(target_collection: Optional[Collection] = None) -> Dict[str, Any]:
    """Computes aggregated analytics on stored 30-day SACHET alerts."""
    col = target_collection if target_collection is not None else sachet_collection
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        total_30d = col.count_documents({"event_time": {"$gte": cutoff}})
        active_alerts = col.count_documents({
            "event_time": {"$gte": cutoff},
            "is_cancelled": {"$ne": True},
            "$or": [{"expires_at": {"$gte": now_iso}}, {"expires_at": None}],
        })
        cancelled_alerts = col.count_documents({"event_time": {"$gte": cutoff}, "is_cancelled": True})

        # Aggregations
        pipeline_sev = [
            {"$match": {"event_time": {"$gte": cutoff}}},
            {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
        ]
        sev_counts = {item["_id"] or "Unknown": item["count"] for item in col.aggregate(pipeline_sev)}

        pipeline_type = [
            {"$match": {"event_time": {"$gte": cutoff}}},
            {"$group": {"_id": "$disaster_type", "count": {"$sum": 1}}},
        ]
        type_counts = {item["_id"] or "other": item["count"] for item in col.aggregate(pipeline_type)}

        pipeline_states = [
            {"$match": {"event_time": {"$gte": cutoff}, "location.state": {"$ne": None}}},
            {"$group": {"_id": "$location.state", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        state_counts = [{"state": item["_id"], "count": item["count"]} for item in col.aggregate(pipeline_states)]

        return {
            "source": "NDMA_SACHET",
            "total_alerts_30d": total_30d,
            "active_alerts_count": active_alerts,
            "cancelled_alerts_count": cancelled_alerts,
            "severity_breakdown": sev_counts,
            "disaster_type_breakdown": type_counts,
            "top_affected_states": state_counts,
            "last_sync": get_last_sync_metrics(),
        }

    except Exception as e:
        logger.error(f"[SACHET] Stats computation error: {e}")
        return {
            "source": "NDMA_SACHET",
            "total_alerts_30d": 0,
            "active_alerts_count": 0,
            "cancelled_alerts_count": 0,
            "severity_breakdown": {},
            "disaster_type_breakdown": {},
            "top_affected_states": [],
            "last_sync": get_last_sync_metrics(),
        }
