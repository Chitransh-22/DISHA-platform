"""
DISHA Platform - OTP Repository Layer
Disaster Intelligence and Situational Hazard Awareness Platform

Encapsulates database operations for verification OTPs and pending registrations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_async_db


class OTPRepository:
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db if self._db is not None else get_async_db()

    @property
    def collection(self):
        return self.db["otps"]

    @staticmethod
    def _format_otp(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        doc = dict(doc)
        if "_id" in doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def create_otp(
        self,
        email: str,
        user_id: Optional[str],
        otp_hash: str,
        expires_at: datetime,
        registration_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clean_email = email.strip().lower()
        # Invalidate/cleanup old OTPs for this email first
        await self.collection.delete_many({"email": clean_email})

        now = datetime.now(timezone.utc)
        doc = {
            "email": clean_email,
            "user_id": str(user_id) if user_id else None,
            "otp_hash": otp_hash,
            "expires_at": expires_at,
            "attempts": 0,
            "created_at": now,
        }
        if registration_data:
            doc["registration_data"] = registration_data

        result = await self.collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        doc["_id"] = result.inserted_id
        return self._format_otp(doc)

    async def get_active_otp(self, email: str) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        now = datetime.now(timezone.utc)
        # Find latest unexpired OTP
        doc = await self.collection.find_one(
            {"email": clean_email, "expires_at": {"$gte": now}},
            sort=[("created_at", -1)],
        )
        return self._format_otp(doc)

    async def get_pending_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        clean_user = username.strip().lower()
        now = datetime.now(timezone.utc)
        doc = await self.collection.find_one(
            {
                "registration_data.username": clean_user,
                "expires_at": {"$gte": now},
            },
            sort=[("created_at", -1)],
        )
        return self._format_otp(doc)

    async def update_otp_code(
        self,
        email: str,
        otp_hash: str,
        expires_at: datetime,
    ) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        now = datetime.now(timezone.utc)
        result = await self.collection.find_one_and_update(
            {"email": clean_email},
            {
                "$set": {
                    "otp_hash": otp_hash,
                    "expires_at": expires_at,
                    "attempts": 0,
                    "updated_at": now,
                }
            },
            return_document=True,
        )
        return self._format_otp(result)

    async def increment_attempts(self, otp_id: str) -> int:
        try:
            query = {"_id": ObjectId(otp_id)}
        except Exception:
            query = {"_id": otp_id}

        result = await self.collection.find_one_and_update(
            query,
            {"$inc": {"attempts": 1}},
            return_document=True,
        )
        if result:
            return result.get("attempts", 1)
        return 1

    async def delete_otp(self, otp_id: str) -> bool:
        try:
            query = {"_id": ObjectId(otp_id)}
        except Exception:
            query = {"_id": otp_id}
        result = await self.collection.delete_one(query)
        return result.deleted_count > 0

    async def delete_otps_for_email(self, email: str) -> int:
        clean_email = email.strip().lower()
        result = await self.collection.delete_many({"email": clean_email})
        return result.deleted_count
