"""
DISHA Platform - User Schemas
Disaster Intelligence and Situational Hazard Awareness Platform
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    verified: bool = Field(default=False, description="Email verification status")
    name: Optional[str] = Field(default=None, description="Full name of user")
    phone: Optional[str] = Field(default=None, description="Contact phone number")
    city: Optional[str] = Field(default=None, description="City")
    pincode: Optional[str] = Field(default=None, description="PIN code")
    created_at: Optional[datetime] = Field(default=None, description="Account creation timestamp")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
