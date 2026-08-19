"""
DISHA Platform - NDMA SACHET Disaster Alert API Routes
Provides on-demand triggering for the NDMA SACHET CAP pipeline and rich read endpoints
for querying stored government alerts with multi-criteria filtering.
"""

import sys
from pathlib import Path
from typing import Optional

# Ensure backend root in sys.path
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")
load_dotenv()

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.services.sachet_service import (
    query_sachet_alerts,
    get_latest_sachet_alerts,
    get_sachet_alert_by_id,
    get_sachet_statistics,
    sync_sachet_pipeline,
)

router = APIRouter(
    prefix="/api/sachet",
    tags=["NDMA SACHET Alerts"],
)


@router.post("/fetch", summary="Trigger NDMA SACHET CAP RSS fetching on-demand")
@router.post("/sync", summary="Trigger NDMA SACHET CAP pipeline synchronization")
async def fetch_sachet_route(
    background_tasks: BackgroundTasks,
    background: bool = Query(
        True,
        description="True to run asynchronously in background; False to wait for synchronous summary response",
    ),
    force_refresh: bool = Query(
        False,
        description="True to bypass ETag/304 check and force full re-sync",
    ),
):
    """
    Trigger the official NDMA SACHET CAP RSS alert fetching, normalization, and deduplication pipeline.
    This pipeline executes ONLY when this route is explicitly called.
    NO background schedulers or startup execution.
    """
    if background:
        background_tasks.add_task(sync_sachet_pipeline, force_refresh=force_refresh)
        return {
            "source": "NDMA_SACHET",
            "status": "started",
            "message": "NDMA SACHET CAP RSS alert fetching started in background",
        }
    else:
        summary = sync_sachet_pipeline(force_refresh=force_refresh)
        return summary


@router.get("", summary="Retrieve stored SACHET disaster alerts with multi-criteria filters")
async def list_sachet_alerts(
    severity: Optional[str] = Query(None, description="Severity filter: Extreme, Severe, Moderate, Minor, or Unknown"),
    urgency: Optional[str] = Query(None, description="Urgency filter: Immediate, Expected, Future, Past, or Unknown"),
    certainty: Optional[str] = Query(None, description="Certainty filter: Observed, Likely, Possible, Unlikely, or Unknown"),
    disaster_type: Optional[str] = Query(None, description="Disaster category (e.g. flood, heavy_rain, cyclone, landslide)"),
    state: Optional[str] = Query(None, description="Filter by Indian State / UT"),
    district: Optional[str] = Query(None, description="Filter by District name"),
    active_only: bool = Query(False, description="True to return only currently unexpired and non-cancelled alerts"),
    status_filter: Optional[str] = Query(None, alias="status", description="CAP Status (e.g. Actual, Exercise, Test)"),
    message_type: Optional[str] = Query(None, description="CAP msgType (e.g. Alert, Update, Cancel)"),
    start_date: Optional[str] = Query(None, description="Start datetime ISO 8601 (e.g. '2026-08-01T00:00:00')"),
    end_date: Optional[str] = Query(None, description="End datetime ISO 8601 (e.g. '2026-08-19T23:59:59')"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    last_30_days_only: bool = Query(True, description="Restrict query strictly to rolling 30-day window"),
):
    """
    Retrieve stored disaster alerts from NDMA SACHET.
    This READ route does NOT trigger scraping.
    """
    result = query_sachet_alerts(
        severity=severity,
        urgency=urgency,
        certainty=certainty,
        disaster_type=disaster_type,
        state=state,
        district=district,
        active_only=active_only,
        status_filter=status_filter,
        message_type=message_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        skip=skip,
        last_30_days_only=last_30_days_only,
    )
    return result


@router.get("/latest", summary="Retrieve most recent NDMA SACHET disaster alerts")
async def latest_sachet_alerts(
    limit: int = Query(10, ge=1, le=100, description="Max recent records to return"),
    severity: Optional[str] = Query(None, description="Filter by severity threshold"),
    state: Optional[str] = Query(None, description="Filter by Indian State"),
    active_only: bool = Query(True, description="Filter to only active unexpired alerts"),
):
    """
    Retrieve the most recent SACHET alerts ordered by event time descending.
    Ideal for real-time map feeds, dashboard ribbons, and emergency banners.
    """
    result = get_latest_sachet_alerts(
        limit=limit,
        severity=severity,
        state=state,
        active_only=active_only,
    )
    return result


@router.get("/stats", summary="Get aggregated 30-day SACHET alert statistics")
async def sachet_stats():
    """
    Get aggregated analytics on 30-day NDMA SACHET alerts:
    Active count, severity breakdown, hazard distribution, state breakdown, and latest sync status.
    """
    return get_sachet_statistics()


@router.get("/{event_id}", summary="Retrieve a single SACHET alert by event ID or alert ID")
async def get_sachet_detail(event_id: str):
    """
    Retrieve full details of a SACHET alert by its deterministic event_id (e.g. `sachet_IN-1787111448985010_10`)
    or its raw alert_id/guid.
    """
    alert = get_sachet_alert_by_id(event_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SACHET alert with ID '{event_id}' not found.",
        )
    return {
        "status": "success",
        "alert": alert,
    }
