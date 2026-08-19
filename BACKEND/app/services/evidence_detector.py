"""
DISHA Incident Evidence, Context & Article Type Detector
Detects physical ground truth evidence, emergency responses, forecasts, policies,
editorial analyses, and classifies article types deterministically.
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from app.services.temporal_extractor import (
    parse_published_date,
    extract_incident_date,
    evaluate_freshness,
)

# ============================================================
# POSITIVE GROUND TRUTH EVIDENCE PATTERNS
# ============================================================

CASUALTY_PATTERNS = [
    r"\b(kill|kills|killed|killing|claiming\s+lives|claims\s+\d+\s+lives|claim\s+\d+\s+lives|died|dead|fatalities|deaths|death\s+toll|drowned|drowning|charred\s+to\s+death|crushed\s+to\s+death|lost\s+(?:their\s+)?lives)\b",
    r"\b(death\s+toll\s+(?:rises|mounts|crosses|reaches|at|\d+)|fatalities\s+reported|succumbed\s+to\s+injuries|bodies\s+recovered|body\s+recovered|corpses\s+recovered|mortal\s+remains\s+recovered)\b",
]

DISTRESS_PATTERNS = [
    r"\b(\d+|several|hundreds\s+of|thousands\s+of)?\s*(trapped|stranded|missing|injured|hospitalized|submerged|inundated|washed\s+away|marooned|cut\s+off|rendered\s+homeless|under\s+rubble|under\s+debris)\b",
    r"\b(villages\s+submerged|houses\s+inundated|water\s+entering|under\s+water|landslide\s+hits|families\s+displaced|workers\s+trapped|workers\s+missing|people\s+trapped|people\s+missing|search\s+continues\s+for\s+(?:\d+|two|three|workers|people|bodies))\b",
]

DAMAGE_PATTERNS = [
    r"\b(bridge\s+collapsed|building\s+collapsed|roof\s+collapsed|wall\s+collapsed|structure\s+damaged|structure\s+collapsed|roads\s+blocked|highway\s+closed|rail\s+tracks\s+submerged|dam\s+breached|embankment\s+breached|factory\s+gutted|gutted\s+in\s+fire|houses\s+destroyed|houses\s+damaged|bund\s+breached|tunnel\s+collapse|tunnel\s+accident|tunnel\s+caved\s+in)\b",
    r"\b(massive\s+destruction|widespread\s+damage|hectares\s+of\s+crops\s+damaged|poles\s+uprooted|trees\s+uprooted|swept\s+away|washed\s+away|property\s+damaged|land\s+subsided|cracks\s+in\s+houses)\b",
]

RESPONSE_PATTERNS = [
    r"\b(ndrf|sdrf|army\s+deployed|airforce|airlifted|evacuation|evacuated|relief\s+camps|rescue\s+operation|rescue\s+operations|rescue\s+teams|relief\s+material|disaster\s+response|search\s+and\s+rescue|fire\s+brigade|fire\s+tenders|firefighters)\b",
    r"\b(emergency\s+services|fire\s+tenders\s+rushed|helpline\s+started|search\s+operation|relief\s+work|rescue\s+work|rescue\s+efforts|rescuers\s+hunt|rescuers\s+search)\b",
]

# ============================================================
# NEGATIVE NON-INCIDENT & CONTEXT PATTERNS
# ============================================================

FORECAST_PATTERNS = [
    r"\b(forecast|forecasted|forecasting|expected\s+to|likely\s+to|may\s+see|may\s+witness|prediction|weather\s+model|predicted|will\s+see\s+rain|heatwave\s+likely|rain\s+likely|showers\s+likely)\b",
    r"\b(yellow\s+alert|orange\s+alert|red\s+alert|warning\s+issued|advisory\s+issued|alert\s+issued|alert\s+sounded|heavy\s+rain\s+predicted|rain\s+alert|flood\s+alert|cyclone\s+alert)\b",
]

POLICY_MEETING_PATTERNS = [
    r"\b(review\s+meeting|meeting\s+held|policy\s+discussed|preparedness\s+reviewed|mou\s+signed|cabinet\s+approves|held\s+talks|bilateral\s+talks|drills\s+conducted|seminar\s+on\s+disaster|foundation\s+day)\b",
    r"\b(peacekeepers|diplomatic\s+talks|rejects\s+pakistan'?s\s+flood\s+claims|un\s+mission)\b",
]

FUNDING_RELIEF_PATTERNS = [
    r"\b(relief\s+package|compensation\s+announced|funds\s+approved|financial\s+assistance\s+approved|rehabilitation\s+appeal|csr\s+aid|aid\s+package|donates\s+lifelong|extends\s+solidarity|relief\s+contribution|ex-gratia\s+announced|aid\s+for\s+flood-affected)\b",
]

ANALYSIS_OPINION_PATTERNS = [
    r"\b(editorial|opinion|analysis|study\s+reveals|study\s+says|study\s+finds|explained:|in-depth|why\s+.+\s+remains|what'?s\s+the\s+ecology|science\s+behind|environmental\s+strain|lessons\s+from|drishti\s+ias|upsc|ias\s+preparation|guide\s+to|best\s+avoided|how\s+native\s+plants|rethinking|how\s+to\s+survive)\b",
]

ANNIVERSARY_PATTERNS = [
    r"\b(anniversary\s+of|years\s+after|years\s+later|remembers|remembering|recalls|historical|revisiting|lessons\s+from|memories\s+of|decade\s+after|looking\s+back\s+at)\b",
]

METAPHOR_PATTERNS = [
    r"\b(landslide\s+victory|landslide\s+win|election\s+landslide|poll\s+victory|bypoll|vote\s+share|exit\s+poll|assembly\s+election|lok\s+sabha|vidhan\s+sabha|cabinet\s+expansion)\b",
    r"\b(cricket|century|wicket|ipl|trophy|world\s+cup|innings|run\s+drought|medal\s+drought|goal\s+scored|match\s+highlights|badminton|olympics|football\s+match|karate\s+gold|gold\s+medal)\b",
    r"\b(box\s+office|trailer\s+release|teaser\s+release|movie\s+review|ott\s+release|bollywood|tollywood|actor|actress|album\s+release|song\s+release|concert\s+blast|party\s+blast)\b",
    r"\b(stock\s+market|shares\s+crash|startup\s+valuation|sales\s+explosion|population\s+explosion|user\s+explosion|market\s+collapse|funding\s+drought|talent\s+drought|deal\s+drought)\b",
    r"\b(paper\s+leak|exam\s+leak|question\s+paper\s+leak|data\s+leak|whatsapp\s+leak|neet\s+leak)\b",
    r"\b(flash\s+mob|flash\s+sale|spread\s+like\s+wildfire|flood\s+of\s+applications|avalanche\s+of\s+comments|tsunami\s+of\s+memes|tsunami\s+of\s+debt)\b",
]

FOREIGN_PATTERNS = [
    r"\b(in\s+(?:southern\s+|northern\s+|eastern\s+|western\s+)?(?:usa|us|united\s+states|florida|texas|california|japan|china|australia|europe|philippines|indiana|indonesia|canada|uk|london|south\s+sudan|hawaii|france|greece|spain|venezuela|colombia|afghanistan|pakistan|taiwan|mexico|brazil|chile))\b",
    r"\b(in\s+los\s+angeles|in\s+new\s+york|in\s+san\s+francisco|in\s+florida|in\s+texas|in\s+california|in\s+paris|in\s+tokyo|in\s+beijing|in\s+sydney|in\s+toronto|in\s+lahore|in\s+karachi|in\s+islamabad|in\s+kabul|in\s+kathmandu|in\s+dhaka|in\s+colombo)\b",
    r"\b(us\s+state|u\.s\.\s+state|california|los\s+angeles|venezuela|colombia|south\s+sudan|hawaii|indiana\s+flooding)\b",
]


def detect_evidence(text: str, published_dt: Optional[datetime] = None, now_utc: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Extracts structured positive ground evidence, negative indicators,
    true recency metadata, and classifies the article type.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    text_clean = text.lower()

    # 1. Positive Ground Evidence
    casualties = []
    for pat in CASUALTY_PATTERNS:
        if re.search(pat, text_clean):
            casualties.append(pat)

    distress = []
    for pat in DISTRESS_PATTERNS:
        if re.search(pat, text_clean):
            distress.append(pat)

    damage = []
    for pat in DAMAGE_PATTERNS:
        if re.search(pat, text_clean):
            damage.append(pat)

    response = []
    for pat in RESPONSE_PATTERNS:
        if re.search(pat, text_clean):
            response.append(pat)

    has_physical_impact = bool(casualties or distress or damage)
    has_ground_impact = bool(has_physical_impact or response)

    # 2. Negative & Context Indicators
    is_forecast_flag = any(re.search(pat, text_clean) for pat in FORECAST_PATTERNS)
    is_policy_flag = any(re.search(pat, text_clean) for pat in POLICY_MEETING_PATTERNS)
    is_funding_flag = any(re.search(pat, text_clean) for pat in FUNDING_RELIEF_PATTERNS)
    is_analysis_flag = any(re.search(pat, text_clean) for pat in ANALYSIS_OPINION_PATTERNS)
    is_anniversary_flag = any(re.search(pat, text_clean) for pat in ANNIVERSARY_PATTERNS)
    is_metaphor = any(re.search(pat, text_clean) for pat in METAPHOR_PATTERNS)

    # India context detection
    has_india_context = bool(re.search(r"\b(india|indian|imd|ndrf|sdrf|cwc|ndma|mha|air force|army|delhi-ncr|national highway|nh-\d+|state highway)\b", text_clean))
    has_foreign_flag = any(re.search(pat, text_clean) for pat in FOREIGN_PATTERNS)
    is_foreign_only = has_foreign_flag and not has_india_context

    # 3. Incident Date & Freshness Evaluation
    inc_dt, inc_method, is_hist_marker = extract_incident_date(text_clean, published_dt, now_utc)
    freshness = evaluate_freshness(published_dt, inc_dt, is_hist_marker or is_anniversary_flag, now_utc)

    # 4. Refined Forecast & Policy Analysis
    # Critical: Do NOT reject forecast words if actual impact exists!
    is_forecast_only = is_forecast_flag and not has_ground_impact
    is_forecast_plus_impact = is_forecast_flag and has_ground_impact
    is_policy_only = is_policy_flag and not has_ground_impact
    is_funding_only = is_funding_flag and not has_ground_impact
    is_analysis_only = is_analysis_flag and not (has_physical_impact and freshness["published_age_hours"] <= 48)

    # 5. Article Type Classification
    if is_metaphor:
        article_type = "METAPHOR"
    elif is_foreign_only:
        article_type = "FOREIGN_INCIDENT"
    elif is_anniversary_flag:
        article_type = "ANNIVERSARY"
    elif freshness["is_historical"]:
        article_type = "HISTORICAL"
    elif is_forecast_only:
        article_type = "FORECAST_ONLY"
    elif is_analysis_only:
        article_type = "ANALYSIS"
    elif is_funding_only:
        article_type = "FUNDING"
    elif is_policy_only:
        article_type = "POLICY"
    elif has_ground_impact:
        if freshness["is_old_incident_in_recent_article"]:
            article_type = "HISTORICAL"
        elif freshness["freshness_tier"] == "DEVELOPING":
            article_type = "ONGOING_INCIDENT"
        else:
            article_type = "CURRENT_INCIDENT"
    else:
        article_type = "UNKNOWN"

    # Human-readable evidence summary
    evidence_items = []
    if casualties:
        evidence_items.append("Reported casualties, deaths, or recovered bodies")
    if distress:
        evidence_items.append("People trapped, stranded, injured, or submerged")
    if damage:
        evidence_items.append("Infrastructure, structural, or property damage reported")
    if response:
        evidence_items.append("Emergency rescue/NDRF/SDRF mobilization active")
    if is_forecast_plus_impact:
        evidence_items.append("Alert/warning accompanied by verified ground impact")

    return {
        "has_ground_impact": has_ground_impact,
        "has_physical_impact": has_physical_impact,
        "has_casualties": bool(casualties),
        "has_distress": bool(distress),
        "has_damage": bool(damage),
        "has_response": bool(response),
        "is_forecast": is_forecast_flag,
        "is_forecast_only": is_forecast_only,
        "is_forecast_plus_impact": is_forecast_plus_impact,
        "is_policy_only": is_policy_only,
        "is_funding_only": is_funding_only,
        "is_analysis_only": is_analysis_only,
        "is_historical": freshness["is_historical"],
        "is_metaphor": is_metaphor,
        "is_foreign_only": is_foreign_only,
        "has_india_context": has_india_context,
        "article_type": article_type,
        "freshness": freshness,
        "incident_date": freshness.get("incident_date_str"),
        "evidence_summary": evidence_items,
    }
