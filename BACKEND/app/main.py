"""
DISHA Platform - Main FastAPI Application
Disaster Intelligence and Situational Hazard Awareness Platform

Main application factory, middleware, router aggregation, and lifecycle hooks.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from starlette.middleware.sessions import SessionMiddleware

# Ensure backend root is in sys.path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import close_db_connections, get_async_db, init_auth_indexes
from app.database.mongodb import init_db_indexes
import app.database.mongodb as sync_mongodb

# Import all route modules
from app.routes.auth import router as auth_router
from app.routes.events import router as events_router
from app.routes.emergency_services import router as emergency_services_router
from app.routes.gnews import router as news_router
from app.routes.earthquakes import router as earthquakes_router
from app.routes.sachet import router as sachet_router
from app.routes.analysis import router as analysis_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("disha.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for async startup and teardown.
    """
    logger.info(f"Initializing {settings.PROJECT_NAME} in [{settings.ENVIRONMENT}] mode...")
    try:
        # Initialize async database indexes
        async_db = get_async_db()
        await init_auth_indexes(async_db)
        # Initialize sync collections indexes for legacy pipelines
        sync_db = sync_mongodb.db
        init_db_indexes(sync_db)
        logger.info("[Database] All MongoDB indexes verified successfully.")
    except Exception as e:
        logger.warning(f"[Database] Notice during database initialization: {e}")

    yield

    logger.info("Shutting down DISHA Backend API...")
    await close_db_connections()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET,
    session_cookie="disha_oauth_session",
    https_only=settings.COOKIE_SECURE,
    same_site=settings.COOKIE_SAMESITE,
)

# CORS Configuration
origins = settings.cors_origins_list
logger.info(f"Configured CORS allowed origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register All API Routers
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(emergency_services_router)
app.include_router(news_router)
app.include_router(earthquakes_router)
app.include_router(sachet_router)
app.include_router(analysis_router)


@app.get("/", tags=["General"], summary="Root Health & API Overview")
async def root():
    return {
        "status": "ok",
        "service": "DISHA Backend",
        "message": "DISHA Disaster Intelligence Platform API is running",
        "docs": "/docs",
        "health": "/health",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["Health"], summary="Health Check")
@app.get("/api/health", tags=["Health"], summary="API Health Check")
@app.head("/api/health", tags=["Health"], summary="API Health Check")
@app.head("/health", tags=["Health"], summary="API Health Check")


async def health():
    return {
        "status": "ok",
        "service": "DISHA Backend",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=not settings.is_production,
    )
