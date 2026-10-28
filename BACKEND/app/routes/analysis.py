"""
DISHA Platform - Comprehensive Disaster Analytics & Intelligence API Route
Provides multi-source aggregation across NCS RISEQ, NDMA SACHET CAP,
Google News Disaster Intelligence, Citizen Incident Reports, Pipeline Filter Metrics,
and AI Verification stats.

Guarantees 100% data consistency with the Home Map and Unified Events API (/api/events).
Zero event loss: T (Total) = M (Mapped) + U (Unmapped).
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
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
incident_reports = db["incident_reports"]
pipeline_runs = db["pipeline_runs"]


@router.get("/overview", summary="Executive Disaster Intelligence KPI Summary")
async def get_analysis_overview(
    time_range: Optional[str] = Query(
        None,
        description="Time filter ('24h', '7d', '15d', '30d', 'all', 'custom'). Default: '24h'",
    ),
    range: Optional[str] = Query(
        None,
        description="Alternative query alias for time filter",
    ),
    time_window: Optional[str] = Query(
        None,
        description="Alternative time window alias ('24h', '7d', '15d', '30d', 'all')",
    ),
    days: Optional[int] = Query(
        None,
        description="Alternative days integer filter (1, 7, 15, 30)",
    ),
    start_date: Optional[str] = Query(
        None,
        description="Custom range start date/timestamp",
    ),
    end_date: Optional[str] = Query(
        None,
        description="Custom range end date/timestamp",
    ),
):
    """
    Returns high-level disaster intelligence KPIs, pipeline telemetry,
    and operational statistics derived from canonical events service.
    Guarantees that analysis totals match the unified incident dataset.
    """
    now_utc = datetime.now(timezone.utc)

    try:
        if days is not None:
            effective_range = f"{days}d"
        elif time_window is not None:
            effective_range = time_window
        else:
            effective_range = time_range or range or "24h"

        # 1. Fetch canonical unified events using the exact same query contract
        canonical_data = get_unified_events(
            time_range=effective_range,
            start_date=start_date,
            end_date=end_date,
            limit=None,
        )

        canonical_events = canonical_data.get("events", [])
        total_verified_events = canonical_data.get("total", len(canonical_events))
        mapped_count = canonical_data.get("mapped_count", 0)
        unmapped_count = canonical_data.get("unmapped_count", 0)
        src_counts = canonical_data.get("source_counts", {})

        total_news_disasters = src_counts.get("news", 0)
        total_earthquakes = src_counts.get("earthquakes", 0)
        total_sachet = src_counts.get("sachet", 0)
        total_citizen_reports = src_counts.get("citizen_reports", 0)

        # 2. Pipeline filtering telemetry
        total_articles_seen = news_temp.count_documents({})
        total_rejected = rejected_news.count_documents({})
        local_rejected = rejected_news.count_documents({"stage": "local"})
        quality_rejected = rejected_news.count_documents({"stage": "quality"})
        ai_rejected = rejected_news.count_documents({"stage": "ai"})
        temporal_rejected = rejected_news.count_documents({"stage": "temporal_old"})
        forecast_rejected = rejected_news.count_documents({"stage": "forecast"})
        pending_ai = news_temp.count_documents({"status": "pending_ai"})

        # 3. Severity breakdown from canonical dataset
        critical_count = sum(1 for e in canonical_events if e.get("severity") == "Critical")
        severe_count = sum(1 for e in canonical_events if e.get("severity") == "Severe")
        moderate_count = sum(1 for e in canonical_events if e.get("severity") == "Moderate")
        low_count = sum(1 for e in canonical_events if e.get("severity") == "Low")

        total_critical_events = critical_count
        total_high_risk_events = critical_count + severe_count
        total_moderate_events = moderate_count
        total_low_events = low_count

        # 4. Disaster Type breakdown from canonical dataset
        type_counts: Dict[str, int] = {}
        for ev in canonical_events:
            cat = ev.get("category") or "Other"
            type_counts[cat] = type_counts.get(cat, 0) + 1
        sorted_types = dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True))

        # 5. State distribution from canonical dataset
        state_counts: Dict[str, int] = {}
        for ev in canonical_events:
            st = ev.get("state")
            if st and isinstance(st, str) and len(st.strip()) > 1:
                cleaned = st.strip().title()
                state_counts[cleaned] = state_counts.get(cleaned, 0) + 1
            else:
                state_counts["Unknown / Unresolved"] = state_counts.get("Unknown / Unresolved", 0) + 1

        top_states = [
            {"state": k, "count": v}
            for k, v in sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        ]

        # Calculation of pipeline precision / noise reduction rate
        noise_reduction_rate = round((total_rejected / max(1, total_articles_seen)) * 100, 1) if total_articles_seen > 0 else 0.0

        return {
            "status": "success",
            "timestamp": now_utc.isoformat(),
            "time_range": canonical_data.get("time_range"),
            "start_time": canonical_data.get("start_time"),
            "end_time": canonical_data.get("end_time"),
            "invariant_holds": canonical_data.get("invariant_holds", True),
            "kpis": {
                "total_verified_events": total_verified_events,
                "mapped_events_count": mapped_count,
                "unmapped_events_count": unmapped_count,
                "total_critical_events": total_critical_events,
                "total_high_risk_events": total_high_risk_events,
                "total_news_disasters": total_news_disasters,
                "total_earthquakes": total_earthquakes,
                "total_sachet_alerts": total_sachet,
                "total_citizen_reports": total_citizen_reports,
                "total_articles_ingested": total_articles_seen,
                "total_noise_rejected": total_rejected,
                "noise_reduction_percentage": noise_reduction_rate,
                "pending_ai_queue": pending_ai,
                "sources_monitored_count": 4, # NCS RISEQ, NDMA SACHET, Multi-Source News, Citizen Reports
            },
            "source_counts": src_counts,
            "source_mapped_counts": canonical_data.get("source_mapped_counts", {}),
            "severity_summary": {
                "critical": total_critical_events,
                "high_severe": severe_count,
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
                "mapped_events_count": 0,
                "unmapped_events_count": 0,
                "total_critical_events": 0,
                "total_high_risk_events": 0,
                "total_news_disasters": 0,
                "total_earthquakes": 0,
                "total_sachet_alerts": 0,
                "total_citizen_reports": 0,
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
    time_window: Optional[str] = Query(None, description="Time window: 24h, 7d, 15d, 30d, all"),
    time_range: Optional[str] = Query(
        "24h",
        alias="range",
        description="Time filter: 24h, 7d, 15d, 30d, all",
    ),
    days: Optional[int] = Query(None, description="Alternative days integer filter"),
    start_date: Optional[str] = Query(None, description="Custom range start date"),
    end_date: Optional[str] = Query(None, description="Custom range end date"),
    limit: Optional[int] = Query(None, ge=1, le=5000),
    skip: int = Query(0, ge=0),
):
    """
    Retrieve comprehensive data across all 4 integrated DISHA streams
    (News Disasters, NCS Earthquakes, NDMA SACHET Alerts, Citizen Reports)
    using the canonical events service.
    """
    try:
        if days is not None:
            effective_range = f"{days}d"
        elif time_window is not None:
            effective_range = time_window
        else:
            effective_range = time_range or range or "24h"

        unified_res = get_unified_events(
            category=disaster_type,
            state=state,
            severity=severity,
            time_range=effective_range,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            skip=skip,
        )

        unified_list = unified_res.get("events", [])
        src_counts = unified_res.get("source_counts", {})

        return {
            "status": "success",
            "time_range": unified_res.get("time_range"),
            "start_time": unified_res.get("start_time"),
            "end_time": unified_res.get("end_time"),
            "total": unified_res.get("total", len(unified_list)),
            "mapped_count": unified_res.get("mapped_count", 0),
            "unmapped_count": unified_res.get("unmapped_count", 0),
            "invariant_holds": unified_res.get("invariant_holds", True),
            "counts": {
                "disaster_events": src_counts.get("news", 0),
                "earthquakes": src_counts.get("earthquakes", 0),
                "sachet_alerts": src_counts.get("sachet", 0),
                "citizen_reports": src_counts.get("citizen_reports", 0),
                "total": unified_res.get("total", len(unified_list)),
                "unified_total": unified_res.get("total", len(unified_list)),
            },
            "source_counts": src_counts,
            "source_mapped_counts": unified_res.get("source_mapped_counts", {}),
            "all_events": unified_list,
        }
    except Exception as e:
        logger.error(f"[Analysis] Data fetch error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "total": 0,
            "mapped_count": 0,
            "unmapped_count": 0,
            "counts": {"disaster_events": 0, "earthquakes": 0, "sachet_alerts": 0, "citizen_reports": 0, "total": 0},
            "all_events": [],
        }
