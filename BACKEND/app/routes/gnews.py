import sys
from pathlib import Path
from typing import Optional

# Ensure backend root is always in sys.path regardless of execution directory
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")
load_dotenv()

from fastapi import APIRouter, BackgroundTasks, Query

from app.database.mongodb import db
from app.services.fetch_gnews import fetch_gnews

router = APIRouter(
    prefix="/api/news",
    tags=["News"]
)

disaster_events = db["disaster_events"]
rejected_news = db["rejected_news"]
news_temp = db["news_temp"]
ai_usage = db["ai_usage"]


@router.post("/fetch")
async def fetch_news_route(
    background_tasks: BackgroundTasks
):
    """
    Trigger the real-time Google News fetching and AI classification pipeline in background.
    """
    background_tasks.add_task(fetch_gnews)
    return {
        "status": "started",
        "message": "News fetching and disaster classification started in background"
    }


@router.get("/disasters")
async def get_disasters(
    disaster_type: Optional[str] = Query(None, description="Filter by disaster type (e.g. flood, landslide)"),
    state: Optional[str] = Query(None, description="Filter by state name"),
    severity: Optional[str] = Query(None, description="Filter by severity (critical, high, medium, low)"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    skip: int = Query(0, ge=0, description="Records to skip"),
):
    """
    Retrieve classified disaster events stored in the database.
    """
    query = {}
    if isinstance(disaster_type, str) and disaster_type:
        query["disaster_type"] = disaster_type.lower()
    if isinstance(state, str) and state:
        query["location.state"] = {"$regex": state, "$options": "i"}
    if isinstance(severity, str) and severity:
        query["severity"] = severity.lower()

    lim = limit if isinstance(limit, int) else 50
    skp = skip if isinstance(skip, int) else 0

    cursor = disaster_events.find(query, {"_id": 0}).sort("processed_at", -1).skip(skp).limit(lim)
    events = list(cursor)
    total = disaster_events.count_documents(query)

    return {
        "total": total,
        "count": len(events),
        "disasters": events,
    }


@router.get("/rejected")
async def get_rejected_news(
    stage: Optional[str] = Query(None, description="Filter by stage (local, quality, ai, temporal_old, forecast)"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    """
    Retrieve news articles filtered out and rejected by local heuristics, quality/recency, or AI.
    """
    query = {}
    if isinstance(stage, str) and stage:
        query["stage"] = stage.lower()

    lim = limit if isinstance(limit, int) else 50
    skp = skip if isinstance(skip, int) else 0

    cursor = rejected_news.find(query, {"_id": 0}).sort("processed_at", -1).skip(skp).limit(lim)
    items = list(cursor)
    total = rejected_news.count_documents(query)

    return {
        "total": total,
        "count": len(items),
        "rejected": items,
    }


@router.get("/stats")
async def get_pipeline_stats():
    """
    Get live overview stats of processed disasters, rejections, pending AI queue, and AI usage.
    """
    total_disasters = disaster_events.count_documents({})
    total_rejected = rejected_news.count_documents({})
    local_rejected = rejected_news.count_documents({"stage": "local"})
    quality_rejected = rejected_news.count_documents({"stage": "quality"})
    ai_rejected = rejected_news.count_documents({"stage": "ai"})
    temporal_rejected = rejected_news.count_documents({"stage": "temporal_old"})
    forecast_rejected = rejected_news.count_documents({"stage": "forecast"})
    pending_ai = news_temp.count_documents({"status": "pending_ai"})
    total_temp = news_temp.count_documents({})

    return {
        "verified_disasters": total_disasters,
        "total_rejected": total_rejected,
        "rejected_by_local_filter": local_rejected,
        "rejected_by_quality_filter": quality_rejected,
        "rejected_by_ai": ai_rejected,
        "rejected_old_news": temporal_rejected,
        "rejected_forecast_only": forecast_rejected,
        "pending_ai_queue": pending_ai,
        "total_articles_seen": total_temp,
    }