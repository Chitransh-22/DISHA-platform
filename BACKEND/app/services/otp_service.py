"""
DISHA Platform - OTP Business Logic & Verification Service
Disaster Intelligence and Situational Hazard Awareness Platform

Coordinates OTP generation, HMAC hashing, email dispatch, attempt rate-limiting,
and constant-time verification.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import generate_secure_otp, hash_otp, verify_otp_hash
from app.repositories.otp_repository import OTPRepository
from app.services.email_service import send_verification_email

logger = logging.getLogger("disha.services.otp")


class OTPService:
    def __init__(self, otp_repo: Optional[OTPRepository] = None):
        self.otp_repo = otp_repo or OTPRepository()

    async def create_and_send_otp(
        self,
        email: str,
        user_id: str,
        username: Optional[str] = None,
    ) -> bool:
        """
        Generates a 6-digit secure OTP, hashes it, stores it in MongoDB with 10-minute expiry,
        and sends the verification email.
        """
        clean_email = email.strip().lower()
        plain_otp = generate_secure_otp(length=settings.OTP_LENGTH)
        hashed_otp = hash_otp(plain_otp, clean_email)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        # Store in MongoDB (automatically invalidates any older OTP for this email)
        await self.otp_repo.create_otp(
            email=clean_email,
            user_id=str(user_id),
            otp_hash=hashed_otp,
            expires_at=expires_at,
        )

        # Dispatch verification email
        email_sent = await send_verification_email(
            email=clean_email,
            otp=plain_otp,
            username=username,
        )
        return email_sent

    async def verify_otp(
        self,
        email: str,
        plain_otp: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verifies the user-supplied OTP:
        - Checks active OTP exists
        - Checks expiration
        - Increments and enforces maximum attempts (5 attempts max)
        - Constant-time hash verification
        - Cleans up OTP on success

        Returns: (is_valid: bool, error_message: Optional[str], user_id: Optional[str])
        """
        clean_email = email.strip().lower()
        otp_doc = await self.otp_repo.get_active_otp(clean_email)

        if not otp_doc:
            return False, "Verification code has expired or was not requested. Please request a new code.", None

        # Check maximum verification attempts to prevent brute-forcing
        attempts = otp_doc.get("attempts", 0)
        if attempts >= settings.OTP_MAX_ATTEMPTS:
            await self.otp_repo.delete_otp(otp_doc["id"])
            return False, "Too many failed attempts. This verification code is now invalidated. Please request a new one.", None

        # Increment attempt counter
        await self.otp_repo.increment_attempts(otp_doc["id"])

        # Check expiration
        expires_at = otp_doc["expires_at"]
        if isinstance(expires_at, datetime):
            # Ensure timezone awareness
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                await self.otp_repo.delete_otp(otp_doc["id"])
                return False, "Verification code has expired. Please request a new code.", None

        # Constant-time comparison
        is_match = verify_otp_hash(
            plain_otp=plain_otp,
            email=clean_email,
            stored_hash=otp_doc["otp_hash"],
        )

        if not is_match:
            remaining = settings.OTP_MAX_ATTEMPTS - (attempts + 1)
            if remaining <= 0:
                await self.otp_repo.delete_otp(otp_doc["id"])
                return False, "Incorrect verification code. Maximum attempts exceeded. Please request a new code.", None
            return False, f"Incorrect verification code. {remaining} attempt(s) remaining.", None

        # Success: Delete OTP document and return user_id
        await self.otp_repo.delete_otp(otp_doc["id"])
        return True, None, otp_doc.get("user_id")
