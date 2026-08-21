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
    FRONTEND_URL: str = Field(
        default="http://localhost:5173",
        validation_alias=AliasChoices("FRONTEND_URL", "CLIENT_URL", "APP_URL", "VERCEL_URL"),
    )
    BACKEND_URL: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "BACKEND_URL", "API_URL", "SERVER_URL", "RENDER_EXTERNAL_URL"
        ),
    )
    ALLOWED_ORIGINS: str = ""
    CORS_ORIGINS: str = ""

    # Google OAuth2 / Gmail API Configuration
    GOOGLE_USER: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_USER", "GMAIL_USER", "GOOGLE_EMAIL"),
    )
    GOOGLE_CLIENT_ID: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_ID", "VITE_GOOGLE_CLIENT_ID"),
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
    GOOGLE_REFRESH_TOKEN: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_REFRESH_TOKEN", "GMAIL_REFRESH_TOKEN"),
    )

    # SMTP / Gmail App Password Email Configuration
    SMTP_HOST: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("SMTP_HOST", "EMAIL_HOST", "MAIL_HOST", "EMAIL_SERVER"),
    )
    SMTP_PORT: int = Field(
        default=587,
        validation_alias=AliasChoices("SMTP_PORT", "EMAIL_PORT", "MAIL_PORT"),
    )
    SMTP_USER: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "SMTP_USER",
            "SMTP_USERNAME",
            "EMAIL_USER",
            "EMAIL_HOST_USER",
            "MAIL_USERNAME",
            "GMAIL_USER",
            "GMAIL_ADDRESS",
        ),
    )
    SMTP_PASSWORD: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "SMTP_PASSWORD",
            "SMTP_PASS",
            "EMAIL_PASSWORD",
            "EMAIL_HOST_PASSWORD",
            "MAIL_PASSWORD",
            "GMAIL_APP_PASSWORD",
            "EMAIL_PASS",
        ),
    )
    SMTP_TLS: bool = Field(
        default=True,
        validation_alias=AliasChoices("SMTP_TLS", "EMAIL_USE_TLS", "MAIL_USE_TLS", "SMTP_USE_TLS"),
    )
    SMTP_FROM: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "SMTP_FROM", "EMAIL_FROM", "MAIL_FROM", "DEFAULT_FROM_EMAIL", "SENDER_EMAIL"
        ),
    )

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
        if self.BACKEND_URL and self.BACKEND_URL not in origins:
            origins.append(self.BACKEND_URL.rstrip("/"))

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

    def get_effective_frontend_url(self, request=None) -> str:
        """
        Returns the resolved frontend URL for OAuth success/error browser redirection.
        In production, prevents accidental redirection to localhost.
        """
        raw_frontend = (self.FRONTEND_URL or "").strip().rstrip("/")
        is_local_frontend = (
            not raw_frontend
            or "localhost" in raw_frontend
            or "127.0.0.1" in raw_frontend
        )

        if self.is_production and is_local_frontend:
            if request:
                origin_hdr = request.headers.get("origin") or request.headers.get("referer")
                if origin_hdr:
                    for allowed in self.cors_origins_list:
                        if allowed != "*" and "localhost" not in allowed and "127.0.0.1" not in allowed:
                            if origin_hdr.startswith(allowed):
                                return allowed.rstrip("/")
            return "https://disha-platform.vercel.app"

        return raw_frontend or "http://localhost:5173"

    def get_effective_google_redirect_uri(self, request=None) -> str:
        """
        Returns the canonical Google OAuth callback URI.
        Prioritizes explicit GOOGLE_REDIRECT_URI if valid for environment.
        In production, protects against stale localhost redirect URIs.
        """
        raw_redirect = (self.GOOGLE_REDIRECT_URI or "").strip()
        is_local_redirect = (
            not raw_redirect
            or "localhost" in raw_redirect
            or "127.0.0.1" in raw_redirect
        )

        if self.is_production:
            if raw_redirect and not is_local_redirect:
                return raw_redirect
            if self.BACKEND_URL and "localhost" not in self.BACKEND_URL and "127.0.0.1" not in self.BACKEND_URL:
                return f"{self.BACKEND_URL.rstrip('/')}/api/auth/google/callback"
            if request:
                try:
                    callback_url = str(request.url_for("google_callback"))
                    if callback_url.startswith("http://"):
                        callback_url = "https://" + callback_url[len("http://") :]
                    if not ("localhost" in callback_url or "127.0.0.1" in callback_url):
                        return callback_url
                except Exception:
                    pass
            return "https://disha-platform.onrender.com/api/auth/google/callback"

        # Development environment
        if raw_redirect:
            return raw_redirect
        if request:
            try:
                return str(request.url_for("google_callback"))
            except Exception:
                pass
        return "http://localhost:8000/api/auth/google/callback"


settings = Settings()
