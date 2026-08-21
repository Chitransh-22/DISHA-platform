"""
DISHA Platform - Incident Report Database Model
Disaster Intelligence and Situational Hazard Awareness Platform
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IncidentLocation(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    coordinates: Optional[List[float]] = None  # [longitude, latitude] for GeoJSON 2dsphere


class IncidentReportCreate(BaseModel):
    event_type: str = Field(..., description="Type of disaster event (e.g. flood, cyclone, earthquake)")
    description: str = Field(..., min_length=5, max_length=2000, description="Description of the incident")
    location: IncidentLocation
    images: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Attached evidence photos")


class IncidentReportModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    report_id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    event_type: str
    description: str
    location: Dict[str, Any]
    images: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "submitted"  # submitted, verified, dispatched, resolved
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }

    def to_mongo(self) -> Dict[str, Any]:
        """Converts model to dictionary suitable for MongoDB document insertion."""
        d = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in d and d["_id"] is None:
            del d["_id"]
        return d
