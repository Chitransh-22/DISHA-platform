"""
DISHA Platform - Root Entrypoint Wrapper
Disaster Intelligence and Situational Hazard Awareness Platform

Delegates to app.main:app for unified production-grade architecture.
"""

import os
import sys
from pathlib import Path

# Ensure root backend directory is in sys.path
_backend_dir = Path(__file__).resolve().parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import uvicorn
from app.core.config import settings
from app.main import app

if __name__ == "__main__":
    host = settings.HOST
    port = settings.PORT
    reload = not settings.is_production

    print(f"Starting DISHA Backend server at http://{host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
    )