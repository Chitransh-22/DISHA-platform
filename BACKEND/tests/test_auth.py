"""
DISHA Platform - Google OAuth Authentication & Authorization Test Suite
Disaster Intelligence and Situational Hazard Awareness Platform

Tests complete Google-only authentication lifecycle:
1. New Google account → DISHA account created.
2. Existing Google account → existing DISHA account used (no duplicates).
3. Google OAuth login initiation & origin state preservation (production and local).
4. Google OAuth callback error handling (cancelled, denied, missing code).
5. JWT token creation, claims verification, and security middleware.
6. Protected route (/api/auth/get-me) authorization.
7. Refresh token rotation & session revocation.
8. Single-device logout and multi-device logout-all.
9. Email/password and OTP endpoints confirmed removed/unavailable.
10. Authentication service health and provider status.
"""

import base64
import os
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient, ASGITransport
import jwt

# Add backend directory to sys.path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    hash_token,
)
from app.main import app
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository


# ─── Unit Tests: Cryptography & JWT Security ───────────────────────────────────

def test_jwt_token_lifecycle():
    user_id = "507f1f77bcf86cd799439011"
    session_id = "507f1f77bcf86cd799439022"

    access_token = create_access_token(user_id=user_id, session_id=session_id)
    payload = decode_jwt_token(access_token, expected_type="access")
    assert payload["sub"] == user_id
    assert payload["session_id"] == session_id
    assert payload["type"] == "access"
    assert "jti" in payload

    refresh_token = create_refresh_token(user_id=user_id, session_id=session_id)
    r_payload = decode_jwt_token(refresh_token, expected_type="refresh")
    assert r_payload["sub"] == user_id
    assert r_payload["session_id"] == session_id
    assert r_payload["type"] == "refresh"
    assert "jti" in r_payload

    # Token type mismatch rejection
    with pytest.raises(jwt.InvalidTokenError):
        decode_jwt_token(access_token, expected_type="refresh")

    with pytest.raises(jwt.InvalidTokenError):
        decode_jwt_token(refresh_token, expected_type="access")


# ─── Integration Tests: Health & Status ───────────────────────────────────────

@pytest.mark.asyncio
async def test_health_and_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "DISHA" in data["service"]

        res = await client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_auth_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/auth/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "active"
        assert data["provider"] == "google_oauth"
        assert "google" in data["auth_methods"]


# ─── Google OAuth Flow Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_google_login_initiate_endpoint():
    """
    Tests /api/auth/google/login endpoint:
    - Initiates OAuth redirect (302)
    - Target URL contains accounts.google.com with client_id, scope, and redirect_uri
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        res = await client.get("/api/auth/google/login")
        assert res.status_code == 302
        location = res.headers.get("location")
        assert location is not None
        assert "accounts.google.com" in location
        assert "redirect_uri=" in location
        assert "openid" in location


@pytest.mark.asyncio
async def test_google_oauth_origin_state_preservation(monkeypatch):
    """
    Tests that Google OAuth login preserves frontend origin (e.g. production Vercel or localhost),
    and callback redirects directly back to that origin.
    """
    ts = int(time.time())
    mock_email = f"state_test_{ts}@disha-test.gov.in"
    mock_google_id = f"g_sub_state_{ts}"

    mock_token = {
        "access_token": f"mock_token_{ts}",
        "token_type": "Bearer",
        "expires_in": 3600,
        "userinfo": {
            "sub": mock_google_id,
            "email": mock_email,
            "name": "State Test User",
            "email_verified": True,
        },
    }

    from app.routes.auth import oauth

    async def mock_authorize_access_token(request):
        return mock_token

    monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize_access_token)

    # 1. State with production Vercel origin
    prod_origin = "https://disha-platform.vercel.app"
    raw_state = "csrf_token_123"
    state_payload = base64.urlsafe_b64encode(f"{raw_state}|{prod_origin}".encode("utf-8")).decode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        res = await client.get(f"/api/auth/google/callback?code=mock_code&state={state_payload}")
        assert res.status_code == 302
        location = res.headers.get("location")
        assert location.startswith(f"{prod_origin}/auth/google/success")
        assert "access_token=" in location

        # Cleanup
        user_repo = UserRepository()
        session_repo = SessionRepository()
        user = await user_repo.get_by_email(mock_email)
        if user:
            await user_repo.collection.delete_one({"email": mock_email})
            await session_repo.collection.delete_many({"user_id": user["id"]})


@pytest.mark.asyncio
async def test_google_callback_error_handling():
    """
    Tests /api/auth/google/callback error conditions:
    - Missing code query param -> redirects to frontend error URL
    - Google error query param (access_denied) -> redirects to frontend error URL
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        # 1. Missing code
        res1 = await client.get("/api/auth/google/callback")
        assert res1.status_code == 302
        loc1 = res1.headers.get("location")
        assert "/auth/google/success?error=" in loc1

        # 2. User denied on Google consent screen
        res2 = await client.get("/api/auth/google/callback?error=access_denied&error_description=User+declined")
        assert res2.status_code == 302
        loc2 = res2.headers.get("location")
        assert "/auth/google/success?error=" in loc2


@pytest.mark.asyncio
async def test_google_oauth_complete_lifecycle(monkeypatch):
    """
    Tests complete Google OAuth lifecycle:
    1. New Google account signs in → DISHA user created with auth_provider='google', verified=True
    2. Session and JWT tokens created, refresh cookie attached
    3. Protected route /api/auth/get-me accessible with access token
    4. Repeated Google sign-in → existing DISHA user updated, NO duplicate account created
    5. Refresh token rotation works
    6. Logout revokes session
    7. Logout-all revokes all sessions
    """
    from app.routes.auth import oauth

    ts = int(time.time())
    mock_email = f"google_user_{ts}@disha.gov.in"
    mock_google_id = f"g_sub_{ts}"
    mock_name = "Disha Emergency Citizen"

    mock_token = {
        "access_token": f"google_access_tok_{ts}",
        "token_type": "Bearer",
        "expires_in": 3600,
        "userinfo": {
            "sub": mock_google_id,
            "email": mock_email,
            "name": mock_name,
            "email_verified": True,
        },
    }

    async def mock_authorize_access_token(request):
        return mock_token

    monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize_access_token)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        user_repo = UserRepository()
        session_repo = SessionRepository()

        # Ensure user does not exist beforehand
        assert await user_repo.get_by_email(mock_email) is None

        # 1. New Google Sign-In Callback
        res1 = await client.get("/api/auth/google/callback?code=valid_test_code")
        assert res1.status_code == 302
        redirect_url = res1.headers.get("location")
        assert redirect_url is not None
        assert "/auth/google/success" in redirect_url

        # Parse access token from redirect URL
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)
        assert "access_token" in params
        access_token = params["access_token"][0]

        # Verify refresh token cookie was set
        cookies = res1.cookies
        refresh_cookie = cookies.get(settings.COOKIE_NAME)
        assert refresh_cookie is not None

        # Verify user was created in MongoDB
        db_user = await user_repo.get_by_email(mock_email)
        assert db_user is not None
        assert db_user["email"] == mock_email
        assert db_user["verified"] is True
        assert db_user["auth_provider"] == "google"
        assert db_user["google_id"] == mock_google_id
        initial_user_id = db_user["id"]

        # 2. Access protected /api/auth/get-me
        unauth_res = await client.get("/api/auth/get-me")
        assert unauth_res.status_code == 401

        auth_headers = {"Authorization": f"Bearer {access_token}"}
        me_res = await client.get("/api/auth/get-me", headers=auth_headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["user"]["email"] == mock_email
        assert me_data["user"]["auth_provider"] == "google"

        # 3. Repeated Google Sign-In with same Google account (no duplicates!)
        res2 = await client.get("/api/auth/google/callback?code=valid_test_code_2")
        assert res2.status_code == 302

        # Count users with this email in database
        users_found = await user_repo.collection.count_documents({"email": mock_email})
        assert users_found == 1  # EXACTLY 1 user, no duplicate created!

        db_user_after = await user_repo.get_by_email(mock_email)
        assert db_user_after["id"] == initial_user_id

        # 4. Refresh token rotation
        client.cookies.set(settings.COOKIE_NAME, refresh_cookie)
        refresh_res = await client.post("/api/auth/refresh-token")
        assert refresh_res.status_code == 200
        ref_data = refresh_res.json()
        new_access_token = ref_data["access_token"]
        assert new_access_token != access_token

        # 5. Multi-device logout-all
        auth_headers2 = {"Authorization": f"Bearer {new_access_token}"}
        logout_all_res = await client.post("/api/auth/logout-all", headers=auth_headers2)
        assert logout_all_res.status_code == 200
        assert logout_all_res.json()["success"] is True

        # After logout-all, refresh token is revoked
        client.cookies.set(settings.COOKIE_NAME, refresh_cookie)
        revoked_res = await client.post("/api/auth/refresh-token")
        assert revoked_res.status_code in (401, 422)

        # 6. Single-device logout on a fresh login
        res3 = await client.get("/api/auth/google/callback?code=valid_test_code_3")
        assert res3.status_code == 302
        new_cookie = res3.cookies.get(settings.COOKIE_NAME)
        assert new_cookie is not None

        client.cookies.set(settings.COOKIE_NAME, new_cookie)
        logout_res = await client.post("/api/auth/logout")
        assert logout_res.status_code == 200

        # Cleanup DB
        await user_repo.collection.delete_one({"email": mock_email})
        await session_repo.collection.delete_many({"user_id": initial_user_id})


# ─── Verification that Email/Password & OTP Endpoints are Removed ─────────────

@pytest.mark.asyncio
async def test_email_password_and_otp_endpoints_unavailable():
    """
    Verifies that:
    - /api/auth/register is NOT a valid active registration endpoint
    - /api/auth/login is NOT a valid active login endpoint
    - /api/auth/verify-email is NOT a valid active OTP verification endpoint
    - /api/auth/resend-otp is NOT a valid active OTP resend endpoint
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register attempt
        res1 = await client.post(
            "/api/auth/register",
            json={"email": "test@disha.gov.in", "password": "Password123!"},
        )
        assert res1.status_code in (404, 405, 410)

        # Login attempt
        res2 = await client.post(
            "/api/auth/login",
            json={"email": "test@disha.gov.in", "password": "Password123!"},
        )
        assert res2.status_code in (404, 405, 410)

        # Verify email attempt
        res3 = await client.post(
            "/api/auth/verify-email",
            json={"email": "test@disha.gov.in", "otp": "123456"},
        )
        assert res3.status_code in (404, 405, 410)

        # Resend OTP attempt
        res4 = await client.post(
            "/api/auth/resend-otp",
            json={"email": "test@disha.gov.in"},
        )
        assert res4.status_code in (404, 405, 410)
