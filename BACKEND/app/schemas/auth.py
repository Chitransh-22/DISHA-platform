"""
DISHA Platform - Authentication Schemas
Disaster Intelligence and Situational Hazard Awareness Platform
"""

import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=30,
        description="Unique username (3-30 chars)",
    )
    email: EmailStr = Field(..., description="User valid email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    name: Optional[str] = Field(default=None, description="Full name of user")
    phone: Optional[str] = Field(default=None, description="Mobile contact number")
    city: Optional[str] = Field(default=None, description="City")
    pincode: Optional[str] = Field(default=None, description="6-digit PIN code")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str], values) -> str:
        if v is not None and v.strip():
            v = v.strip().lower()
            if not re.match(r"^[a-zA-Z0-9_\.\-]+$", v):
                raise ValueError(
                    "Username may only contain letters, numbers, dots, hyphens, and underscores."
                )
            return v
        # If username was not provided, fallback to local-part of email
        return ""

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one numeric digit.")
        return v


class VerifyEmailRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit numeric OTP")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 numeric digits.")
        return v


class ResendOTPRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address to resend OTP to")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email or username")
    password: str = Field(..., min_length=1, description="Password")

    @field_validator("email")
    @classmethod
    def clean_identifier(cls, v: str) -> str:
        return v.strip().lower()


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
    data: Optional[dict] = None
