"""
DISHA Platform - User Repository Layer
Disaster Intelligence and Situational Hazard Awareness Platform

Encapsulates all database operations for the users collection.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_async_db


class UserRepository:
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db if self._db is not None else get_async_db()

    @property
    def collection(self):
        return self.db["users"]

    @staticmethod
    def _format_user(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        doc = dict(doc)
        if "_id" in doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(user_id)
            doc = await self.collection.find_one({"_id": oid})
        except Exception:
            doc = await self.collection.find_one({"_id": user_id})
        return self._format_user(doc)

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        if not email:
            return None
        doc = await self.collection.find_one({"email": email.strip().lower()})
        return self._format_user(doc)

    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        if not username:
            return None
        doc = await self.collection.find_one({"username": username.strip().lower()})
        return self._format_user(doc)

    async def get_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Finds user by either email or username."""
        clean = identifier.strip().lower()
        doc = await self.collection.find_one({
            "$or": [{"email": clean}, {"username": clean}]
        })
        return self._format_user(doc)

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(user_data)
        now = datetime.now(timezone.utc)
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        data.setdefault("verified", False)
        if "email" in data:
            data["email"] = data["email"].strip().lower()
        if "username" in data:
            data["username"] = data["username"].strip().lower()

        result = await self.collection.insert_one(data)
        data["id"] = str(result.inserted_id)
        data["_id"] = result.inserted_id
        return self._format_user(data)

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        updates = dict(updates)
        updates["updated_at"] = datetime.now(timezone.utc)
        try:
            query = {"_id": ObjectId(user_id)}
        except Exception:
            query = {"_id": user_id}

        await self.collection.update_one(query, {"$set": updates})
        return await self.get_by_id(user_id)

    async def mark_verified(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.update_user(user_id, {"verified": True})
