"""
DISHA Article Quality & True Current-Incident Scorer
Computes deterministic multi-factor quality and recency scores to prioritize genuine
current disasters in India before AI classification.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.services.source_scorer import score_source
from app.services.evidence_detector import detect_evidence
from app.services.temporal_extractor import parse_published_date

# Configurable Scoring Thresholds
MIN_LOCAL_CANDIDATE_SCORE = float(os.getenv("MIN_LOCAL_CANDIDATE_SCORE", "5.0"))
NEWS_MAX_AGE_HOURS = int(os.getenv("NEWS_MAX_AGE_HOURS", "72"))


def score_article(
    article: Dict[str, Any],
    disasters: List[str],
    locations: List[str],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Evaluates an article's disaster credibility, true incident recency, ground-truth signals,
    and calculates candidate_priority_score for AI verification queue ordering.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    title = article.get("title", "")
    desc = article.get("description", "")
    source_name = article.get("source", "")
    full_text = f"{title} {desc}".strip()

    # 1. Parse publication datetime
    pub_dt = parse_published_date(article.get("published_at"))

    # 2. Evidence, Freshness & Article Type Detection
    ev = detect_evidence(full_text, published_dt=pub_dt, now_utc=now)
    src = score_source(source_name)
    freshness = ev.get("freshness", {})

    # 3. Score Breakdown Calculation
    score_breakdown = {}

    # Disaster category match
    if disasters:
        d_score = 3.0 + min(len(disasters) - 1, 2) * 0.5
    else:
        # If no explicit disaster keyword, but ground impact is present, assign moderate base
        d_score = 2.0 if ev["has_ground_impact"] else 0.0
    score_breakdown["disaster_match"] = round(d_score, 2)

    # Indian location presence
    if locations:
        loc_score = 2.5 + min(len(locations) - 1, 2) * 0.5
    elif ev.get("has_india_context"):
        loc_score = 1.5
    else:
        loc_score = 0.0
    score_breakdown["location_score"] = round(loc_score, 2)

    # Source reliability weight (+0.0 to +3.0) - purely ranking factor
    source_weight = src.get("weight", 0.0)
    score_breakdown["source_reliability"] = source_weight

    # True Publication Recency Score
    pub_recency_score = freshness.get("pub_recency_score", 1.0)
    score_breakdown["pub_recency_score"] = pub_recency_score

    # True Incident Recency Score
    incident_recency_score = freshness.get("incident_recency_score", 2.0)
    score_breakdown["incident_recency_score"] = incident_recency_score

    # Physical Impact Evidence Bonuses
    impact_score = 0.0
    if ev["has_casualties"]:
        impact_score += 4.0
    if ev["has_distress"]:
        impact_score += 4.0
    if ev["has_damage"]:
        impact_score += 3.0
    if ev["has_response"]:
        impact_score += 3.0
    score_breakdown["physical_impact_evidence"] = impact_score

    # Penalties & Disqualifications
    penalties = 0.0
    rejection_reasons = []

    if ev["is_metaphor"]:
        penalties -= 10.0
        rejection_reasons.append("metaphorical_or_sports_usage")

    if ev["is_foreign_only"]:
        penalties -= 10.0
        rejection_reasons.append("foreign_exclusive_event")

    if ev["is_historical"] or freshness.get("is_historical"):
        penalties -= 10.0
        rejection_reasons.append("historical_or_anniversary_story")

    if ev["is_forecast_only"]:
        penalties -= 6.0
        rejection_reasons.append("forecast_without_ground_impact")

    if ev["is_policy_only"]:
        penalties -= 5.0
        rejection_reasons.append("policy_or_review_meeting_only")

    if ev["is_funding_only"]:
        penalties -= 5.0
        rejection_reasons.append("funding_or_relief_appeal_only")

    if ev["is_analysis_only"]:
        penalties -= 5.0
        rejection_reasons.append("analysis_or_opinion_piece")

    if freshness.get("is_old_incident_in_recent_article"):
        penalties -= 5.0
        rejection_reasons.append("old_incident_in_recent_article")

    score_breakdown["penalties"] = penalties

    # Total Score (Candidate Priority Score)
    total_score = max(
        0.0,
        d_score
        + loc_score
        + source_weight
        + pub_recency_score
        + incident_recency_score
        + impact_score
        + penalties
    )

    passed = (total_score >= MIN_LOCAL_CANDIDATE_SCORE) and not rejection_reasons

    return {
        "passed": passed,
        "total_score": round(total_score, 2),
        "candidate_priority_score": round(total_score, 2),
        "article_type": ev.get("article_type", "UNKNOWN"),
        "freshness_tier": freshness.get("freshness_tier", "RECENT"),
        "incident_date": ev.get("incident_date"),
        "score_breakdown": score_breakdown,
        "evidence": ev.get("evidence_summary", []),
        "source_reliability": src,
        "rejection_reasons": rejection_reasons,
    }
