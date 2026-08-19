"""
DISHA Temporal Extractor & True Recency Service
Handles timezone-aware UTC datetime parsing, relative and explicit incident date extraction,
historical disaster detection, and configurable freshness tier evaluation.
"""

import os
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

# ============================================================
# CONFIGURABLE FRESHNESS PARAMETERS (Defaults)
# ============================================================

NEWS_MAX_AGE_HOURS = int(os.getenv("NEWS_MAX_AGE_HOURS", "72"))
NEWS_ACTIVE_AGE_HOURS = int(os.getenv("NEWS_ACTIVE_AGE_HOURS", "24"))
NEWS_MAX_INCIDENT_AGE_HOURS = int(os.getenv("NEWS_MAX_INCIDENT_AGE_HOURS", "72"))
NEWS_HISTORICAL_CUTOFF_DAYS = int(os.getenv("NEWS_HISTORICAL_CUTOFF_DAYS", "7"))

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9, "sept": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

HISTORICAL_TRIGGERS = [
    r"\b(anniversary\s+of|years\s+after|years\s+later|retrospective|memories\s+of|historical\s+flood|historical\s+disaster|lessons\s+from|revisiting\s+the|looking\s+back\s+at|decade\s+after|recalls|remembering|remembered)\b",
]


def parse_published_date(published_str: Optional[Any]) -> Optional[datetime]:
    """
    Parses diverse RSS, ISO, and human-formatted timestamps into a timezone-aware UTC datetime.
    """
    if not published_str:
        return None

    if isinstance(published_str, datetime):
        if published_str.tzinfo is None:
            return published_str.replace(tzinfo=timezone.utc)
        return published_str.astimezone(timezone.utc)

    p_str = str(published_str).strip()
    if not p_str:
        return None

    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",     # Tue, 18 Aug 2026 14:30:00 GMT
        "%a, %d %b %Y %H:%M:%S %z",     # Tue, 18 Aug 2026 14:30:00 +0000
        "%a, %d %b %Y %H:%M:%S",
        "%d %b %Y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%SZ",           # 2026-08-18T14:30:00Z
        "%Y-%m-%dT%H:%M:%S%z",          # ISO format with timezone
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(p_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue

    # Fallback to standard ISO parser
    try:
        dt = datetime.fromisoformat(p_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    return None


def extract_incident_date(
    text: str,
    published_dt: Optional[datetime],
    now_utc: Optional[datetime] = None,
) -> Tuple[Optional[datetime], str, bool]:
    """
    Extracts the estimated ground incident date, the resolution method, and whether a historical trigger is present.
    Normalizes relative temporal expressions using the article's published_at date as reference.
    
    Returns: (incident_datetime, resolution_method, is_historical_marker)
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    ref_dt = published_dt if published_dt else now_utc
    text_clean = text.lower()

    # 1. Check explicit retrospective / historical keywords
    for pat in HISTORICAL_TRIGGERS:
        if re.search(pat, text_clean):
            return None, "historical_trigger", True

    # 2. Check explicit years older than reference year (e.g., "in 2023", "of 2024")
    year_matches = re.findall(r"\b(?:in|during|of|since)?\s*(20\d\d|19\d\d)\b", text_clean)
    for yr_str in year_matches:
        try:
            yr = int(yr_str)
            if yr < ref_dt.year:
                dt = datetime(yr, 1, 1, tzinfo=timezone.utc)
                return dt, f"past_year_{yr}", True
        except ValueError:
            pass

    # 3. Check "X years ago" / "last year"
    years_ago = re.search(r"\b(?:(\d+)\s+years?\s+ago|last\s+year)\b", text_clean)
    if years_ago:
        n = int(years_ago.group(1)) if years_ago.group(1) else 1
        dt = ref_dt - timedelta(days=365 * n)
        return dt, f"{n}_years_ago", True

    # 4. Check "X months ago" / "last month" / "earlier this month"
    months_ago = re.search(r"\b(?:(\d+)\s+months?\s+ago|last\s+month|earlier\s+this\s+month)\b", text_clean)
    if months_ago:
        n = int(months_ago.group(1)) if months_ago.group(1) else 1
        dt = ref_dt - timedelta(days=30 * n)
        return dt, f"{n}_months_ago", False

    # 5. Check "X weeks ago" / "last week"
    weeks_ago = re.search(r"\b(?:(\d+)\s+weeks?\s+ago|last\s+week)\b", text_clean)
    if weeks_ago:
        n = int(weeks_ago.group(1)) if weeks_ago.group(1) else 1
        dt = ref_dt - timedelta(days=7 * n)
        return dt, f"{n}_weeks_ago", False

    # 6. Check "X days ago"
    days_ago = re.search(r"\b(\d+)\s+days?\s+ago\b", text_clean)
    if days_ago:
        n = int(days_ago.group(1))
        dt = ref_dt - timedelta(days=n)
        return dt, f"{n}_days_ago", False

    # 7. Check "yesterday" / "last night"
    if re.search(r"\b(yesterday|last night)\b", text_clean):
        dt = ref_dt - timedelta(days=1)
        return dt, "yesterday", False

    # 8. Check "today" / "this morning" / "earlier today" / "hours ago"
    if re.search(r"\b(today|this morning|earlier today|hours ago|just in)\b", text_clean):
        return ref_dt, "today", False

    # 9. Check explicit weekday: "on monday", "on tuesday", etc.
    for i, wday in enumerate(WEEKDAYS):
        if re.search(r"\bon\s+" + wday + r"\b", text_clean):
            ref_wday = ref_dt.weekday()  # 0 = Monday, 6 = Sunday
            diff = (ref_wday - i) % 7
            if diff == 0:
                diff = 7  # If same day name mentioned with 'on', refer to previous cycle
            dt = ref_dt - timedelta(days=diff)
            return dt, f"on_{wday}", False

    # 10. Check explicit Date in text (e.g. "18 August", "August 18", "7 July 2026")
    date_pat1 = r"\b([0-3]?\d)(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s*,?\s*(\d{4}))?\b"
    m1 = re.search(date_pat1, text_clean)
    if m1:
        day = int(m1.group(1))
        month_str = m1.group(2)[:3]
        month = MONTH_MAP.get(month_str, ref_dt.month)
        year = int(m1.group(3)) if m1.group(3) else ref_dt.year
        try:
            dt = datetime(year, month, day, tzinfo=timezone.utc)
            is_hist = (ref_dt - dt).days > NEWS_HISTORICAL_CUTOFF_DAYS
            return dt, "explicit_date", is_hist
        except ValueError:
            pass

    date_pat2 = r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+([0-3]?\d)(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?\b"
    m2 = re.search(date_pat2, text_clean)
    if m2:
        month_str = m2.group(1)[:3]
        month = MONTH_MAP.get(month_str, ref_dt.month)
        day = int(m2.group(2))
        year = int(m2.group(3)) if m2.group(3) else ref_dt.year
        try:
            dt = datetime(year, month, day, tzinfo=timezone.utc)
            is_hist = (ref_dt - dt).days > NEWS_HISTORICAL_CUTOFF_DAYS
            return dt, "explicit_date", is_hist
        except ValueError:
            pass

    # Default fallback: assume incident occurred around published time
    return ref_dt, "published_date_default", False


def evaluate_freshness(
    published_dt: Optional[datetime],
    incident_dt: Optional[datetime],
    is_historical_marker: bool = False,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Computes true publication age, incident age, freshness classification tier,
    and granular recency scores.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    # 1. Publication age
    if published_dt:
        pub_age_hours = max(0.0, (now_utc - published_dt).total_seconds() / 3600.0)
    else:
        pub_age_hours = 0.0  # Fresh default

    # 2. Incident age
    if incident_dt:
        inc_age_hours = max(0.0, (now_utc - incident_dt).total_seconds() / 3600.0)
    else:
        inc_age_hours = pub_age_hours

    # 3. Detect Old Incident in Recent Article
    is_old_incident_in_recent_article = (
        pub_age_hours <= NEWS_MAX_AGE_HOURS
        and inc_age_hours > NEWS_MAX_INCIDENT_AGE_HOURS
    )

    # 4. Detect Historical status
    is_historical = (
        is_historical_marker
        or inc_age_hours > (NEWS_HISTORICAL_CUTOFF_DAYS * 24)
        or pub_age_hours > (NEWS_HISTORICAL_CUTOFF_DAYS * 24)
    )

    # 5. Freshness Tier Classification
    if is_historical:
        freshness_tier = "HISTORICAL"
    elif inc_age_hours <= NEWS_ACTIVE_AGE_HOURS:
        freshness_tier = "BREAKING"
    elif inc_age_hours <= 48:
        freshness_tier = "RECENT"
    elif inc_age_hours <= NEWS_MAX_INCIDENT_AGE_HOURS:
        freshness_tier = "DEVELOPING"
    else:
        freshness_tier = "STALE"

    # 6. Granular Recency Score (Published Recency)
    if pub_age_hours <= 6:
        pub_recency_score = 5.0
    elif pub_age_hours <= 24:
        pub_recency_score = 4.0
    elif pub_age_hours <= 48:
        pub_recency_score = 3.0
    elif pub_age_hours <= NEWS_MAX_AGE_HOURS:
        pub_recency_score = 1.0
    elif pub_age_hours <= (NEWS_HISTORICAL_CUTOFF_DAYS * 24):
        pub_recency_score = -3.0
    else:
        pub_recency_score = -8.0

    # 7. Incident Recency Score
    if is_historical:
        incident_recency_score = -10.0
    elif inc_age_hours <= NEWS_ACTIVE_AGE_HOURS:
        incident_recency_score = 5.0
    elif inc_age_hours <= 48:
        incident_recency_score = 4.0
    elif inc_age_hours <= NEWS_MAX_INCIDENT_AGE_HOURS:
        incident_recency_score = 2.0
    else:
        incident_recency_score = -5.0

    return {
        "freshness_tier": freshness_tier,
        "is_historical": is_historical,
        "is_old_incident_in_recent_article": is_old_incident_in_recent_article,
        "published_age_hours": round(pub_age_hours, 2),
        "incident_age_hours": round(inc_age_hours, 2),
        "pub_recency_score": pub_recency_score,
        "incident_recency_score": incident_recency_score,
        "incident_date_str": incident_dt.strftime("%Y-%m-%d") if incident_dt else None,
    }
