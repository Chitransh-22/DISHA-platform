"""
DISHA Platform - Comprehensive Disaster Analytics & Intelligence API Route
Provides multi-source aggregation across NCS RISEQ, NDMA SACHET CAP,
Google News Disaster Intelligence, Pipeline Filter Metrics, and AI Verification stats.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

# Ensure backend directory in sys.path
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")
load_dotenv()

from fastapi import APIRouter, Query
from app.database.mongodb import db

logger = logging.getLogger("disha.routes.analysis")

router = APIRouter(
    prefix="/api/analysis",
    tags=["Disaster Intelligence & Analytics"],
)

disaster_events = db["disaster_events"]
rejected_news = db["rejected_news"]
news_temp = db["news_temp"]
ai_usage = db["ai_usage"]
earthquakes = db["earthquakes"]
sachet_alerts = db["sachet_alerts"]
pipeline_runs = db["pipeline_runs"]


@router.get("/overview", summary="Executive Disaster Intelligence KPI Summary")
async def get_analysis_overview():
    """
    Returns high-level disaster intelligence KPIs, pipeline telemetry,
    and operational statistics derived from real database collections.
    """
    now_utc = datetime.now(timezone.utc)
    cutoff_30d = (now_utc - timedelta(days=30)).isoformat()
    cutoff_7d = (now_utc - timedelta(days=7)).isoformat()
    cutoff_24h = (now_utc - timedelta(hours=24)).isoformat()

    try:
        # 1. Total counts across primary data feeds
        total_news_disasters = disaster_events.count_documents({})
        total_earthquakes_30d = earthquakes.count_documents({"origin_time": {"$gte": cutoff_30d}})
        total_sachet_30d = sachet_alerts.count_documents({"event_time": {"$gte": cutoff_30d}})
        
        # 2. Pipeline filtering metrics
        total_articles_seen = news_temp.count_documents({})
        total_rejected = rejected_news.count_documents({})
        local_rejected = rejected_news.count_documents({"stage": "local"})
        quality_rejected = rejected_news.count_documents({"stage": "quality"})
        ai_rejected = rejected_news.count_documents({"stage": "ai"})
        temporal_rejected = rejected_news.count_documents({"stage": "temporal_old"})
        forecast_rejected = rejected_news.count_documents({"stage": "forecast"})
        pending_ai = news_temp.count_documents({"status": "pending_ai"})

        # 3. Severity aggregations for news disasters
        critical_news = disaster_events.count_documents({"severity": "critical"})
        high_news = disaster_events.count_documents({"severity": "high"})
        medium_news = disaster_events.count_documents({"severity": "medium"})
        low_news = disaster_events.count_documents({"severity": "low"})

        # 4. Severity aggregations for SACHET alerts
        sachet_extreme = sachet_alerts.count_documents({"severity": "Extreme", "event_time": {"$gte": cutoff_30d}})
        sachet_severe = sachet_alerts.count_documents({"severity": "Severe", "event_time": {"$gte": cutoff_30d}})
        sachet_moderate = sachet_alerts.count_documents({"severity": "Moderate", "event_time": {"$gte": cutoff_30d}})
        sachet_minor = sachet_alerts.count_documents({"severity": "Minor", "event_time": {"$gte": cutoff_30d}})

        # 5. Earthquake magnitude distribution
        eq_6_plus = earthquakes.count_documents({"magnitude": {"$gte": 6.0}, "origin_time": {"$gte": cutoff_30d}})
        eq_5_to_5_9 = earthquakes.count_documents({"magnitude": {"$gte": 5.0, "$lt": 6.0}, "origin_time": {"$gte": cutoff_30d}})
        eq_4_to_4_9 = earthquakes.count_documents({"magnitude": {"$gte": 4.0, "$lt": 5.0}, "origin_time": {"$gte": cutoff_30d}})
        eq_under_4 = earthquakes.count_documents({"magnitude": {"$lt": 4.0}, "origin_time": {"$gte": cutoff_30d}})

        # 6. Combined active and critical metrics
        total_verified_events = total_news_disasters + total_earthquakes_30d + total_sachet_30d
        total_critical_events = critical_news + sachet_extreme + eq_6_plus
        total_high_risk_events = high_news + sachet_severe + eq_5_to_5_9

        # 7. Disaster type distribution aggregation
        pipeline_types = [
            {"$group": {"_id": "$disaster_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        news_types = {item["_id"]: item["count"] for item in disaster_events.aggregate(pipeline_types) if item["_id"]}

        # 8. State distribution aggregation
        pipeline_states = [
            {"$match": {"location.state": {"$ne": None, "$ne": ""}}},
            {"$group": {"_id": "$location.state", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        top_states = [{"state": item["_id"], "count": item["count"]} for item in disaster_events.aggregate(pipeline_states)]

        # Calculation of pipeline precision / noise reduction rate
        noise_reduction_rate = round((total_rejected / max(1, total_articles_seen)) * 100, 1) if total_articles_seen > 0 else 0.0

        return {
            "status": "success",
            "timestamp": now_utc.isoformat(),
            "kpis": {
                "total_verified_events": total_verified_events,
                "total_critical_events": total_critical_events,
                "total_high_risk_events": total_high_risk_events,
                "total_news_disasters": total_news_disasters,
                "total_earthquakes_30d": total_earthquakes_30d,
                "total_sachet_alerts_30d": total_sachet_30d,
                "total_articles_ingested": total_articles_seen,
                "total_noise_rejected": total_rejected,
                "noise_reduction_percentage": noise_reduction_rate,
                "pending_ai_queue": pending_ai,
                "sources_monitored_count": 4, # NCS RISEQ, NDMA SACHET, IMD/CWC, Multi-Source News
            },
            "severity_summary": {
                "critical": total_critical_events,
                "high_severe": total_high_risk_events,
                "moderate_medium": medium_news + sachet_moderate + eq_4_to_4_9,
                "low_minor": low_news + sachet_minor + eq_under_4,
            },
            "pipeline_funnel": {
                "articles_ingested": total_articles_seen,
                "rejected_local": local_rejected,
                "rejected_quality": quality_rejected,
                "rejected_ai": ai_rejected,
                "rejected_temporal_old": temporal_rejected,
                "rejected_forecast_only": forecast_rejected,
                "verified_disasters": total_news_disasters,
            },
            "top_states": top_states,
            "disaster_types": news_types,
        }

    except Exception as e:
        logger.error(f"[Analysis] Error generating overview stats: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": now_utc.isoformat(),
            "kpis": {
                "total_verified_events": 0,
                "total_critical_events": 0,
                "total_high_risk_events": 0,
                "total_news_disasters": 0,
                "total_earthquakes_30d": 0,
                "total_sachet_alerts_30d": 0,
                "total_articles_ingested": 0,
                "total_noise_rejected": 0,
                "noise_reduction_percentage": 0.0,
                "pending_ai_queue": 0,
                "sources_monitored_count": 4,
            }
        }


@router.get("/data", summary="Multi-Criteria Filtered Events & Intelligence Feeds")
async def get_analysis_data(
    disaster_type: Optional[str] = Query(None, description="Filter by hazard type"),
    state: Optional[str] = Query(None, description="Filter by Indian State/UT"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    time_window: Optional[str] = Query("all", description="Time window: 24h, 7d, 30d, all"),
    limit: int = Query(200, ge=1, le=1000),
):
    """
    Retrieve comprehensive data across all 3 integrated DISHA streams
    (News Disasters, NCS Earthquakes, and NDMA SACHET Alerts) for full client analytics.
    """
    query: Dict[str, Any] = {}
    if disaster_type and disaster_type.lower() != "all":
        query["disaster_type"] = disaster_type.lower()
    if state and state.lower() != "all":
        query["location.state"] = {"$regex": state, "$options": "i"}
    if severity and severity.lower() != "all":
        query["severity"] = severity.lower()

    try:
        events = list(disaster_events.find(query, {"_id": 0}).sort("processed_at", -1).limit(limit))
        eqs = list(earthquakes.find({}, {"_id": 0}).sort("origin_time", -1).limit(limit))
        alerts = list(sachet_alerts.find({}, {"_id": 0}).sort("event_time", -1).limit(limit))

        return {
            "status": "success",
            "counts": {
                "disaster_events": len(events),
                "earthquakes": len(eqs),
                "sachet_alerts": len(alerts),
            },
            "disasters": events,
            "earthquakes": eqs,
            "sachet_alerts": alerts,
        }
    except Exception as e:
        logger.error(f"[Analysis] Data fetch error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "disasters": [],
            "earthquakes": [],
            "sachet_alerts": [],
        }
