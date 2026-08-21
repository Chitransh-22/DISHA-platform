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
from app.services.events_service import get_unified_events, map_category, map_severity

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
    and operational statistics derived from real database collections
    (disaster_events, earthquakes, sachet_alerts).
    """
    now_utc = datetime.now(timezone.utc)

    try:
        # 1. Total counts across all 3 primary data collections
        total_news_disasters = disaster_events.count_documents({})
        total_earthquakes = earthquakes.count_documents({})
        total_sachet = sachet_alerts.count_documents({})
        total_verified_events = total_news_disasters + total_earthquakes + total_sachet
        
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
        critical_news = disaster_events.count_documents({"severity": {"$regex": "^critical", "$options": "i"}})
        high_news = disaster_events.count_documents({"severity": {"$regex": "^(high|severe)", "$options": "i"}})
        medium_news = disaster_events.count_documents({"severity": {"$regex": "^(medium|moderate)", "$options": "i"}})
        low_news = disaster_events.count_documents({"severity": {"$regex": "^low", "$options": "i"}})

        # 4. Severity aggregations for SACHET alerts
        sachet_extreme = sachet_alerts.count_documents({"severity": {"$regex": "^(extreme|critical)", "$options": "i"}})
        sachet_severe = sachet_alerts.count_documents({"severity": {"$regex": "^severe", "$options": "i"}})
        sachet_moderate = sachet_alerts.count_documents({"severity": {"$regex": "^moderate", "$options": "i"}})
        sachet_minor = sachet_alerts.count_documents({"severity": {"$regex": "^(minor|low)", "$options": "i"}})

        # 5. Earthquake magnitude distribution
        eq_6_plus = earthquakes.count_documents({"magnitude": {"$gte": 6.0}})
        eq_5_to_5_9 = earthquakes.count_documents({"magnitude": {"$gte": 4.5, "$lt": 6.0}})
        eq_4_to_4_9 = earthquakes.count_documents({"magnitude": {"$gte": 3.5, "$lt": 4.5}})
        eq_under_4 = earthquakes.count_documents({"magnitude": {"$lt": 3.5}})

        # 6. Combined active and critical metrics across all 3 collections
        total_critical_events = critical_news + sachet_extreme + eq_6_plus
        total_high_risk_events = high_news + sachet_severe + eq_5_to_5_9
        total_moderate_events = medium_news + sachet_moderate + eq_4_to_4_9
        total_low_events = low_news + sachet_minor + eq_under_4

        # 7. Combined Disaster Type Distribution (from disaster_events + sachet_alerts + earthquakes)
        type_counts: Dict[str, int] = {}
        if total_earthquakes > 0:
            type_counts["Earthquake"] = total_earthquakes

        # News disaster types
        pipeline_news_types = [
            {"$group": {"_id": "$disaster_type", "count": {"$sum": 1}}},
        ]
        for item in disaster_events.aggregate(pipeline_news_types):
            raw = item.get("_id")
            if raw:
                display_cat, _ = map_category(str(raw))
                type_counts[display_cat] = type_counts.get(display_cat, 0) + item.get("count", 0)

        # Sachet disaster types
        pipeline_sachet_types = [
            {"$group": {"_id": "$disaster_type", "count": {"$sum": 1}}},
        ]
        for item in sachet_alerts.aggregate(pipeline_sachet_types):
            raw = item.get("_id")
            if raw:
                display_cat, _ = map_category(str(raw))
                type_counts[display_cat] = type_counts.get(display_cat, 0) + item.get("count", 0)

        # Sort disaster types by frequency descending
        sorted_types = dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True))

        # 8. Combined State Distribution (from disaster_events + sachet_alerts + earthquakes)
        state_counts: Dict[str, int] = {}

        # From disaster_events
        for doc in disaster_events.find({}, {"location.state": 1, "location.detected_states": 1}):
            st = doc.get("location", {}).get("state")
            if st and isinstance(st, str) and len(st.strip()) > 1:
                cleaned = st.strip().title()
                state_counts[cleaned] = state_counts.get(cleaned, 0) + 1

        # From sachet_alerts
        for doc in sachet_alerts.find({}, {"location.state": 1, "state": 1}):
            st = doc.get("location", {}).get("state") or doc.get("state")
            if st and isinstance(st, str) and len(st.strip()) > 1:
                cleaned = st.strip().title()
                state_counts[cleaned] = state_counts.get(cleaned, 0) + 1

        # From earthquakes
        for doc in earthquakes.find({}, {"relevance_details.detected_states": 1, "region": 1, "state": 1}):
            detected = doc.get("relevance_details", {}).get("detected_states")
            if detected and isinstance(detected, list) and len(detected) > 0:
                for st in detected:
                    if st and isinstance(st, str):
                        cleaned = st.strip().title()
                        state_counts[cleaned] = state_counts.get(cleaned, 0) + 1
            else:
                region = doc.get("region") or doc.get("state")
                if region and isinstance(region, str):
                    cleaned = region.strip().title()
                    state_counts[cleaned] = state_counts.get(cleaned, 0) + 1

        top_states = [{"state": k, "count": v} for k, v in sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:15]]

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
                "total_earthquakes_30d": total_earthquakes,
                "total_sachet_alerts_30d": total_sachet,
                "total_articles_ingested": total_articles_seen,
                "total_noise_rejected": total_rejected,
                "noise_reduction_percentage": noise_reduction_rate,
                "pending_ai_queue": pending_ai,
                "sources_monitored_count": 4, # NCS RISEQ, NDMA SACHET, IMD/CWC, Multi-Source News
            },
            "severity_summary": {
                "critical": total_critical_events,
                "high_severe": total_high_risk_events,
                "moderate_medium": total_moderate_events,
                "low_minor": total_low_events,
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
            "disaster_types": sorted_types,
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
    limit: int = Query(1000, ge=1, le=2000),
):
    """
    Retrieve comprehensive data across all 3 integrated DISHA streams
    (News Disasters, NCS Earthquakes, and NDMA SACHET Alerts) for full client analytics.
    """
    try:
        lim = 1000
        if isinstance(limit, int):
            lim = limit
        elif hasattr(limit, "default") and isinstance(limit.default, int):
            lim = limit.default

        tw = "all"
        if isinstance(time_window, str):
            tw = time_window
        elif hasattr(time_window, "default") and isinstance(time_window.default, str):
            tw = time_window.default

        events = list(disaster_events.find({}, {"_id": 0}).sort("processed_at", -1).limit(lim))
        eqs = list(earthquakes.find({}, {"_id": 0}).sort("origin_time", -1).limit(lim))
        alerts = list(sachet_alerts.find({}, {"_id": 0}).sort("event_time", -1).limit(lim))

        # Also get unified normalized events via events_service
        unified_res = get_unified_events(time_range=tw)
        unified_list = unified_res.get("events", []) if isinstance(unified_res, dict) else []

        return {
            "status": "success",
            "counts": {
                "disaster_events": len(events),
                "earthquakes": len(eqs),
                "sachet_alerts": len(alerts),
                "total": len(events) + len(eqs) + len(alerts),
                "unified_total": len(unified_list),
            },
            "disasters": events,
            "earthquakes": eqs,
            "sachet_alerts": alerts,
            "all_events": unified_list,
        }
    except Exception as e:
        logger.error(f"[Analysis] Data fetch error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "counts": {"disaster_events": 0, "earthquakes": 0, "sachet_alerts": 0, "total": 0},
            "disasters": [],
            "earthquakes": [],
            "sachet_alerts": [],
            "all_events": [],
        }
