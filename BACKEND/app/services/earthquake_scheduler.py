"""
DISHA Platform - NCS RISEQ Earthquake Background Scheduler
Provides non-blocking periodic background synchronization of earthquake data from NCS RISEQ.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Ensure .env is loaded and backend directory in sys.path for direct CLI execution
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

load_dotenv(_backend_dir / ".env")
load_dotenv()

from app.services.earthquake_service import sync_earthquakes_pipeline

logger = logging.getLogger("disha.scheduler.riseq")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

RISEQ_ENABLED = os.getenv("RISEQ_ENABLED", "false").lower() in ("true", "1", "yes")
RISEQ_SYNC_INTERVAL = int(os.getenv("RISEQ_SYNC_INTERVAL", "300"))  # Default: 300 seconds (5 minutes)
RISEQ_INITIAL_DELAY = int(os.getenv("RISEQ_INITIAL_DELAY", "5"))   # 5s startup delay

_scheduler_task: Optional[asyncio.Task] = None
_is_running = False


async def _earthquake_sync_loop():
    """Background async worker loop for polling NCS RISEQ."""
    global _is_running
    logger.info(f"[RISEQ Scheduler] Started. Polling interval: {RISEQ_SYNC_INTERVAL}s (Enabled: {RISEQ_ENABLED})")

    # Initial warm-up delay before first sync
    if RISEQ_INITIAL_DELAY > 0:
        await asyncio.sleep(RISEQ_INITIAL_DELAY)

    while _is_running:
        if RISEQ_ENABLED:
            try:
                # Run sync in thread pool to avoid blocking the asyncio event loop
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, sync_earthquakes_pipeline)
            except Exception as err:
                logger.error(f"[RISEQ Scheduler] Unexpected error in sync cycle: {err}", exc_info=True)

        try:
            await asyncio.sleep(RISEQ_SYNC_INTERVAL)
        except asyncio.CancelledError:
            logger.info("[RISEQ Scheduler] Task cancelled, exiting loop.")
            break


def start_earthquake_scheduler():
    """Starts the periodic background earthquake sync task."""
    global _scheduler_task, _is_running
    if not RISEQ_ENABLED:
        logger.info("[RISEQ Scheduler] Disabled via RISEQ_ENABLED configuration.")
        return

    if _scheduler_task is None or _scheduler_task.done():
        _is_running = True
        _scheduler_task = asyncio.create_task(_earthquake_sync_loop())
        logger.info("[RISEQ Scheduler] Background worker task initiated.")


def stop_earthquake_scheduler():
    """Cancels and stops the periodic background earthquake sync task."""
    global _scheduler_task, _is_running
    _is_running = False
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("[RISEQ Scheduler] Background worker task stopped.")
