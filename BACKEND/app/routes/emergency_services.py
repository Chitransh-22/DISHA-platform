"""
DISHA Platform - Nearby Emergency Services API Routes
Disaster Intelligence and Situational Hazard Awareness Platform

Exposes clean endpoints for on-demand nearby emergency services retrieval
based on incident coordinates (Incident -> Emergency Services).
"""

import sys
from pathlib import Path
from typing import Optional

# Ensure backend root is always in sys.path
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi import APIRouter, Query, HTTPException, status
from app.services.emergency_service import get_nearby_emergency_services

router = APIRouter(
    tags=["Emergency Services"],
)


@router.get(
    "/api/emergency-services",
    summary="Retrieve nearby emergency services for given incident coordinates",
)
@router.get(
    "/api/emergency-services/nearby",
    summary="Retrieve nearby emergency services for given incident coordinates (subroute alias)",
)
@router.get(
    "/api/nearby-services",
    summary="Retrieve nearby emergency services for given incident coordinates (alias)",
)
@router.get(
    "/api/nearby-services/nearby",
    summary="Retrieve nearby emergency services for given incident coordinates (alias)",
)
async def get_nearby_services_endpoint(
    lat: Optional[float] = Query(
        None,
        ge=-90.0,
        le=90.0,
        description="Incident latitude (e.g. 23.0225)",
    ),
    latitude: Optional[float] = Query(
        None,
        ge=-90.0,
        le=90.0,
        description="Incident latitude alias",
    ),
    lng: Optional[float] = Query(
        None,
        ge=-180.0,
        le=180.0,
        description="Incident longitude (e.g. 72.5714)",
    ),
    longitude: Optional[float] = Query(
        None,
        ge=-180.0,
        le=180.0,
        description="Incident longitude alias",
    ),
    lon: Optional[float] = Query(
        None,
        ge=-180.0,
        le=180.0,
        description="Incident longitude alias",
    ),
    radius: Optional[int] = Query(
        None,
        ge=500,
        le=100000,
        description="Search radius in meters around incident (default: 5000m / 5km)",
    ),
    radius_km: Optional[float] = Query(
        None,
        ge=0.5,
        le=100.0,
        description="Search radius in kilometers around incident (e.g. 5.0)",
    ),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=100,
        description="Optional maximum facilities to return per category (default: None, returns all in radius)",
    ),
    auto_expand: bool = Query(
        True,
        description="Automatically expand radius to 15km/25km if 0 services found in initial radius (default: True)",
    ),
):
    """
    Finds real-world emergency services (hospitals/medical, police stations, fire stations)
    nearest to the selected incident's latitude and longitude.

    - Uses incident coordinates as the origin.
    - Calculates exact Haversine distances (Incident -> Emergency Service).
    - Sorts each category from nearest to farthest.
    - Provides directions navigation URLs and phone contact buttons where available.
    """
    # Resolve coordinate parameters
    final_lat = lat if lat is not None else latitude
    final_lng = lng if lng is not None else (longitude if longitude is not None else lon)

    if final_lat is None or final_lng is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required coordinate parameters: please provide 'lat' (or 'latitude') and 'lng' (or 'longitude').",
        )

    # Resolve radius (default 5000 meters)
    if radius_km is not None and radius_km > 0:
        actual_radius_m = int(radius_km * 1000)
    elif radius is not None and radius > 0:
        actual_radius_m = radius
    else:
        actual_radius_m = 5000

    try:
        data = get_nearby_emergency_services(
            lat=final_lat,
            lng=final_lng,
            radius_m=actual_radius_m,
            limit=limit,
            auto_expand=auto_expand,
        )
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch nearby emergency services: {str(e)}",
        )
