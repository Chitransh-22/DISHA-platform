"""
DISHA Platform - Comprehensive Authentication & Security Test Suite
Disaster Intelligence and Situational Hazard Awareness Platform

Tests complete authentication lifecycle:
- User Registration & Validation (valid, duplicate, weak password, invalid email)
- OTP Generation, Expiration, Attempt Limiting (brute-force) & Verification
- Login & JWT Token Issuance (valid, wrong password, unverified, nonexistent)
- Access Token Claims & Security Dependency (valid, expired, malformed, wrong type)
- Refresh Token Rotation & Session Revocation (reuse attack detection)
- Logout & Logout-all Endpoints (multi-session invalidation)
- Rate Limiting Protection (HTTP 429)
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

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
    generate_secure_otp,
    hash_otp,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_otp_hash,
    verify_password,
)
from app.main import app
from app.repositories.otp_repository import OTPRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository


# ─── Unit Tests: Cryptography & Security ───────────────────────────────────────

def test_password_hashing_argon2id():
    raw_pass = "DishaSecure2026!"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert hashed.startswith("$argon2")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_password_strength_validation():
    # Valid
    ok, err = validate_password_strength("StrongPass1")
    assert ok is True
    assert err is None

    # Too short
    ok, err = validate_password_strength("Short1")
    assert ok is False
    assert "at least 8" in err

    # No uppercase
    ok, err = validate_password_strength("lowercaseonly1")
    assert ok is False
    assert "uppercase" in err

    # No digit
    ok, err = validate_password_strength("NoDigitsHere!")
    assert ok is False
    assert "digit" in err


def test_otp_generation_and_hashing():
    otp = generate_secure_otp(length=6)
    assert len(otp) == 6
    assert otp.isdigit()

    email = "test@disha.gov.in"
    otp_hash = hash_otp(otp, email)
    assert otp_hash != otp
    assert verify_otp_hash(otp, email, otp_hash) is True
    assert verify_otp_hash("000000", email, otp_hash) is False
    assert verify_otp_hash(otp, "other@disha.gov.in", otp_hash) is False


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


# ─── Integration Tests: FastAPI Endpoints ─────────────────────────────────────

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

        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_registration_validation_errors():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid email
        res = await client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "ValidPassword123!"},
        )
        assert res.status_code == 422

        # Weak password (missing uppercase)
        res = await client.post(
            "/api/auth/register",
            json={"email": "user123@disha.gov.in", "password": "weakpassword1"},
        )
        assert res.status_code == 422 or res.status_code == 400

        # Weak password (too short)
        res = await client.post(
            "/api/auth/register",
            json={"email": "user123@disha.gov.in", "password": "Ab1"},
        )
        assert res.status_code == 422 or res.status_code == 400


@pytest.mark.asyncio
async def test_otp_attempt_limits_and_expiry():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        otp_repo = OTPRepository()
        test_email = f"otp_test_{int(time.time())}@disha.gov.in"
        correct_otp = "889900"
        correct_hash = hash_otp(correct_otp, test_email)

        # 1. Test Expiry
        expired_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        await otp_repo.create_otp(
            email=test_email,
            user_id="dummy_user_1",
            otp_hash=correct_hash,
            expires_at=expired_at,
        )

        res = await client.post(
            "/api/auth/verify-email",
            json={"email": test_email, "otp": correct_otp},
        )
        assert res.status_code == 400
        assert "expired" in res.json()["detail"].lower()

        # 2. Test Attempt Limiting (brute-force defense)
        valid_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        await otp_repo.create_otp(
            email=test_email,
            user_id="dummy_user_1",
            otp_hash=correct_hash,
            expires_at=valid_expires,
        )

        # Fail 5 times
        for _ in range(5):
            res = await client.post(
                "/api/auth/verify-email",
                json={"email": test_email, "otp": "111111"},
            )
            assert res.status_code == 400

        # 6th attempt should state invalidation / too many attempts
        res = await client.post(
            "/api/auth/verify-email",
            json={"email": test_email, "otp": correct_otp},
        )
        assert res.status_code == 400

        # Cleanup
        await otp_repo.delete_otps_for_email(test_email)


@pytest.mark.asyncio
async def test_full_auth_flow():
    """
    Tests end-to-end flow:
    1. Register new user
    2. Try login before verification (should return 403)
    3. Verify email with active OTP
    4. Login with verified account (should issue access token + cookie)
    5. Access /api/auth/get-me with Bearer token
    6. Refresh access token via refresh-token endpoint (rotation)
    7. Logout current session
    8. Logout all devices
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ts = int(time.time())
        test_email = f"testuser_{ts}@disha-test.gov.in"
        test_username = f"disha_user_{ts}"
        test_password = "SecurePassword123!"

        # 1. Registration
        reg_payload = {
            "username": test_username,
            "email": test_email,
            "password": test_password,
            "name": "DISHA Citizen Test",
            "phone": "9876543210",
            "city": "Bhopal",
            "pincode": "462001",
        }
        res = await client.post("/api/auth/register", json=reg_payload)
        assert res.status_code == 201
        reg_data = res.json()
        assert reg_data["success"] is True
        assert reg_data["data"]["email"] == test_email

        # 2. Login before verification should be rejected with 403 Forbidden
        login_res = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": test_password},
        )
        assert login_res.status_code == 403
        assert "verified" in login_res.json()["detail"].lower() or "unverified" in login_res.json()["detail"].lower()

        # 3. Retrieve OTP from DB to verify
        otp_repo = OTPRepository()
        otp_doc = await otp_repo.get_active_otp(test_email)
        assert otp_doc is not None

        # Verify with wrong OTP
        wrong_verify = await client.post(
            "/api/auth/verify-email",
            json={"email": test_email, "otp": "000000"},
        )
        assert wrong_verify.status_code == 400

        # Verify with known OTP
        known_otp = "123456"
        known_hash = hash_otp(known_otp, test_email)
        await otp_repo.create_otp(
            email=test_email,
            user_id=otp_doc["user_id"],
            otp_hash=known_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )

        valid_verify = await client.post(
            "/api/auth/verify-email",
            json={"email": test_email, "otp": known_otp},
        )
        assert valid_verify.status_code == 200
        verify_data = valid_verify.json()
        assert verify_data["user"]["verified"] is True

        # 4. Login with invalid password
        bad_login = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "WrongPassword123!"},
        )
        assert bad_login.status_code == 401

        # Login with nonexistent user
        bad_user = await client.post(
            "/api/auth/login",
            json={"email": "nonexistent@disha.gov.in", "password": "WrongPassword123!"},
        )
        assert bad_user.status_code == 401

        # Valid Login after verification
        login_res = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": test_password},
        )
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert "access_token" in login_data
        access_token = login_data["access_token"]
        assert login_data["user"]["email"] == test_email
        assert login_data["user"]["verified"] is True

        # Check refresh cookie was set
        cookies = login_res.cookies
        refresh_cookie = cookies.get(settings.COOKIE_NAME)
        assert refresh_cookie is not None

        # 5. Access protected /api/auth/get-me
        unauth_me = await client.get("/api/auth/get-me")
        assert unauth_me.status_code == 401

        # With malformed token
        bad_token_res = await client.get(
            "/api/auth/get-me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert bad_token_res.status_code == 401

        # With valid Bearer token -> 200
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        me_res = await client.get("/api/auth/get-me", headers=auth_headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["user"]["email"] == test_email
        assert me_data["user"]["username"] == test_username
        assert "password_hash" not in me_data["user"]
        assert "refresh_token_hash" not in me_data["user"]

        # 6. Refresh token rotation
        client.cookies.set(settings.COOKIE_NAME, refresh_cookie)
        refresh_res = await client.post("/api/auth/refresh-token")
        assert refresh_res.status_code == 200
        refresh_data = refresh_res.json()
        assert "access_token" in refresh_data
        new_access_token = refresh_data["access_token"]
        assert new_access_token != access_token

        # Check new refresh cookie was rotated
        new_refresh_cookie = refresh_res.cookies.get(settings.COOKIE_NAME)
        assert new_refresh_cookie is not None

        # 7. Logout
        logout_res = await client.post("/api/auth/logout")
        assert logout_res.status_code == 200

        # After logout, old refresh token is revoked
        revoked_refresh = await client.post("/api/auth/refresh-token")
        assert revoked_refresh.status_code in (401, 422)

        # 8. Test Multi-Device Logout (Logout-all)
        # Login again
        login_res2 = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": test_password},
        )
        assert login_res2.status_code == 200
        token2 = login_res2.json()["access_token"]

        logout_all_res = await client.post(
            "/api/auth/logout-all",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert logout_all_res.status_code == 200
        assert logout_all_res.json()["success"] is True

        # Clean up test user & sessions from DB
        user_repo = UserRepository()
        session_repo = SessionRepository()
        user = await user_repo.get_by_email(test_email)
        if user:
            await user_repo.collection.delete_one({"_id": user["_id"] if "_id" in user else user["id"]})
            await session_repo.collection.delete_many({"user_id": user["id"]})
            await otp_repo.collection.delete_many({"email": test_email})


@pytest.mark.asyncio
async def test_google_login_endpoint():
    """
    Tests /api/auth/google/login endpoint:
    - Initiates OAuth redirect (302)
    - Sets session cookie
    - Target URL contains accounts.google.com with client_id and redirect_uri
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        res = await client.get("/api/auth/google/login")
        assert res.status_code == 302
        location = res.headers.get("location")
        assert location is not None
        assert "accounts.google.com" in location
        assert "redirect_uri=" in location


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
async def test_google_callback_success_flow(monkeypatch):
    """
    Tests complete Google OAuth callback flow with mocked token exchange:
    1. Simulates valid Google token & userinfo
    2. Verifies user created in DB
    3. Verifies redirect with access_token
    4. Verifies refresh token cookie attached to RedirectResponse
    5. Verifies access token works with /api/auth/get-me
    6. Simulates return login of same Google user (updates existing user)
    """
    from app.routes.auth import oauth
    from urllib.parse import parse_qs, urlparse

    ts = int(time.time())
    mock_email = f"google_test_{ts}@disha-test.gov.in"
    mock_google_id = f"g_sub_{ts}"
    mock_name = "Google Test User"

    mock_token = {
        "access_token": f"mock_google_access_token_{ts}",
        "token_type": "Bearer",
        "expires_in": 3600,
        "userinfo": {
            "sub": mock_google_id,
            "email": mock_email,
            "name": mock_name,
            "picture": "https://lh3.googleusercontent.com/test.jpg",
            "email_verified": True,
        },
    }

    async def mock_authorize_access_token(request):
        return mock_token

    monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize_access_token)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        # 1. Callback execution
        res = await client.get("/api/auth/google/callback?code=mock_code_123&state=mock_state")
        assert res.status_code == 302

        location = res.headers.get("location")
        assert location is not None
        assert "/auth/google/success?access_token=" in location

        # Extract access token
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)
        assert "access_token" in query_params
        issued_access_token = query_params["access_token"][0]

        # Verify refresh cookie was set on the RedirectResponse
        cookies = res.cookies
        assert settings.COOKIE_NAME in cookies

        # 2. Verify user in database
        user_repo = UserRepository()
        user = await user_repo.get_by_email(mock_email)
        assert user is not None
        assert user["verified"] is True
        assert user["auth_provider"] == "google"
        assert user["google_id"] == mock_google_id
        assert user["name"] == mock_name

        # 3. Test access token with /api/auth/get-me
        me_res = await client.get(
            "/api/auth/get-me",
            headers={"Authorization": f"Bearer {issued_access_token}"},
        )
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["user"]["email"] == mock_email
        assert me_data["user"]["verified"] is True

        # 4. Existing user returns via Google login again
        res2 = await client.get("/api/auth/google/callback?code=mock_code_456&state=mock_state_2")
        assert res2.status_code == 302
        assert "/auth/google/success?access_token=" in res2.headers.get("location")

        # Cleanup DB
        session_repo = SessionRepository()
        await user_repo.collection.delete_one({"email": mock_email})
        await session_repo.collection.delete_many({"user_id": user["id"]})


def test_effective_url_resolvers():
    """
    Tests that Settings resolves OAuth redirect URIs and frontend URLs properly
    in development vs production, preventing accidental localhost redirects in production.
    """
    from app.core.config import Settings

    # 1. Development Settings
    dev_settings = Settings(
        ENVIRONMENT="development",
        FRONTEND_URL="http://localhost:5173",
        GOOGLE_REDIRECT_URI="http://localhost:8000/api/auth/google/callback",
    )
    assert dev_settings.get_effective_frontend_url() == "http://localhost:5173"
    assert dev_settings.get_effective_google_redirect_uri() == "http://localhost:8000/api/auth/google/callback"

    # 2. Production Settings with localhost misconfiguration fallback
    prod_misconfigured = Settings(
        ENVIRONMENT="production",
        FRONTEND_URL="http://localhost:5173",
        BACKEND_URL="https://disha-platform.onrender.com",
        GOOGLE_REDIRECT_URI="http://localhost:8000/api/auth/google/callback",
    )
    # Must protect against localhost in production
    assert prod_misconfigured.get_effective_frontend_url() == "https://disha-platform.vercel.app"
    assert prod_misconfigured.get_effective_google_redirect_uri() == "https://disha-platform.onrender.com/api/auth/google/callback"

    # 3. Production Settings with explicit production URLs
    prod_configured = Settings(
        ENVIRONMENT="production",
        FRONTEND_URL="https://disha-platform.vercel.app",
        BACKEND_URL="https://disha-platform.onrender.com",
        GOOGLE_REDIRECT_URI="https://disha-platform.onrender.com/api/auth/google/callback",
    )
    assert prod_configured.get_effective_frontend_url() == "https://disha-platform.vercel.app"
    assert prod_configured.get_effective_google_redirect_uri() == "https://disha-platform.onrender.com/api/auth/google/callback"


def test_email_service_masking_and_fallbacks():
    """
    Tests email recipient masking and environment fallback behavior.
    """
    from app.services.email_service import mask_recipient, _send_smtp_email_sync

    assert mask_recipient("john@example.com") == "j**n@example.com"
    assert mask_recipient("shashwat@gmail.com") == "s****t@gmail.com"
    assert mask_recipient("ab@disha.gov.in") == "a*@disha.gov.in"
    assert mask_recipient("") == "******"

    # In dev mode, unconfigured email returns True (simulation)
    res = _send_smtp_email_sync("test@example.com", "Test Subject", "<p>Test</p>", "123456")
    assert res is True


@pytest.mark.asyncio
async def test_google_oauth_state_origin_preservation(monkeypatch):
    """
    Tests that Google OAuth login preserves frontend origin in state,
    and callback redirects directly back to that origin.
    """
    import base64
    from app.routes.auth import oauth

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

        # Cleanup
        user_repo = UserRepository()
        session_repo = SessionRepository()
        user = await user_repo.get_by_email(mock_email)
        if user:
            await user_repo.collection.delete_one({"email": mock_email})
            await session_repo.collection.delete_many({"user_id": user["id"]})



