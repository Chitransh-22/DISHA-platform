"""
DISHA Platform - Session Database Model
Disaster Intelligence and Situational Hazard Awareness Platform
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class SessionModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    refresh_token_hash: str
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    revoked: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }

    def to_mongo(self) -> Dict[str, Any]:
        d = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in d and d["_id"] is None:
            del d["_id"]
        return d
