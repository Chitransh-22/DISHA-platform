"""
DISHA Platform - Unified Disaster Events API Routes
Disaster Intelligence and Situational Hazard Awareness Platform

Exposes clean endpoints for map visualization, geospatial filtering,
and unified hazard feeds from NCS RISEQ, NDMA SACHET, and verified news intelligence.
"""

import sys
from pathlib import Path
from typing import Optional

# Ensure backend root is in sys.path
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi import APIRouter, Query, HTTPException, status
from app.services.events_service import get_unified_events, get_event_by_id

router = APIRouter(
    prefix="/api/events",
    tags=["Events"],
)


@router.get(
    "",
    summary="Retrieve unified disaster and hazard events for map visualization",
)
async def list_unified_events(
    time_range: Optional[str] = Query(
        "24h",
        alias="range",
        description="Time filter ('24h', '7d', '15d', '30d', 'all'). Default: '24h'",
    ),
    days: Optional[int] = Query(
        None,
        description="Alternative days integer filter (1, 7, 15, 30)",
    ),
    category: Optional[str] = Query(
        None,
        description="Filter by disaster category (e.g. 'Earthquake', 'Flood', 'Heavy Rain', 'Landslide', 'Lightning', 'Fire')",
    ),
    severity: Optional[str] = Query(
        None,
        description="Filter by severity tier ('Critical', 'Severe', 'Moderate', 'Low')",
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status ('Active', 'Reviewed', 'Actual', 'Monitoring')",
    ),
    source: Optional[str] = Query(
        None,
        description="Filter by source ('all', 'earthquakes', 'sachet', 'news')",
    ),
    state: Optional[str] = Query(
        None,
        description="Filter by Indian State / Region",
    ),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=2000,
        description="Maximum events to return",
    ),
    skip: int = Query(
        0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
):
    """
    Returns 100% real verified disaster events directly from MongoDB
    (NCS RISEQ Earthquakes, NDMA SACHET Alerts, and Verified Disaster News)
    with exact coordinates for Leaflet/GIS map plotting.
    Time filtered at database query level (default: last 24 hours).
    """
    try:
        effective_range = f"{days}d" if days is not None else (time_range or "24h")
        data = get_unified_events(
            category=category,
            severity=severity,
            status=status_filter,
            source=source,
            state=state,
            limit=limit,
            skip=skip,
            time_range=effective_range,
        )
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch disaster events: {str(e)}",
        )


@router.get(
    "/{event_id}",
    summary="Retrieve single disaster event by deterministic ID",
)
async def get_event_detail(event_id: str):
    """
    Retrieve full details of a specific disaster event by its deterministic event_id.
    """
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID '{event_id}' not found.",
        )
    return {
        "status": "success",
        "event": event,
    }
