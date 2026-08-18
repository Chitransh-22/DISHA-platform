"""
DISHA Article Quality Scorer
Computes deterministic multi-factor local quality score before AI classification.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.services.source_scorer import score_source
from app.services.evidence_detector import detect_evidence, parse_published_date

# Configurable Scoring Thresholds
MIN_LOCAL_CANDIDATE_SCORE = float(os.getenv("MIN_LOCAL_CANDIDATE_SCORE", "6.0"))
NEWS_MAX_AGE_HOURS = int(os.getenv("NEWS_MAX_AGE_HOURS", "72"))


def score_article(
    article: Dict[str, Any],
    disasters: List[str],
    locations: List[str],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Evaluates an article's disaster credibility, relevance, and ground-truth signals.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    title = article.get("title", "")
    desc = article.get("description", "")
    source_name = article.get("source", "")
    full_text = f"{title} {desc}"

    # 1. Evidence and context detection
    ev = detect_evidence(full_text)
    src = score_source(source_name)

    # 2. Score Calculation
    score_breakdown = {}

    # Disaster keyword strength (+3.0 base, +1.0 for multiple categories)
    if disasters:
        d_score = 3.0 + min(len(disasters) - 1, 2) * 0.5
    else:
        d_score = 0.0
    score_breakdown["disaster_match"] = d_score

    # Indian location presence
    if locations:
        loc_score = 2.5 + min(len(locations) - 1, 2) * 0.5
    elif "india" in full_text.lower():
        loc_score = 1.5
    else:
        loc_score = 0.0
    score_breakdown["location_score"] = loc_score

    # Source reliability weight (+0.0 to +3.0)
    score_breakdown["source_reliability"] = src.get("weight", 0.0)

    # Recency score
    pub_dt = parse_published_date(article.get("published_at"))
    if pub_dt:
        age_hours = (now - pub_dt).total_seconds() / 3600.0
        if age_hours <= 24:
            recency_score = 1.5
        elif age_hours <= 48:
            recency_score = 1.0
        elif age_hours <= NEWS_MAX_AGE_HOURS:
            recency_score = 0.0
        else:
            recency_score = -2.0
    else:
        recency_score = 0.5  # Fresh fetch default
    score_breakdown["recency_score"] = recency_score

    # Physical Impact Evidence Bonuses
    impact_score = 0.0
    if ev["has_casualties"]:
        impact_score += 2.5
    if ev["has_distress"]:
        impact_score += 2.0
    if ev["has_damage"]:
        impact_score += 2.0
    if ev["has_response"]:
        impact_score += 2.0
    score_breakdown["physical_impact_evidence"] = impact_score

    # Negative Deductions
    penalties = 0.0
    rejection_reasons = []

    if ev["is_metaphor"]:
        penalties -= 5.0
        rejection_reasons.append("metaphorical_or_sports_usage")
    if ev["is_foreign_only"]:
        penalties -= 5.0
        rejection_reasons.append("foreign_exclusive_event")
    if ev["is_forecast"] and not ev["has_ground_impact"]:
        penalties -= 4.0
        rejection_reasons.append("forecast_without_ground_impact")
    if ev["is_policy_only"]:
        penalties -= 4.0
        rejection_reasons.append("policy_or_review_meeting_only")
    if ev["is_historical"]:
        penalties -= 4.0
        rejection_reasons.append("historical_or_anniversary_story")

    score_breakdown["penalties"] = penalties

    # Total Score
    total_score = max(
        0.0,
        d_score + loc_score + src.get("weight", 0.0) + recency_score + impact_score + penalties
    )

    passed = (total_score >= MIN_LOCAL_CANDIDATE_SCORE) and not rejection_reasons

    return {
        "passed": passed,
        "total_score": round(total_score, 2),
        "score_breakdown": score_breakdown,
        "evidence": ev["evidence_summary"],
        "source_reliability": src,
        "rejection_reasons": rejection_reasons,
    }
