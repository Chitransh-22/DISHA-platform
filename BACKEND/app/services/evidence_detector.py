"""
DISHA Incident Evidence & Context Detector
Detects physical ground truth evidence vs speculative, policy, or metaphorical language.
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Positive Physical Evidence Patterns
CASUALTY_PATTERNS = [
    r"\b(kill|kills|killed|claiming lives|claims \d+ lives|claim \d+ lives|died|dead|fatalities|deaths|drowned|charred to death|crushed to death|lost (their )?lives)\b",
    r"\b(death toll (rises|mounts|crosses|reaches|at|\d+)|fatalities reported|succumbed to injuries)\b",
]

DISTRESS_PATTERNS = [
    r"\b(\d+|several|hundreds of|thousands of)?\s*(trapped|stranded|missing|injured|hospitalized|submerged|inundated|washed away|marooned|cut off|rendered homeless)\b",
    r"\b(villages submerged|houses inundated|water entering|under water|landslide hits|families displaced)\b",
]

DAMAGE_PATTERNS = [
    r"\b(bridge collapsed|building collapsed|roof collapsed|wall collapsed|structure damaged|roads blocked|highway closed|rail tracks submerged|dam breached|embankment breached|factory gutted|gutted in fire)\b",
    r"\b(massive destruction|widespread damage|hectares of crops damaged|poles uprooted|trees uprooted)\b",
]

RESPONSE_PATTERNS = [
    r"\b(ndrf|sdrf|army deployed|airforce|airlifted|evacuation|evacuated|relief camps|rescue operation|rescue teams|relief material|disaster response)\b",
    r"\b(emergency services|fire tenders rushed|helpline started|search and rescue)\b",
]

# Negative Non-Incident Patterns
FORECAST_PATTERNS = [
    r"\b(forecast|forecasted|forecasting|expected to|likely to|may see|may witness|prediction|weather model|predicted)\b",
    r"\b(yellow alert|orange alert|red alert|warning issued|advisory issued|alert issued|alert sounded|heavy rain predicted)\b",
]

POLICY_MEETING_PATTERNS = [
    r"\b(review meeting|meeting held|policy discussed|relief package announced|compensation announced|funds approved|financial assistance approved|preparedness reviewed|mou signed|cabinet approves)\b",
    r"\b(plans for flood management|drills conducted|seminar on disaster)\b",
]

HISTORICAL_PATTERNS = [
    r"\b(anniversary of|years after|retrospective|memories of|historical flood of|lessons from|revisiting the|looking back at)\b",
]

METAPHOR_PATTERNS = [
    r"\b(landslide victory|landslide win|election landslide|poll victory|bypoll|vote share|exit poll|assembly election)\b",
    r"\b(cricket|century|wicket|ipl|trophy|world cup|innings|run drought|medal drought|goal scored|match highlights|badminton)\b",
    r"\b(box office|trailer release|teaser release|movie review|ott release|bollywood|tollywood|actor|actress|album release|song release|concert blast|party blast)\b",
    r"\b(stock market|shares crash|startup valuation|sales explosion|population explosion|user explosion|market collapse|funding drought|talent drought|deal drought)\b",
    r"\b(paper leak|exam leak|question paper leak|data leak|whatsapp leak|neet leak)\b",
    r"\b(flash mob|flash sale|spread like wildfire|flood of applications|avalanche of comments|tsunami of memes|tsunami of debt)\b",
]

FOREIGN_PATTERNS = [
    r"\b(in usa|in us|in united states|in florida|in texas|in california|in japan|in china|in australia|in europe|in philippines|in indiana|in indonesia|in canada|in uk|in london)\b"
]


def detect_evidence(text: str) -> Dict[str, Any]:
    """
    Extracts structured evidence metrics and signals from normalized text.
    """
    text_clean = text.lower()

    # 1. Positive evidence extraction
    casualties = []
    for pat in CASUALTY_PATTERNS:
        matches = re.findall(pat, text_clean)
        if matches:
            casualties.append(pat)

    distress = []
    for pat in DISTRESS_PATTERNS:
        matches = re.findall(pat, text_clean)
        if matches:
            distress.append(pat)

    damage = []
    for pat in DAMAGE_PATTERNS:
        matches = re.findall(pat, text_clean)
        if matches:
            damage.append(pat)

    response = []
    for pat in RESPONSE_PATTERNS:
        matches = re.findall(pat, text_clean)
        if matches:
            response.append(pat)

    # 2. Negative indicator extraction
    is_forecast = any(re.search(pat, text_clean) for pat in FORECAST_PATTERNS)
    is_policy = any(re.search(pat, text_clean) for pat in POLICY_MEETING_PATTERNS)
    is_historical = any(re.search(pat, text_clean) for pat in HISTORICAL_PATTERNS)
    is_metaphor = any(re.search(pat, text_clean) for pat in METAPHOR_PATTERNS)
    is_foreign_only = any(re.search(pat, text_clean) for pat in FOREIGN_PATTERNS) and not re.search(r"\b(india|indian)\b", text_clean)

    # Compile human-readable evidence summaries
    evidence_items = []
    if casualties:
        evidence_items.append("Reported casualties, deaths, or fatalities")
    if distress:
        evidence_items.append("People trapped, stranded, injured, or submerged")
    if damage:
        evidence_items.append("Physical infrastructure or property damage reported")
    if response:
        evidence_items.append("Emergency rescue/NDRF/SDRF mobilization active")

    has_ground_impact = bool(casualties or distress or damage or response)

    return {
        "has_ground_impact": has_ground_impact,
        "has_casualties": bool(casualties),
        "has_distress": bool(distress),
        "has_damage": bool(damage),
        "has_response": bool(response),
        "is_forecast": is_forecast,
        "is_policy_only": is_policy and not has_ground_impact,
        "is_historical": is_historical,
        "is_metaphor": is_metaphor,
        "is_foreign_only": is_foreign_only,
        "evidence_summary": evidence_items,
    }


def parse_published_date(published_str: Optional[str]) -> Optional[datetime]:
    """
    Parses diverse RSS timestamp formats into UTC datetime.
    """
    if not published_str:
        return None

    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",     # Tue, 18 Aug 2026 14:30:00 GMT
        "%a, %d %b %Y %H:%M:%S %z",     # Tue, 18 Aug 2026 14:30:00 +0000
        "%Y-%m-%dT%H:%M:%SZ",           # 2026-08-18T14:30:00Z
        "%Y-%m-%dT%H:%M:%S%z",          # ISO format
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(published_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue

    return None
