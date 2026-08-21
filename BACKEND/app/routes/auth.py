"""
DISHA Platform - Production Authentication & Authorization Routes
Disaster Intelligence and Situational Hazard Awareness Platform

Implements RESTful endpoints for:
- POST /api/auth/register
- POST /api/auth/verify-email
- POST /api/auth/resend-otp
- POST /api/auth/login
- GET  /api/auth/google/login
- GET  /api/auth/google/callback/
- POST /api/auth/refresh-token
- GET  /api/auth/get-me
- POST /api/auth/logout
- POST /api/auth/logout-all
"""

import logging
import secrets
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)

from authlib.integrations.starlette_client import OAuth
from starlette.responses import RedirectResponse

from app.core.config import settings
from app.dependencies.auth import get_current_user
from app.dependencies.rate_limiter import limit_rate
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResendOTPRequest,
    TokenRefreshResponse,
    VerifyEmailRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.utils.helpers import (
    clear_refresh_cookie,
    get_client_ip,
    get_user_agent,
    set_refresh_cookie,
)


logger = logging.getLogger("disha.routes.auth")


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


_auth_service = AuthService()


# ============================================================
# GOOGLE OAUTH CONFIGURATION
# ============================================================

oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        "prompt": "select_account",
    },
)


def _get_google_redirect_uri(request: Request) -> str:
    """
    Computes the canonical redirect URI for Google OAuth.
    Delegates to Centralized Settings with production guardrails.
    """
    return settings.get_effective_google_redirect_uri(request)


# ============================================================
# GOOGLE LOGIN
# ============================================================

@router.get(
    "/google/login",
    summary="Start Google OAuth login",
    name="google_login",
)
async def google_login(request: Request):
    """
    Initiates Google OAuth2 / OpenID Connect login flow.
    Redirects the user's browser to Google's consent screen.
    """
    frontend_url = settings.get_effective_frontend_url(request)
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        logger.error(
            "Google OAuth login attempted but GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing."
        )
        redirect_err = f"{frontend_url}/auth/google/success?error={quote_plus('Google OAuth is not configured on the server.')}"
        return RedirectResponse(url=redirect_err, status_code=status.HTTP_302_FOUND)

    redirect_uri = _get_google_redirect_uri(request)
    logger.info("Initiating Google OAuth login with redirect_uri: %s", redirect_uri)

    try:
        return await oauth.google.authorize_redirect(
            request,
            redirect_uri,
        )
    except Exception as exc:
        logger.warning(
            "Authlib authorize_redirect failed (%s); generating direct Google authorization URL fallback",
            exc,
        )
        try:
            import urllib.parse
            state = secrets.token_urlsafe(24)
            if hasattr(request, "session"):
                request.session["_state_google"] = state

            params = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "prompt": "select_account",
                "access_type": "offline",
            }
            google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
            return RedirectResponse(url=google_auth_url, status_code=status.HTTP_302_FOUND)
        except Exception as fallback_exc:
            logger.exception("Both Authlib and direct Google authorization fallback failed: %s", fallback_exc)
            redirect_err = f"{frontend_url}/auth/google/success?error={quote_plus('Unable to connect to Google OAuth service. Please try again or use email sign in.')}"
            return RedirectResponse(url=redirect_err, status_code=status.HTTP_302_FOUND)


# ============================================================
# GOOGLE CALLBACK
# ============================================================

@router.get(
    "/google/callback",
    name="google_callback",
    summary="Handle Google OAuth callback",
)
@router.get(
    "/google/callback/",
    include_in_schema=False,
)
async def google_callback(
    request: Request,
    response: Response,
):
    """
    Handles Google's OAuth callback:
    1. Validates callback query parameters (error / code).
    2. Exchanges authorization code for Google access token.
    3. Retrieves user information (email, name, sub/google_id).
    4. Finds or creates the corresponding DISHA user account.
    5. Issues DISHA JWT access token & sets HTTP-Only refresh cookie.
    6. Redirects browser back to frontend with the access token.
    """
    frontend_url = settings.get_effective_frontend_url(request)

    # 1. Handle error response directly from Google
    oauth_error = request.query_params.get("error")
    if oauth_error:
        error_desc = request.query_params.get("error_description") or oauth_error
        logger.warning(
            "Google OAuth callback received error from Google: %s (description: %s)",
            oauth_error,
            error_desc,
        )
        safe_error = (
            "Google login was cancelled or denied."
            if oauth_error == "access_denied"
            else "Google authentication failed."
        )
        redirect_err = f"{frontend_url}/auth/google/success?error={quote_plus(safe_error)}"
        return RedirectResponse(url=redirect_err, status_code=status.HTTP_302_FOUND)

    # 2. Check for authorization code
    code = request.query_params.get("code")
    if not code:
        logger.warning("Google OAuth callback called without authorization code.")
        redirect_err = f"{frontend_url}/auth/google/success?error={quote_plus('Missing authorization code from Google.')}"
        return RedirectResponse(url=redirect_err, status_code=status.HTTP_302_FOUND)

    try:
        # 3. Exchange authorization code with Google
        token = None
        try:
            token = await oauth.google.authorize_access_token(request)
        except Exception as exc:
            logger.warning(
                "Authlib authorize_access_token exception: %s. Attempting direct Google token endpoint exchange fallback.",
                exc,
            )
            # Direct token exchange fallback using httpx
            import httpx
            redirect_uri = _get_google_redirect_uri(request)
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
            async with httpx.AsyncClient() as client:
                token_res = await client.post(token_url, data=data, timeout=15.0)
                if token_res.is_success:
                    token = token_res.json()
                    logger.info("Direct Google token endpoint fallback succeeded.")
                else:
                    logger.error(
                        "Direct Google token exchange fallback failed (%s): %s",
                        token_res.status_code,
                        token_res.text,
                    )
                    redirect_err = f"{frontend_url}/auth/google/success?error={quote_plus('Google authentication token exchange failed.')}"
                    return RedirectResponse(url=redirect_err, status_code=status.HTTP_302_FOUND)

        if not token or not isinstance(token, dict):
            logger.error(
                "Google OAuth token exchange returned unexpected payload type: %s",
                type(token),
            )
            redirect_err = f"{frontend_url}/auth/google/success?error={quote_plus('Invalid response from Google token endpoint.')}"
            return RedirectResponse(url=redirect_err, status_code=status.HTTP_302_FOUND)

        # 4. Retrieve Google user profile info
        user_info = token.get("userinfo")
        if not user_info:
            try:
                user_info = await oauth.google.userinfo(token=token)
            except Exception as u_exc:
                logger.warning(
                    "Google OAuth userinfo endpoint request failed: %s; attempting id_token parse fallback",
                    u_exc,
                )

        # Fallback to parsing id_token payload if userinfo is still not available
        if not user_info and token.get("id_token"):
            try:
                import jwt as pyjwt
                user_info = pyjwt.decode(
                    token["id_token"],
                    options={"verify_signature": False},
                )
            except Exception as jwt_exc:
                logger.error("Failed to parse Google id_token fallback: %s", jwt_exc)

        # Extra fallback: fetch from Google's userinfo endpoint directly with access_token
        if not user_info and token.get("access_token"):
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    ui_res = await client.get(
                        "https://www.googleapis.com/oauth2/v3/userinfo",
                        headers={"Authorization": f"Bearer {token['access_token']}"},
                        timeout=10.0,
                    )
                    if ui_res.is_success:
                        user_info = ui_res.json()
            except Exception as ui_e:
                logger.warning("Direct Google userinfo fetch failed: %s", ui_e)

        if not user_info:
            logger.error(
                "Unable to retrieve Google user information from token or userinfo endpoint."
            )
            redirect_err = f"{frontend_url}/auth/google/success?error={quote_plus('Unable to retrieve Google user profile.')}"
            return RedirectResponse(url=redirect_err, status_code=status.HTTP_302_FOUND)

        google_email = (user_info.get("email") or "").strip().lower()
        google_name = (
            user_info.get("name")
            or f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip()
            or None
        )
        google_sub = str(user_info.get("sub") or "").strip()

        if not google_email or not google_sub:
            logger.error(
                "Google account info missing mandatory fields (email_present=%s, sub_present=%s)",
                bool(google_email),
                bool(google_sub),
            )
            redirect_err = f"{frontend_url}/auth/google/success?error={quote_plus('Google account did not provide required email or ID.')}"
            return RedirectResponse(url=redirect_err, status_code=status.HTTP_302_FOUND)

        # 5. Find or create DISHA user
        user = await _auth_service.user_repo.get_by_email(google_email)

        if not user:
            username_base = "".join(
                c for c in google_email.split("@")[0].lower() if c.isalnum() or c in "_-."
            )[:24]
            if not username_base:
                username_base = "disha_user"

            username = username_base
            existing_username = await _auth_service.user_repo.get_by_username(username)
            if existing_username:
                username = f"{username_base[:20]}_{google_sub[-6:]}"
                if await _auth_service.user_repo.get_by_username(username):
                    username = f"{username_base[:16]}_{secrets.token_hex(4)}"

            user_data = {
                "username": username,
                "email": google_email,
                "password_hash": None,
                "verified": True,
                "auth_provider": "google",
                "google_id": google_sub,
                "name": google_name,
                "phone": None,
                "city": None,
                "pincode": None,
            }

            user = await _auth_service.user_repo.create_user(user_data)
            logger.info("Created new DISHA user account via Google OAuth for: %s", google_email)
        else:
            updates = {
                "verified": True,
                "auth_provider": user.get("auth_provider") or "google",
                "google_id": google_sub,
            }
            if not user.get("name") and google_name:
                updates["name"] = google_name

            user_id = str(user.get("id") or user.get("_id"))
            user = await _auth_service.user_repo.update_user(user_id, updates)
            logger.info("Updated existing DISHA user account via Google OAuth for: %s", google_email)

        if not user:
            logger.error(
                "Failed to retrieve or create user in database for: %s",
                google_email,
            )
            redirect_err = f"{frontend_url}/auth/google/success?error={quote_plus('Database error creating or updating user account.')}"
            return RedirectResponse(url=redirect_err, status_code=status.HTTP_302_FOUND)

        # 6. Create normal DISHA session + JWTs
        ip = get_client_ip(request)
        user_agent = get_user_agent(request)

        access_token, refresh_token, user_dict = await _auth_service.login_with_oauth(
            user=user,
            ip=ip,
            user_agent=user_agent,
        )

        # 7. Construct frontend success redirect and attach refresh cookie to redirect response
        redirect_url = f"{frontend_url}/auth/google/success?access_token={access_token}&refresh_token={refresh_token}"
        redirect_response = RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND,
        )

        set_refresh_cookie(
            redirect_response,
            refresh_token,
        )

        return redirect_response

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Unexpected error during Google OAuth callback: %s", exc)
        redirect_err = f"{frontend_url}/auth/google/success?error={quote_plus('Google authentication failed.')}"
        return RedirectResponse(url=redirect_err, status_code=status.HTTP_302_FOUND)

# ============================================================
# REGISTER
# ============================================================

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new DISHA user account",
    dependencies=[
        Depends(
            limit_rate(
                "register",
                max_requests=settings.RATE_LIMIT_REGISTER,
            )
        )
    ],
)
async def register(req: RegisterRequest):
    """
    Registers a new citizen/responder user account
    and triggers email verification via OTP.
    """

    result = await _auth_service.register(
        email=req.email,
        password=req.password,
        username=req.username,
        name=req.name,
        phone=req.phone,
        city=req.city,
        pincode=req.pincode,
    )

    return MessageResponse(
        message=result["message"],
        success=True,
        data={
            "user_id": result["user_id"],
            "email": result["email"],
            "verified": result["verified"],
        },
    )


# ============================================================
# VERIFY EMAIL
# ============================================================

@router.post(
    "/verify-email",
    summary="Verify email address with 6-digit OTP",
    dependencies=[
        Depends(
            limit_rate(
                "verify-email",
                max_requests=settings.RATE_LIMIT_OTP,
            )
        )
    ],
)
async def verify_email(
    req: VerifyEmailRequest,
    request: Request,
    response: Response,
):
    """
    Verifies user's email address using the supplied 6-digit OTP and authenticates the user.
    """
    ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    result = await _auth_service.verify_email(
        email=req.email,
        otp=req.otp,
        ip=ip,
        user_agent=user_agent,
    )

    if isinstance(result, dict) and "refresh_token" in result:
        set_refresh_cookie(response, result["refresh_token"])

    return result


# ============================================================
# RESEND OTP
# ============================================================

@router.post(
    "/resend-otp",
    response_model=MessageResponse,
    summary="Resend verification OTP",
    dependencies=[
        Depends(
            limit_rate(
                "resend-otp",
                max_requests=settings.RATE_LIMIT_OTP,
            )
        )
    ],
)
async def resend_otp(req: ResendOTPRequest):
    """
    Resends a fresh 6-digit verification OTP
    to the user's email address.
    """

    result = await _auth_service.resend_otp(
        email=req.email
    )

    return MessageResponse(
        message=result["message"],
        success=True,
    )


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Sign in with email and password",
    dependencies=[
        Depends(
            limit_rate(
                "login",
                max_requests=settings.RATE_LIMIT_LOGIN,
            )
        )
    ],
)
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
):
    """
    Authenticates a verified user.

    - Issues short-lived access JWT
    - Sets long-lived refresh JWT in HTTP-only cookie
    - Tracks active session with client IP and User-Agent
    """

    ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    access_token, refresh_token, user_dict = await _auth_service.login(
        email_or_username=req.email,
        password=req.password,
        ip=ip,
        user_agent=user_agent,
    )

    set_refresh_cookie(
        response,
        refresh_token,
    )

    return AuthResponse(
        message="Sign in successful",
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(**user_dict),
    )


# ============================================================
# REFRESH TOKEN
# ============================================================

@router.post(
    "/refresh-token",
    response_model=TokenRefreshResponse,
    summary="Refresh access token with refresh token rotation",
    dependencies=[
        Depends(
            limit_rate(
                "refresh-token",
                max_requests=settings.RATE_LIMIT_REFRESH,
            )
        )
    ],
)
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(
        default=None,
        alias=settings.COOKIE_NAME,
    ),
):
    """
    Refreshes the access token using the HTTP-only
    refresh token cookie.

    Executes refresh token rotation.
    """

    token = refresh_token or request.headers.get(
        "x-refresh-token"
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing.",
        )

    ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    new_access_token, new_refresh_token = (
        await _auth_service.refresh_tokens(
            refresh_token=token,
            ip=ip,
            user_agent=user_agent,
        )
    )

    set_refresh_cookie(
        response,
        new_refresh_token,
    )

    return TokenRefreshResponse(
        message="Access token refreshed successfully",
        access_token=new_access_token,
        token_type="bearer",
    )


# ============================================================
# GET CURRENT USER
# ============================================================

@router.get(
    "/get-me",
    summary="Fetch current authenticated user profile",
)
async def get_me(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Returns profile information of the currently
    authenticated user.
    """

    return {
        "message": "User fetched successfully",
        "user": {
            "id": str(
                current_user.get("id")
                or current_user.get("_id")
            ),
            "username": current_user.get("username"),
            "email": current_user.get("email"),
            "verified": current_user.get(
                "verified",
                False,
            ),
            "name": current_user.get("name"),
            "phone": current_user.get("phone"),
            "city": current_user.get("city"),
            "pincode": current_user.get("pincode"),
            "created_at": current_user.get("created_at"),
        },
    }


# ============================================================
# LOGOUT
# ============================================================

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out and invalidate current session",
)
async def logout(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(
        default=None,
        alias=settings.COOKIE_NAME,
    ),
):
    """
    Logs out the user.

    - Revokes the active session
    - Clears refresh token cookie
    """

    token = refresh_token or request.headers.get(
        "x-refresh-token"
    )

    await _auth_service.logout(
        refresh_token=token
    )

    clear_refresh_cookie(response)

    return MessageResponse(
        message="Logged out successfully",
        success=True,
    )


# ============================================================
# LOGOUT ALL
# ============================================================

@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Log out from all devices",
)
async def logout_all(
    response: Response,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Revokes all active sessions across all devices
    for the current authenticated user.
    """

    user_id = str(
        current_user.get("id")
        or current_user.get("_id")
    )

    revoked_count = await _auth_service.logout_all(
        user_id=user_id
    )

    clear_refresh_cookie(response)

    return MessageResponse(
        message=(
            f"Logged out from all devices "
            f"({revoked_count} active sessions revoked)"
        ),
        success=True,
        data={
            "revoked_sessions": revoked_count
        },
    )