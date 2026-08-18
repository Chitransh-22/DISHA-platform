import sys
from pathlib import Path
from typing import Optional

# Ensure backend root is always in sys.path regardless of execution directory
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")
load_dotenv()

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.services.earthquake_service import (
    query_earthquakes,
    get_latest_earthquakes,
    get_earthquake_by_id,
    get_earthquake_statistics,
    sync_earthquakes_pipeline,
)

router = APIRouter(
    prefix="/api/earthquakes",
    tags=["Earthquakes"],
)


@router.get("", summary="Retrieve earthquakes with multi-criteria filters")
async def list_earthquakes(
    min_magnitude: Optional[float] = Query(None, description="Minimum magnitude filter (e.g. 3.0)"),
    max_magnitude: Optional[float] = Query(None, description="Maximum magnitude filter (e.g. 7.0)"),
    relevance: Optional[str] = Query(
        None,
        description="Relevance classification: INDIA, INDIA_BORDER, REGIONAL, or OTHER",
    ),
    region: Optional[str] = Query(None, description="Text filter for region (e.g. 'Himachal', 'Hindu Kush')"),
    state: Optional[str] = Query(None, description="Filter for Indian State / UT"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="NCS event status (e.g. 'Reviewed', 'Auto', 'Unscruitnized')",
    ),
    start_date: Optional[str] = Query(None, description="Start datetime ISO 8601 (e.g. '2026-08-01T00:00:00')"),
    end_date: Optional[str] = Query(None, description="End datetime ISO 8601 (e.g. '2026-08-19T23:59:59')"),
    min_lat: Optional[float] = Query(None, description="Bounding box minimum latitude"),
    max_lat: Optional[float] = Query(None, description="Bounding box maximum latitude"),
    min_lon: Optional[float] = Query(None, description="Bounding box minimum longitude"),
    max_lon: Optional[float] = Query(None, description="Bounding box maximum longitude"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    last_30_days_only: bool = Query(True, description="Restrict queries strictly to rolling 30-day window"),
):
    """
    Retrieve real-time and 30-day rolling earthquake events scraped from NCS RISEQ.
    Supports filtering by magnitude, Indian relevance, geographic bounding box, state, and date range.
    """
    result = query_earthquakes(
        min_magnitude=min_magnitude,
        max_magnitude=max_magnitude,
        relevance=relevance,
        region=region,
        state=state,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        limit=limit,
        skip=skip,
        last_30_days_only=last_30_days_only,
    )
    return result


@router.get("/latest", summary="Retrieve most recent earthquakes")
async def latest_earthquakes(
    limit: int = Query(10, ge=1, le=100, description="Max recent records to return"),
    relevance: Optional[str] = Query(
        None,
        description="Filter by relevance: INDIA, INDIA_BORDER, REGIONAL, or OTHER",
    ),
    min_magnitude: Optional[float] = Query(None, description="Minimum magnitude threshold"),
):
    """
    Retrieve the most recent earthquakes ordered by origin time descending.
    Ideal for real-time map feeds and dashboard alert banners.
    """
    result = get_latest_earthquakes(
        limit=limit,
        relevance=relevance,
        min_magnitude=min_magnitude,
    )
    return result


@router.get("/stats", summary="Get rolling 30-day earthquake statistics")
async def earthquake_stats():
    """
    Get aggregated analytics on 30-day earthquakes:
    Total events, relevance breakdown, magnitude distribution, and latest sync status.
    """
    return get_earthquake_statistics()


@router.post("/fetch", summary="Trigger real-time NCS RISEQ earthquake fetching in background")
@router.post("/sync", summary="Trigger manual NCS RISEQ pipeline synchronization")
async def fetch_earthquakes_route(
    background_tasks: BackgroundTasks,
    background: bool = Query(
        True,
        description="True to run asynchronously in background; False to wait for synchronous response",
    ),
):
    """
    Trigger the official NCS RISEQ earthquake fetching, normalization, and deduplication pipeline.
    Identical in behavior and convention to POST /api/news/fetch.
    """
    if background:
        background_tasks.add_task(sync_earthquakes_pipeline)
        return {
            "status": "started",
            "message": "NCS RISEQ earthquake fetching started in background",
        }
    else:
        summary = sync_earthquakes_pipeline()
        return summary


@router.get("/{event_id}", summary="Retrieve a single earthquake by event ID")
async def get_earthquake_detail(event_id: str):
    """
    Retrieve full details of an earthquake by its deterministic event_id.
    Example: `ncs_20260818T195107Z_36.494_70.664`
    """
    event = get_earthquake_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Earthquake event with ID '{event_id}' not found.",
        )
    return {
        "status": "success",
        "earthquake": event,
    }
