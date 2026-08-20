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
from typing import Any, Dict, Optional

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
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
    },
)


# ============================================================
# GOOGLE LOGIN
# ============================================================
@router.get(
    "/google/login",
    summary="Start Google OAuth login",
    name="google_login",
)
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")

    print("GOOGLE REDIRECT URI:", redirect_uri)

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
    )

@router.get(
    "/google/callback/",
    name="google_callback",
    summary="Handle Google OAuth callback",
)
async def google_callback(
    request: Request,
    response: Response,
):
    """
    Handles Google's OAuth callback.

    Finds or creates the DISHA user and then creates
    the normal DISHA JWT/session authentication state.
    """

    try:
        token = await oauth.google.authorize_access_token(request)

        user_info = token.get("userinfo")

        if not user_info:
            user_info = await oauth.google.parse_id_token(
                request,
                token,
            )

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to retrieve Google user information.",
            )

        google_email = user_info.get("email")
        google_name = user_info.get("name")
        google_sub = user_info.get("sub")

        if not google_email or not google_sub:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account did not provide required information.",
            )

        google_email = google_email.strip().lower()

        # ----------------------------------------------------
        # Find existing user
        # ----------------------------------------------------

        user = await _auth_service.user_repo.get_by_email(
            google_email
        )

        # ----------------------------------------------------
        # Create user if it doesn't exist
        # ----------------------------------------------------

        if not user:
            username_base = (
                google_email.split("@")[0]
                .lower()
            )

            username = username_base[:30]

            existing_username = (
                await _auth_service.user_repo.get_by_username(
                    username
                )
            )

            if existing_username:
                username = f"{username}_{google_sub[-6:]}"

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

            user = await _auth_service.user_repo.create_user(
                user_data
            )

        else:
            # ------------------------------------------------
            # Existing account
            # ------------------------------------------------

            updates = {
                "verified": True,
                "auth_provider": user.get(
                    "auth_provider",
                    "google",
                ),
                "google_id": google_sub,
            }

            user = await _auth_service.user_repo.update_user(
                user["id"],
                updates,
            )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to create or retrieve DISHA user.",
            )

        # ----------------------------------------------------
        # Create normal DISHA session + JWTs
        # ----------------------------------------------------

        ip = get_client_ip(request)
        user_agent = get_user_agent(request)

        access_token, refresh_token, user_dict = (
            await _auth_service.login_with_oauth(
                user=user,
                ip=ip,
                user_agent=user_agent,
            )
        )

        # ----------------------------------------------------
        # Set normal DISHA refresh cookie
        # ----------------------------------------------------

        set_refresh_cookie(
            response,
            refresh_token,
        )

        # ----------------------------------------------------
        # Redirect to frontend
        # ----------------------------------------------------

        frontend_url = settings.FRONTEND_URL.rstrip("/")

        redirect_url = (
            f"{frontend_url}"
            f"/auth/google/success"
            f"?access_token={access_token}"
        )

        return RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND,
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Google OAuth authentication failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication failed.",
        )

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
async def verify_email(req: VerifyEmailRequest):
    """
    Verifies user's email address using the supplied 6-digit OTP.
    """

    result = await _auth_service.verify_email(
        email=req.email,
        otp=req.otp,
    )

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