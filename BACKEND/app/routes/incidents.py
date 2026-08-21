"""
DISHA Platform - Incident Reporting Routes
Disaster Intelligence and Situational Hazard Awareness Platform

Provides endpoints for authenticated citizens to report disaster incidents,
attach evidence photos/location, and view reported incident statuses.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import get_current_user, get_optional_user
from app.models.incident_report import IncidentReportCreate
from app.repositories.incident_repository import IncidentRepository

logger = logging.getLogger("disha.routes.incidents")

router = APIRouter(
    prefix="/api/incidents",
    tags=["Incidents"],
)

reports_alias_router = APIRouter(
    prefix="/api/reports",
    tags=["Incidents"],
)


def _process_location(loc_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures coordinates array [lng, lat] is properly formed for GeoJSON queries."""
    result = dict(loc_dict)
    lat = result.get("lat") or result.get("latitude")
    lng = result.get("lng") or result.get("longitude")

    if lat is not None and lng is not None:
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            result["lat"] = lat_f
            result["lng"] = lng_f
            result["coordinates"] = [lng_f, lat_f]  # GeoJSON [longitude, latitude]
        except (ValueError, TypeError):
            pass
    return result


def get_incident_repo() -> IncidentRepository:
    return IncidentRepository()


@router.post(
    "/report",
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new citizen disaster incident report",
    name="submit_incident_report",
)
@reports_alias_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new citizen disaster incident report (alias)",
    name="submit_incident_report_alias",
)
@reports_alias_router.post(
    "/report",
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new citizen disaster incident report (alias 2)",
    name="submit_incident_report_alias_2",
)
async def submit_incident_report(
    payload: IncidentReportCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    repo: IncidentRepository = Depends(get_incident_repo),
):
    """
    Submits a disaster incident report with location, category, description, and photos.
    Requires authenticated user session.
    """
    try:
        user_id = str(current_user["id"])
        user_name = current_user.get("name") or current_user.get("username") or "Verified Citizen"
        user_email = current_user.get("email") or ""

        loc_data = _process_location(payload.location.model_dump(exclude_none=True))

        report_data = {
            "user_id": user_id,
            "user_name": user_name,
            "user_email": user_email,
            "event_type": payload.event_type.strip().lower(),
            "description": payload.description.strip(),
            "location": loc_data,
            "images": payload.images or [],
            "status": "submitted",
        }

        created_report = await repo.create_report(report_data)

        logger.info(
            "Incident report %s created by user %s (%s) for event_type: %s",
            created_report.get("report_id"),
            user_id,
            user_email,
            payload.event_type,
        )

        return {
            "success": True,
            "message": "Incident reported successfully",
            "report_id": created_report.get("report_id"),
            "report": created_report,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to submit incident report: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit incident report due to a server error. Please try again.",
        )


@router.get(
    "/my-reports",
    summary="Get incident reports submitted by current authenticated user",
    name="get_my_incident_reports",
)
async def get_my_incident_reports(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
    repo: IncidentRepository = Depends(get_incident_repo),
):
    """Returns list of incident reports submitted by the logged-in user."""
    user_id = str(current_user["id"])
    reports = await repo.get_user_reports(user_id=user_id, limit=limit)
    return {
        "success": True,
        "total": len(reports),
        "reports": reports,
    }


@router.get(
    "/recent",
    summary="Get recent public incident reports",
    name="get_recent_incident_reports",
)
async def get_recent_incident_reports(
    limit: int = Query(default=50, ge=1, le=100),
    repo: IncidentRepository = Depends(get_incident_repo),
):
    """Returns list of recent disaster incident reports."""
    reports = await repo.get_recent_reports(limit=limit)
    # Sanitize user details for public view
    sanitized = []
    for r in reports:
        item = dict(r)
        if "user_email" in item:
            item["user_email"] = None  # privacy
        sanitized.append(item)
    return {
        "success": True,
        "total": len(sanitized),
        "reports": sanitized,
    }


@router.get(
    "/{report_id}",
    summary="Get incident report by ID",
    name="get_incident_report_by_id",
)
async def get_incident_report_by_id(
    report_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    repo: IncidentRepository = Depends(get_incident_repo),
):
    """Finds and returns a single incident report by report ID."""
    report = await repo.get_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident report '{report_id}' not found.",
        )
    return {
        "success": True,
        "report": report,
    }
