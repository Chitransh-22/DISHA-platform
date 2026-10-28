"""
DISHA Platform - Unified Disaster Events API Routes
Disaster Intelligence and Situational Hazard Awareness Platform

Exposes clean endpoints for map visualization, geospatial filtering,
and unified hazard feeds from NCS RISEQ, NDMA SACHET, verified news intelligence,
and citizen incident reports.
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
    summary="Retrieve unified disaster and hazard events for map visualization and analysis",
)
async def list_unified_events(
    time_range: Optional[str] = Query(
        None,
        description="Time filter ('24h', '7d', '15d', '30d', 'all', 'custom'). Default: '24h'",
    ),
    range: Optional[str] = Query(
        None,
        description="Alternative query alias for time range",
    ),
    time_window: Optional[str] = Query(
        None,
        description="Alias for time range ('24h', '7d', '15d', '30d', 'all')",
    ),
    days: Optional[int] = Query(
        None,
        description="Alternative days integer filter (1, 7, 15, 30)",
    ),
    start_date: Optional[str] = Query(
        None,
        description="Custom range start date/timestamp (ISO 8601 or YYYY-MM-DD)",
    ),
    end_date: Optional[str] = Query(
        None,
        description="Custom range end date/timestamp (ISO 8601 or YYYY-MM-DD)",
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
        description="Filter by source ('all', 'earthquakes', 'sachet', 'news', 'citizen')",
    ),
    state: Optional[str] = Query(
        None,
        description="Filter by Indian State / Region",
    ),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=5000,
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
    (NCS RISEQ Earthquakes, NDMA SACHET Alerts, Verified Disaster News, Citizen Incident Reports).
    Preserves zero-event-loss invariant: Total (T) = Mapped (M) + Unmapped (U).
    """
    try:
        if days is not None:
            effective_range = f"{days}d"
        elif time_window is not None:
            effective_range = time_window
        else:
            effective_range = time_range or range or "24h"

        data = get_unified_events(
            category=category,
            severity=severity,
            status=status_filter,
            source=source,
            state=state,
            limit=limit,
            skip=skip,
            time_range=effective_range,
            start_date=start_date,
            end_date=end_date,
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
