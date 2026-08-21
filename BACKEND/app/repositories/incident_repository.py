"""
DISHA Platform - Incident Repository Layer
Disaster Intelligence and Situational Hazard Awareness Platform

Encapsulates all database operations for the incident_reports collection.
"""

from datetime import datetime, timezone
import secrets
from typing import Any, Dict, List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_async_db


class IncidentRepository:
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db if self._db is not None else get_async_db()

    @property
    def collection(self):
        return self.db["incident_reports"]

    @staticmethod
    def _format_report(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        doc = dict(doc)
        if "_id" in doc:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
        if "created_at" in doc and isinstance(doc["created_at"], datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        if "updated_at" in doc and isinstance(doc["updated_at"], datetime):
            doc["updated_at"] = doc["updated_at"].isoformat()
        return doc

    async def create_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new incident report document in MongoDB."""
        data = dict(report_data)
        now = datetime.now(timezone.utc)
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        data.setdefault("status", "submitted")

        # Generate human-readable report_id if missing (e.g. INC-681923)
        if "report_id" not in data or not data["report_id"]:
            data["report_id"] = f"INC-{secrets.randbelow(900000) + 100000}"

        result = await self.collection.insert_one(data)
        data["_id"] = result.inserted_id
        data["id"] = str(result.inserted_id)
        return self._format_report(data)

    async def get_by_id(self, report_id_or_oid: str) -> Optional[Dict[str, Any]]:
        """Finds report by report_id (e.g. INC-123456) or MongoDB ObjectId."""
        doc = await self.collection.find_one({"report_id": report_id_or_oid})
        if not doc:
            try:
                doc = await self.collection.find_one({"_id": ObjectId(report_id_or_oid)})
            except Exception:
                doc = await self.collection.find_one({"_id": report_id_or_oid})
        return self._format_report(doc)

    async def get_user_reports(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves reports submitted by a specific user."""
        cursor = self.collection.find({"user_id": str(user_id)}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self._format_report(d) for d in docs]

    async def get_recent_reports(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves recent incident reports."""
        cursor = self.collection.find().sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self._format_report(d) for d in docs]
