"""
DISHA Platform - MongoDB Distributed Locking Service
Disaster Intelligence and Situational Hazard Awareness Platform

Guarantees mutual exclusion for scheduled and manual ingestion pipelines across
multiple backend replicas, worker processes, and containers.
Prevents overlapping job executions.
"""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Any, Dict

from pymongo.collection import Collection
from app.database.mongodb import db

logger = logging.getLogger("disha.distributed_lock")

LOCKS_COLLECTION = "ingestion_locks"


def get_locks_collection() -> Collection:
    return db[LOCKS_COLLECTION]


def to_utc(dt: Any) -> Optional[datetime]:
    """Ensures datetime is offset-aware in UTC. Accepts datetime, ISO string, or None."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def init_lock_indexes():
    """Ensure indexes on lock collection including TTL expiration safeguard."""
    try:
        col = get_locks_collection()
        col.create_index("lock_name", unique=True)
        col.create_index("expires_at")
    except Exception as e:
        logger.warning(f"[DistributedLock] Notice initializing lock indexes: {e}")


class DistributedLock:
    """
    Deployment-safe distributed lock implemented with MongoDB atomic find_one_and_update.
    Safe against process crashes via lease expiration (default: 30 minutes).
    """

    def __init__(
        self,
        lock_name: str,
        lease_seconds: int = 1800,
        owner_id: Optional[str] = None,
    ):
        self.lock_name = lock_name
        self.lease_seconds = lease_seconds
        self.owner_id = owner_id or f"{os.getpid()}_{uuid.uuid4().hex[:8]}"
        self.acquired = False

    @property
    def is_acquired(self) -> bool:
        return self.acquired

    def acquire(self) -> bool:
        """
        Attempts to acquire the lock atomically.
        Succeeds if:
        1. Lock document does not exist (created via upsert).
        2. Lock document exists but has expired.
        3. Lock is already held by this same owner.
        """
        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(seconds=self.lease_seconds)
        col = get_locks_collection()

        try:
            # First check if document exists
            existing = col.find_one({"lock_name": self.lock_name})
            if existing:
                is_locked = existing.get("is_locked", False)
                exp_dt = to_utc(existing.get("expires_at"))
                is_expired = exp_dt is not None and exp_dt < now_utc
                same_owner = existing.get("owner_id") == self.owner_id

                if is_locked and not is_expired and not same_owner:
                    logger.info(f"[DistributedLock] Lock '{self.lock_name}' is currently held by {existing.get('owner_id')}. Skipping.")
                    self.acquired = False
                    return False

            # Atomically claim the lock
            res = col.find_one_and_update(
                {
                    "lock_name": self.lock_name,
                    "$or": [
                        {"expires_at": {"$lt": now_utc}},
                        {"owner_id": self.owner_id},
                        {"is_locked": False},
                    ],
                },
                {
                    "$set": {
                        "lock_name": self.lock_name,
                        "is_locked": True,
                        "owner_id": self.owner_id,
                        "acquired_at": now_utc,
                        "expires_at": expires_at,
                        "lease_seconds": self.lease_seconds,
                        "updated_at": now_utc,
                    }
                },
                return_document=True,
            )

            if res:
                self.acquired = True
                logger.debug(f"[DistributedLock] Acquired existing lock '{self.lock_name}' by {self.owner_id}")
                return True

            # If document did not exist, insert atomically
            if not existing:
                try:
                    col.insert_one({
                        "lock_name": self.lock_name,
                        "is_locked": True,
                        "owner_id": self.owner_id,
                        "acquired_at": now_utc,
                        "expires_at": expires_at,
                        "lease_seconds": self.lease_seconds,
                        "updated_at": now_utc,
                    })
                    self.acquired = True
                    logger.debug(f"[DistributedLock] Created & acquired new lock '{self.lock_name}' by {self.owner_id}")
                    return True
                except Exception:
                    pass

            self.acquired = False
            return False

        except Exception as err:
            logger.error(f"[DistributedLock] Error acquiring lock '{self.lock_name}': {err}")
            self.acquired = False
            return False

    def release(self) -> bool:
        """Releases the lock if held by this owner."""
        if not self.acquired:
            return True

        col = get_locks_collection()
        try:
            res = col.find_one_and_update(
                {"lock_name": self.lock_name, "owner_id": self.owner_id},
                {
                    "$set": {
                        "is_locked": False,
                        "released_at": datetime.now(timezone.utc),
                        "owner_id": None,
                    }
                },
            )
            self.acquired = False
            logger.debug(f"[DistributedLock] Released lock '{self.lock_name}' by {self.owner_id}")
            return bool(res)
        except Exception as err:
            logger.error(f"[DistributedLock] Error releasing lock '{self.lock_name}': {err}")
            return False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def check_lock_status(lock_name: str) -> Dict[str, Any]:
    """Returns the current state of a lock for observability."""
    col = get_locks_collection()
    now_utc = datetime.now(timezone.utc)
    try:
        doc = col.find_one({"lock_name": lock_name})
        if not doc:
            return {"lock_name": lock_name, "is_locked": False, "status": "free"}

        is_locked = doc.get("is_locked", False)
        expires_at = to_utc(doc.get("expires_at"))
        if is_locked and expires_at and expires_at < now_utc:
            is_locked = False

        return {
            "lock_name": lock_name,
            "is_locked": is_locked,
            "owner_id": doc.get("owner_id") if is_locked else None,
            "acquired_at": doc.get("acquired_at"),
            "expires_at": doc.get("expires_at"),
            "status": "locked" if is_locked else "free",
        }
    except Exception as err:
        return {"lock_name": lock_name, "error": str(err), "is_locked": False}


def force_release_lock(lock_name: str) -> bool:
    """Administrative force unlock in case of manual override."""
    col = get_locks_collection()
    try:
        col.update_one(
            {"lock_name": lock_name},
            {"$set": {"is_locked": False, "owner_id": None, "released_at": datetime.now(timezone.utc)}},
        )
        logger.info(f"[DistributedLock] Force-released lock '{lock_name}'")
        return True
    except Exception as err:
        logger.error(f"[DistributedLock] Error force-releasing lock '{lock_name}': {err}")
        return False
