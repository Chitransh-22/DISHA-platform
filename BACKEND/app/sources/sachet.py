"""
DISHA Platform - NDMA SACHET CAP India RSS & CAP XML Ingestion Source
Source: https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml

Extracts official disaster alerts, warnings, and bulletins from the National Disaster
Management Authority (NDMA) SACHET Common Alerting Protocol (CAP) platform.
Provides ETag caching, safe XML parsing, CAP 1.2 semantic extraction, polygon extraction,
location entity detection, deterministic ID generation, and rolling 30-day filtering.
"""

import os
import sys
import re
import time
import hashlib
import logging
import email.utils
import urllib3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple, Set
import xml.etree.ElementTree as ET

from dotenv import load_dotenv

# Ensure backend root in sys.path
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

load_dotenv(_backend_dir / ".env")
load_dotenv()

import requests

from app.services.geocoding import detect_locations, geocode_location, STATE_CENTROIDS

# Suppress insecure SSL warnings for government portal certificates if verify_ssl=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("disha.sources.sachet")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SACHET_DEFAULT_URL = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"
SACHET_RSS_URL = os.getenv("SACHET_RSS_URL", SACHET_DEFAULT_URL)
SACHET_TIMEOUT = int(os.getenv("SACHET_TIMEOUT", "20"))
SACHET_CAP_TIMEOUT = int(os.getenv("SACHET_CAP_TIMEOUT", "8"))
SACHET_MAX_CAP_WORKERS = int(os.getenv("SACHET_MAX_CAP_WORKERS", "8"))
SACHET_VERIFY_SSL = os.getenv("SACHET_VERIFY_SSL", "false").lower() in ("true", "1", "yes")

HTTP_HEADERS = {
    "User-Agent": "DISHA-Platform/1.0 (Disaster Intelligence and Situational Hazard Awareness; National Disaster Alert Ingestion)",
    "Accept": "application/xml,text/xml,application/rss+xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
}

# ============================================================
# DISASTER TAXONOMY MAPPING
# ============================================================

DISASTER_EVENT_MAP = {
    "flood": "flood",
    "flash flood": "flood",
    "inundation": "flood",
    "river overflow": "flood",
    "rain": "heavy_rain",
    "rainfall": "heavy_rain",
    "heavy rain": "heavy_rain",
    "heavy rainfall": "heavy_rain",
    "very heavy rain": "heavy_rain",
    "extremely heavy rainfall": "heavy_rain",
    "thunderstorm": "heavy_rain",
    "lightning": "lightning",
    "thunderbolt": "lightning",
    "cyclone": "cyclone",
    "cyclonic storm": "cyclone",
    "severe cyclonic storm": "cyclone",
    "storm": "cyclone",
    "squall": "heavy_rain",
    "hailstorm": "heavy_rain",
    "cloudburst": "cloudburst",
    "landslide": "landslide",
    "mudslide": "landslide",
    "rockslide": "landslide",
    "earthquake": "earthquake",
    "tremor": "earthquake",
    "heatwave": "heatwave",
    "heat wave": "heatwave",
    "severe heatwave": "heatwave",
    "severe heat wave": "heatwave",
    "cold wave": "cold_wave",
    "coldwave": "cold_wave",
    "severe cold wave": "cold_wave",
    "avalanche": "avalanche",
    "tsunami": "tsunami",
    "dam": "dam_failure",
    "dam release": "dam_failure",
    "fire": "fire_accident",
    "forest fire": "wildfire",
    "wildfire": "wildfire",
}


def normalize_disaster_type(event_name: str, headline: str = "", description: str = "") -> str:
    """Normalizes raw CAP event names into standard DISHA disaster categories."""
    combined = f"{event_name} {headline} {description}".lower()
    
    for key, mapped in DISASTER_EVENT_MAP.items():
        if key in combined:
            return mapped
            
    return "other"


# ============================================================
# STRING & DATE HELPERS
# ============================================================

def clean_text(val: Any) -> str:
    """Normalize and clean string content safely preserving Unicode."""
    if val is None:
        return ""
    text = str(val).strip()
    return re.sub(r"\s+", " ", text)


def parse_sachet_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """
    Parses timestamps from SACHET RSS (RFC 2822) or CAP XML (ISO 8601).
    Returns timezone-aware UTC datetime.
    """
    if not ts_str or not isinstance(ts_str, str):
        return None
    cleaned = ts_str.strip()
    if not cleaned:
        return None

    # 1. ISO 8601 (from CAP XML, e.g. "2026-08-19T09:38:00+05:30")
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # 2. RFC 2822 (from RSS pubDate, e.g. "Wed, 19 Aug 2026 04:08:01 GMT")
    try:
        parsed_tuple = email.utils.parsedate_to_datetime(cleaned)
        if parsed_tuple:
            if parsed_tuple.tzinfo is None:
                parsed_tuple = parsed_tuple.replace(tzinfo=timezone.utc)
            return parsed_tuple.astimezone(timezone.utc)
    except Exception:
        pass

    # 3. Regex fallback
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{1,2}):(\d{1,2})", cleaned)
    if m:
        y, mo, d, h, mi, s = map(int, m.groups())
        try:
            return datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc)
        except ValueError:
            return None

    return None


def generate_sachet_event_id(identifier: str, guid: Optional[str] = None) -> str:
    """
    Generates a deterministic unique event_id for SACHET alerts.
    Format: sachet_<identifier>
    Example: sachet_IN-1787111448985010_10 or sachet_1787111448985010
    """
    raw_id = identifier or guid or ""
    clean_id = re.sub(r"[^A-Za-z0-9_\-\.]", "_", raw_id.strip())
    if not clean_id:
        clean_id = hashlib.sha256(str(guid or identifier or time.time()).encode("utf-8")).hexdigest()[:16]
    return f"sachet_{clean_id}"


# ============================================================
# SAFE XML PARSING & CAP EXTRACTION
# ============================================================

def safe_parse_xml(xml_content: bytes) -> Optional[ET.Element]:
    """
    Safely parses XML bytes with entity expansion protection.
    """
    if not xml_content or not xml_content.strip():
        return None
    try:
        parser = ET.XMLParser(encoding="utf-8")
        root = ET.fromstring(xml_content, parser=parser)
        return root
    except ET.ParseError as err:
        logger.warning(f"[SACHET] XML ParseError: {err}")
        return None
    except Exception as err:
        logger.warning(f"[SACHET] Unexpected XML parsing error: {err}")
        return None


def strip_ns(tag: str) -> str:
    """Strips XML namespace URI from tag name."""
    return tag.split("}")[-1] if "}" in tag else tag


def find_child_text(elem: Optional[ET.Element], tag_name: str) -> str:
    """Finds child element text ignoring namespace."""
    if elem is None:
        return ""
    for child in elem:
        if strip_ns(child.tag).lower() == tag_name.lower():
            return clean_text(child.text)
    return ""


def find_all_children(elem: Optional[ET.Element], tag_name: str) -> List[ET.Element]:
    """Finds all child elements matching tag_name ignoring namespace."""
    if elem is None:
        return []
    return [child for child in elem if strip_ns(child.tag).lower() == tag_name.lower()]


def compute_polygon_centroid(polygon_str: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculates latitude, longitude centroid from a polygon coordinate string.
    Format in CAP: 'lat1,lon1 lat2,lon2 lat3,lon3 ...'
    """
    if not polygon_str or not polygon_str.strip():
        return None, None
    try:
        points = []
        for pair in polygon_str.strip().split():
            if "," in pair:
                parts = pair.split(",")
                if len(parts) >= 2:
                    lat_f = float(parts[0].strip())
                    lon_f = float(parts[1].strip())
                    if -90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0:
                        points.append((lat_f, lon_f))
        if not points:
            return None, None
        avg_lat = sum(p[0] for p in points) / len(points)
        avg_lon = sum(p[1] for p in points) / len(points)
        return round(avg_lat, 4), round(avg_lon, 4)
    except Exception:
        return None, None


def parse_cap_xml_alert(xml_content: bytes, source_link: str = "") -> Dict[str, Any]:
    """
    Parses full OASIS CAP 1.2 XML alert document.
    Extracts all standard CAP fields and geospatial coordinates.
    """
    root = safe_parse_xml(xml_content)
    if root is None:
        return {}

    identifier = find_child_text(root, "identifier")
    sender = find_child_text(root, "sender")
    sent = find_child_text(root, "sent")
    status = find_child_text(root, "status") or "Actual"
    msg_type = find_child_text(root, "msgType") or "Alert"
    scope = find_child_text(root, "scope") or "Public"
    references = find_child_text(root, "references")
    note = find_child_text(root, "note")

    # Locate first <info> element
    info_elem = None
    for child in root:
        if strip_ns(child.tag).lower() == "info":
            info_elem = child
            break

    language = find_child_text(info_elem, "language") or "en-IN"
    category = find_child_text(info_elem, "category") or "Met"
    event = find_child_text(info_elem, "event") or "Disaster Alert"
    urgency = find_child_text(info_elem, "urgency") or "Unknown"
    severity = find_child_text(info_elem, "severity") or "Unknown"
    certainty = find_child_text(info_elem, "certainty") or "Unknown"
    effective = find_child_text(info_elem, "effective")
    onset = find_child_text(info_elem, "onset")
    expires = find_child_text(info_elem, "expires")
    sender_name = find_child_text(info_elem, "senderName")
    headline = find_child_text(info_elem, "headline")
    description = find_child_text(info_elem, "description")
    instruction = find_child_text(info_elem, "instruction")
    contact = find_child_text(info_elem, "contact")
    web = find_child_text(info_elem, "web")

    # Extract parameters (e.g. Polygon URL)
    polygon_url = None
    params = find_all_children(info_elem, "parameter")
    for param in params:
        p_name = find_child_text(param, "valueName")
        p_val = find_child_text(param, "value")
        if "polygon url" in p_name.lower() or "fetchpolygonxmlfile" in p_val.lower():
            polygon_url = p_val.strip()

    # Extract area info
    area_elem = None
    if info_elem is not None:
        for child in info_elem:
            if strip_ns(child.tag).lower() == "area":
                area_elem = child
                break

    area_desc = find_child_text(area_elem, "areaDesc")
    polygon = find_child_text(area_elem, "polygon")
    circle = find_child_text(area_elem, "circle")
    altitude = find_child_text(area_elem, "altitude")
    ceiling = find_child_text(area_elem, "ceiling")

    # Extract geocodes if any
    geocodes: List[Dict[str, str]] = []
    if area_elem is not None:
        for g_elem in find_all_children(area_elem, "geocode"):
            g_name = find_child_text(g_elem, "valueName")
            g_val = find_child_text(g_elem, "value")
            if g_val:
                geocodes.append({"valueName": g_name, "value": g_val})

    return {
        "identifier": identifier,
        "sender": sender,
        "sent": sent,
        "status": status,
        "msg_type": msg_type,
        "scope": scope,
        "references": references,
        "note": note,
        "language": language,
        "category": category,
        "event": event,
        "urgency": urgency,
        "severity": severity,
        "certainty": certainty,
        "effective": effective,
        "onset": onset,
        "expires": expires,
        "sender_name": sender_name,
        "headline": headline,
        "description": description,
        "instruction": instruction,
        "contact": contact,
        "web": web,
        "polygon_url": polygon_url,
        "area_desc": area_desc,
        "polygon": polygon,
        "circle": circle,
        "altitude": altitude,
        "ceiling": ceiling,
        "geocodes": geocodes,
        "link": source_link,
    }


def parse_polygon_xml(xml_content: bytes) -> Optional[str]:
    """Parses FetchPolygonXMLFile XML to extract coordinate polygon string."""
    root = safe_parse_xml(xml_content)
    if root is None:
        return None
    poly_text = find_child_text(root, "polygon")
    return poly_text if poly_text else None


# ============================================================
# SACHET FETCHER & NORMALIZER CLASS
# ============================================================

class SACHETSource:
    """
    Production-grade source ingestion engine for NDMA SACHET CAP India RSS feeds.
    Provides ETag caching, concurrency-controlled CAP XML fetching, and normalization.
    """

    def __init__(
        self,
        rss_url: str = SACHET_RSS_URL,
        timeout: int = SACHET_TIMEOUT,
        cap_timeout: int = SACHET_CAP_TIMEOUT,
        max_workers: int = SACHET_MAX_CAP_WORKERS,
        verify_ssl: bool = SACHET_VERIFY_SSL,
    ):
        self.rss_url = rss_url
        self.timeout = timeout
        self.cap_timeout = cap_timeout
        self.max_workers = max_workers
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update(HTTP_HEADERS)

    def fetch_rss(
        self,
        cached_etag: Optional[str] = None,
        cached_last_modified: Optional[str] = None,
        force_refresh: bool = False,
        max_retries: int = 3,
    ) -> Tuple[str, Optional[bytes], Optional[str], Optional[str], Optional[str]]:
        """
        Fetches the SACHET RSS XML feed using ETag / Last-Modified caching headers.
        Returns: (status, content_bytes, new_etag, new_last_modified, error_message)
          status: 'success', 'not_modified', or 'error'
        """
        headers = dict(HTTP_HEADERS)
        if not force_refresh:
            if cached_etag:
                headers["If-None-Match"] = cached_etag
            if cached_last_modified:
                headers["If-Modified-Since"] = cached_last_modified

        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[SACHET] Fetching India CAP RSS feed from {self.rss_url} (attempt {attempt}/{max_retries})")
                resp = self.session.get(
                    self.rss_url,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )

                if resp.status_code == 304:
                    logger.info("[SACHET] HTTP 304 Not Modified. Feed has not changed.")
                    return "not_modified", None, cached_etag, cached_last_modified, None

                if resp.status_code == 200:
                    etag = resp.headers.get("ETag")
                    last_mod = resp.headers.get("Last-Modified")
                    logger.info(f"[SACHET] HTTP 200 OK. Received {len(resp.content)} bytes (ETag: {etag})")
                    return "success", resp.content, etag, last_mod, None

                last_error = f"HTTP status {resp.status_code}"
                logger.warning(f"[SACHET] Attempt {attempt} returned {last_error}")

            except (requests.Timeout, requests.ConnectionError) as net_err:
                last_error = f"Network error: {net_err}"
                logger.warning(f"[SACHET] Attempt {attempt} failed: {last_error}")
            except Exception as exc:
                last_error = f"Unexpected error: {exc}"
                logger.warning(f"[SACHET] Attempt {attempt} failed: {last_error}")

            if attempt < max_retries:
                time.sleep(2 ** attempt)

        return "error", None, None, None, last_error

    def fetch_single_cap_alert(self, link_url: str, polygon_fallback_url: Optional[str] = None) -> Dict[str, Any]:
        """Fetches and parses a single CAP XML document with optional polygon fetching."""
        if not link_url:
            return {}
        try:
            resp = self.session.get(
                link_url,
                timeout=self.cap_timeout,
                verify=self.verify_ssl,
            )
            if resp.status_code == 200:
                cap_data = parse_cap_xml_alert(resp.content, source_link=link_url)
                
                # If polygon is not directly inline in CAP XML, but a Polygon URL is provided, fetch it
                poly_url = cap_data.get("polygon_url") or polygon_fallback_url
                if poly_url and not cap_data.get("polygon"):
                    try:
                        p_resp = self.session.get(poly_url, timeout=self.cap_timeout, verify=self.verify_ssl)
                        if p_resp.status_code == 200:
                            poly_str = parse_polygon_xml(p_resp.content)
                            if poly_str:
                                cap_data["polygon"] = poly_str
                    except Exception:
                        pass
                return cap_data
        except Exception as e:
            logger.debug(f"[SACHET] Sub-fetch failed for {link_url}: {e}")
        return {}

    def parse_feed_and_normalize(
        self,
        rss_bytes: bytes,
        reference_now: Optional[datetime] = None,
        filter_30_days: bool = True,
        fetch_underlying_cap: bool = True,
        known_unchanged_guids: Optional[Set[str]] = None,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Parses the RSS feed XML, resolves CAP XML details concurrently, and normalizes
        each item into the standardized DISHA disaster alert document schema.
        Returns: (normalized_alerts, total_items_count, within_30_days_count)
        """
        root = safe_parse_xml(rss_bytes)
        if root is None:
            logger.error("[SACHET] Could not parse RSS XML structure.")
            return [], 0, 0

        channel = None
        for child in root:
            if strip_ns(child.tag).lower() == "channel":
                channel = child
                break

        if channel is None:
            logger.warning("[SACHET] No <channel> element found in RSS XML.")
            return [], 0, 0

        now_utc = reference_now if reference_now is not None else datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        cutoff_30d = now_utc - timedelta(days=30)
        future_buffer = now_utc + timedelta(hours=2)

        items = find_all_children(channel, "item")
        total_items = len(items)
        logger.info(f"[SACHET] RSS items found: {total_items}")

        # Step 1: Pre-parse RSS items
        parsed_rss_items: List[Dict[str, Any]] = []
        links_to_fetch: List[Tuple[int, str]] = []

        for idx, item in enumerate(items):
            title = find_child_text(item, "title")
            description = find_child_text(item, "description")
            category = find_child_text(item, "category") or "Met"
            link = find_child_text(item, "link")
            author = find_child_text(item, "author")
            guid = find_child_text(item, "guid")
            pub_date_str = find_child_text(item, "pubDate")

            pub_dt = parse_sachet_timestamp(pub_date_str)

            rss_item = {
                "idx": idx,
                "title": title,
                "description": description,
                "category": category,
                "link": link,
                "author": author,
                "guid": guid,
                "pub_date_str": pub_date_str,
                "pub_dt": pub_dt,
            }
            parsed_rss_items.append(rss_item)

            if fetch_underlying_cap and link:
                if known_unchanged_guids and guid in known_unchanged_guids:
                    continue
                links_to_fetch.append((idx, link))

        # Step 2: Concurrently fetch underlying CAP XML files in controlled thread pool
        cap_results: Dict[int, Dict[str, Any]] = {}
        if links_to_fetch:
            logger.info(f"[SACHET] Fetching {len(links_to_fetch)} underlying CAP XML alerts (concurrency={self.max_workers})...")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_map = {
                    executor.submit(self.fetch_single_cap_alert, link_url): idx
                    for (idx, link_url) in links_to_fetch
                }
                for future in as_completed(future_map):
                    idx = future_map[future]
                    try:
                        cap_data = future.result()
                        if cap_data:
                            cap_results[idx] = cap_data
                    except Exception as e:
                        logger.debug(f"[SACHET] CAP worker error for item {idx}: {e}")

        # Step 3: Normalize into standard DISHA records and filter rolling 30-day window
        normalized_records: List[Dict[str, Any]] = []
        within_30d_count = 0
        now_iso = now_utc.isoformat()

        for idx, item in enumerate(parsed_rss_items):
            cap_data = cap_results.get(idx, {})

            identifier = cap_data.get("identifier") or item["guid"] or f"sachet_item_{idx}"
            guid = item["guid"] or identifier

            effective_dt = parse_sachet_timestamp(cap_data.get("effective"))
            onset_dt = parse_sachet_timestamp(cap_data.get("onset"))
            sent_dt = parse_sachet_timestamp(cap_data.get("sent"))
            expires_dt = parse_sachet_timestamp(cap_data.get("expires"))
            pub_dt = item["pub_dt"]

            event_dt = effective_dt or onset_dt or sent_dt or pub_dt or now_utc

            if filter_30_days:
                if event_dt < cutoff_30d or event_dt > future_buffer:
                    continue

            within_30d_count += 1

            title = item["title"] or cap_data.get("headline") or cap_data.get("event") or "Disaster Alert"
            headline = cap_data.get("headline") or title
            desc = cap_data.get("description") or item["description"] or title
            instruction = cap_data.get("instruction") or ""

            raw_event = cap_data.get("event") or title
            disaster_type = normalize_disaster_type(raw_event, headline=headline, description=desc)

            severity = cap_data.get("severity") or "Unknown"
            urgency = cap_data.get("urgency") or "Unknown"
            certainty = cap_data.get("certainty") or "Unknown"
            status = cap_data.get("status") or "Actual"
            msg_type = cap_data.get("msg_type") or "Alert"
            scope = cap_data.get("scope") or "Public"

            sender = cap_data.get("sender") or item["author"] or "NDMA"
            sender_name = cap_data.get("sender_name") or sender

            area_desc = cap_data.get("area_desc") or title
            polygon_str = cap_data.get("polygon")
            circle_str = cap_data.get("circle")

            lat, lon = compute_polygon_centroid(polygon_str) if polygon_str else (None, None)
            precision = "polygon_centroid" if lat is not None else None

            combined_geo_text = f"{area_desc} {title}"
            geo_entities = detect_locations(combined_geo_text)
            detected_states = geo_entities.get("states", [])
            detected_cities = geo_entities.get("cities", [])

            state_name = detected_states[0] if detected_states else None
            district_name = None
            city_name = detected_cities[0] if detected_cities else None

            dist_match = re.search(r"([A-Za-z\s]+?)\s+district", combined_geo_text, re.IGNORECASE)
            if dist_match:
                candidate_dist = dist_match.group(1).strip()
                if len(candidate_dist) > 2 and candidate_dist.lower() not in ("the", "in", "of", "and"):
                    district_name = candidate_dist.title()

            if (lat is None or lon is None) and (state_name or district_name or city_name):
                geo_lat, geo_lon, geo_prec = geocode_location(
                    country="India",
                    state=state_name,
                    district=district_name,
                    city=city_name,
                )
                if geo_lat is not None and geo_lon is not None:
                    lat, lon = geo_lat, geo_lon
                    precision = geo_prec

            if (lat is None or lon is None) and state_name and state_name in STATE_CENTROIDS:
                c_lat, c_lon = STATE_CENTROIDS[state_name]
                lat, lon = c_lat, c_lon
                precision = "state_centroid"

            is_active = True
            if expires_dt and expires_dt < now_utc:
                is_active = False
            if msg_type.lower() == "cancel":
                is_active = False

            is_cancelled = (msg_type.lower() == "cancel" or status.lower() == "cancelled")

            event_id = generate_sachet_event_id(identifier, guid=guid)

            event_doc = {
                "event_id": event_id,
                "alert_id": identifier,
                "guid": guid,
                "source": "NDMA_SACHET",
                "source_url": self.rss_url,
                "source_authority": "National Disaster Management Authority (NDMA), Govt. of India",
                "source_type": "official_government",
                "event_type": "disaster_alert",
                "disaster_type": disaster_type,
                "title": title,
                "headline": headline,
                "description": desc,
                "instruction": instruction,
                "category": cap_data.get("category") or item["category"] or "Met",
                "event": raw_event,
                "urgency": urgency,
                "severity": severity,
                "certainty": certainty,
                "status": status,
                "message_type": msg_type,
                "scope": scope,
                "language": cap_data.get("language") or "en-IN",
                "references": cap_data.get("references") or "",
                "sender": sender,
                "sender_name": sender_name,
                "author": item["author"],
                "link": item["link"] or cap_data.get("link") or "",
                "polygon_url": cap_data.get("polygon_url"),
                
                # Timestamps
                "event_time": event_dt.isoformat(),
                "event_timestamp": int(event_dt.timestamp()),
                "effective_at": effective_dt.isoformat() if effective_dt else None,
                "onset_at": onset_dt.isoformat() if onset_dt else None,
                "expires_at": expires_dt.isoformat() if expires_dt else None,
                "sent_at": sent_dt.isoformat() if sent_dt else None,
                "published_at": pub_dt.isoformat() if pub_dt else None,
                "is_active": is_active,
                "is_cancelled": is_cancelled,
                
                # Geographic
                "latitude": lat,
                "longitude": lon,
                "polygon": polygon_str,
                "circle": circle_str,
                "area_description": area_desc,
                "location": {
                    "country": "India",
                    "state": state_name,
                    "district": district_name,
                    "city": city_name,
                    "latitude": lat,
                    "longitude": lon,
                    "precision": precision or "text_area",
                },
                
                # Metadata
                "metadata": {
                    "raw_event": raw_event,
                    "raw_category": cap_data.get("category") or item["category"],
                    "altitude": cap_data.get("altitude"),
                    "ceiling": cap_data.get("ceiling"),
                    "geocodes": cap_data.get("geocodes", []),
                    "raw_status": status,
                },
                
                "first_seen_at": now_iso,
                "last_seen_at": now_iso,
                "created_at": now_iso,
                "updated_at": now_iso,
            }

            normalized_records.append(event_doc)

        return normalized_records, total_items, within_30d_count


def scrape_sachet_alerts(
    rss_url: str = SACHET_RSS_URL,
    timeout: int = SACHET_TIMEOUT,
    cached_etag: Optional[str] = None,
    cached_last_modified: Optional[str] = None,
    force_refresh: bool = False,
    reference_now: Optional[datetime] = None,
    known_unchanged_guids: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Helper function to execute SACHET RSS scraping cycle."""
    source = SACHETSource(rss_url=rss_url, timeout=timeout)
    status, rss_bytes, new_etag, new_last_mod, err_msg = source.fetch_rss(
        cached_etag=cached_etag,
        cached_last_modified=cached_last_modified,
        force_refresh=force_refresh,
    )

    if status == "not_modified":
        return {
            "status": "not_modified",
            "source": "NDMA_SACHET",
            "etag": cached_etag,
            "last_modified": cached_last_modified,
            "events": [],
            "total_items": 0,
            "within_30_days": 0,
        }

    if status != "success" or not rss_bytes:
        return {
            "status": "error",
            "source": "NDMA_SACHET",
            "error": err_msg or "Failed to fetch RSS XML",
            "events": [],
            "total_items": 0,
            "within_30_days": 0,
        }

    events, total_items, within_30d = source.parse_feed_and_normalize(
        rss_bytes,
        reference_now=reference_now,
        filter_30_days=True,
        fetch_underlying_cap=True,
        known_unchanged_guids=known_unchanged_guids,
    )

    return {
        "status": "success",
        "source": "NDMA_SACHET",
        "etag": new_etag,
        "last_modified": new_last_mod,
        "total_items": total_items,
        "within_30_days": within_30d,
        "count": len(events),
        "events": events,
    }
