"""
DISHA Platform - Earthquake Data Pipeline Service
Manages synchronization, deduplication, rolling 30-day retention, database upserts,
and querying for NCS RISEQ earthquakes.
"""

import os
import sys
import logging
import threading
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

from dotenv import load_dotenv

# Ensure .env is loaded and backend directory in sys.path for direct CLI execution
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

load_dotenv(_backend_dir / ".env")
load_dotenv()

from pymongo.collection import Collection
from pymongo.errors import PyMongoError, DuplicateKeyError

from app.database.mongodb import db
from app.sources.riseq import scrape_riseq_earthquakes

logger = logging.getLogger("disha.services.earthquake")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

earthquakes_collection: Collection = db["earthquakes"]
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


def sync_earthquakes_pipeline(
    days: int = 30,
    timeout: int = 20,
    max_retries: int = 3,
    force_cleanup: bool = True,
    reference_now: Optional[datetime] = None,
    target_collection: Optional[Collection] = None,
) -> Dict[str, Any]:
    """
    Executes a complete synchronization of the NCS RISEQ earthquake pipeline:
    1. Scrapes rolling 30-day earthquake events from NCS RISEQ.
    2. Identifies new, updated, and unchanged events using deterministic event_id.
    3. Performs atomic MongoDB upserts with first_seen_at/last_seen_at tracking.
    4. Automatically purges records older than 30 days.
    5. Records execution metrics for system observability.
    """
    global _last_sync_info

    # Non-blocking lock check: if already running, skip safely
    if not _sync_lock.acquire(blocking=False):
        logger.warning("[RISEQ] Synchronization already in progress. Skipping concurrent request.")
        return {
            "status": "skipped",
            "message": "Another synchronization is currently running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    start_time = time.time()
    now_utc = reference_now if reference_now is not None else datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    now_iso = now_utc.isoformat()

    col = target_collection if target_collection is not None else earthquakes_collection

    logger.info("[RISEQ] Fetching earthquake data")

    try:
        # Step 1: Scrape RISEQ portal
        scrape_res = scrape_riseq_earthquakes(
            timeout=timeout,
            max_retries=max_retries,
            days=days,
            reference_now=now_utc,
        )

        if scrape_res.get("status") != "success":
            err_msg = scrape_res.get("error", "Unknown scraping error")
            duration = round(time.time() - start_time, 2)
            logger.error(f"[RISEQ] Fetch failed: {err_msg}")
            
            summary = {
                "status": "error",
                "source": "NCS_RISEQ",
                "error": err_msg,
                "scraped_count": 0,
                "within_30_days_count": 0,
                "new_count": 0,
                "updated_count": 0,
                "unchanged_count": 0,
                "invalid_count": 0,
                "removed_expired_count": 0,
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
        total_scraped = scrape_res.get("count", len(events))

        logger.info(f"[RISEQ] Found: {total_scraped} events")
        logger.info(f"[RISEQ] Last 30 days: {len(events)} events")

        # Step 2: Query existing active records for fast in-memory comparison
        cutoff_30d = now_utc - timedelta(days=30)
        cutoff_30d_iso = cutoff_30d.isoformat()

        existing_cursor = col.find(
            {"origin_time": {"$gte": cutoff_30d_iso}},
            {
                "_id": 0,
                "event_id": 1,
                "magnitude": 1,
                "depth_km": 1,
                "status": 1,
                "location": 1,
                "region": 1,
                "latitude": 1,
                "longitude": 1,
                "felt_report_url": 1,
            },
        )
        existing_map: Dict[str, Dict[str, Any]] = {doc["event_id"]: doc for doc in existing_cursor if "event_id" in doc}

        new_count = 0
        updated_count = 0
        unchanged_count = 0
        invalid_count = 0

        bulk_ops = []

        # Step 3: Compare and upsert records
        for event in events:
            ev_id = event.get("event_id")
            if not ev_id:
                invalid_count += 1
                continue

            if ev_id in existing_map:
                existing_doc = existing_map[ev_id]

                # Check if NCS modified any field (e.g. magnitude, depth, status, location)
                fields_changed = (
                    abs(existing_doc.get("magnitude", 0.0) - event["magnitude"]) > 1e-4
                    or abs(existing_doc.get("depth_km", 0.0) - event["depth_km"]) > 1e-4
                    or existing_doc.get("status") != event["status"]
                    or existing_doc.get("location") != event["location"]
                    or existing_doc.get("region") != event["region"]
                    or abs(existing_doc.get("latitude", 0.0) - event["latitude"]) > 1e-4
                    or abs(existing_doc.get("longitude", 0.0) - event["longitude"]) > 1e-4
                    or existing_doc.get("felt_report_url") != event.get("felt_report_url")
                )

                if fields_changed:
                    # Update modified values and touch updated_at & last_seen_at
                    update_data = {
                        "magnitude": event["magnitude"],
                        "depth_km": event["depth_km"],
                        "status": event["status"],
                        "location": event["location"],
                        "region": event["region"],
                        "latitude": event["latitude"],
                        "longitude": event["longitude"],
                        "relevance": event["relevance"],
                        "relevance_details": event["relevance_details"],
                        "felt_report_url": event.get("felt_report_url"),
                        "felt_token": event.get("felt_token"),
                        "metadata": event.get("metadata", {}),
                        "updated_at": now_iso,
                        "last_seen_at": now_iso,
                    }
                    if hasattr(col, "bulk_write"):
                        from pymongo import UpdateOne
                        bulk_ops.append(UpdateOne({"event_id": ev_id}, {"$set": update_data}))
                    else:
                        col.update_one({"event_id": ev_id}, {"$set": update_data})
                    updated_count += 1
                else:
                    # Data is unchanged; refresh last_seen_at
                    if hasattr(col, "bulk_write"):
                        from pymongo import UpdateOne
                        bulk_ops.append(UpdateOne({"event_id": ev_id}, {"$set": {"last_seen_at": now_iso}}))
                    else:
                        col.update_one({"event_id": ev_id}, {"$set": {"last_seen_at": now_iso}})
                    unchanged_count += 1

            else:
                # Brand new event: atomic upsert with first_seen_at preservation
                set_fields = {k: v for k, v in event.items() if k not in ("first_seen_at", "created_at")}
                set_fields["last_seen_at"] = now_iso
                set_fields["updated_at"] = now_iso

                if hasattr(col, "bulk_write"):
                    from pymongo import UpdateOne
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

        # Execute high-speed batch write if operations pending
        if bulk_ops and hasattr(col, "bulk_write"):
            try:
                col.bulk_write(bulk_ops, ordered=False)
            except PyMongoError as b_err:
                logger.error(f"[RISEQ] Bulk write error: {b_err}")

        # Step 4: 30-Day Cleanup (remove events older than 30 days)
        removed_expired_count = 0
        if force_cleanup:
            try:
                del_result = col.delete_many({"origin_time": {"$lt": cutoff_30d_iso}})
                removed_expired_count = del_result.deleted_count
            except PyMongoError as err:
                logger.error(f"[RISEQ] Error during 30-day cleanup: {err}")

        duration = round(time.time() - start_time, 2)

        # Log formatted summary as specified in guidelines
        logger.info(f"[RISEQ] New: {new_count}")
        logger.info(f"[RISEQ] Updated: {updated_count}")
        logger.info(f"[RISEQ] Unchanged: {unchanged_count}")
        logger.info(f"[RISEQ] Removed (>30 days): {removed_expired_count}")
        logger.info(f"[RISEQ] Completed successfully in {duration}s")

        summary = {
            "status": "success",
            "source": "NCS_RISEQ",
            "scraped_count": total_scraped,
            "within_30_days_count": len(events),
            "new_count": new_count,
            "updated_count": updated_count,
            "unchanged_count": unchanged_count,
            "invalid_count": invalid_count,
            "removed_expired_count": removed_expired_count,
            "duration_seconds": duration,
            "timestamp": now_iso,
        }

        _last_sync_info = {
            "status": "success",
            "last_run_at": now_iso,
            "last_run_duration": duration,
            "last_run_metrics": summary,
        }

        # Optionally record execution log in database
        try:
            pipeline_runs_collection.insert_one({
                "pipeline": "NCS_RISEQ_EARTHQUAKES",
                "ran_at": now_iso,
                "duration_seconds": duration,
                "metrics": summary,
            })
        except Exception:
            pass

        return summary

    finally:
        _sync_lock.release()


def query_earthquakes(
    min_magnitude: Optional[float] = None,
    max_magnitude: Optional[float] = None,
    relevance: Optional[str] = None,
    region: Optional[str] = None,
    state: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
    limit: int = 50,
    skip: int = 0,
    last_30_days_only: bool = True,
    col: Optional[Collection] = None,
) -> Dict[str, Any]:
    """
    Queries earthquakes from MongoDB with comprehensive filtering capabilities.
    """
    target_col = col if col is not None else earthquakes_collection
    query: Dict[str, Any] = {}

    # Magnitude filtering
    if min_magnitude is not None or max_magnitude is not None:
        mag_filter: Dict[str, Any] = {}
        if min_magnitude is not None:
            mag_filter["$gte"] = float(min_magnitude)
        if max_magnitude is not None:
            mag_filter["$lte"] = float(max_magnitude)
        query["magnitude"] = mag_filter

    # Relevance filtering (INDIA, INDIA_BORDER, REGIONAL, OTHER)
    if relevance:
        query["relevance"] = relevance.strip().upper()

    # Region / State text search
    if region:
        query["region"] = {"$regex": region.strip(), "$options": "i"}
    if state:
        query["$or"] = [
            {"region": {"$regex": state.strip(), "$options": "i"}},
            {"location": {"$regex": state.strip(), "$options": "i"}},
            {"relevance_details.detected_states": {"$regex": state.strip(), "$options": "i"}},
        ]

    # Status filtering (Reviewed, Auto, Unscruitnized)
    if status:
        query["status"] = {"$regex": f"^{status.strip()}", "$options": "i"}

    # Date range filtering
    time_filter: Dict[str, Any] = {}
    if start_date:
        time_filter["$gte"] = start_date.strip()
    elif last_30_days_only:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        time_filter["$gte"] = cutoff

    if end_date:
        time_filter["$lte"] = end_date.strip()

    if time_filter:
        query["origin_time"] = time_filter

    # Geographic bounding box filtering
    if any(coord is not None for coord in (min_lat, max_lat, min_lon, max_lon)):
        lat_filter: Dict[str, Any] = {}
        if min_lat is not None:
            lat_filter["$gte"] = float(min_lat)
        if max_lat is not None:
            lat_filter["$lte"] = float(max_lat)
        if lat_filter:
            query["latitude"] = lat_filter

        lon_filter: Dict[str, Any] = {}
        if min_lon is not None:
            lon_filter["$gte"] = float(min_lon)
        if max_lon is not None:
            lon_filter["$lte"] = float(max_lon)
        if lon_filter:
            query["longitude"] = lon_filter

    total_count = target_col.count_documents(query)
    lim = max(1, min(limit, 500))
    skp = max(0, skip)

    cursor = target_col.find(query, {"_id": 0}).sort("origin_time", -1).skip(skp).limit(lim)
    records = list(cursor)

    return {
        "status": "success",
        "source": "NCS_RISEQ",
        "source_url": "https://riseq.seismo.gov.in/riseq/earthquake",
        "total": total_count,
        "count": len(records),
        "last_30_days": last_30_days_only,
        "filters_applied": {
            "min_magnitude": min_magnitude,
            "max_magnitude": max_magnitude,
            "relevance": relevance,
            "region": region,
            "state": state,
            "status": status,
            "start_date": start_date,
            "end_date": end_date,
        },
        "earthquakes": records,
    }


def get_latest_earthquakes(
    limit: int = 10,
    relevance: Optional[str] = None,
    min_magnitude: Optional[float] = None,
    col: Optional[Collection] = None,
) -> Dict[str, Any]:
    """Retrieves the latest earthquake records sorted by origin_time descending."""
    return query_earthquakes(
        limit=limit,
        skip=0,
        relevance=relevance,
        min_magnitude=min_magnitude,
        last_30_days_only=True,
        col=col,
    )


def get_earthquake_by_id(event_id: str, col: Optional[Collection] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single earthquake record by its deterministic event_id."""
    target_col = col if col is not None else earthquakes_collection
    return target_col.find_one({"event_id": event_id.strip()}, {"_id": 0})


def get_earthquake_statistics(col: Optional[Collection] = None) -> Dict[str, Any]:
    """
    Computes real-time statistics for the rolling 30-day earthquake dataset.
    """
    target_col = col if col is not None else earthquakes_collection
    now_utc = datetime.now(timezone.utc)
    cutoff_30d = (now_utc - timedelta(days=30)).isoformat()
    base_query = {"origin_time": {"$gte": cutoff_30d}}

    total_30d = target_col.count_documents(base_query)
    india_count = target_col.count_documents({**base_query, "relevance": "INDIA"})
    border_count = target_col.count_documents({**base_query, "relevance": "INDIA_BORDER"})
    regional_count = target_col.count_documents({**base_query, "relevance": "REGIONAL"})
    other_count = target_col.count_documents({**base_query, "relevance": "OTHER"})

    # Magnitude brackets
    mag_under_3 = target_col.count_documents({**base_query, "magnitude": {"$lt": 3.0}})
    mag_3_to_3_9 = target_col.count_documents({**base_query, "magnitude": {"$gte": 3.0, "$lt": 4.0}})
    mag_4_to_4_9 = target_col.count_documents({**base_query, "magnitude": {"$gte": 4.0, "$lt": 5.0}})
    mag_5_to_5_9 = target_col.count_documents({**base_query, "magnitude": {"$gte": 5.0, "$lt": 6.0}})
    mag_6_plus = target_col.count_documents({**base_query, "magnitude": {"$gte": 6.0}})

    # Most recent event
    latest_doc = target_col.find_one(base_query, {"_id": 0, "origin_time": 1, "magnitude": 1, "region": 1, "location": 1}, sort=[("origin_time", -1)])

    # Maximum magnitude in last 30 days
    max_mag_doc = target_col.find_one(base_query, {"_id": 0, "magnitude": 1, "region": 1, "origin_time": 1}, sort=[("magnitude", -1)])

    return {
        "status": "success",
        "source": "NCS_RISEQ",
        "time_window": "30_days",
        "total_events_30d": total_30d,
        "by_relevance": {
            "india": india_count,
            "india_border": border_count,
            "regional": regional_count,
            "other": other_count,
        },
        "by_magnitude": {
            "under_3": mag_under_3,
            "mag_3_0_to_3_9": mag_3_to_3_9,
            "mag_4_0_to_4_9": mag_4_to_4_9,
            "mag_5_0_to_5_9": mag_5_to_5_9,
            "mag_6_0_plus": mag_6_plus,
        },
        "latest_event": latest_doc,
        "max_magnitude_event": max_mag_doc,
        "sync_status": get_last_sync_metrics(),
        "generated_at": now_utc.isoformat(),
    }


if __name__ == "__main__":
    sync_earthquakes_pipeline()
