"""
DISHA Real-Time Disaster Intelligence Pipeline
Master Ingestion, Pre-filtering, Temporal Scoring, AI Verification, and Event Deduplication Pipeline.
"""

import os
import re
import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs, urlunparse
from typing import List, Dict, Any, Optional, Tuple, Set

import feedparser
import requests
from dotenv import load_dotenv

# Ensure .env is loaded
_backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_backend_dir / ".env")
load_dotenv()

from app.database.mongodb import db
from app.services.geocoding import geocode_location, detect_locations
from app.services.source_scorer import score_source
from app.services.temporal_extractor import (
    parse_published_date,
    extract_incident_date,
    evaluate_freshness,
    NEWS_MAX_AGE_HOURS,
    NEWS_ACTIVE_AGE_HOURS,
    NEWS_MAX_INCIDENT_AGE_HOURS,
    NEWS_HISTORICAL_CUTOFF_DAYS,
)
from app.services.evidence_detector import detect_evidence
from app.services.quality_scorer import score_article, MIN_LOCAL_CANDIDATE_SCORE
from app.services.event_clustering import (
    pre_cluster_candidates,
    generate_stable_event_id,
    find_matching_active_event,
)
from app.services.gemini_controller import (
    QuotaController,
    validate_and_retry_gemini_batch,
    GEMINI_MODEL,
)

# ============================================================
# CONFIGURATION
# ============================================================

GEMINI_BATCH_SIZE = int(os.getenv("GEMINI_BATCH_SIZE", "10"))
NEWS_RESULTS_PER_QUERY = int(os.getenv("NEWS_RESULTS_PER_QUERY", "25"))
MAX_PENDING_AI_RECOVERY = int(os.getenv("MAX_PENDING_AI_RECOVERY", "50"))
GEMINI_CONFIDENCE_THRESHOLD = float(os.getenv("GEMINI_CONFIDENCE_THRESHOLD", "0.70"))
GEMINI_AUTO_VERIFY_THRESHOLD = float(os.getenv("GEMINI_AUTO_VERIFY_THRESHOLD", "0.90"))
ENABLE_CORROBORATION = os.getenv("ENABLE_CORROBORATION", "true").lower() == "true"
ENABLE_GEOCODING = os.getenv("ENABLE_GEOCODING", "true").lower() == "true"
MAX_AI_RETRIES = int(os.getenv("MAX_AI_RETRIES", "3"))

# MongoDB Collections
news_temp = db["news_temp"]
disaster_events = db["disaster_events"]
rejected_news = db["rejected_news"]
ai_usage = db["ai_usage"]

quota_controller = QuotaController(ai_usage)

# ============================================================
# IMPACT-FOCUSED NEWS QUERY FAMILIES
# ============================================================

NEWS_QUERIES = [
    # Flood & Inundation
    "flood India",
    "flash flood India",
    "flood rescue India",
    "river overflow India",
    "villages submerged India",
    "floods Assam OR Bihar OR Odisha OR Kerala OR Bengal",

    # Landslides
    "landslide India",
    "landslide deaths India",
    "landslide rescue India",
    "landslide trapped India",
    "landslide Himachal OR Uttarakhand OR Kerala OR Northeast",

    # Earthquake & Tremors
    "earthquake tremors India",
    "earthquake India damage",
    "earthquake India casualties",

    # Cyclone & Storms
    "cyclone India landfall",
    "cyclone India evacuation",
    "cloudburst Himachal OR Uttarakhand OR Kashmir",
    "heavy rainfall waterlogging India",

    # Fires & Industrial Disasters
    "factory fire blaze India",
    "fire India deaths",
    "chemical leak OR gas leak India",
    "explosion blast India",

    # Collapse & Structural Failures
    "building collapse India",
    "bridge collapse India",
    "tunnel collapse India",
    "dam breach OR reservoir overflow India",

    # Transport & High-Impact Emergencies
    "train accident OR derailment India",
    "bus accident gorge India",
    "lightning strike deaths India",
    "severe heatwave India deaths",
    "cold wave India deaths",
]

# Comprehensive Disaster Keywords Mapping
DISASTERS = {
    "flood": [
        "flood", "floods", "flooding", "flooded", "flash flood", "flash floods",
        "inundation", "inundated", "waterlogging", "waterlogged", "submerged",
        "rivers overflow", "river overflowing", "swollen river", "water entering houses", "deluge"
    ],
    "earthquake": [
        "earthquake", "earthquakes", "earth tremor", "earth tremors",
        "seismic activity", "tremors felt", "tremor", "tremors", "quake", "quakes",
        "aftershock", "aftershocks"
    ],
    "landslide": [
        "landslide", "landslides", "mudslide", "mudslides", "rockslide",
        "rockslides", "landslip", "landslips", "debris flow", "hill collapse"
    ],
    "cyclone": [
        "cyclone", "cyclones", "cyclonic storm", "tropical storm", "super cyclone",
        "severe cyclonic", "landfall", "typhoon", "hurricane"
    ],
    "cloudburst": [
        "cloudburst", "cloudbursts"
    ],
    "lightning": [
        "lightning", "lightning strike", "lightning strikes", "lightning struck",
        "thunderbolt", "struck by lightning"
    ],
    "heavy_rain": [
        "heavy rain", "heavy rains", "heavy rainfall", "torrential rain",
        "torrential rains", "extreme rainfall", "incessant rain", "incessant rains",
        "downpour", "monsoon fury", "record rainfall"
    ],
    "heatwave": [
        "heatwave", "heatwaves", "heat wave", "heat waves", "severe heatwave",
        "sunstroke", "scorching heat"
    ],
    "cold_wave": [
        "cold wave", "cold waves", "coldwave", "coldwaves", "severe cold wave",
        "chilling cold"
    ],
    "wildfire": [
        "wildfire", "wildfires", "forest fire", "forest fires", "bushfire",
        "bushfires", "jungle fire"
    ],
    "avalanche": [
        "avalanche", "avalanches", "snowslide", "snow slide"
    ],
    "tsunami": [
        "tsunami", "tsunamis"
    ],
    "drought": [
        "drought", "droughts", "severe drought", "acute water scarcity", "water crisis"
    ],
    "dam_failure": [
        "dam failure", "dam collapse", "dam breach", "dam breached", "dam burst",
        "dam overflow", "barrage breach", "embankment breach", "canal breach"
    ],
    "building_collapse": [
        "building collapse", "building collapses", "building collapsed",
        "structure collapse", "structure collapsed", "roof collapse", "roof collapsed",
        "bridge collapse", "bridge collapsed", "wall collapse", "wall collapsed",
        "scaffolding collapse", "tunnel collapse", "tunnel accident"
    ],
    "fire_accident": [
        "massive fire", "major fire", "devastating fire", "blaze", "inferno",
        "charred to death", "gutted in fire", "gutted by fire", "fire breaks out",
        "fire broke out", "hotel fire", "hospital fire", "residential fire",
        "commercial complex fire", "firecracker unit blast", "cylinder blast"
    ],
    "industrial_accident": [
        "industrial accident", "industrial disaster", "chemical leak", "chemical leaks",
        "gas leak", "gas leaks", "toxic gas leak", "factory fire", "boiler blast",
        "boiler explosion", "blast in chemical factory", "mine collapse"
    ],
    "explosion": [
        "explosion", "explosions", "bomb blast", "bomb blasts", "ied blast",
        "blast killed", "blast injured", "detonation"
    ],
    "transport_accident": [
        "train accident", "train crash", "train derailment", "coaches derailed",
        "bus plunges into gorge", "bus falls into gorge", "bus fell into gorge",
        "bus accident", "boat capsize", "boat capsized", "plane crash", "helicopter crash"
    ],
}

GLOBAL_EXCLUSIONS = [
    r"\b(landslide\s+victory|landslide\s+win|election\s+landslide|poll\s+victory|bypoll|vote\s+share|exit\s+poll|assembly\s+election|lok\s+sabha|vidhan\s+sabha|cabinet\s+expansion)\b",
    r"\b(cricket|century|wicket|ipl|trophy|world\s+cup|innings|run\s+drought|medal\s+drought|goal\s+scored|match\s+highlights|badminton|olympics|football\s+match|karate\s+gold|gold\s+medal)\b",
    r"\b(box\s+office|trailer\s+release|teaser\s+release|movie\s+review|ott\s+release|bollywood|tollywood|actor|actress|album\s+release|song\s+release|concert\s+blast|party\s+blast)\b",
    r"\b(stock\s+market|shares\s+crash|startup\s+valuation|sales\s+explosion|population\s+explosion|user\s+explosion|market\s+collapse|funding\s+drought|talent\s+drought|deal\s+drought)\b",
    r"\b(paper\s+leak|exam\s+leak|question\s+paper\s+leak|data\s+leak|whatsapp\s+leak|neet\s+leak)\b",
    r"\b(flash\s+mob|flash\s+sale|spread\s+like\s+wildfire|flood\s+of\s+applications|avalanche\s+of\s+comments|tsunami\s+of\s+memes|tsunami\s+of\s+debt)\b",
]

FOREIGN_ONLY_INDICATORS = [
    r"\b(in\s+(?:southern\s+|northern\s+|eastern\s+|western\s+)?(?:usa|us|united\s+states|florida|texas|california|japan|china|australia|europe|philippines|indiana|indonesia|canada|uk|london|south\s+sudan|hawaii|france|greece|spain|venezuela|colombia|afghanistan|pakistan|taiwan|mexico|brazil|chile))\b",
    r"\b(in\s+los\s+angeles|in\s+new\s+york|in\s+san\s+francisco|in\s+florida|in\s+texas|in\s+california|in\s+paris|in\s+tokyo|in\s+beijing|in\s+sydney|in\s+toronto|in\s+lahore|in\s+karachi|in\s+islamabad|in\s+kabul|in\s+kathmandu|in\s+dhaka|in\s+colombo)\b",
    r"\b(us\s+state|u\.s\.\s+state|california|los\s+angeles|venezuela|colombia|south\s+sudan|hawaii|indiana\s+flooding)\b",
]


def clean_text(text: str) -> str:
    """Removes HTML tags, punctuation, and extra whitespace."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_url(url: str) -> str:
    """Strips tracking query parameters from URLs for canonical deduplication."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path
        qs = parse_qs(parsed.query)
        clean_qs = {k: v for k, v in qs.items() if not k.startswith("utm_") and k not in ("fbclid", "gclid", "ocid")}
        clean_query = "&".join(f"{k}={v[0]}" for k, v in clean_qs.items())
        return urlunparse((scheme, netloc, path, parsed.params, clean_query, ""))
    except Exception:
        return url.strip()


def generate_article_id(article: dict) -> str:
    """Generates a stable sha256 hash using normalized URL or title."""
    norm_url = normalize_url(article.get("url", ""))
    if norm_url:
        return hashlib.sha256(norm_url.encode("utf-8")).hexdigest()
    raw_title = clean_text(article.get("title", ""))
    return hashlib.sha256(raw_title.encode("utf-8")).hexdigest()


def detect_disaster_keywords(text: str) -> List[Tuple[str, str]]:
    """Detects matching disaster types and keywords in text."""
    found = []
    for disaster_type, keywords in DISASTERS.items():
        for keyword in keywords:
            if re.search(r"\b" + re.escape(keyword) + r"\b", text):
                found.append((disaster_type, keyword))
                break
    return found


def is_excluded_headline(text: str) -> Tuple[bool, str]:
    """Checks for metaphor, non-disaster sports/entertainment/exam, or foreign indicators."""
    for pattern in GLOBAL_EXCLUSIONS:
        if re.search(pattern, text):
            return True, "metaphor_or_non_disaster_topic"

    has_india = bool(re.search(r"\b(india|indian|imd|ndrf|sdrf|delhi|mumbai|kerala|assam|bihar|uttarakhand|himachal|odisha|gujarat|bengal|kashmir|punjab|tamil nadu|karnataka|andhra|telangana|uttar pradesh|rajasthan|maharashtra|jharkhand|chhattisgarh|manipur|tripura|meghalaya|sikkim|goa|ladakh)\b", text))
    for foreign_pat in FOREIGN_ONLY_INDICATORS:
        if re.search(foreign_pat, text) and not has_india:
            return True, "foreign_only_event"

    return False, ""


def local_filter(article: dict, now_utc: Optional[datetime] = None) -> dict:
    """
    High-recall pre-filter. Removes obvious garbage (sports, metaphors, foreign events)
    while ensuring articles with ground impact, trapped workers, SDRF rescues, or casualties
    are eligible even without traditional disaster keywords.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    title = article.get("title", "")
    summary = article.get("description", "")
    full_text = f"{title} {summary}"
    text_clean = clean_text(full_text)

    # 1. Global Exclusion check
    excluded, reason = is_excluded_headline(text_clean)
    if excluded:
        return {
            "passed": False,
            "reason": reason,
            "disasters": [],
            "locations": [],
            "article_type": "METAPHOR" if reason == "metaphor_or_non_disaster_topic" else "FOREIGN_INCIDENT",
        }

    # 2. Location & Geographic Entity Detection
    loc_res = detect_locations(full_text)
    locations = loc_res.get("locations", [])
    has_india = loc_res.get("has_india", False)

    # 3. Ground Evidence & Disaster Category Extraction
    pub_dt = parse_published_date(article.get("published_at"))
    ev = detect_evidence(full_text, published_dt=pub_dt, now_utc=now_utc)
    disaster_hits = detect_disaster_keywords(text_clean)

    # Rejection of pure foreign events without India context
    if (ev.get("is_foreign_only") or not has_india):
        return {
            "passed": False,
            "reason": "foreign_only_event" if ev.get("is_foreign_only") else "no_india_location_or_context",
            "disasters": [d[0] for d in disaster_hits],
            "locations": locations,
            "article_type": "FOREIGN_INCIDENT" if ev.get("is_foreign_only") else ev.get("article_type", "UNKNOWN"),
        }

    # Eligibility Criteria (HIGH RECALL WITH MANDATORY INDIA CONTEXT)
    # A candidate passes if has_india AND (disaster_hits OR ground impact OR emergency response)
    is_eligible = (
        bool(disaster_hits)
        or ev["has_ground_impact"]
        or ev["has_response"]
    )

    if not is_eligible:
        return {
            "passed": False,
            "reason": "no_disaster_or_impact_evidence",
            "disasters": [d[0] for d in disaster_hits],
            "locations": locations,
            "article_type": ev.get("article_type", "UNKNOWN"),
        }

    disaster_types = list({d[0] for d in disaster_hits})
    if not disaster_types and ev["has_ground_impact"]:
        disaster_types = ["emergency_incident"]

    return {
        "passed": True,
        "reason": "candidate",
        "disasters": disaster_types,
        "locations": locations,
        "article_type": ev.get("article_type", "UNKNOWN"),
    }


def google_news(query: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetches articles from Google News RSS for a specified query.
    Prioritizes the newest articles and limits output per query.
    """
    if max_results is None:
        max_results = NEWS_RESULTS_PER_QUERY

    url = (
        "https://news.google.com/rss/search?"
        f"q={quote(query)}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        entries = getattr(feed, "entries", [])
        if not entries:
            return []

        # Sort entries by parsed published date descending to prioritize the newest articles
        def _get_entry_published_ts(entry) -> float:
            pub_str = entry.get("published", "")
            dt = parse_published_date(pub_str)
            return dt.timestamp() if dt else 0.0

        sorted_entries = sorted(entries, key=_get_entry_published_ts, reverse=True)
        selected_entries = sorted_entries[:max_results]

        articles = []
        for item in selected_entries:
            source = ""
            if hasattr(item, "source") and isinstance(item.source, dict):
                source = item.source.get("title", "")
            elif hasattr(item, "source"):
                source = getattr(item.source, "title", "")

            raw_url = item.get("link", "")
            norm_url = normalize_url(raw_url)

            article = {
                "title": item.get("title", ""),
                "url": norm_url,
                "raw_url": raw_url,
                "published_at": item.get("published", ""),
                "description": item.get("summary", ""),
                "source": source,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            article["_id"] = generate_article_id(article)
            articles.append(article)

        return articles

    except Exception as e:
        print(f"[NEWS ERROR] Query '{query}': {repr(e)}")
        return []


def get_existing_article_ids(article_ids: List[str]) -> Set[str]:
    """
    Performs fast bulk lookups across MongoDB collections to identify previously processed or rejected IDs.
    """
    if not article_ids:
        return set()

    found_ids = set()

    # Look in news_temp (only already finalized ones, not pending_ai)
    for doc in news_temp.find(
        {"_id": {"$in": article_ids}, "status": {"$in": ["processed", "processed_sibling", "rejected_local", "rejected_quality", "rejected_ai", "rejected_ai_sibling"]}},
        {"_id": 1}
    ):
        found_ids.add(doc["_id"])

    # Look in disaster_events
    for doc in disaster_events.find({"article_id": {"$in": article_ids}}, {"article_id": 1}):
        found_ids.add(doc["article_id"])

    # Look in rejected_news
    for doc in rejected_news.find({"article_id": {"$in": article_ids}}, {"article_id": 1}):
        found_ids.add(doc["article_id"])

    return found_ids


def get_pending_ai_candidates(max_count: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves pending AI candidates from news_temp for safe retry handling.
    """
    cursor = news_temp.find(
        {
            "status": "pending_ai",
            "retry_count": {"$lt": MAX_AI_RETRIES},
        }
    ).sort("fetched_at", -1).limit(max_count)

    pending = []
    for doc in cursor:
        pending.append(doc)
    return pending


def save_temp_article(article: dict, filter_result: dict, quality_result: Optional[dict] = None):
    """Saves or updates processing state in news_temp."""
    article["local_filter"] = filter_result
    if quality_result:
        article["quality_score"] = quality_result
        article["candidate_priority_score"] = quality_result.get("candidate_priority_score", 0.0)
        article["article_type"] = quality_result.get("article_type", "UNKNOWN")
        article["freshness_tier"] = quality_result.get("freshness_tier", "RECENT")

    if not filter_result.get("passed"):
        article["status"] = "rejected_local"
    elif quality_result and not quality_result.get("passed"):
        article["status"] = "rejected_quality"
    else:
        article["status"] = "pending_ai"

    if "retry_count" not in article:
        article["retry_count"] = 0

    news_temp.update_one(
        {"_id": article["_id"]},
        {"$set": article},
        upsert=True,
    )


# ============================================================
# MASTER NEWS INGESTION & CLASSIFICATION PIPELINE
# ============================================================

def fetch_gnews() -> dict:
    """
    Executes the production DISHA disaster intelligence pipeline:
    Current Queries -> RSS Ingestion -> Normalization -> Deduplication ->
    High-Recall Local Filter -> True-Recency Quality Scoring ->
    Priority Ranking -> Pre-Clustering -> Validated Gemini Verification ->
    Selective Retries -> Fine-Grained Event Corroboration & Geocoding ->
    Full Metrics Reporting.
    """
    print("\n" + "=" * 75)
    print("DISHA PRODUCTION DISASTER INTELLIGENCE PIPELINE")
    print("=" * 75)

    started_at = datetime.now(timezone.utc)
    all_articles = []

    # --------------------------------------------------------
    # 1. RAW INGESTION FROM GOOGLE NEWS
    # --------------------------------------------------------
    for query in NEWS_QUERIES:
        print(f"[NEWS] Fetching query: {query}")
        articles = google_news(query)
        print(f"[NEWS] Found: {len(articles)}")
        all_articles.extend(articles)

    total_raw = len(all_articles)
    print(f"[NEWS] Total raw articles fetched: {total_raw}")

    # --------------------------------------------------------
    # 2. URL & CONTENT HASH DEDUPLICATION
    # --------------------------------------------------------
    unique_articles = {}
    for article in all_articles:
        art_id = article.get("_id")
        if not art_id:
            continue
        if art_id not in unique_articles:
            unique_articles[art_id] = article

    duplicates_count = total_raw - len(unique_articles)
    print(f"[DEDUP] Unique articles: {len(unique_articles)} (Duplicates: {duplicates_count})")

    # --------------------------------------------------------
    # 3. BULK DATABASE CHECK FOR EXISTING ARTICLES
    # --------------------------------------------------------
    all_unique_ids = list(unique_articles.keys())
    existing_ids = get_existing_article_ids(all_unique_ids)
    print(f"[DB] Previously finalized articles: {len(existing_ids)}")

    new_articles = [a for a_id, a in unique_articles.items() if a_id not in existing_ids]

    # --------------------------------------------------------
    # 4. HARD LOCAL FILTERING (HIGH RECALL)
    # --------------------------------------------------------
    passed_local_filter = []
    local_rejected_count = 0

    for article in new_articles:
        filter_res = local_filter(article, now_utc=started_at)
        if filter_res["passed"]:
            article["local_filter"] = filter_res
            passed_local_filter.append(article)
        else:
            local_rejected_count += 1
            save_temp_article(article, filter_res)
            rejected_news.update_one(
                {"article_id": article["_id"]},
                {
                    "$set": {
                        "article_id": article["_id"],
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", ""),
                        "reason": filter_res.get("reason"),
                        "article_type": filter_res.get("article_type"),
                        "stage": "local",
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=True,
            )

    print(f"[FILTER] Passed Local Filter: {len(passed_local_filter)} (Rejected: {local_rejected_count})")

    # --------------------------------------------------------
    # 5. QUALITY SCORING & INCIDENT EVIDENCE RANKING
    # --------------------------------------------------------
    quality_candidates = []
    quality_rejected_count = 0
    old_news_rejected = 0
    forecast_rejected = 0
    foreign_rejected = 0

    for article in passed_local_filter:
        disasters = article["local_filter"].get("disasters", [])
        locations = article["local_filter"].get("locations", [])
        q_res = score_article(article, disasters, locations, now=started_at)
        article["quality_score"] = q_res
        article["candidate_priority_score"] = q_res.get("candidate_priority_score", 0.0)

        # Track granular rejection categories
        reasons = q_res.get("rejection_reasons", [])
        if "old_incident_in_recent_article" in reasons or "historical_or_anniversary_story" in reasons:
            old_news_rejected += 1
        if "forecast_without_ground_impact" in reasons:
            forecast_rejected += 1
        if "foreign_exclusive_event" in reasons:
            foreign_rejected += 1

        if q_res["passed"]:
            save_temp_article(article, article["local_filter"], q_res)
            quality_candidates.append(article)
        else:
            quality_rejected_count += 1
            save_temp_article(article, article["local_filter"], q_res)
            rejection_reason = (
                reasons[0]
                if reasons
                else f"low_quality_score_{q_res.get('total_score')}"
            )
            stage_name = "temporal_old" if ("old_incident" in rejection_reason or "historical" in rejection_reason) else "quality"

            rejected_news.update_one(
                {"article_id": article["_id"]},
                {
                    "$set": {
                        "article_id": article["_id"],
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", ""),
                        "reason": rejection_reason,
                        "article_type": q_res.get("article_type"),
                        "freshness_tier": q_res.get("freshness_tier"),
                        "quality_score": q_res.get("total_score"),
                        "stage": stage_name,
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=True,
            )

    print(f"[SCORE] High-Quality New Candidates: {len(quality_candidates)} (Rejected: {quality_rejected_count})")

    # --------------------------------------------------------
    # 6. PENDING AI QUEUE RECOVERY & PRIORITY RANKING
    # --------------------------------------------------------
    pending_ai_items = get_pending_ai_candidates(max_count=MAX_PENDING_AI_RECOVERY)
    pending_retried_count = len(pending_ai_items)
    print(f"[QUEUE] Pending AI candidates recovered for retry: {pending_retried_count}")

    # Combine new quality candidates and pending AI candidates
    all_ai_candidates_dict = {a["_id"]: a for a in quality_candidates}
    for p_art in pending_ai_items:
        if p_art["_id"] not in all_ai_candidates_dict:
            all_ai_candidates_dict[p_art["_id"]] = p_art

    combined_candidates = list(all_ai_candidates_dict.values())

    # Sort descending by candidate_priority_score (True Recency + Ground Impact first)
    combined_candidates.sort(
        key=lambda c: c.get("candidate_priority_score", c.get("quality_score", {}).get("total_score", 0)),
        reverse=True,
    )

    # --------------------------------------------------------
    # 7. EVENT PRE-CLUSTERING & TOP-N SELECTION
    # --------------------------------------------------------
    gemini_candidates = pre_cluster_candidates(combined_candidates)
    pre_clusters_count = len(gemini_candidates)
    print(f"[CLUSTER] Clustered Candidates for AI Verification: {pre_clusters_count}")

    # --------------------------------------------------------
    # 8. QUOTA-AWARE GEMINI BATCH CLASSIFICATION & VALIDATION
    # --------------------------------------------------------
    gemini_requests_count = 0
    gemini_articles_processed = 0
    ai_rejected_count = 0
    ai_verified_count = 0
    events_created_count = 0
    events_updated_count = 0
    events_merged_count = 0
    geocoding_success_count = 0
    geocoding_failed_count = 0

    if not gemini_candidates:
        print("[GEMINI] No candidates require AI verification.")
    else:
        for i in range(0, len(gemini_candidates), GEMINI_BATCH_SIZE):
            batch = gemini_candidates[i : i + GEMINI_BATCH_SIZE]

            if not quota_controller.can_make_request():
                print("[GEMINI] Daily quota limit reached. Retaining remaining batch in pending_ai queue.")
                break

            print(f"[GEMINI] Processing batch {i // GEMINI_BATCH_SIZE + 1} ({len(batch)} candidates)...")
            compact_articles = [
                {
                    "id": a["_id"],
                    "title": a.get("title", ""),
                    "description": clean_text(a.get("description", ""))[:700],
                    "source": a.get("source", ""),
                    "published_at": a.get("published_at", ""),
                    "extracted_incident_date": a.get("quality_score", {}).get("incident_date"),
                    "extracted_locations": a.get("local_filter", {}).get("locations", []),
                    "candidate_priority_score": a.get("candidate_priority_score", 0.0),
                }
                for a in batch
            ]

            # Validate and selective retry missing IDs
            results, calls_made = validate_and_retry_gemini_batch(
                compact_articles,
                quota_controller,
                max_missing_retries=2,
            )
            gemini_requests_count += calls_made
            gemini_articles_processed += len(batch)

            if not results:
                print("[GEMINI] Batch execution returned no valid results. Updating retry count and retaining as pending_ai.")
                for art in batch:
                    news_temp.update_one(
                        {"_id": art["_id"]},
                        {
                            "$set": {
                                "status": "pending_ai",
                                "last_ai_attempt_at": datetime.now(timezone.utc).isoformat(),
                            },
                            "$inc": {"retry_count": 1},
                        },
                    )
                continue

            # Map results to batch articles
            batch_map = {a["_id"]: a for a in batch}
            verified_ids = set()

            for res in results:
                art_id = res.get("id")
                art = batch_map.get(art_id)
                if not art:
                    continue

                verified_ids.add(art_id)
                is_disaster = bool(res.get("is_disaster", False))
                is_current = bool(res.get("is_current", True))
                is_hist = bool(res.get("is_historical", False))
                is_forecast = bool(res.get("is_forecast_only", False))
                is_india = bool(res.get("is_india", True))

                try:
                    confidence = float(res.get("confidence", 0.0))
                except (TypeError, ValueError):
                    confidence = 0.0

                # ----------------------------------------------------
                # AI REJECTION LOGIC
                # ----------------------------------------------------
                should_reject = (
                    not is_disaster
                    or not is_india
                    or is_hist
                    or is_forecast
                    or not is_current
                    or confidence < GEMINI_CONFIDENCE_THRESHOLD
                )

                if should_reject:
                    ai_rejected_count += 1
                    if not is_india:
                        rejection_reason = "foreign_disaster_not_in_india"
                        stage_name = "foreign"
                    elif is_hist or not is_current:
                        rejection_reason = "historical_or_old_disaster_report"
                        stage_name = "temporal_old"
                    elif is_forecast:
                        rejection_reason = "forecast_advisory_without_impact"
                        stage_name = "forecast"
                    elif not is_disaster:
                        rejection_reason = res.get("reason") or "ai_non_disaster"
                        stage_name = "ai"
                    else:
                        rejection_reason = f"low_ai_confidence_{confidence:.2f}"
                        stage_name = "ai"

                    rejected_news.update_one(
                        {"article_id": art_id},
                        {
                            "$set": {
                                "article_id": art_id,
                                "title": art.get("title", ""),
                                "url": art.get("url", ""),
                                "source": art.get("source", ""),
                                "reason": rejection_reason,
                                "article_type": res.get("article_type", art.get("article_type")),
                                "confidence": confidence,
                                "stage": stage_name,
                                "processed_at": datetime.now(timezone.utc).isoformat(),
                            }
                        },
                        upsert=True,
                    )
                    news_temp.update_one(
                        {"_id": art_id},
                        {"$set": {"status": "rejected_ai"}},
                    )

                    # Update sibling articles
                    for sib_id in art.get("cluster_sibling_ids", []):
                        if sib_id != art_id:
                            news_temp.update_one(
                                {"_id": sib_id},
                                {"$set": {"status": "rejected_ai_sibling"}},
                            )
                    continue

                # ----------------------------------------------------
                # AI VERIFIED DISASTER EVENT CREATION / MERGE
                # ----------------------------------------------------
                ai_verified_count += 1
                tier = "high" if confidence >= GEMINI_AUTO_VERIFY_THRESHOLD else "medium"

                d_type = res.get("disaster_type") or art.get("local_filter", {}).get("disasters", ["other"])[0]
                state_name = res.get("state")
                district_name = res.get("district")
                city_name = res.get("city")
                incident_date = res.get("incident_date") or art.get("quality_score", {}).get("incident_date")

                # Fallback to local filter locations if state omitted
                if not state_name and art.get("local_filter", {}).get("locations"):
                    state_name = art["local_filter"]["locations"][0]

                # ----------------------------------------------------
                # EVENT DEDUPLICATION & CORROBORATION
                # ----------------------------------------------------
                existing_event = find_matching_active_event(
                    disaster_events,
                    disaster_type=d_type,
                    state=state_name,
                    city=city_name,
                    district=district_name,
                    incident_date=incident_date,
                    title=art.get("title"),
                )

                if existing_event and ENABLE_CORROBORATION:
                    events_updated_count += 1
                    events_merged_count += len(art.get("cluster_sibling_ids", [art_id]))

                    existing_sources = set(existing_event.get("corroboration", {}).get("sources", []))
                    if art.get("source"):
                        existing_sources.add(art["source"])

                    new_evidence = list(set(
                        existing_event.get("evidence", []) + (res.get("evidence") or [])
                    ))

                    new_confidence = max(existing_event.get("confidence", 0.0), confidence)

                    disaster_events.update_one(
                        {"_id": existing_event["_id"]},
                        {
                            "$set": {
                                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                                "confidence": new_confidence,
                                "corroboration.source_count": len(existing_sources),
                                "corroboration.sources": list(existing_sources),
                                "evidence": new_evidence,
                            },
                            "$addToSet": {
                                "source_articles": {
                                    "article_id": art_id,
                                    "title": art.get("title", ""),
                                    "url": art.get("url", ""),
                                    "source": art.get("source", ""),
                                    "published_at": art.get("published_at", ""),
                                }
                            },
                        },
                    )

                else:
                    events_created_count += 1
                    event_id = generate_stable_event_id(d_type, state_name, city=city_name, district=district_name, incident_date=incident_date)

                    # Geocoding resolution
                    lat, lon, precision = None, None, "unknown"
                    if ENABLE_GEOCODING:
                        lat, lon, precision = geocode_location(
                            country="India",
                            state=state_name,
                            city=city_name,
                            district=district_name,
                        )
                        if lat is not None and lon is not None:
                            geocoding_success_count += 1
                        else:
                            geocoding_failed_count += 1

                    evidence_list = res.get("evidence") or []
                    if not evidence_list and art.get("quality_score", {}).get("evidence"):
                        evidence_list = art["quality_score"]["evidence"]

                    now_iso = datetime.now(timezone.utc).isoformat()
                    disaster_document = {
                        "event_id": event_id,
                        "article_id": art_id,
                        "title": art.get("title", ""),
                        "description": art.get("description", ""),
                        "url": art.get("url", ""),
                        "source": art.get("source", ""),
                        "published_at": art.get("published_at", ""),
                        "disaster_type": d_type,
                        "severity": res.get("severity", "unknown"),
                        "status": "active",
                        "confidence": confidence,
                        "classification": {
                            "model": GEMINI_MODEL,
                            "confidence": confidence,
                            "tier": tier,
                            "article_type": res.get("article_type", "CURRENT_INCIDENT"),
                        },
                        "location": {
                            "country": "India",
                            "state": state_name,
                            "district": district_name,
                            "city": city_name,
                            "latitude": lat,
                            "longitude": lon,
                            "precision": precision,
                        },
                        "incident_date": incident_date or (art.get("published_at")[:10] if art.get("published_at") else None),
                        "reason": res.get("reason", ""),
                        "evidence": evidence_list,
                        "corroboration": {
                            "source_count": 1,
                            "sources": [art["source"]] if art.get("source") else [],
                        },
                        "source_articles": [
                            {
                                "article_id": art_id,
                                "title": art.get("title", ""),
                                "url": art.get("url", ""),
                                "source": art.get("source", ""),
                                "published_at": art.get("published_at", ""),
                            }
                        ],
                        "first_seen_at": now_iso,
                        "last_updated_at": now_iso,
                        "processed_at": now_iso,
                    }

                    disaster_events.update_one(
                        {"event_id": event_id},
                        {"$set": disaster_document},
                        upsert=True,
                    )

                # Mark processed in news_temp
                news_temp.update_one(
                    {"_id": art_id},
                    {"$set": {"status": "processed"}},
                )

                for sib_id in art.get("cluster_sibling_ids", []):
                    if sib_id != art_id:
                        news_temp.update_one(
                            {"_id": sib_id},
                            {"$set": {"status": "processed_sibling"}},
                        )

            # Handle unverified articles in batch
            unverified_ids = set(batch_map.keys()) - verified_ids
            for u_id in unverified_ids:
                news_temp.update_one(
                    {"_id": u_id},
                    {
                        "$set": {
                            "status": "pending_ai",
                            "last_ai_attempt_at": datetime.now(timezone.utc).isoformat(),
                        },
                        "$inc": {"retry_count": 1},
                    },
                )

    # --------------------------------------------------------
    # 9. PIPELINE SUMMARY & OBSERVABILITY METRICS
    # --------------------------------------------------------
    finished_at = datetime.now(timezone.utc)
    duration = (finished_at - started_at).total_seconds()

    print("\n" + "=" * 75)
    print("DISHA PIPELINE SUMMARY")
    print("=" * 75)
    print(f"Raw articles fetched:       {total_raw}")
    print(f"URL/Hash duplicates:        {duplicates_count}")
    print(f"Already finalized:          {len(existing_ids)}")
    print(f"New articles to process:    {len(new_articles)}")
    print(f"Local filter rejected:      {local_rejected_count}")
    print(f"Quality filter rejected:    {quality_rejected_count}")
    print(f"  - Old news rejected:      {old_news_rejected}")
    print(f"  - Forecast only rejected: {forecast_rejected}")
    print(f"  - Foreign only rejected:  {foreign_rejected}")
    print(f"Pending AI retried:         {pending_retried_count}")
    print(f"Gemini candidates:          {len(gemini_candidates)}")
    print(f"Gemini requests made:       {gemini_requests_count}")
    print(f"Gemini articles evaluated:  {gemini_articles_processed}")
    print(f"AI rejected:                {ai_rejected_count}")
    print(f"AI verified:                {ai_verified_count}")
    print(f"Events created:             {events_created_count}")
    print(f"Events updated:             {events_updated_count}")
    print(f"Events merged:              {events_merged_count}")
    print(f"Geocoding success:          {geocoding_success_count}")
    print(f"Geocoding failed:           {geocoding_failed_count}")
    print(f"Duration:                   {duration:.2f}s")
    print("=" * 75 + "\n")

    return {
        "status": "success",
        "articles_fetched": total_raw,
        "new_articles": len(new_articles),
        "duplicates": duplicates_count,
        "already_finalized": len(existing_ids),
        "local_rejected": local_rejected_count,
        "quality_rejected": quality_rejected_count,
        "old_news_rejected": old_news_rejected,
        "forecast_rejected": forecast_rejected,
        "foreign_rejected": foreign_rejected,
        "pending_retried": pending_retried_count,
        "candidate_count": len(gemini_candidates),
        "gemini_requests": gemini_requests_count,
        "gemini_processed": gemini_articles_processed,
        "gemini_rejected": ai_rejected_count,
        "gemini_verified": ai_verified_count,
        "events_created": events_created_count,
        "events_updated": events_updated_count,
        "events_merged": events_merged_count,
        "geocoding_success": geocoding_success_count,
        "geocoding_failed": geocoding_failed_count,
        "processing_time": round(duration, 2),
    }


# Alias for backward compatibility
run_news_pipeline = fetch_gnews