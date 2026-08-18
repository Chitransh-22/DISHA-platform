"""
DISHA Source Reliability Scorer
Categorizes and scores publisher trustworthiness for disaster intelligence.
"""

from typing import Dict, Any

VERY_HIGH_SOURCES = {
    "imd",
    "india meteorological department",
    "ndma",
    "national disaster management authority",
    "ndrf",
    "national disaster response force",
    "sdrf",
    "state disaster response force",
    "pib",
    "press information bureau",
    "news on air",
    "all india radio",
    "dd news",
    "doordarshan news",
    "disaster management authority",
    "central water commission",
    "cwc",
}

HIGH_SOURCES = {
    "pti",
    "press trust of india",
    "ani",
    "asian news international",
    "reuters",
    "the hindu",
    "the indian express",
    "indian express",
    "hindustan times",
    "times of india",
    "the times of india",
    "ndtv",
    "ndtv news",
    "bbc",
    "bbc news",
    "india today",
    "the telegraph",
    "telegraph india",
    "deccan herald",
    "the tribune",
    "tribune india",
    "mint",
    "business standard",
    "the economic times",
    "economic times",
    "the new indian express",
    "new indian express",
}

NORMAL_SOURCES = {
    "theprint",
    "scroll.in",
    "the wire",
    "news18",
    "abp news",
    "abp live",
    "zee news",
    "aaj tak",
    "jagran",
    "dainik jagran",
    "amar ujala",
    "lokmat",
    "dainik bhaskar",
    "bhaskar",
    "assam tribune",
    "the assam tribune",
    "mathrubhumi",
    "manorama",
    "malayala manorama",
    "eenadu",
    "sakshi",
    "daily excelsior",
    "greater kashmir",
    "kashmir reader",
    "shillong times",
    "meghalaya monitor",
    "prag news",
    "eastmojo",
    "millennium post",
    "sambad",
    "odisha tv",
    "otv",
    "deccan chronicle",
    "freepressjournal",
    "the pioneer",
    "mid-day",
    "moneycontrol",
    "financial express",
    "outlook india",
    "firstpost",
    "oneindia",
}


def score_source(source_name: str) -> Dict[str, Any]:
    """
    Evaluates source trustworthiness and returns scoring breakdown.
    """
    if not source_name:
        return {
            "level": "low",
            "score": 0.30,
            "weight": 0.0,
            "reason": "unspecified_source",
        }

    s_clean = source_name.strip().lower()

    # Check VERY_HIGH
    for vh in VERY_HIGH_SOURCES:
        if vh in s_clean or s_clean == vh:
            return {
                "level": "very_high",
                "score": 1.0,
                "weight": 3.0,
                "reason": "official_emergency_agency",
            }

    # Check HIGH
    for h in HIGH_SOURCES:
        if h in s_clean or s_clean == h:
            return {
                "level": "high",
                "score": 0.85,
                "weight": 2.0,
                "reason": "major_national_wire_or_daily",
            }

    # Check NORMAL
    for n in NORMAL_SOURCES:
        if n in s_clean or s_clean == n:
            return {
                "level": "normal",
                "score": 0.60,
                "weight": 1.0,
                "reason": "established_regional_outlet",
            }

    return {
        "level": "low",
        "score": 0.30,
        "weight": 0.0,
        "reason": "unverified_digital_outlet",
    }
