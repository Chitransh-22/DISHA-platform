"""
DISHA Event Clustering & Deduplication Engine
Handles pre-AI article clustering, fine-grained multi-level event deduplication,
and cross-source corroboration without overly broad state-wide mergers.
"""

import os
import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

from app.services.geocoding import geocode_location
from app.services.source_scorer import score_source
from app.services.evidence_detector import detect_evidence

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
        "are", "as", "by", "after", "with", "from", "into", "over", "under", "more",
        "near", "about", "reported", "across", "hit", "hits", "triggers"
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
    Ensures that different districts in the same state (e.g. Barpeta vs Dibrugarh)
    are NOT merged automatically.
    """
    # 1. Check disaster type overlap
    dt_a = set(art_a.get("local_filter", {}).get("disasters", []))
    dt_b = set(art_b.get("local_filter", {}).get("disasters", []))
    if not dt_a.intersection(dt_b):
        return False

    # 2. Check location details
    loc_a = [loc.lower() for loc in art_a.get("local_filter", {}).get("locations", [])]
    loc_b = [loc.lower() for loc in art_b.get("local_filter", {}).get("locations", [])]

    # Calculate title similarity
    sim = title_similarity(art_a.get("title", ""), art_b.get("title", ""))

    # High title similarity (>= 0.45) indicates same incident regardless of explicit city extraction
    if sim >= 0.45:
        return True

    # If both have location mentions
    if loc_a and loc_b:
        common_locs = set(loc_a).intersection(set(loc_b))
        if common_locs:
            non_common_a = set(loc_a) - common_locs
            non_common_b = set(loc_b) - common_locs

            # Different explicit district/city locations mentioned (e.g. Barpeta vs Dibrugarh)
            if non_common_a and non_common_b and sim < 0.35:
                return False

            # Exact same locations or common locations with slight title similarity
            if not (non_common_a or non_common_b) or sim >= 0.12:
                return True
        else:
            # Entirely different locations mentioned (e.g. Barpeta vs Dibrugarh) -> distinct events!
            return False

    # Moderate title similarity (>= 0.35)
    if sim >= 0.35:
        return True

    return False


def get_article_evidence_strength(article: Dict[str, Any]) -> Tuple[int, int, int, int, float, float]:
    """
    Computes a deterministic evidence ranking key following the hierarchy:
    casualties > missing/trapped > physical damage > rescue/evacuation > official source > generic report.
    
    Returns a comparable tuple:
    (
        1 if casualties reported else 0,
        1 if missing/trapped reported else 0,
        1 if physical/structural damage reported else 0,
        1 if rescue/evacuation/NDRF/SDRF reported else 0,
        source reliability weight (0.0 to 3.0),
        candidate priority score (float)
    )
    """
    title = article.get("title", "")
    desc = article.get("description", "")
    full_text = f"{title} {desc}".strip()

    ev = detect_evidence(full_text)

    has_casualties = 1 if ev.get("has_casualties") else 0
    has_distress = 1 if ev.get("has_distress") else 0
    has_damage = 1 if ev.get("has_damage") else 0
    has_response = 1 if ev.get("has_response") else 0

    source_name = article.get("source", "")
    src_res = score_source(source_name)
    src_weight = float(src_res.get("weight", 0.0))

    q_score = article.get("quality_score", {})
    priority_score = float(article.get("candidate_priority_score", q_score.get("total_score", 0.0)))

    return (
        has_casualties,
        has_distress,
        has_damage,
        has_response,
        src_weight,
        priority_score,
    )


def pre_cluster_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups related articles before sending to Gemini, picking the representative article
    with the strongest evidence (casualties > missing/trapped > physical damage > rescue/evacuation > official source > generic report).
    """
    if not candidates:
        return []

    # Initial sort by candidate priority score descending
    sorted_candidates = sorted(
        candidates,
        key=lambda c: c.get("candidate_priority_score", c.get("quality_score", {}).get("total_score", 0)),
        reverse=True,
    )

    if not ENABLE_EVENT_CLUSTERING:
        return sorted_candidates[:MAX_GEMINI_CANDIDATES]

    clusters: List[List[Dict[str, Any]]] = []

    for art in sorted_candidates:
        placed = False
        for cluster in clusters:
            # Compare with all existing members of the cluster
            if any(are_articles_same_event(art, member) for member in cluster):
                cluster.append(art)
                placed = True
                break
        if not placed:
            clusters.append([art])

    # Select representative article from each cluster based on strongest evidence hierarchy
    representatives = []
    for cluster in clusters:
        # Sort cluster members so the strongest evidence article becomes representative
        cluster.sort(key=get_article_evidence_strength, reverse=True)
        rep = cluster[0]
        rep["cluster_sibling_ids"] = [a["_id"] for a in cluster]
        rep["cluster_sibling_count"] = len(cluster)
        representatives.append(rep)

    # Sort representatives by evidence hierarchy descending
    representatives.sort(key=get_article_evidence_strength, reverse=True)

    # Top-N Selection
    final_candidates = representatives[:MAX_GEMINI_CANDIDATES]
    return final_candidates


def generate_stable_event_id(
    disaster_type: str,
    state: Optional[str],
    city: Optional[str] = None,
    district: Optional[str] = None,
    incident_date: Optional[str] = None,
) -> str:
    """
    Generates a deterministic, human-readable disaster event ID.
    Example: DISHA-FLOOD-ASSAM_DIBRUGARH-20260818-8A3F
    """
    d_type = (disaster_type or "EVENT").upper().replace(" ", "_")
    
    loc_tokens = []
    if state:
        loc_tokens.append(state.strip().upper().replace(" ", "_")[:10])
    if district:
        loc_tokens.append(district.strip().upper().replace(" ", "_")[:10])
    elif city:
        loc_tokens.append(city.strip().upper().replace(" ", "_")[:10])
    
    loc_part = "_".join(loc_tokens) if loc_tokens else "INDIA"

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
    city: Optional[str] = None,
    district: Optional[str] = None,
    incident_date: Optional[str] = None,
    title: Optional[str] = None,
    max_days: int = 5,
) -> Optional[Dict[str, Any]]:
    """
    Searches for an active disaster event in MongoDB that matches type, state, and specific
    district/city without merging unrelated events across a state.
    """
    if not disaster_type or not state:
        return None

    query: Dict[str, Any] = {
        "status": "active",
        "disaster_type": disaster_type.lower(),
        "location.state": {"$regex": f"^{re.escape(state.strip())}$", "$options": "i"},
    }

    cursor = db_collection.find(query).sort("last_updated_at", -1).limit(15)
    now = datetime.now(timezone.utc)

    target_loc = (district or city or "").strip().lower()

    for event in cursor:
        last_updated = event.get("last_updated_at")
        if not last_updated:
            continue

        try:
            dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            if (now - dt).total_seconds() > max_days * 86400:
                continue
        except (ValueError, TypeError):
            continue

        event_loc_dict = event.get("location", {})
        event_city = (event_loc_dict.get("city") or "").strip().lower()
        event_district = (event_loc_dict.get("district") or "").strip().lower()
        event_loc = event_district or event_city

        # 1. If both have specific city/district, they MUST match
        if target_loc and event_loc:
            if target_loc in event_loc or event_loc in target_loc:
                return event
            else:
                # Different cities/districts -> NOT the same event
                continue

        # 2. If one or both lack specific city/district, check title similarity
        if title and event.get("title"):
            sim = title_similarity(title, event.get("title", ""))
            if sim >= 0.35:
                return event

        # 3. If same incident date and high semantic connection
        if incident_date and event.get("incident_date"):
            if incident_date[:10] == str(event.get("incident_date"))[:10] and not target_loc and not event_loc:
                return event

    return None
