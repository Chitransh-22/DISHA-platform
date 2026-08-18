"""
DISHA Event Clustering & Deduplication Engine
Handles pre-AI article clustering and post-AI event-level deduplication and corroboration.
"""

import os
import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from app.services.geocoding import geocode_location

MAX_GEMINI_CANDIDATES = int(os.getenv("MAX_GEMINI_CANDIDATES", "75"))
ENABLE_EVENT_CLUSTERING = os.getenv("ENABLE_EVENT_CLUSTERING", "true").lower() == "true"
ENABLE_CORROBORATION = os.getenv("ENABLE_CORROBORATION", "true").lower() == "true"


def stem_word(w: str) -> str:
    """Simple rule-based suffix normalization."""
    if len(w) > 4:
        if w.endswith("ing"):
            return w[:-3]
        if w.endswith("ies"):
            return w[:-3] + "y"
        if w.endswith("es"):
            return w[:-2]
        if w.endswith("ed"):
            return w[:-2]
        if w.endswith("s") and not w.endswith("ss"):
            return w[:-1]
    return w


def tokenize_title(title: str) -> set:
    """Extracts significant normalized alphanumeric word tokens."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", title.lower())
    stop_words = {
        "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "is",
        "are", "as", "by", "after", "with", "from", "into", "over", "under", "more"
    }
    tokens = {
        stem_word(w)
        for w in clean.split()
        if len(w) > 2 and w not in stop_words
    }
    return tokens


def title_similarity(title_a: str, title_b: str) -> float:
    """Calculates Jaccard similarity between tokenized titles."""
    tokens_a = tokenize_title(title_a)
    tokens_b = tokenize_title(title_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)


def are_articles_same_event(art_a: Dict[str, Any], art_b: Dict[str, Any]) -> bool:
    """
    Determines if two articles likely describe the exact same disaster incident.
    """
    # 1. Check disaster type overlap
    dt_a = set(art_a.get("local_filter", {}).get("disasters", []))
    dt_b = set(art_b.get("local_filter", {}).get("disasters", []))
    if not dt_a.intersection(dt_b):
        return False

    # 2. Check location overlap
    loc_a = set(art_a.get("local_filter", {}).get("locations", []))
    loc_b = set(art_b.get("local_filter", {}).get("locations", []))
    location_match = bool(loc_a.intersection(loc_b))

    # 3. Check title similarity
    sim = title_similarity(art_a.get("title", ""), art_b.get("title", ""))

    # If same location and title similarity (>= 0.25) -> same event
    if location_match and sim >= 0.25:
        return True

    # If high title similarity (>= 0.45) regardless of explicit state name
    if sim >= 0.45:
        return True

    return False


def pre_cluster_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups related articles before sending to Gemini, picking the best representative article per cluster.
    """
    if not ENABLE_EVENT_CLUSTERING or not candidates:
        return candidates[:MAX_GEMINI_CANDIDATES]

    # Sort candidates by quality score descending
    sorted_candidates = sorted(
        candidates,
        key=lambda c: c.get("quality_score", {}).get("total_score", 0),
        reverse=True,
    )

    clusters: List[List[Dict[str, Any]]] = []

    for art in sorted_candidates:
        placed = False
        for cluster in clusters:
            # Compare with the representative (first element) of the cluster
            if are_articles_same_event(art, cluster[0]):
                cluster.append(art)
                placed = True
                break
        if not placed:
            clusters.append([art])

    # Select representative article from each cluster, embedding sibling article IDs
    representatives = []
    for cluster in clusters:
        rep = cluster[0]  # highest score in cluster
        rep["cluster_sibling_ids"] = [a["_id"] for a in cluster]
        rep["cluster_sibling_count"] = len(cluster)
        representatives.append(rep)

    # Top-N Selection
    final_candidates = representatives[:MAX_GEMINI_CANDIDATES]
    return final_candidates


def generate_stable_event_id(
    disaster_type: str,
    state: Optional[str],
    city: Optional[str],
    incident_date: Optional[str] = None,
) -> str:
    """
    Generates a human-readable, deterministic disaster event ID.
    Example: DISHA-FLOOD-ASSAM-20260818-8A3F
    """
    d_type = (disaster_type or "EVENT").upper().replace(" ", "_")
    loc_part = (state or city or "INDIA").upper().replace(" ", "_")[:12]
    
    if incident_date:
        date_str = incident_date[:10].replace("-", "")
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    entropy = hashlib.md5(f"{d_type}_{loc_part}_{date_str}".encode("utf-8")).hexdigest()[:4].upper()
    return f"DISHA-{d_type}-{loc_part}-{date_str}-{entropy}"


def find_matching_active_event(
    db_collection,
    disaster_type: str,
    state: Optional[str],
    city: Optional[str],
    max_days: int = 5,
) -> Optional[Dict[str, Any]]:
    """
    Searches for an active disaster event in MongoDB that matches type and location within time window.
    """
    query = {
        "status": "active",
        "disaster_type": disaster_type.lower(),
    }

    if state:
        query["location.state"] = {"$regex": f"^{re.escape(state.strip())}$", "$options": "i"}

    # Search recently processed events
    cursor = db_collection.find(query).sort("last_updated_at", -1).limit(10)
    now = datetime.now(timezone.utc)

    for event in cursor:
        last_updated = event.get("last_updated_at")
        if last_updated:
            try:
                dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                if (now - dt).total_seconds() <= max_days * 86400:
                    # If city is specified, prefer city match
                    event_city = event.get("location", {}).get("city")
                    if city and event_city:
                        if city.strip().lower() in event_city.strip().lower() or event_city.strip().lower() in city.strip().lower():
                            return event
                    else:
                        return event
            except (ValueError, TypeError):
                continue

    return None
