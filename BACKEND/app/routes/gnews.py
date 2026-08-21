import html
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure backend root is always in sys.path regardless of execution directory
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")
load_dotenv()

from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Query, HTTPException, status

from app.database.mongodb import db
from app.services.fetch_gnews import fetch_gnews
from app.services.events_service import (
    normalize_event_time,
    map_category,
    map_severity,
    map_status,
    parse_time_range_cutoff,
)

router = APIRouter(
    prefix="/api/news",
    tags=["News"]
)

disaster_events = db["disaster_events"]
rejected_news = db["rejected_news"]
news_temp = db["news_temp"]
ai_usage = db["ai_usage"]


def clean_html_text(text: Optional[str]) -> str:
    """
    Cleans raw and escaped HTML tags, unescapes entities, and removes
    residual RSS anchor tags while preserving natural text.
    """
    if not text:
        return ""
    # 1. Unescape HTML entities (&amp;, &quot;, &lt;, &gt;, &#39;, etc.)
    unescaped = html.unescape(str(text))
    # 2. Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", unescaped)
    # 3. Clean up extra whitespace and newlines
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _format_news_summary(doc: dict) -> dict:
    """Formats a disaster news document into a clean, lightweight summary record."""
    iso_dt, epoch_ts, d_str, t_str = normalize_event_time(doc)
    raw_type = doc.get("disaster_type") or doc.get("category") or "Disaster"
    cat_display, cat_slug = map_category(raw_type)
    sev = map_severity(doc.get("severity"))
    stat = map_status(doc.get("status"))

    loc = doc.get("location") or {}
    if isinstance(loc, dict):
        parts = [p for p in [loc.get("city"), loc.get("district"), loc.get("state")] if p]
        loc_str = ", ".join(parts) if parts else (loc.get("country") or "India")
        lat = loc.get("latitude")
        lng = loc.get("longitude")
    else:
        loc_str = str(loc) if loc else "India"
        lat = doc.get("latitude")
        lng = doc.get("longitude")

    doc_id = str(doc.get("_id")) if doc.get("_id") else f"news_{epoch_ts}"
    event_key = doc.get("event_id") or doc.get("article_id") or doc_id

    # Source extraction
    source_name = "Verified Disaster News"
    corroboration = doc.get("corroboration") or {}
    if isinstance(corroboration, dict) and corroboration.get("sources"):
        source_name = corroboration["sources"][0]
    elif doc.get("source"):
        source_name = doc["source"]

    raw_desc = doc.get("description") or doc.get("content") or ""
    clean_desc = clean_html_text(raw_desc)
    clean_title = clean_html_text(doc.get("title") or f"{cat_display} Report")

    return {
        "id": event_key,
        "event_id": event_key,
        "db_id": doc_id,
        "title": clean_title,
        "summary": clean_desc[:280] if clean_desc else f"{cat_display} situation report in {loc_str}.",
        "category": cat_display,
        "category_slug": cat_slug,
        "severity": sev,
        "status": stat,
        "source": source_name,
        "source_url": doc.get("url") or doc.get("source_url") or "",
        "image": doc.get("image") or None,
        "location": loc_str,
        "state": loc.get("state") if isinstance(loc, dict) else "",
        "district": loc.get("district") if isinstance(loc, dict) else "",
        "latitude": lat,
        "longitude": lng,
        "date": d_str,
        "time": t_str,
        "datetime": iso_dt,
        "timestamp": epoch_ts,
    }


def _format_news_detail(doc: dict) -> dict:
    """Formats a disaster news document into a complete, comprehensive detail view."""
    summary = _format_news_summary(doc)
    loc = doc.get("location") or {}

    raw_full_desc = doc.get("description") or ""
    raw_full_content = doc.get("content") or doc.get("full_text") or doc.get("description") or ""

    summary.update({
        "full_description": clean_html_text(raw_full_desc),
        "full_content": clean_html_text(raw_full_content),
        "incident_date": doc.get("incident_date") or summary["date"],
        "processed_at": doc.get("processed_at"),
        "published_at": doc.get("published_at"),
        "classification": doc.get("classification") or {},
        "corroboration": doc.get("corroboration") or {},
        "raw_location": loc if isinstance(loc, dict) else {},
        "metadata": {
            "confidence": doc.get("confidence") or (doc.get("classification", {}).get("confidence") if isinstance(doc.get("classification"), dict) else None),
            "tier": doc.get("classification", {}).get("tier") if isinstance(doc.get("classification"), dict) else None,
            "article_type": doc.get("classification", {}).get("article_type") if isinstance(doc.get("classification"), dict) else None,
        }
    })
    return summary


@router.get("/sources", summary="Get distinct active news and alert sources")
async def get_news_sources() -> Dict[str, Any]:
    """
    Returns the distinct list of real news and alert sources present in the database.
    """
    try:
        sources_set = set()
        
        # 1. Distinct sources from disaster_events
        for doc in disaster_events.find({}, {"source": 1, "corroboration.sources": 1}).limit(500):
            if doc.get("source"):
                sources_set.add(doc["source"].strip())
            corrob = doc.get("corroboration")
            if isinstance(corrob, dict) and corrob.get("sources"):
                for s in corrob["sources"]:
                    if s and isinstance(s, str):
                        sources_set.add(s.strip())

        # Filter out empty or whitespace-only strings
        sources_list = sorted([s for s in sources_set if s])
        
        # If list is empty, default to primary official streams
        if not sources_list:
            sources_list = ["NDMA SACHET", "NCS Seismology", "Verified Disaster News"]

        return {
            "status": "success",
            "total": len(sources_list),
            "sources": sources_list,
        }
    except Exception as e:
        return {
            "status": "error",
            "sources": ["All Sources", "NDMA SACHET", "NCS Seismology", "Verified Disaster News"],
        }


@router.get("/recent", summary="Retrieve clean list of recent verified disaster news")
async def get_recent_news(
    time_range: Optional[str] = Query("24h", alias="range", description="Time filter ('24h', '7d', '15d', '30d', 'all'). Default: '24h'"),
    category: Optional[str] = Query(None, description="Filter by disaster category"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    source: Optional[str] = Query(None, description="Filter by news source agency"),
    limit: int = Query(20, ge=1, le=100, description="Max news records to return"),
    skip: int = Query(0, ge=0, description="Pagination skip offset"),
):
    """
    Returns time-filtered, source-filtered, paginated recent disaster news items
    with summary fields projected for high UI performance.
    """
    cutoff_info, canonical_range = parse_time_range_cutoff(time_range)

    query: Dict[str, Any] = {}
    if cutoff_info:
        _, c_iso, c_date = cutoff_info
        query["$or"] = [
            {"processed_at": {"$gte": c_iso}},
            {"first_seen_at": {"$gte": c_iso}},
            {"published_at": {"$gte": c_iso}},
            {"incident_date": {"$gte": c_date}},
        ]

    if category and category.strip().lower() not in ["all", ""]:
        query["disaster_type"] = {"$regex": f"^{re.escape(category.strip())}$", "$options": "i"}

    if severity and severity.strip().lower() not in ["all", ""]:
        query["severity"] = {"$regex": f"^{re.escape(severity.strip())}$", "$options": "i"}

    if source and source.strip().lower() not in ["all", "all sources", ""]:
        escaped_src = re.escape(source.strip())
        source_filter = [
            {"source": {"$regex": escaped_src, "$options": "i"}},
            {"corroboration.sources": {"$regex": escaped_src, "$options": "i"}},
        ]
        if "$or" in query:
            query["$and"] = [{"$or": query.pop("$or")}, {"$or": source_filter}]
        else:
            query["$or"] = source_filter

    projection = {
        "_id": 1,
        "event_id": 1,
        "article_id": 1,
        "title": 1,
        "description": 1,
        "disaster_type": 1,
        "severity": 1,
        "status": 1,
        "url": 1,
        "image": 1,
        "location": 1,
        "incident_date": 1,
        "processed_at": 1,
        "published_at": 1,
        "first_seen_at": 1,
        "corroboration": 1,
    }

    total_matching = disaster_events.count_documents(query)
    cursor = disaster_events.find(query, projection).sort("processed_at", -1).skip(skip).limit(limit)
    raw_docs = list(cursor)

    items = [_format_news_summary(d) for d in raw_docs]

    # Sort descending by timestamp
    items.sort(key=lambda x: x.get("timestamp", 0.0), reverse=True)

    return {
        "status": "success",
        "time_range": canonical_range,
        "total": total_matching,
        "count": len(items),
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(items)) < total_matching,
        "news": items,
    }


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


@router.get("/detail/{news_id}", summary="Retrieve complete details for a single news article")
@router.get("/{news_id}", summary="Retrieve complete details for a single news article (alias)")
async def get_news_detail(news_id: str):
    """
    Retrieves full details, evidence metadata, geospatial data, and corroboration for a single news item.
    """
    clean_id = news_id.strip()

    # Search in disaster_events by article_id, event_id, or ObjectId
    query = {
        "$or": [
            {"event_id": clean_id},
            {"article_id": clean_id},
        ]
    }
    if len(clean_id) == 24:
        try:
            query["$or"].append({"_id": ObjectId(clean_id)})
        except Exception:
            pass

    doc = disaster_events.find_one(query)

    # Fallback to sachet_alerts or earthquakes if not in disaster_events
    if not doc:
        sa_doc = db["sachet_alerts"].find_one({
            "$or": [
                {"event_id": clean_id},
                {"alert_id": clean_id},
                {"guid": clean_id},
            ]
        })
        if sa_doc:
            doc = sa_doc

    if not doc:
        eq_doc = db["earthquakes"].find_one({
            "$or": [
                {"event_id": clean_id},
            ]
        })
        if eq_doc:
            doc = eq_doc

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"News article with ID '{news_id}' not found.",
        )

    formatted = _format_news_detail(doc)
    return {
        "status": "success",
        "news": formatted,
    }