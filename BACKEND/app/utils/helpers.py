"""
DISHA Platform - Authentication Helper Utilities
Disaster Intelligence and Situational Hazard Awareness Platform
"""

from typing import Optional
from fastapi import Request, Response
from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """Extracts client IP address considering proxy headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


def get_user_agent(request: Request) -> str:
    """Extracts User-Agent string from request headers."""
    return request.headers.get("user-agent", "Unknown Device")[:255]


def set_refresh_cookie(
    response: Response,
    refresh_token: str,
    max_age_days: Optional[int] = None,
) -> None:
    """
    Sets the HTTP-Only Secure cookie for the refresh token.
    Configurable via environment variables.
    """
    days = max_age_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
    max_age = days * 24 * 60 * 60

    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        expires=max_age,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE or settings.is_production,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,  # 'lax', 'strict', or 'none'
    )


def clear_refresh_cookie(response: Response) -> None:
    """Clears the refresh token cookie upon logout."""
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE or settings.is_production,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )
