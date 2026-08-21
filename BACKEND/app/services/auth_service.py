"""
DISHA Platform - Main Authentication Service Layer
Disaster Intelligence and Situational Hazard Awareness Platform

Coordinates Google OAuth login, JWT token issuance, session tracking,
refresh token rotation, and logout.
"""

import logging
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, status
from bson import ObjectId

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    hash_token,
)
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger("disha.services.auth")


class AuthService:
    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        session_repo: Optional[SessionRepository] = None,
    ):
        self.user_repo = user_repo or UserRepository()
        self.session_repo = session_repo or SessionRepository()

    async def login_with_oauth(
        self,
        user: Dict[str, Any],
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Creates an active DISHA session and issues access & refresh JWTs
        for an authenticated Google OAuth user.
        """
        user_id = str(user.get("id") or user.get("_id"))
        temp_session_id = str(ObjectId())

        refresh_token = create_refresh_token(
            user_id=user_id,
            session_id=temp_session_id,
        )
        refresh_hash = hash_token(refresh_token)

        # Create session in MongoDB
        session = await self.session_repo.create_session(
            user_id=user_id,
            refresh_token_hash=refresh_hash,
            ip=ip,
            user_agent=user_agent,
        )

        real_session_id = session["id"]

        # Bind tokens to real session ID if different
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
            "username": user.get("username"),
            "email": user.get("email"),
            "verified": user.get("verified", True),
            "auth_provider": user.get("auth_provider", "google"),
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

        # Find active session in database
        session = await self.session_repo.get_active_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or expired. Please sign in again.",
            )

        # Verify refresh token hash matches stored hash (reuse attack detection)
        current_hash = hash_token(refresh_token)
        if session.get("refresh_token_hash") != current_hash:
            # Token reuse detected! Invalidate entire session family for security
            logger.warning(
                "Security alert: Refresh token reuse detected for session %s (user %s). Revoking session.",
                session_id,
                user_id,
            )
            await self.session_repo.revoke_session(session_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security violation: Token reuse detected. Session invalidated. Please sign in again.",
            )

        # Issue rotated refresh token
        new_refresh_token = create_refresh_token(
            user_id=user_id,
            session_id=session_id,
        )
        new_refresh_hash = hash_token(new_refresh_token)

        # Update session with new rotated hash
        await self.session_repo.rotate_refresh_token(
            session_id=session_id,
            new_token_hash=new_refresh_hash,
            ip=ip,
            user_agent=user_agent,
        )

        # Issue new access token
        new_access_token = create_access_token(
            user_id=user_id,
            session_id=session_id,
        )

        return new_access_token, new_refresh_token

    async def logout(self, refresh_token: Optional[str]) -> bool:
        """
        Invalidates current session upon user logout.
        """
        if not refresh_token:
            return True

        try:
            payload = decode_jwt_token(refresh_token, expected_type="refresh")
            session_id = payload.get("session_id")
            if session_id:
                return await self.session_repo.revoke_session(session_id)
        except Exception:
            pass

        return True

    async def logout_all(self, user_id: str) -> int:
        """
        Revokes all active sessions for user across all devices.
        """
        return await self.session_repo.revoke_all_user_sessions(user_id)
