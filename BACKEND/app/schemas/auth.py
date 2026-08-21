"""
DISHA Platform - Authentication Schemas
Disaster Intelligence and Situational Hazard Awareness Platform
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel
from app.schemas.user import UserResponse


class AuthResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefreshResponse(BaseModel):
    message: str = "Token refreshed successfully"
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
    success: bool = True
    data: Optional[Dict[str, Any]] = None
