"""
DISHA Platform - OTP Database Model
Disaster Intelligence and Situational Hazard Awareness Platform
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr, Field


class OTPModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    user_id: str
    otp_hash: str
    expires_at: datetime
    attempts: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }

    def to_mongo(self) -> Dict[str, Any]:
        d = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in d and d["_id"] is None:
            del d["_id"]
        if "email" in d and isinstance(d["email"], str):
            d["email"] = d["email"].lower().strip()
        return d
