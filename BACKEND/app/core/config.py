"""
DISHA Platform - Centralized Configuration System
Disaster Intelligence and Situational Hazard Awareness Platform

Manages environment configuration, database URIs, JWT security,
OAuth2 credentials, CORS policies, and cookie settings.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General Application Settings
    PROJECT_NAME: str = "DISHA Platform API"
    PROJECT_DESCRIPTION: str = (
        "Disaster Intelligence and Situational Hazard Awareness Platform API"
    )
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "ENV"),
    )
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # MongoDB Configuration
    MONGO_URI: str = Field(
        default="mongodb://localhost:27017/DISHA",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )
    MONGO_DB: str = "DISHA"

    # JWT Authentication & Security
    JWT_SECRET: str = Field(
        default="disha-super-secret-jwt-key-2026-production-grade-sec-token",
        validation_alias=AliasChoices("JWT_SECRET", "JWT_SECRET_KEY", "SECRET_KEY"),
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OTP System Settings
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    OTP_LENGTH: int = 6

    # Cookie Configuration
    COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = False  # Set to True in production (HTTPS)
    COOKIE_SAMESITE: str = "lax"  # 'lax', 'strict', or 'none'
    COOKIE_DOMAIN: Optional[str] = None
    COOKIE_PATH: str = "/"

    # Frontend Integration & CORS
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: str = ""
    CORS_ORIGINS: str = ""

    # Google OAuth2 / Gmail API Configuration
    GOOGLE_USER: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_ID"),
    )
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_CLIENT_SECRET", "GOOGLE_OAUTH_CLIENT_SECRET"),
    )
    GOOGLE_REDIRECT_URI: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "GOOGLE_REDIRECT_URI", "GOOGLE_OAUTH_REDIRECT_URI", "GOOGLE_CALLBACK_URL"
        ),
    )
    GOOGLE_REFRESH_TOKEN: Optional[str] = None

    # SMTP Fallback Email Configuration
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    SMTP_FROM: Optional[str] = None

    # Rate Limiting Settings (Requests per minute)
    RATE_LIMIT_REGISTER: int = 10
    RATE_LIMIT_LOGIN: int = 10
    RATE_LIMIT_OTP: int = 15
    RATE_LIMIT_REFRESH: int = 30

    @property
    def cors_origins_list(self) -> List[str]:
        default_origins = [
            "https://disha-platform.vercel.app",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
        origins = list(default_origins)
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL.rstrip("/"))

        for env_val in [self.ALLOWED_ORIGINS, self.CORS_ORIGINS]:
            if env_val:
                for item in env_val.split(","):
                    cleaned = item.strip().rstrip("/")
                    if cleaned and cleaned not in origins:
                        origins.append(cleaned)
        return origins

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")


settings = Settings()
