"""
DISHA Platform - Session Repository Layer
Disaster Intelligence and Situational Hazard Awareness Platform

Encapsulates database operations for active, rotated, and revoked user sessions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_async_db


class SessionRepository:
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db if self._db is not None else get_async_db()

    @property
    def collection(self):
        return self.db["sessions"]

    @staticmethod
    def _format_session(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        doc = dict(doc)
        if "_id" in doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def create_session(
        self,
        user_id: str,
        refresh_token_hash: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": str(user_id),
            "refresh_token_hash": refresh_token_hash,
            "ip": ip,
            "user_agent": user_agent,
            "revoked": False,
            "created_at": now,
            "updated_at": now,
            "last_used_at": now,
        }
        result = await self.collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        doc["_id"] = result.inserted_id
        return self._format_session(doc)

    async def get_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(session_id)
            doc = await self.collection.find_one({"_id": oid})
        except Exception:
            doc = await self.collection.find_one({"_id": session_id})
        return self._format_session(doc)

    async def get_active_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            query = {"_id": ObjectId(session_id), "revoked": False}
        except Exception:
            query = {"_id": session_id, "revoked": False}
        doc = await self.collection.find_one(query)
        return self._format_session(doc)

    async def rotate_refresh_token(
        self,
        session_id: str,
        new_token_hash: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        updates: Dict[str, Any] = {
            "refresh_token_hash": new_token_hash,
            "updated_at": now,
            "last_used_at": now,
        }
        if ip:
            updates["ip"] = ip
        if user_agent:
            updates["user_agent"] = user_agent

        try:
            query = {"_id": ObjectId(session_id), "revoked": False}
        except Exception:
            query = {"_id": session_id, "revoked": False}

        result = await self.collection.update_one(query, {"$set": updates})
        if result.modified_count == 0:
            return None
        return await self.get_by_id(session_id)

    async def revoke_session(self, session_id: str) -> bool:
        now = datetime.now(timezone.utc)
        try:
            query = {"_id": ObjectId(session_id)}
        except Exception:
            query = {"_id": session_id}
        result = await self.collection.update_one(
            query,
            {"$set": {"revoked": True, "updated_at": now}},
        )
        return result.modified_count > 0

    async def revoke_all_user_sessions(self, user_id: str) -> int:
        now = datetime.now(timezone.utc)
        result = await self.collection.update_many(
            {"user_id": str(user_id), "revoked": False},
            {"$set": {"revoked": True, "updated_at": now}},
        )
        return result.modified_count

    async def get_user_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"user_id": str(user_id), "revoked": False}).sort(
            "last_used_at", -1
        )
        docs = await cursor.to_list(length=100)
        return [self._format_session(d) for d in docs]
