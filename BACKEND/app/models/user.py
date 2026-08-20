"""
DISHA Platform - User Database Model
Disaster Intelligence and Situational Hazard Awareness Platform
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr, Field


class UserModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    username: str
    email: EmailStr
    password_hash: str
    verified: bool = False
    name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
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
        # Ensure email and username are normalized
        if "email" in d and isinstance(d["email"], str):
            d["email"] = d["email"].lower().strip()
        if "username" in d and isinstance(d["username"], str):
            d["username"] = d["username"].strip()
        return d
