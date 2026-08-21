"""
DISHA Platform - Async & Sync Database Management Layer
Disaster Intelligence and Situational Hazard Awareness Platform

Provides Motor async client/database for FastAPI routes and operations,
along with database index initialization and collection helpers.
"""

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.config import settings

logger = logging.getLogger("disha.core.database")

import asyncio

# Global clients and database handles
_async_client: Optional[AsyncIOMotorClient] = None
_async_db: Optional[AsyncIOMotorDatabase] = None
_async_client_loop: Optional[asyncio.AbstractEventLoop] = None
_sync_client: Optional[MongoClient] = None


def get_async_client() -> AsyncIOMotorClient:
    global _async_client, _async_client_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _async_client is None or _async_client_loop != current_loop or (current_loop and current_loop.is_closed()):
        _async_client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000,
        )
        _async_client_loop = current_loop
    return _async_client


def get_async_db() -> AsyncIOMotorDatabase:
    global _async_db
    client = get_async_client()
    return client[settings.MONGO_DB]


def get_sync_client() -> MongoClient:
    global _sync_client
    if _sync_client is None:
        _sync_client = MongoClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000,
        )
    return _sync_client


def get_sync_db():
    return get_sync_client()[settings.MONGO_DB]


async def init_auth_indexes(db: Optional[AsyncIOMotorDatabase] = None):
    """
    Initializes indexes for authentication, session lifecycle, and OTP management.
    Handles duplicate index warnings gracefully.
    """
    if db is None:
        db = get_async_db()

    try:
        # 1. Users collection indexes
        await db["users"].create_index(
            [("email", ASCENDING)],
            unique=True,
            background=True,
            name="uniq_users_email",
        )
        await db["users"].create_index(
            [("username", ASCENDING)],
            unique=True,
            background=True,
            name="uniq_users_username",
        )
        await db["users"].create_index(
            [("created_at", DESCENDING)],
            background=True,
        )
        await db["users"].create_index(
            [("verified", ASCENDING)],
            background=True,
        )

        # 2. Sessions collection indexes
        await db["sessions"].create_index(
            [("user_id", ASCENDING)],
            background=True,
            name="idx_sessions_user_id",
        )
        await db["sessions"].create_index(
            [("refresh_token_hash", ASCENDING)],
            background=True,
            name="idx_sessions_token_hash",
        )
        await db["sessions"].create_index(
            [("revoked", ASCENDING)],
            background=True,
        )
        await db["sessions"].create_index(
            [("last_used_at", DESCENDING)],
            background=True,
        )
        await db["sessions"].create_index(
            [("created_at", DESCENDING)],
            background=True,
        )

        # 3. OTPs collection indexes
        await db["otps"].create_index(
            [("email", ASCENDING)],
            background=True,
            name="idx_otps_email",
        )
        await db["otps"].create_index(
            [("user_id", ASCENDING)],
            background=True,
            name="idx_otps_user_id",
        )
        await db["otps"].create_index(
            [("created_at", DESCENDING)],
            background=True,
        )
        # TTL Index: MongoDB automatically removes expired OTP documents
        await db["otps"].create_index(
            [("expires_at", ASCENDING)],
            expireAfterSeconds=0,
            background=True,
            name="idx_otps_ttl",
        )

        logger.info("[Database] Auth indexes created/verified successfully.")
    except PyMongoError as err:
        logger.warning(f"[Database] Auth index initialization notice: {err}")
    except Exception as err:
        logger.warning(f"[Database] Unexpected index setup notice: {err}")


async def init_incident_indexes(db: Optional[AsyncIOMotorDatabase] = None):
    """
    Initializes indexes for the incident_reports collection.
    Idempotent and safe: preserves existing data and handles index creation gracefully.
    """
    if db is None:
        db = get_async_db()

    try:
        # 4. Incident Reports collection indexes
        await db["incident_reports"].create_index([("report_id", ASCENDING)], unique=True, background=True)
        await db["incident_reports"].create_index([("user_id", ASCENDING)], background=True)
        await db["incident_reports"].create_index([("event_type", ASCENDING)], background=True)
        await db["incident_reports"].create_index([("status", ASCENDING)], background=True)
        await db["incident_reports"].create_index([("created_at", DESCENDING)], background=True)
        await db["incident_reports"].create_index([("location.coordinates", "2dsphere")], sparse=True, background=True)
        logger.info("[Database] Report Incident collection and indexes verified successfully.")
    except PyMongoError as err:
        logger.warning(f"[Database] Incident index initialization notice: {err}")
    except Exception as err:
        logger.warning(f"[Database] Unexpected incident index setup notice: {err}")


async def close_db_connections():
    """
    Closes async and sync database connections gracefully.
    """
    global _async_client, _async_db, _sync_client
    if _async_client is not None:
        _async_client.close()
        _async_client = None
        _async_db = None
    if _sync_client is not None:
        _sync_client.close()
        _sync_client = None
    logger.info("[Database] MongoDB connections closed.")
