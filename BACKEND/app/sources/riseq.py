"""
DISHA Platform - National Center for Seismology (NCS) RISEQ Earthquake Scraper
Source: https://riseq.seismo.gov.in/riseq/earthquake

Extracts real-time and 30-day rolling earthquake data from the official NCS RISEQ portal.
Provides deterministic normalization, timestamp conversion to UTC, coordinate validation,
and geographic India relevance classification.
"""

import os
import re
import time
import logging
import urllib3
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from app.services.geocoding import detect_locations, STATE_CENTROIDS

# Suppress SSL warnings for government portal certificates if verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("disha.sources.riseq")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

RISEQ_DEFAULT_URL = "https://riseq.seismo.gov.in/riseq/earthquake"
RISEQ_URL = os.getenv("RISEQ_URL", RISEQ_DEFAULT_URL)
RISEQ_TIMEOUT = int(os.getenv("RISEQ_TIMEOUT", "20"))
RISEQ_VERIFY_SSL = os.getenv("RISEQ_VERIFY_SSL", "false").lower() in ("true", "1", "yes")

# User agent string mimicking modern desktop browser
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://riseq.seismo.gov.in",
    "Referer": "https://riseq.seismo.gov.in/riseq/earthquake",
}

# ============================================================
# GEOGRAPHIC BOUNDS & CLASSIFICATION
# ============================================================

# India Mainland & Island approximate boundary boxes
INDIA_MAINLAND_BOUNDS = {"lat_min": 8.0, "lat_max": 37.5, "lon_min": 68.0, "lon_max": 97.5}
ANDAMAN_NICOBAR_BOUNDS = {"lat_min": 6.5, "lat_max": 14.0, "lon_min": 92.0, "lon_max": 94.5}
LAKSHADWEEP_BOUNDS = {"lat_min": 8.0, "lat_max": 12.5, "lon_min": 71.5, "lon_max": 74.5}

# India Border Buffer Zone (approx. 200km buffer around subcontinental borders)
INDIA_BORDER_BOUNDS = {"lat_min": 5.5, "lat_max": 38.5, "lon_min": 60.0, "lon_max": 100.5}

# Regional (South Asia, Central Asia, Indian Ocean basin)
REGIONAL_BOUNDS = {"lat_min": -15.0, "lat_max": 45.0, "lon_min": 45.0, "lon_max": 115.0}

KNOWN_NEIGHBOR_COUNTRIES = [
    "nepal", "bhutan", "bangladesh", "myanmar", "burma", "pakistan",
    "sri lanka", "afghanistan", "tibet", "china", "tajikistan",
    "hindu kush", "arabian sea", "bay of bengal", "indian ocean"
]


def parse_float_safe(val: Any) -> Optional[float]:
    """Safely parse a string or numeric value into a float, returning None if invalid."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "none", "null", "-", "n/a"):
        return None
    try:
        # Remove any non-numeric noise except minus and decimal point
        cleaned = re.sub(r"[^\d\.\-]", "", val_str)
        if not cleaned or cleaned in ("-", "."):
            return None
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def clean_text(val: Any) -> str:
    """Normalize and clean string content."""
    if val is None:
        return ""
    text = str(val).strip()
    # Replace multiple spaces/newlines with single space
    return re.sub(r"\s+", " ", text)


def parse_riseq_origin_time(time_str: str, timezone_mode: str = "UTC") -> Optional[datetime]:
    """
    Parses origin time string from RISEQ into a UTC timezone-aware datetime object.
    Supports formats like 'YYYY-MM-DD HH:MM:SS', 'YYYY-MM-DDTHH:MM:SS', etc.
    If timezone_mode is 'IST', converts Indian Standard Time (UTC+5:30) to UTC.
    """
    if not time_str:
        return None

    cleaned = clean_text(time_str)
    # Match standard datetime patterns
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{1,2}):(\d{1,2})", cleaned)
    if not match:
        # Fallback date only
        match_date = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", cleaned)
        if match_date:
            y, m, d = map(int, match_date.groups())
            dt = datetime(y, m, d, 0, 0, 0)
        else:
            return None
    else:
        y, m, d, hh, mm, ss = map(int, match.groups())
        try:
            dt = datetime(y, m, d, hh, mm, ss)
        except ValueError:
            return None

    if timezone_mode.upper() == "IST":
        # Convert IST to UTC (subtract 5 hours 30 minutes)
        dt_utc = dt - timedelta(hours=5, minutes=30)
        return dt_utc.replace(tzinfo=timezone.utc)
    else:
        # Already UTC (as requested via timezone=1 in POST query)
        return dt.replace(tzinfo=timezone.utc)


def generate_earthquake_event_id(origin_dt: datetime, lat: float, lon: float) -> str:
    """
    Generates a deterministic unique event_id for duplicate detection.
    Format: ncs_<YYYYMMDDTHHMMSSZ>_<LAT>_<LON>
    Example: ncs_20260818T195107Z_36.494_70.664
    """
    time_tag = origin_dt.strftime("%Y%m%dT%H%M%SZ")
    lat_tag = f"{lat:.3f}"
    lon_tag = f"{lon:.3f}"
    return f"ncs_{time_tag}_{lat_tag}_{lon_tag}"


def is_within_bounding_box(lat: float, lon: float, bbox: Dict[str, float]) -> bool:
    """Check if lat/lon falls within given min/max bounding box."""
    return (
        bbox["lat_min"] <= lat <= bbox["lat_max"]
        and bbox["lon_min"] <= lon <= bbox["lon_max"]
    )


def classify_india_relevance(
    lat: Optional[float],
    lon: Optional[float],
    region: str,
    location: str,
) -> Tuple[str, Dict[str, Any]]:
    """
    Classifies earthquake relevance into INDIA, INDIA_BORDER, REGIONAL, or OTHER.
    Combines geographic coordinate bounding with NLP entity detection from DISHA geocoding.
    """
    region_lower = (region or "").lower()
    location_lower = (location or "").lower()
    combined_text = f"{region} {location}"

    # Extract Indian states/locations using DISHA geocoding service
    loc_entities = detect_locations(combined_text)
    detected_states = loc_entities.get("states", [])
    detected_cities = loc_entities.get("cities", [])
    has_india_keyword = loc_entities.get("has_india", False) or "india" in combined_text.lower()

    # Check if a foreign country is explicitly specified in the region name
    is_foreign_region = any(neighbor in region_lower for neighbor in KNOWN_NEIGHBOR_COUNTRIES)

    details: Dict[str, Any] = {
        "detected_states": detected_states,
        "detected_cities": detected_cities,
        "region": region,
        "location": location,
        "is_foreign_region": is_foreign_region,
    }

    # Case 1: Coordinates available
    if lat is not None and lon is not None:
        in_mainland = is_within_bounding_box(lat, lon, INDIA_MAINLAND_BOUNDS)
        in_islands = (
            is_within_bounding_box(lat, lon, ANDAMAN_NICOBAR_BOUNDS)
            or is_within_bounding_box(lat, lon, LAKSHADWEEP_BOUNDS)
        )
        in_border_box = is_within_bounding_box(lat, lon, INDIA_BORDER_BOUNDS)
        in_regional_box = is_within_bounding_box(lat, lon, REGIONAL_BOUNDS)

        # 1. Epicenter firmly inside India
        if (in_mainland or in_islands) and not is_foreign_region:
            details["classification_method"] = "coordinates_inside_india"
            return "INDIA", details

        # 1b. If region specifically names an Indian state (e.g. "Chamba, Himachal Pradesh")
        if detected_states and (in_mainland or in_islands):
            details["classification_method"] = "state_match_inside_india"
            return "INDIA", details

        # 2. Border zone (e.g. Nepal, Bhutan, Myanmar border, Kashmir border)
        if in_border_box and (is_foreign_region or has_india_keyword or any(w in location_lower for w in ["border", "near india", "km of"])):
            details["classification_method"] = "border_proximity_box"
            return "INDIA_BORDER", details

        # 3. Regional (Hindu Kush, Afghanistan, Pakistan, Tibet, Myanmar, Sri Lanka, Indian Ocean)
        if in_regional_box or is_foreign_region:
            details["classification_method"] = "regional_seismic_zone"
            return "REGIONAL", details

        # 4. Global / Other
        details["classification_method"] = "distant_global_coordinates"
        return "OTHER", details

    # Case 2: Coordinates not available, rely on text
    if detected_states or (has_india_keyword and not is_foreign_region):
        details["classification_method"] = "text_india_entities"
        return "INDIA", details

    if is_foreign_region:
        details["classification_method"] = "text_neighbor_country"
        return "REGIONAL", details

    details["classification_method"] = "default_other"
    return "OTHER", details


def extract_felt_report_info(td_elem) -> Tuple[Optional[str], Optional[str]]:
    """Extract felt report URL and event token from td element if available."""
    if not td_elem:
        return None, None

    a_tag = td_elem.find("a") if hasattr(td_elem, "find") else None
    if not a_tag:
        return None, None

    href = a_tag.get("href", "").strip()
    if not href:
        return None, None

    # Resolve relative URL if needed
    if href.startswith("/"):
        full_url = f"https://riseq.seismo.gov.in{href}"
    elif not href.startswith("http"):
        full_url = f"https://riseq.seismo.gov.in/riseq/{href}"
    else:
        full_url = href

    token = None
    parts = full_url.rstrip("/").split("/")
    if len(parts) >= 2:
        token = parts[-2]

    return full_url, token


def parse_riseq_html(
    html_content: str,
    timezone_mode: str = "UTC",
    reference_now: Optional[datetime] = None,
    filter_30_days: bool = True,
) -> List[Dict[str, Any]]:
    """
    Parses HTML content from RISEQ website and extracts structured, normalized earthquake records.
    Only retains events within the rolling 30-day window: (reference_now - 30 days) <= origin_time <= reference_now + 2h.
    """
    if not html_content or not html_content.strip():
        logger.warning("[RISEQ] Empty HTML content provided for parsing")
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table", id="eqdatalist")
    if not table:
        # Fallback to any table with class table
        for candidate in soup.find_all("table"):
            headers = [th.get_text(strip=True).lower() for th in candidate.find_all("th")]
            if any("magnitude" in h for h in headers) and any("origin" in h or "time" in h for h in headers):
                table = candidate
                break

    if not table:
        logger.warning("[RISEQ] Could not locate earthquake table (table#eqdatalist) in HTML")
        return []

    # Map column headers dynamically
    th_elems = table.find_all("th")
    col_map = {
        "magnitude": 0,
        "origin_time": 1,
        "latitude": 2,
        "longitude": 3,
        "depth": 4,
        "region": 5,
        "location": 6,
        "status": 7,
        "felt": 8,
    }

    if th_elems:
        for idx, th in enumerate(th_elems):
            txt = th.get_text(strip=True).lower()
            if "magnitude" in txt or "mag" == txt:
                col_map["magnitude"] = idx
            elif "origin" in txt or "time" in txt or "date" in txt:
                col_map["origin_time"] = idx
            elif "lat" in txt:
                col_map["latitude"] = idx
            elif "long" in txt or "lon" in txt:
                col_map["longitude"] = idx
            elif "depth" in txt:
                col_map["depth"] = idx
            elif "region" in txt:
                col_map["region"] = idx
            elif "location" in txt:
                col_map["location"] = idx
            elif "type" in txt or "status" in txt:
                col_map["status"] = idx
            elif "felt" in txt:
                col_map["felt"] = idx

    now_utc = reference_now if reference_now is not None else datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    cutoff_30d = now_utc - timedelta(days=30)
    future_buffer = now_utc + timedelta(hours=2) # Allow 2h clock discrepancy

    parsed_records: List[Dict[str, Any]] = []
    rows = table.find_all("tr")

    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 5:
            # Header or loading or spacer row
            continue

        try:
            # Extract cell values using column map safely
            def get_cell_text(col_name: str, fallback_idx: int) -> str:
                idx = col_map.get(col_name, fallback_idx)
                if 0 <= idx < len(tds):
                    return clean_text(tds[idx].get_text(strip=True))
                return ""

            raw_mag = get_cell_text("magnitude", 0)
            raw_time = get_cell_text("origin_time", 1)
            raw_lat = get_cell_text("latitude", 2)
            raw_lon = get_cell_text("longitude", 3)
            raw_depth = get_cell_text("depth", 4)
            raw_region = get_cell_text("region", 5)
            raw_location = get_cell_text("location", 6)
            raw_status = get_cell_text("status", 7) or "Reviewed"

            felt_idx = col_map.get("felt", 8)
            felt_elem = tds[felt_idx] if 0 <= felt_idx < len(tds) else None
            felt_url, felt_token = extract_felt_report_info(felt_elem)

            # 1. Parse origin time
            origin_dt = parse_riseq_origin_time(raw_time, timezone_mode=timezone_mode)
            if not origin_dt:
                logger.debug(f"[RISEQ] Skipping row with invalid origin time: '{raw_time}'")
                continue

            # 2. 30-Day Window Filter
            if filter_30_days:
                if origin_dt < cutoff_30d or origin_dt > future_buffer:
                    logger.debug(f"[RISEQ] Skipping event outside 30-day window: {origin_dt.isoformat()}")
                    continue

            # 3. Parse numeric values
            magnitude = parse_float_safe(raw_mag)
            latitude = parse_float_safe(raw_lat)
            longitude = parse_float_safe(raw_lon)
            depth_km = parse_float_safe(raw_depth)

            # Validate mandatory fields
            if magnitude is None or latitude is None or longitude is None:
                logger.debug(f"[RISEQ] Skipping row with missing core numeric values: mag={raw_mag}, lat={raw_lat}, lon={raw_lon}")
                continue

            # Validate coordinate boundaries
            if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
                logger.debug(f"[RISEQ] Skipping row with out-of-bounds coordinates: ({latitude}, {longitude})")
                continue

            # Validate magnitude reasonable range (-2.0 to 10.0)
            if not (-2.0 <= magnitude <= 10.0):
                logger.debug(f"[RISEQ] Skipping row with unrealistic magnitude: {magnitude}")
                continue

            depth_val = max(0.0, depth_km) if depth_km is not None else 10.0

            # 4. Generate deterministic event_id
            event_id = generate_earthquake_event_id(origin_dt, latitude, longitude)

            # 5. Classify India relevance
            relevance, relevance_details = classify_india_relevance(
                latitude, longitude, raw_region, raw_location
            )

            # 6. Normalize into standard DISHA event schema
            now_iso = now_utc.isoformat()
            origin_iso = origin_dt.isoformat()

            event_doc = {
                "event_id": event_id,
                "source": "NCS_RISEQ",
                "source_url": RISEQ_URL,
                "event_type": "earthquake",
                "disaster_type": "earthquake",
                "origin_time": origin_iso,
                "origin_timestamp": int(origin_dt.timestamp()),
                "latitude": round(latitude, 4),
                "longitude": round(longitude, 4),
                "depth_km": round(depth_val, 2),
                "magnitude": round(magnitude, 2),
                "region": raw_region or "Unknown Region",
                "location": raw_location or raw_region or "Unknown Location",
                "status": raw_status,
                "relevance": relevance,
                "relevance_details": relevance_details,
                "felt_report_url": felt_url,
                "felt_token": felt_token,
                "metadata": {
                    "source_agency": "National Center for Seismology (NCS), Ministry of Earth Sciences, Govt. of India",
                    "raw_status": raw_status,
                    "timezone_ingested": timezone_mode,
                },
                "first_seen_at": now_iso,
                "last_seen_at": now_iso,
                "created_at": now_iso,
                "updated_at": now_iso,
            }

            parsed_records.append(event_doc)

        except Exception as err:
            logger.debug(f"[RISEQ] Error parsing table row: {err}")
            continue

    return parsed_records


class RISEQScraper:
    """
    Dedicated production scraper for NCS RISEQ Earthquake Portal.
    Implements session pooling, exponential backoff retries, and 30-day POST query filtering.
    """

    def __init__(
        self,
        base_url: str = RISEQ_URL,
        timeout: int = RISEQ_TIMEOUT,
        verify_ssl: bool = RISEQ_VERIFY_SSL,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update(HTTP_HEADERS)

    def fetch_html(self, days: int = 30, max_retries: int = 3) -> Tuple[bool, str, Optional[str]]:
        """
        Fetches earthquake HTML from RISEQ.
        First tries POST with days=30 and timezone=1 (UTC).
        Falls back to standard GET if POST fails.
        Returns: (success, html_text, error_message)
        """
        post_payload = {
            "days": str(days),
            "timezone": "1",  # 1 = UTC in RISEQ form
            "event_type": "Auto",  # Auto includes both Auto/Unscruitnized and Reviewed
            "submit": "Apply",
        }

        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[RISEQ] Fetching earthquake data from {self.base_url} (attempt {attempt}/{max_retries})")
                
                # Attempt POST query for 30 days UTC
                resp = self.session.post(
                    self.base_url,
                    data=post_payload,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )

                if resp.status_code == 200 and "eqdatalist" in resp.text:
                    logger.info(f"[RISEQ] Fetch succeeded (POST, status 200, {len(resp.text)} bytes)")
                    return True, resp.text, None

                # If POST returned 200 but didn't have eqdatalist or returned error code, try GET
                logger.warning(f"[RISEQ] POST returned status {resp.status_code}, falling back to GET")
                get_resp = self.session.get(
                    self.base_url,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )

                if get_resp.status_code == 200:
                    logger.info(f"[RISEQ] Fetch succeeded (GET fallback, status 200, {len(get_resp.text)} bytes)")
                    return True, get_resp.text, None

                last_error = f"HTTP status {get_resp.status_code}"

            except (requests.Timeout, requests.ConnectionError) as net_err:
                last_error = f"Network error: {net_err}"
                logger.warning(f"[RISEQ] Attempt {attempt} failed: {last_error}")
            except Exception as exc:
                last_error = f"Unexpected error: {exc}"
                logger.warning(f"[RISEQ] Attempt {attempt} failed: {last_error}")

            if attempt < max_retries:
                sleep_time = 2 ** attempt
                time.sleep(sleep_time)

        return False, "", last_error

    def scrape(
        self,
        days: int = 30,
        max_retries: int = 3,
        reference_now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Executes full scrape cycle, returning normalized records and execution metrics.
        """
        start_time = time.time()
        success, html_text, err_msg = self.fetch_html(days=days, max_retries=max_retries)

        if not success:
            duration = round(time.time() - start_time, 2)
            logger.error(f"[RISEQ] Scraping failed after {max_retries} attempts: {err_msg}")
            return {
                "status": "error",
                "error": err_msg,
                "count": 0,
                "events": [],
                "duration_seconds": duration,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        events = parse_riseq_html(
            html_text,
            timezone_mode="UTC",
            reference_now=reference_now,
            filter_30_days=True,
        )

        duration = round(time.time() - start_time, 2)
        logger.info(f"[RISEQ] Parsed {len(events)} valid 30-day earthquake events in {duration}s")

        return {
            "status": "success",
            "source": "NCS_RISEQ",
            "source_url": self.base_url,
            "count": len(events),
            "events": events,
            "duration_seconds": duration,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def scrape_riseq_earthquakes(
    timeout: int = RISEQ_TIMEOUT,
    max_retries: int = 3,
    days: int = 30,
    reference_now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Helper function to execute a RISEQ scrape with default scraper configuration."""
    scraper = RISEQScraper(timeout=timeout)
    return scraper.scrape(days=days, max_retries=max_retries, reference_now=reference_now)
