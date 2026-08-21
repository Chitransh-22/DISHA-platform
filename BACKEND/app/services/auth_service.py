"""
DISHA Platform - Main Authentication Service Layer
Disaster Intelligence and Situational Hazard Awareness Platform

Coordinates user registration, Argon2id password hashing, email verification,
login, token issuance, session tracking, refresh token rotation, and logout.
"""

import logging
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.repositories.otp_repository import OTPRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.otp_service import OTPService

logger = logging.getLogger("disha.services.auth")


class AuthService:
    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        session_repo: Optional[SessionRepository] = None,
        otp_service: Optional[OTPService] = None,
    ):
        self.user_repo = user_repo or UserRepository()
        self.session_repo = session_repo or SessionRepository()
        self.otp_service = otp_service or OTPService()

    async def register(
        self,
        email: str,
        password: str,
        username: Optional[str] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        city: Optional[str] = None,
        pincode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registers a new user account:
        - Validates password strength
        - Validates username/email uniqueness
        - Hashes password with Argon2id
        - Creates unverified user document
        - Generates, hashes, stores OTP and sends email
        """
        clean_email = email.strip().lower()

        # Generate default username from email if not provided
        if not username or not username.strip():
            local_part = clean_email.split("@")[0]
            clean_username = "".join(c for c in local_part if c.isalnum() or c in "_-.")[:30]
        else:
            clean_username = username.strip().lower()

        # 1. Validate password strength
        is_valid_pass, pass_err = validate_password_strength(password)
        if not is_valid_pass:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=pass_err,
            )

        # 2. Check email uniqueness
        existing_email = await self.user_repo.get_by_email(clean_email)
        if existing_email:
            # If user already exists and is unverified, resend OTP instead of failing hard
            if not existing_email.get("verified", False):
                await self.otp_service.create_and_send_otp(
                    email=clean_email,
                    user_id=existing_email["id"],
                    username=existing_email.get("username", clean_username),
                )
                return {
                    "message": "Account already registered but not verified. A fresh OTP has been sent to your email.",
                    "user_id": existing_email["id"],
                    "email": clean_email,
                    "verified": False,
                }
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists.",
            )

        # 3. Check username uniqueness
        existing_username = await self.user_repo.get_by_username(clean_username)
        if existing_username:
            # Append random digits if fallback username conflicted
            clean_username = f"{clean_username}_{str(int(settings.PORT))[:2]}"
            if await self.user_repo.get_by_username(clean_username):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This username is already taken. Please choose another.",
                )

        # 4. Hash password with Argon2id
        pwd_hash = hash_password(password)

        # 5. Create user document in MongoDB
        user_data = {
            "username": clean_username,
            "email": clean_email,
            "password_hash": pwd_hash,
            "verified": False,
            "name": name.strip() if name else None,
            "phone": phone.strip() if phone else None,
            "city": city.strip() if city else None,
            "pincode": pincode.strip() if pincode else None,
        }

        try:
            created_user = await self.user_repo.create_user(user_data)
        except DuplicateKeyError as e:
            if "email" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An account with this email address already exists.",
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username or email already exists.",
            )

        # 6. Generate and send verification OTP
        await self.otp_service.create_and_send_otp(
            email=clean_email,
            user_id=created_user["id"],
            username=created_user.get("username"),
        )

        return {
            "message": "Registration successful. Please verify your email with the 6-digit OTP sent to your inbox.",
            "user_id": created_user["id"],
            "email": clean_email,
            "username": clean_username,
            "verified": False,
        }

    async def verify_email(
        self,
        email: str,
        otp: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verifies the user's email using the 6-digit OTP,
        marks the user as verified, and creates an authenticated session.
        """
        clean_email = email.strip().lower()
        is_valid, err_msg, user_id = await self.otp_service.verify_otp(
            email=clean_email,
            plain_otp=otp,
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg or "Invalid verification code.",
            )

        # Fetch user
        user = None
        if user_id:
            user = await self.user_repo.get_by_id(user_id)
        if not user:
            user = await self.user_repo.get_by_email(clean_email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account associated with this verification code not found.",
            )

        # Mark user as verified
        updated_user = await self.user_repo.mark_verified(user["id"])

        # Create session + tokens for auto-login
        access_token, refresh_token, user_resp = await self.login_with_oauth(
            user=updated_user,
            ip=ip,
            user_agent=user_agent,
        )

        return {
            "message": "Email verified successfully.",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_resp,
        }

    async def resend_otp(self, email: str) -> Dict[str, Any]:
        """
        Resends a fresh OTP to an existing unverified user.
        """
        clean_email = email.strip().lower()
        user = await self.user_repo.get_by_email(clean_email)
        if not user:
            # Timing attack mitigation: don't reveal email existence
            return {
                "message": "If an unverified account with this email exists, a new verification code has been sent.",
            }

        if user.get("verified", False):
            return {
                "message": "This email address is already verified. You can proceed to sign in.",
            }

        await self.otp_service.create_and_send_otp(
            email=clean_email,
            user_id=user["id"],
            username=user.get("username"),
        )
        return {
            "message": "A new verification code has been sent to your email.",
        }

    async def login(
        self,
        email_or_username: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Authenticates user:
        - Verifies existence
        - Verifies email is verified
        - Verifies password with Argon2id
        - Creates active session in MongoDB
        - Issues Access & Refresh JWTs

        Returns: (access_token, refresh_token, user_dict)
        """
        user = await self.user_repo.get_by_identifier(email_or_username)

        # Constant-time failure message (never reveal if email exists)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        # Verify password
        if not verify_password(password, user.get("password_hash", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        # Verify email verification status
        if not user.get("verified", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your email address has not been verified. Please verify your email before logging in.",
            )

        # Issue tokens and create session
        from bson import ObjectId
        temp_session_id = str(ObjectId())

        refresh_token = create_refresh_token(
            user_id=user["id"],
            session_id=temp_session_id,
        )
        refresh_hash = hash_token(refresh_token)

        # Create session in DB
        session = await self.session_repo.create_session(
            user_id=user["id"],
            refresh_token_hash=refresh_hash,
            ip=ip,
            user_agent=user_agent,
        )
        real_session_id = session["id"]

        # If generated session ID was different, issue real tokens bound to session_id
        if real_session_id != temp_session_id:
            refresh_token = create_refresh_token(
                user_id=user["id"],
                session_id=real_session_id,
            )
            refresh_hash = hash_token(refresh_token)
            await self.session_repo.rotate_refresh_token(
                session_id=real_session_id,
                new_token_hash=refresh_hash,
                ip=ip,
                user_agent=user_agent,
            )

        access_token = create_access_token(
            user_id=user["id"],
            session_id=real_session_id,
        )

        user_resp = {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "verified": user["verified"],
            "name": user.get("name"),
            "phone": user.get("phone"),
            "city": user.get("city"),
            "pincode": user.get("pincode"),
            "created_at": user.get("created_at"),
        }

        return access_token, refresh_token, user_resp

    async def login_with_oauth(
        self,
        user: Dict[str, Any],
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Creates a DISHA session and issues access/refresh JWTs
        for an already-authenticated OAuth user.
        """

        from bson import ObjectId

        user_id = str(user["id"])
        temp_session_id = str(ObjectId())

        refresh_token = create_refresh_token(
            user_id=user_id,
            session_id=temp_session_id,
        )

        refresh_hash = hash_token(refresh_token)

        session = await self.session_repo.create_session(
            user_id=user_id,
            refresh_token_hash=refresh_hash,
            ip=ip,
            user_agent=user_agent,
        )

        real_session_id = session["id"]

        if real_session_id != temp_session_id:
            refresh_token = create_refresh_token(
                user_id=user_id,
                session_id=real_session_id,
            )

            refresh_hash = hash_token(refresh_token)

            await self.session_repo.rotate_refresh_token(
                session_id=real_session_id,
                new_token_hash=refresh_hash,
                ip=ip,
                user_agent=user_agent,
            )

        access_token = create_access_token(
            user_id=user_id,
            session_id=real_session_id,
        )

        user_resp = {
            "id": user_id,
            "username": user["username"],
            "email": user["email"],
            "verified": user.get("verified", True),
            "name": user.get("name"),
            "phone": user.get("phone"),
            "city": user.get("city"),
            "pincode": user.get("pincode"),
            "created_at": user.get("created_at"),
        }

        return access_token, refresh_token, user_resp    

    async def refresh_tokens(
        self,
        refresh_token: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Refreshes access token with Refresh Token Rotation:
        - Validates refresh JWT
        - Locates active session
        - Checks token hash matches
        - Rotates refresh token (generates new refresh JWT)
        - Issues new access token

        Returns: (new_access_token, new_refresh_token)
        """
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token missing from request.",
            )

        try:
            payload = decode_jwt_token(refresh_token, expected_type="refresh")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
            )

        user_id = payload.get("sub")
        session_id = payload.get("session_id")
        if not user_id or not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed token claims.",
            )

        # Find active session
        session = await self.session_repo.get_active_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or expired. Please sign in again.",
            )

        # Verify token hash
        current_hash = hash_token(refresh_token)
        if session.get("refresh_token_hash") != current_hash:
            # Token reuse detected! Revoke session immediately for security
            await self.session_repo.revoke_session(session_id)
            logger.warning(
                f"[Security Alert] Refresh token mismatch/reuse attempt on session {session_id}. Session revoked."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token state detected. Session revoked.",
            )

        # Issue new rotated refresh token & new access token
        new_refresh_token = create_refresh_token(
            user_id=user_id,
            session_id=session_id,
        )
        new_refresh_hash = hash_token(new_refresh_token)

        # Update session with rotated hash
        await self.session_repo.rotate_refresh_token(
            session_id=session_id,
            new_token_hash=new_refresh_hash,
            ip=ip,
            user_agent=user_agent,
        )

        new_access_token = create_access_token(
            user_id=user_id,
            session_id=session_id,
        )

        return new_access_token, new_refresh_token

    async def logout(self, refresh_token: Optional[str] = None) -> bool:
        """
        Revokes the current user session if a valid refresh token is supplied.
        """
        if not refresh_token:
            return True

        try:
            payload = decode_jwt_token(refresh_token, expected_type="refresh")
            session_id = payload.get("session_id")
            if session_id:
                await self.session_repo.revoke_session(session_id)
        except Exception:
            pass

        return True

    async def logout_all(self, user_id: str) -> int:
        """
        Revokes all active sessions for the specified user.
        """
        count = await self.session_repo.revoke_all_user_sessions(user_id)
        logger.info(f"[Auth] Revoked all {count} active sessions for user {user_id}")
        return count
