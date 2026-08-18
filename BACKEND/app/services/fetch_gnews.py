"""
DISHA Real-Time Disaster Intelligence Pipeline
Master Ingestion, Pre-filtering, Scoring, AI Verification, and Event Deduplication Pipeline.
"""

import os
import re
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from typing import List, Dict, Any, Optional

import feedparser
import requests
from dotenv import load_dotenv

# Ensure .env is loaded
_backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_backend_dir / ".env")
load_dotenv()

from app.database.mongodb import db
from app.services.geocoding import geocode_location
from app.services.source_scorer import score_source
from app.services.evidence_detector import detect_evidence, parse_published_date
from app.services.quality_scorer import score_article, MIN_LOCAL_CANDIDATE_SCORE
from app.services.event_clustering import (
    pre_cluster_candidates,
    generate_stable_event_id,
    find_matching_active_event,
)
from app.services.gemini_controller import (
    QuotaController,
    call_gemini_api,
    parse_gemini_response,
    GEMINI_MODEL,
)

# ============================================================
# CONFIGURATION
# ============================================================

GEMINI_BATCH_SIZE = int(os.getenv("GEMINI_BATCH_SIZE", "30"))
GEMINI_CONFIDENCE_THRESHOLD = float(os.getenv("GEMINI_CONFIDENCE_THRESHOLD", "0.70"))
GEMINI_AUTO_VERIFY_THRESHOLD = float(os.getenv("GEMINI_AUTO_VERIFY_THRESHOLD", "0.90"))
ENABLE_CORROBORATION = os.getenv("ENABLE_CORROBORATION", "true").lower() == "true"
ENABLE_GEOCODING = os.getenv("ENABLE_GEOCODING", "true").lower() == "true"

# MongoDB Collections
news_temp = db["news_temp"]
disaster_events = db["disaster_events"]
rejected_news = db["rejected_news"]
ai_usage = db["ai_usage"]

quota_controller = QuotaController(ai_usage)

# ============================================================
# NEWS QUERIES
# ============================================================

NEWS_QUERIES = [
    "flood India",
    "floods Assam OR Bihar OR Odisha OR Kerala OR Bengal",
    "earthquake tremors India",
    "landslide Himachal OR Uttarakhand OR Kerala OR Northeast",
    "cyclone India IMD",
    "heavy rainfall waterlogging India",
    "cloudburst Himachal OR Uttarakhand OR Kashmir",
    "lightning strike deaths India",
    "severe heatwave India deaths",
    "cold wave India deaths",
    "forest fire wildfire India",
    "avalanche Kashmir OR Ladakh OR Uttarakhand",
    "dam breach OR reservoir overflow India",
    "building collapse OR bridge collapse India",
    "factory fire blaze India",
    "chemical leak OR gas leak India",
    "explosion blast India",
    "train accident OR derailment India",
    "bus plunges gorge India",
]

# ============================================================
# COMPREHENSIVE DISASTER KEYWORDS
# ============================================================

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
        "scaffolding collapse", "tunnel collapse"
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

# Indian State Aliases & Cities
STATE_ALIASES = {
    "Andhra Pradesh": ["andhra pradesh", "andhra", "visakhapatnam", "vizag", "vijayawada", "guntur", "tirupati", "kurnool"],
    "Arunachal Pradesh": ["arunachal pradesh", "arunachal", "itanagar", "tawang", "pasighat"],
    "Assam": ["assam", "guwahati", "silchar", "dibrugarh", "jorhat", "nagaon", "kaziranga", "brahmaputra"],
    "Bihar": ["bihar", "patna", "gaya", "bhagalpur", "muzaffarpur", "purnia", "darbhanga", "kosi"],
    "Chhattisgarh": ["chhattisgarh", "raipur", "bilaspur", "durg", "bastar"],
    "Goa": ["goa", "panaji", "margao"],
    "Gujarat": ["gujarat", "ahmedabad", "surat", "vadodara", "rajkot", "bhavnagar", "kutch", "bhuj"],
    "Haryana": ["haryana", "gurgaon", "gurugram", "faridabad", "panipat", "ambala", "karnal"],
    "Himachal Pradesh": ["himachal pradesh", "himachal", "shimla", "manali", "kullu", "mandi", "dharamshala", "kinnaur", "lahaul"],
    "Jharkhand": ["jharkhand", "ranchi", "jamshedpur", "dhanbad", "bokaro"],
    "Karnataka": ["karnataka", "bengaluru", "bangalore", "mysore", "mysuru", "hubli", "mangalore", "belagavi"],
    "Kerala": ["kerala", "wayanad", "idukki", "kochi", "cochin", "thiruvananthapuram", "trivandrum", "kozhikode", "calicut", "munnar"],
    "Madhya Pradesh": ["madhya pradesh", "bhopal", "indore", "gwalior", "jabalpur", "ujjain"],
    "Maharashtra": ["maharashtra", "mumbai", "pune", "nagpur", "thane", "nashik", "aurangabad", "kolhapur", "konkan"],
    "Manipur": ["manipur", "imphal", "churachandpur"],
    "Meghalaya": ["meghalaya", "shillong", "cherrapunji", "mawsynram"],
    "Mizoram": ["mizoram", "aizawl"],
    "Nagaland": ["nagaland", "kohima", "dimapur"],
    "Odisha": ["odisha", "orissa", "bhubaneswar", "cuttack", "puri", "balasore", "rourkela"],
    "Punjab": ["punjab", "ludhiana", "amritsar", "jalandhar", "patiala"],
    "Rajasthan": ["rajasthan", "jaipur", "jodhpur", "udaipur", "kota", "bikaner", "ajmer"],
    "Sikkim": ["sikkim", "gangtok", "namchi", "teesta"],
    "Tamil Nadu": ["tamil nadu", "tamilnadu", "chennai", "coimbatore", "madurai", "salem", "tiruchirappalli"],
    "Telangana": ["telangana", "hyderabad", "warangal", "nizamabad"],
    "Tripura": ["tripura", "agartala"],
    "Uttar Pradesh": ["uttar pradesh", "lucknow", "kanpur", "varanasi", "agra", "noida", "ghaziabad", "prayagraj", "allahabad", "gorakhpur", "meerut"],
    "Uttarakhand": ["uttarakhand", "uttaranchal", "dehradun", "rishikesh", "haridwar", "chamoli", "joshimath", "nainital", "kedarnath", "badrinath", "uttarkashi"],
    "West Bengal": ["west bengal", "bengal", "kolkata", "howrah", "darjeeling", "siliguri", "birbhum", "durgapur", "asansol", "sunderbans"],
    "Delhi": ["delhi", "new delhi", "nct of delhi"],
    "Jammu and Kashmir": ["jammu and kashmir", "jammu & kashmir", "jammu kashmir", "j&k", "kashmir", "jammu", "srinagar", "anantnag", "baramulla"],
    "Ladakh": ["ladakh", "leh", "kargil"],
    "Puducherry": ["puducherry", "pondicherry"],
    "Chandigarh": ["chandigarh"],
    "Andaman and Nicobar": ["andaman and nicobar", "andaman & nicobar", "port blair", "andaman", "nicobar"],
}

GLOBAL_EXCLUSIONS = [
    r"\b(landslide victory|landslide win|election landslide|poll victory|bypoll|vote share|exit poll|assembly election|lok sabha|vidhan sabha|cabinet expansion)\b",
    r"\b(cricket|century|wicket|ipl|trophy|world cup|innings|run drought|medal drought|goal scored|match highlights|badminton|olympics|football match)\b",
    r"\b(box office|trailer release|teaser release|movie review|ott release|bollywood|tollywood|actor|actress|album release|song release|concert blast|party blast)\b",
    r"\b(stock market|shares crash|startup valuation|sales explosion|population explosion|user explosion|market collapse|funding drought|talent drought|deal drought)\b",
    r"\b(paper leak|exam leak|question paper leak|data leak|whatsapp leak|neet leak)\b",
    r"\b(flash mob|flash sale|spread like wildfire|flood of applications|avalanche of comments|tsunami of memes|tsunami of debt)\b",
]

FOREIGN_ONLY_INDICATORS = [
    r"\b(in usa|in us|in united states|in florida|in texas|in california|in japan|in china|in australia|in europe|in philippines|in indiana|in indonesia|in canada|in uk|in london)\b"
]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_disaster_keywords(text: str) -> List[tuple]:
    found = []
    for disaster_type, keywords in DISASTERS.items():
        for keyword in keywords:
            if re.search(r"\b" + re.escape(keyword) + r"\b", text):
                found.append((disaster_type, keyword))
                break
    return found


def detect_locations(text: str) -> List[str]:
    found_states = []
    for canonical_state, aliases in STATE_ALIASES.items():
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", text):
                if canonical_state not in found_states:
                    found_states.append(canonical_state)
                break
    return found_states


def is_excluded_headline(text: str) -> tuple[bool, str]:
    for pattern in GLOBAL_EXCLUSIONS:
        if re.search(pattern, text):
            return True, "metaphor_or_non_disaster_topic"

    for foreign_pat in FOREIGN_ONLY_INDICATORS:
        if re.search(foreign_pat, text) and not re.search(r"\b(india|indian)\b", text):
            return True, "foreign_only_event"

    return False, ""


def local_filter(article: dict) -> dict:
    title = article.get("title", "")
    summary = article.get("description", "")
    full_text = clean_text(f"{title} {summary}")

    # 1. Global Exclusion check
    excluded, reason = is_excluded_headline(full_text)
    if excluded:
        return {
            "passed": False,
            "reason": reason,
            "disasters": [],
            "locations": [],
        }

    # 2. Disaster Keyword Detection
    disaster_hits = detect_disaster_keywords(full_text)
    if not disaster_hits:
        return {
            "passed": False,
            "reason": "no_disaster_keyword",
            "disasters": [],
            "locations": [],
        }

    # 3. Location Detection
    locations = detect_locations(full_text)
    has_india = bool(re.search(r"\b(india|indian|national disaster|imd|ndrf|sdrf)\b", full_text))

    if not locations and not has_india:
        return {
            "passed": False,
            "reason": "no_india_location_or_context",
            "disasters": [d[0] for d in disaster_hits],
            "locations": [],
        }

    disaster_types = list({d[0] for d in disaster_hits})

    return {
        "passed": True,
        "reason": "candidate",
        "disasters": disaster_types,
        "locations": locations,
    }


def generate_article_id(article: dict) -> str:
    raw = article.get("url", "") or article.get("title", "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def google_news(query: str) -> List[Dict[str, Any]]:
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

        articles = []
        for item in getattr(feed, "entries", []):
            source = ""
            if hasattr(item, "source") and isinstance(item.source, dict):
                source = item.source.get("title", "")
            elif hasattr(item, "source"):
                source = getattr(item.source, "title", "")

            article = {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
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


def get_existing_article_ids(article_ids: List[str]) -> set:
    """
    Performs fast bulk lookups across MongoDB collections to find already-processed IDs.
    """
    if not article_ids:
        return set()

    found_ids = set()

    # Look in news_temp
    for doc in news_temp.find({"_id": {"$in": article_ids}}, {"_id": 1}):
        found_ids.add(doc["_id"])

    # Look in disaster_events
    for doc in disaster_events.find({"article_id": {"$in": article_ids}}, {"article_id": 1}):
        found_ids.add(doc["article_id"])

    # Look in rejected_news
    for doc in rejected_news.find({"article_id": {"$in": article_ids}}, {"article_id": 1}):
        found_ids.add(doc["article_id"])

    return found_ids


def save_temp_article(article: dict, filter_result: dict, quality_result: Optional[dict] = None):
    article["local_filter"] = filter_result
    if quality_result:
        article["quality_score"] = quality_result
    article["status"] = (
        "pending_ai" if filter_result.get("passed") and (quality_result is None or quality_result.get("passed"))
        else "rejected_local"
    )

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
    Executes the production-grade DISHA disaster intelligence pipeline.
    """
    print("\n" + "=" * 70)
    print("DISHA PRODUCTION DISASTER INTELLIGENCE PIPELINE")
    print("=" * 70)

    started_at = datetime.now(timezone.utc)
    all_articles = []

    # --------------------------------------------------------
    # 1. RAW INGESTION
    # --------------------------------------------------------
    for query in NEWS_QUERIES:
        print(f"[NEWS] Query: {query}")
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
        url = article.get("url", "")
        if not url:
            continue
        if url not in unique_articles:
            unique_articles[url] = article

    duplicates_count = total_raw - len(unique_articles)
    print(f"[DEDUP] Unique articles: {len(unique_articles)} (Duplicates: {duplicates_count})")

    # --------------------------------------------------------
    # 3. BULK DATABASE CHECK FOR EXISTING ARTICLES
    # --------------------------------------------------------
    all_unique_ids = [a["_id"] for a in unique_articles.values()]
    existing_ids = get_existing_article_ids(all_unique_ids)
    print(f"[DB] Already processed articles: {len(existing_ids)}")

    new_articles = [a for a in unique_articles.values() if a["_id"] not in existing_ids]

    # --------------------------------------------------------
    # 4. HARD LOCAL FILTERING
    # --------------------------------------------------------
    passed_local_filter = []
    local_rejected_count = 0

    for article in new_articles:
        filter_res = local_filter(article)
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
                        "stage": "local",
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=True,
            )

    print(f"[FILTER] Passed Hard Filter: {len(passed_local_filter)} (Rejected: {local_rejected_count})")

    # --------------------------------------------------------
    # 5. QUALITY SCORING & INCIDENT EVIDENCE RANKING
    # --------------------------------------------------------
    quality_candidates = []
    quality_rejected_count = 0

    for article in passed_local_filter:
        disasters = article["local_filter"].get("disasters", [])
        locations = article["local_filter"].get("locations", [])
        q_res = score_article(article, disasters, locations)
        article["quality_score"] = q_res

        if q_res["passed"]:
            save_temp_article(article, article["local_filter"], q_res)
            quality_candidates.append(article)
        else:
            quality_rejected_count += 1
            save_temp_article(article, article["local_filter"], q_res)
            rejection_reason = (
                q_res.get("rejection_reasons")[0]
                if q_res.get("rejection_reasons")
                else f"low_quality_score_{q_res.get('total_score')}"
            )
            rejected_news.update_one(
                {"article_id": article["_id"]},
                {
                    "$set": {
                        "article_id": article["_id"],
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", ""),
                        "reason": rejection_reason,
                        "quality_score": q_res.get("total_score"),
                        "stage": "quality",
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=True,
            )

    print(f"[SCORE] High-Quality Candidates: {len(quality_candidates)} (Rejected: {quality_rejected_count})")

    # --------------------------------------------------------
    # 6. EVENT PRE-CLUSTERING & TOP-N SELECTION
    # --------------------------------------------------------
    gemini_candidates = pre_cluster_candidates(quality_candidates)
    pre_clusters_count = len(gemini_candidates)
    print(f"[CLUSTER] Pre-Clustered Candidates for AI: {pre_clusters_count}")

    # --------------------------------------------------------
    # 7. QUOTA-AWARE GEMINI BATCH CLASSIFICATION
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
                print("[GEMINI] Daily quota limit reached. Halting AI calls and keeping batch pending.")
                break

            quota_controller.wait_for_slot()

            print(f"[GEMINI] Classifying batch {i // GEMINI_BATCH_SIZE + 1} ({len(batch)} articles)...")
            compact_articles = [
                {
                    "id": a["_id"],
                    "title": a.get("title", ""),
                    "description": clean_text(a.get("description", ""))[:700],
                    "source": a.get("source", ""),
                    "published_at": a.get("published_at", ""),
                }
                for a in batch
            ]

            payload = {"articles": compact_articles}
            raw_response = call_gemini_api(payload)
            gemini_requests_count += 1
            gemini_articles_processed += len(batch)

            quota_controller.record_usage(
                requests_count=1,
                articles_count=len(batch),
                estimated_tokens=len(str(payload)) // 4,
            )

            results = parse_gemini_response(raw_response) if raw_response else []

            if not results:
                print("[GEMINI] No usable results for batch. Retaining as pending_ai.")
                for art in batch:
                    news_temp.update_one(
                        {"_id": art["_id"]},
                        {"$set": {"status": "pending_ai"}},
                    )
                continue

            # Map results to batch articles
            batch_map = {a["_id"]: a for a in batch}

            for res in results:
                art_id = res.get("id")
                art = batch_map.get(art_id)
                if not art:
                    continue

                is_disaster = bool(res.get("is_disaster", False))
                try:
                    confidence = float(res.get("confidence", 0.0))
                except (TypeError, ValueError):
                    confidence = 0.0

                # ----------------------------------------------------
                # AI REJECTION
                # ----------------------------------------------------
                if not is_disaster or confidence < GEMINI_CONFIDENCE_THRESHOLD:
                    ai_rejected_count += 1
                    rejection_reason = (
                        res.get("reason")
                        or ("gemini_non_disaster" if not is_disaster else "low_confidence")
                    )

                    # Update representative
                    rejected_news.update_one(
                        {"article_id": art_id},
                        {
                            "$set": {
                                "article_id": art_id,
                                "title": art.get("title", ""),
                                "url": art.get("url", ""),
                                "source": art.get("source", ""),
                                "reason": rejection_reason,
                                "confidence": confidence,
                                "stage": "ai",
                                "processed_at": datetime.now(timezone.utc).isoformat(),
                            }
                        },
                        upsert=True,
                    )
                    news_temp.update_one(
                        {"_id": art_id},
                        {"$set": {"status": "rejected_ai"}},
                    )

                    # Also update sibling articles if any
                    for sib_id in art.get("cluster_sibling_ids", []):
                        if sib_id != art_id:
                            news_temp.update_one(
                                {"_id": sib_id},
                                {"$set": {"status": "rejected_ai_sibling"}},
                            )
                    continue

                # ----------------------------------------------------
                # AI VERIFIED DISASTER EVENT
                # ----------------------------------------------------
                ai_verified_count += 1
                tier = "high" if confidence >= GEMINI_AUTO_VERIFY_THRESHOLD else "medium"

                d_type = res.get("disaster_type") or art.get("local_filter", {}).get("disasters", ["other"])[0]
                state_name = res.get("state")
                city_name = res.get("city")
                incident_date = res.get("incident_date")

                # Fallback to local filter locations if Gemini omitted state
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
                )

                if existing_event and ENABLE_CORROBORATION:
                    # Update existing event
                    events_updated_count += 1
                    events_merged_count += len(art.get("cluster_sibling_ids", [art_id]))

                    existing_sources = set(existing_event.get("corroboration", {}).get("sources", []))
                    if art.get("source"):
                        existing_sources.add(art["source"])

                    new_evidence = list(set(
                        existing_event.get("evidence", []) + (res.get("evidence") or [])
                    ))

                    # Elevate confidence/severity if new article has higher rating
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
                    # Create new disaster event
                    events_created_count += 1
                    event_id = generate_stable_event_id(d_type, state_name, city_name, incident_date)

                    # Geocoding
                    lat, lon, precision = None, None, "unknown"
                    if ENABLE_GEOCODING:
                        lat, lon, precision = geocode_location(
                            country="India",
                            state=state_name,
                            city=city_name,
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
                        "article_id": art_id,  # backward compatibility
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
                        },
                        "location": {
                            "country": "India",
                            "state": state_name,
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

    # --------------------------------------------------------
    # 8. PIPELINE SUMMARY & OBSERVABILITY
    # --------------------------------------------------------
    finished_at = datetime.now(timezone.utc)
    duration = (finished_at - started_at).total_seconds()

    print("\n" + "=" * 70)
    print("DISHA PIPELINE SUMMARY")
    print("=" * 70)
    print(f"Raw articles:              {total_raw}")
    print(f"URL duplicates:            {duplicates_count}")
    print(f"Already processed:         {len(existing_ids)}")
    print(f"Local rejected:            {local_rejected_count}")
    print(f"Quality rejected:          {quality_rejected_count}")
    print(f"Pre-clustered candidates:  {pre_clusters_count}")
    print(f"Gemini candidates:         {len(gemini_candidates)}")
    print(f"Gemini requests:           {gemini_requests_count}")
    print(f"Gemini articles processed: {gemini_articles_processed}")
    print(f"AI rejected:               {ai_rejected_count}")
    print(f"AI verified:               {ai_verified_count}")
    print(f"Events created:            {events_created_count}")
    print(f"Events updated:            {events_updated_count}")
    print(f"Events merged:             {events_merged_count}")
    print(f"Geocoding success:         {geocoding_success_count}")
    print(f"Geocoding failed:          {geocoding_failed_count}")
    print(f"Duration:                  {duration:.2f}s")
    print("=" * 70 + "\n")

    return {
        "status": "success",
        "raw_articles": total_raw,
        "url_duplicates": duplicates_count,
        "already_processed": len(existing_ids),
        "local_rejected": local_rejected_count,
        "quality_rejected": quality_rejected_count,
        "pre_clustered_candidates": pre_clusters_count,
        "gemini_candidates": len(gemini_candidates),
        "gemini_requests": gemini_requests_count,
        "gemini_articles_processed": gemini_articles_processed,
        "ai_rejected": ai_rejected_count,
        "ai_verified": ai_verified_count,
        "events_created": events_created_count,
        "events_updated": events_updated_count,
        "events_merged": events_merged_count,
        "geocoding_success": geocoding_success_count,
        "geocoding_failed": geocoding_failed_count,
        "duration_seconds": duration,
    }


# Alias for backward compatibility
run_news_pipeline = fetch_gnews