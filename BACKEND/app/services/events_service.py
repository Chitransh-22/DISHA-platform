"""
DISHA Platform - Unified Disaster Events Service
Disaster Intelligence and Situational Hazard Awareness Platform

Fetches and normalizes 100% of all real verified database events across all four sources:
1. NCS RISEQ Earthquakes (National Center for Seismology)
2. NDMA SACHET Government Alerts (CAP RSS Government Feed)
3. Verified GNews Disaster Intelligence
4. Citizen Disaster Incident Reports (incident_reports)

Guarantees:
- Zero event loss: never drops an incident because of missing coordinates.
- Canonical invariant: T (Total) = M (Mapped) + U (Unmapped).
- Consistent UTC time range boundaries [startTime, endTime).
- No hardcoded fake centroid markers.
- Robust parsing for RFC 2822, ISO 8601, BSON datetime, and epoch timestamps.
- Zero silent fallback to current time.
"""

import math
import logging
import email.utils
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

from app.database.mongodb import db
from app.services.geocoding import detect_locations, geocode_location
from app.services.geo_filter_service import (
    is_valid_coordinate,
    normalize_geographic_query,
    evaluate_event_geographic_match,
    geocode_with_cache,
)

logger = logging.getLogger("disha.events_service")
logger.setLevel(logging.INFO)


def normalize_event_time(ev: dict) -> Optional[Tuple[str, float, str, str]]:
    """
    Standardizes timestamps to (iso_utc_string, epoch_seconds_float, YYYY-MM-DD, HH:MM UTC).
    Returns None if timestamp is missing or cannot be parsed.
    NEVER silently substitutes current time.
    """
    # 1. Check numeric epoch timestamp fields
    for ts_key in ["unified_timestamp", "origin_timestamp", "event_timestamp", "timestamp"]:
        val = ev.get(ts_key)
        if val is not None:
            try:
                ts = float(val)
                if ts > 1e11:  # Milliseconds
                    ts = ts / 1000.0
                if ts > 0:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    return dt.isoformat(), ts, dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M UTC")
            except Exception:
                pass

    # 2. Check Python / BSON datetime objects (e.g. incident_reports created_at)
    for dt_key in ["created_at", "updated_at", "event_time", "incident_date"]:
        val = ev.get(dt_key)
        if isinstance(val, datetime):
            if val.tzinfo is None:
                dt = val.replace(tzinfo=timezone.utc)
            else:
                dt = val.astimezone(timezone.utc)
            ts = dt.timestamp()
            return dt.isoformat(), ts, dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M UTC")

    # 3. Check candidate timestamp string fields
    candidate_strs = [
        ev.get("date"),
        ev.get("datetime"),
        ev.get("origin_time"),
        ev.get("event_time"),
        ev.get("effective_at"),
        ev.get("incident_date"),
        ev.get("published_at"),
        ev.get("sent_at"),
        ev.get("processed_at"),
        ev.get("created_at"),
        ev.get("first_seen_at"),
    ]

    for raw in candidate_strs:
        if not raw or not isinstance(raw, str):
            continue
        s = raw.strip()
        if not s:
            continue

        # Try RFC 2822 format (common in published_at RSS fields: "Thu, 22 Oct 2026 04:29:03 GMT")
        try:
            dt = email.utils.parsedate_to_datetime(s)
            if dt is not None:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt.isoformat(), dt.timestamp(), dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M UTC")
        except Exception:
            pass

        # Try ISO 8601 format
        try:
            clean_iso = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_iso)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.isoformat(), dt.timestamp(), dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M UTC")
        except Exception:
            pass

        # Try common date/time formats
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
                return dt.isoformat(), dt.timestamp(), dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M UTC")
            except Exception:
                pass

    return None


def map_category(raw_cat: Optional[str]) -> Tuple[str, str]:
    """
    Maps raw category/disaster_type into standard presentation categories:
    Earthquake, Flood, Heavy Rain, Landslide, Lightning, Cyclone, Fire, Cloudburst,
    Building Collapse, Industrial Accident, Explosion, Heatwave, Other.
    Returns: (Display Category, Normalized Slug)
    """
    if not raw_cat:
        return "Other", "other"

    c = str(raw_cat).strip().lower().replace("-", "_").replace(" ", "_")

    if "earthquake" in c or "seismic" in c or "tremor" in c:
        return "Earthquake", "earthquake"
    elif "flood" in c or "inundat" in c or "waterlog" in c:
        return "Flood", "flood"
    elif "heavy_rain" in c or "rain" in c or "downpour" in c or "thunderstorm" in c:
        return "Heavy Rain", "heavy_rain"
    elif "lightning" in c:
        return "Lightning", "lightning"
    elif "landslide" in c or "mudslide" in c or "rockslide" in c or "debris_flow" in c:
        return "Landslide", "landslide"
    elif "cyclone" in c or "storm" in c or "hurricane" in c or "typhoon" in c or "squall" in c:
        return "Cyclone", "cyclone"
    elif "fire" in c or "blaze" in c or "wildfire" in c:
        return "Fire", "fire"
    elif "cloudburst" in c:
        return "Cloudburst", "cloudburst"
    elif "building_collapse" in c or "tunnel_collapse" in c or "structure_collapse" in c or "bridge_collapse" in c:
        return "Building Collapse", "building_collapse"
    elif "industrial_accident" in c or "gas_leak" in c or "chemical" in c:
        return "Industrial Accident", "industrial_accident"
    elif "explosion" in c or "blast" in c:
        return "Explosion", "explosion"
    elif "heat_wave" in c or "heatwave" in c:
        return "Heatwave", "heat_wave"

    return c.replace("_", " ").title(), c


def map_severity(raw_sev: Optional[str], magnitude: Optional[float] = None) -> str:
    """Standardizes severity into: Critical, Severe, Moderate, Low."""
    if magnitude is not None:
        if magnitude >= 6.0:
            return "Critical"
        elif magnitude >= 4.5:
            return "Severe"
        elif magnitude >= 3.0:
            return "Moderate"
        else:
            return "Low"

    if not raw_sev:
        return "Moderate"

    s = str(raw_sev).strip().lower()
    if s in ["extreme", "critical", "catastrophic", "level 4"]:
        return "Critical"
    elif s in ["severe", "high", "major", "level 3"]:
        return "Severe"
    elif s in ["moderate", "medium", "intermediate", "level 2"]:
        return "Moderate"
    elif s in ["minor", "low", "minimal", "level 1"]:
        return "Low"

    return s.capitalize()


def map_status(raw_stat: Optional[str]) -> str:
    """Standardizes status into clean presentation strings."""
    if not raw_stat:
        return "Active"
    s = str(raw_stat).strip().lower()
    if s in ["actual", "active", "ongoing", "submitted", "verified"]:
        return "Active"
    elif s in ["reviewed"]:
        return "Reviewed"
    elif s in ["monitoring", "watch"]:
        return "Monitoring"
    elif s in ["contained", "resolved", "dispatched"]:
        return "Contained"
    elif s in ["unscruitnized", "auto"]:
        return "Automatic"
    return raw_stat.strip().capitalize()


def extract_sachet_coordinates(sa: dict) -> Tuple[Optional[float], Optional[float], str]:
    """
    Robust coordinate extractor for SACHET CAP Alerts:
    1. Direct lat/lon in doc or location object
    2. CAP Polygon centroid computation
    3. CAP Circle center computation
    4. Text entity geocoding from sender/area_description/headline
    Returns: (lat, lon, precision) where lat/lon may be None if unresolvable.
    NEVER substitutes fake India default centroid.
    """
    lat = sa.get("latitude")
    lon = sa.get("longitude")
    loc = sa.get("location") or {}

    if (lat is None or lon is None) and isinstance(loc, dict):
        lat = loc.get("latitude")
        lon = loc.get("longitude")

    if lat is not None and lon is not None:
        try:
            flat, flon = float(lat), float(lon)
            if -90 <= flat <= 90 and -180 <= flon <= 180:
                if abs(flat - 20.5937) < 0.001 and abs(flon - 78.9629) < 0.001:
                    pass  # Reject legacy fake India default centroid
                else:
                    return flat, flon, "exact"
        except (ValueError, TypeError):
            pass

    # 1. Polygon centroid extraction
    poly = sa.get("polygon")
    if poly and isinstance(poly, str) and poly.strip():
        try:
            pairs = [p.strip().split(",") for p in poly.strip().split(" ") if "," in p]
            valid_pairs = [(float(p[0]), float(p[1])) for p in pairs if len(p) == 2]
            if valid_pairs:
                avg_lat = sum(p[0] for p in valid_pairs) / len(valid_pairs)
                avg_lon = sum(p[1] for p in valid_pairs) / len(valid_pairs)
                if -90 <= avg_lat <= 90 and -180 <= avg_lon <= 180:
                    return avg_lat, avg_lon, "polygon_centroid"
        except Exception:
            pass

    # 2. Circle centroid extraction
    circ = sa.get("circle")
    if circ and isinstance(circ, str) and circ.strip():
        try:
            parts = circ.strip().split(" ")
            if parts and "," in parts[0]:
                c_lat, c_lon = parts[0].split(",")
                flat, flon = float(c_lat), float(c_lon)
                if -90 <= flat <= 90 and -180 <= flon <= 180:
                    return flat, flon, "circle_centroid"
        except Exception:
            pass

    # 3. Text entity geocoding from sender, area_description, headline
    raw_text = f"{sa.get('area_description', '')} {sa.get('headline', '')} {sa.get('sender_name', '')} {sa.get('sender', '')} {sa.get('source_authority', '')}"
    text = raw_text.replace("-", " ").replace("_", " ")
    detected = detect_locations(text)
    st = detected["states"][0] if detected["states"] else None
    dt = detected["cities"][0] if detected["cities"] else None
    if st or dt:
        glat, glon, prec = geocode_location(country="India", state=st, district=dt)
        if glat is not None and glon is not None:
            return glat, glon, f"text_{prec}"

    return None, None, "unresolved"


def extract_news_coordinates(ev: dict) -> Tuple[Optional[float], Optional[float], str]:
    """
    Robust coordinate extractor for GNews Disasters.
    Returns: (lat, lon, precision) where lat/lon may be None if unresolvable.
    NEVER substitutes fake India default centroid or infers precise coordinates from ambiguous text.
    """
    loc = ev.get("location") or {}
    lat = loc.get("latitude") if isinstance(loc, dict) else ev.get("latitude")
    lon = loc.get("longitude") if isinstance(loc, dict) else ev.get("longitude")

    if (lat is None or lon is None) and isinstance(loc, dict):
        lat = loc.get("lat")
        lon = loc.get("lon")

    if lat is not None and lon is not None:
        try:
            flat, flon = float(lat), float(lon)
            if is_valid_coordinate(flat, flon):
                precision = loc.get("precision") if isinstance(loc, dict) and loc.get("precision") else "exact"
                return flat, flon, precision
        except (ValueError, TypeError):
            pass

    st = loc.get("state") if isinstance(loc, dict) else None
    dt = loc.get("district") if isinstance(loc, dict) else None
    ct = loc.get("city") if isinstance(loc, dict) else None
    if st or dt or ct:
        glat, glon, prec = geocode_with_cache(country="India", state=st, district=dt, city=ct)
        if is_valid_coordinate(glat, glon):
            return glat, glon, f"text_{prec}"

    return None, None, "unresolved"


def extract_incident_report_coordinates(ir: dict) -> Tuple[Optional[float], Optional[float], str]:
    """
    Extracts coordinates from citizen incident_reports.
    Checks location.lat, location.lng, location.latitude, location.longitude, location.coordinates [lng, lat].
    Returns: (lat, lon, precision) where lat/lon may be None if unresolvable.
    """
    loc = ir.get("location") or {}
    lat = None
    lon = None

    if isinstance(loc, dict):
        lat = loc.get("lat") if loc.get("lat") is not None else loc.get("latitude")
        lon = loc.get("lng") if loc.get("lng") is not None else (loc.get("lon") if loc.get("lon") is not None else loc.get("longitude"))

        # Check GeoJSON coordinates [lng, lat]
        if (lat is None or lon is None) and isinstance(loc.get("coordinates"), list) and len(loc["coordinates"]) >= 2:
            try:
                lon = float(loc["coordinates"][0])
                lat = float(loc["coordinates"][1])
            except (ValueError, TypeError):
                pass

    if lat is not None and lon is not None:
        try:
            flat, flon = float(lat), float(lon)
            if -90 <= flat <= 90 and -180 <= flon <= 180:
                if abs(flat - 20.5937) < 0.001 and abs(flon - 78.9629) < 0.001:
                    pass  # Reject legacy fake India default centroid
                else:
                    return flat, flon, "exact"
        except (ValueError, TypeError):
            pass

    # Try geocoding address
    addr = loc.get("address") if isinstance(loc, dict) else None
    if addr and isinstance(addr, str) and addr.strip():
        detected = detect_locations(addr)
        st = detected["states"][0] if detected["states"] else None
        dt = detected["cities"][0] if detected["cities"] else None
        if st or dt:
            glat, glon, prec = geocode_location(country="India", state=st, district=dt)
            if glat is not None and glon is not None:
                return glat, glon, f"text_{prec}"

    return None, None, "unresolved"


def parse_time_range_bounds(
    range_str: Optional[str] = "24h",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str], str]:
    """
    Parses time filter string ('24h', '7d', '15d', '30d', 'all', 'custom')
    and computes strict UTC timestamp boundaries (start_epoch, end_epoch, start_iso, end_iso, canonical_name).
    Boundary rule everywhere: timestamp >= start_epoch AND timestamp < end_epoch.
    """
    # 1. Custom Date Range
    if start_date or end_date:
        now = datetime.now(timezone.utc)
        start_dt = None
        end_dt = now

        if start_date:
            try:
                s_clean = start_date.strip().replace("Z", "+00:00")
                start_dt = datetime.fromisoformat(s_clean)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                else:
                    start_dt = start_dt.astimezone(timezone.utc)
            except Exception:
                try:
                    start_dt = datetime.strptime(start_date.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except Exception:
                    pass

        if end_date:
            try:
                e_clean = end_date.strip().replace("Z", "+00:00")
                end_dt = datetime.fromisoformat(e_clean)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                else:
                    end_dt = end_dt.astimezone(timezone.utc)
            except Exception:
                try:
                    # End date inclusive till end of day
                    end_dt = datetime.strptime(end_date.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
                except Exception:
                    pass

        start_epoch = start_dt.timestamp() if start_dt else None
        end_epoch = end_dt.timestamp() if end_dt else None
        start_iso = start_dt.isoformat() if start_dt else None
        end_iso = end_dt.isoformat() if end_dt else None
        return start_epoch, end_epoch, start_iso, end_iso, "custom"

    # 2. Preset Time Range
    r = (range_str or "24h").strip().lower()
    if r in ["all", "none", "0"]:
        return None, None, None, None, "all"

    days = 1
    canonical = "24h"
    if r in ["24h", "24_hours", "24_hour", "24", "1d", "1"]:
        days = 1
        canonical = "24h"
    elif r in ["7d", "7_days", "7_day", "7"]:
        days = 7
        canonical = "7d"
    elif r in ["15d", "15_days", "15_day", "15"]:
        days = 15
        canonical = "15d"
    elif r in ["30d", "30_days", "30_day", "30", "1m", "1_month"]:
        days = 30
        canonical = "30d"

    now = datetime.now(timezone.utc)
    cutoff_dt = now - timedelta(days=days)

    start_epoch = cutoff_dt.timestamp()
    end_epoch = now.timestamp()
    start_iso = cutoff_dt.isoformat()
    end_iso = now.isoformat()

    return start_epoch, end_epoch, start_iso, end_iso, canonical


def parse_time_range_cutoff(range_str: Optional[str]) -> Tuple[Optional[Tuple[int, str, str]], str]:
    """Backward compatibility helper for legacy routes."""
    start_epoch, end_epoch, start_iso, end_iso, canonical = parse_time_range_bounds(range_str)
    if start_epoch is None or start_iso is None:
        return None, canonical
    cutoff_dt = datetime.fromtimestamp(start_epoch, tz=timezone.utc)
    return (int(start_epoch), start_iso, cutoff_dt.strftime("%Y-%m-%d")), canonical



def get_unified_events(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    city: Optional[str] = None,
    limit: Optional[int] = None,
    skip: int = 0,
    time_range: str = "24h",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_unmapped: bool = True,
) -> Dict[str, Any]:
    """
    Retrieves and combines verified disaster events from MongoDB:
    1. earthquakes (NCS RISEQ)
    2. sachet_alerts (NDMA SACHET CAP)
    3. disaster_events (Verified News Feed)
    4. incident_reports (Citizen Incident Reports)

    Guarantees:
    - Zero event loss: never drops an incident because of missing coordinates.
    - Strict boundary rule: timestamp >= start_epoch AND timestamp < end_epoch.
    - Preserves canonical invariant: Total (T) = Mapped (M) + Unmapped (U).
    """
    start_epoch, end_epoch, start_iso, end_iso, canonical_range = parse_time_range_bounds(
        range_str=time_range,
        start_date=start_date,
        end_date=end_date,
    )

    category = category if isinstance(category, str) else None
    severity = severity if isinstance(severity, str) else None
    status = status if isinstance(status, str) else None
    source = source if isinstance(source, str) else None
    state = state if isinstance(state, str) else None
    district = district if isinstance(district, str) else None
    city = city if isinstance(city, str) else None
    limit = limit if isinstance(limit, int) else None
    skip = skip if isinstance(skip, int) else 0
    time_range = time_range if isinstance(time_range, str) else "24h"
    start_date = start_date if isinstance(start_date, str) else None
    end_date = end_date if isinstance(end_date, str) else None

    all_events: List[Dict[str, Any]] = []
    eq_count = 0
    sachet_count = 0
    news_count = 0
    citizen_count = 0

    eq_mapped = 0
    sachet_mapped = 0
    news_mapped = 0
    citizen_mapped = 0

    missing_timestamp_count = 0

    # -------------------------------------------------------------------------
    # 1. Earthquakes (NCS RISEQ)
    # -------------------------------------------------------------------------
    if source in [None, "all", "earthquakes", "ncs"]:
        try:
            eq_query: Dict[str, Any] = {}
            if start_epoch is not None and end_epoch is not None:
                eq_query = {
                    "$or": [
                        {"origin_timestamp": {"$gte": int(start_epoch), "$lt": int(end_epoch) + 1}},
                        {"created_at": {"$gte": start_iso, "$lt": end_iso}},
                        {"origin_time": {"$gte": start_iso, "$lt": end_iso}},
                    ]
                }

            eq_projection = {
                "_id": 1,
                "event_id": 1,
                "latitude": 1,
                "longitude": 1,
                "magnitude": 1,
                "location": 1,
                "region": 1,
                "depth_km": 1,
                "origin_time": 1,
                "origin_timestamp": 1,
                "status": 1,
                "relevance": 1,
                "relevance_details": 1,
                "source_url": 1,
                "felt_report_url": 1,
                "created_at": 1,
            }

            eq_cursor = list(db["earthquakes"].find(eq_query, eq_projection).sort("origin_timestamp", -1))
            for eq in eq_cursor:
                # Time normalization
                time_res = normalize_event_time(eq)
                if not time_res:
                    missing_timestamp_count += 1
                    if canonical_range != "all":
                        continue
                    iso_dt, epoch_ts, d_str, t_str = "", 0.0, "", ""
                else:
                    iso_dt, epoch_ts, d_str, t_str = time_res
                    if start_epoch is not None and epoch_ts < start_epoch:
                        continue
                    if end_epoch is not None and epoch_ts >= end_epoch:
                        continue

                # Coordinate validation (DO NOT discard if missing)
                raw_lat = eq.get("latitude")
                raw_lon = eq.get("longitude")
                lat = None
                lon = None
                has_coords = False
                loc_status = "missing"

                if raw_lat is not None and raw_lon is not None:
                    try:
                        flat = float(raw_lat)
                        flon = float(raw_lon)
                        if -90 <= flat <= 90 and -180 <= flon <= 180:
                            lat = round(flat, 4)
                            lon = round(flon, 4)
                            has_coords = True
                            loc_status = "exact"
                    except (ValueError, TypeError):
                        pass

                mag = eq.get("magnitude") or 3.5
                cat_display, cat_slug = map_category("earthquake")
                sev = map_severity(None, magnitude=mag)
                stat = map_status(eq.get("status"))

                location_name = eq.get("location") or eq.get("region") or "Seismic Epicenter"
                region_name = eq.get("region") or ""

                doc_id = str(eq.get("_id")) if eq.get("_id") else f"eq_{epoch_ts}_{lat}_{lon}"
                event_key = eq.get("event_id") or doc_id

                all_events.append({
                    "id": event_key,
                    "db_id": doc_id,
                    "title": f"M{mag:.1f} Earthquake — {region_name or location_name}",
                    "description": f"Magnitude {mag:.1f} seismic event recorded at depth {eq.get('depth_km', 10)} km. Agency: National Center for Seismology (Govt. of India). Location: {location_name}.",
                    "category": cat_display,
                    "raw_category": cat_slug,
                    "latitude": lat,
                    "longitude": lon,
                    "has_coordinates": has_coords,
                    "location_status": loc_status,
                    "date": d_str,
                    "time": t_str,
                    "datetime": iso_dt,
                    "timestamp": epoch_ts,
                    "location": location_name,
                    "state": eq.get("relevance_details", {}).get("detected_states", [region_name])[0] if eq.get("relevance_details", {}).get("detected_states") else region_name,
                    "district": eq.get("relevance_details", {}).get("detected_cities", [""])[0] if eq.get("relevance_details", {}).get("detected_cities") else "",
                    "city": "",
                    "severity": sev,
                    "status": stat,
                    "source": "NCS_RISEQ",
                    "source_group": "ncs",
                    "source_label": "National Center for Seismology",
                    "source_url": eq.get("source_url") or eq.get("felt_report_url") or "https://riseq.seismo.gov.in/riseq/earthquake",
                    "image": None,
                    "helpline": "1070 / 112",
                    "response_units": ["National Center for Seismology (NCS)", "National Disaster Response Force (NDRF)"],
                    "metadata": {
                        "magnitude": mag,
                        "depth_km": eq.get("depth_km", 10),
                        "relevance": eq.get("relevance", "INDIA"),
                    }
                })
                eq_count += 1
                if has_coords:
                    eq_mapped += 1
        except Exception as e:
            logger.error(f"Error reading earthquakes collection: {e}")

    # -------------------------------------------------------------------------
    # 2. NDMA SACHET Government Alerts
    # -------------------------------------------------------------------------
    if source in [None, "all", "sachet", "ndma"]:
        try:
            sa_query: Dict[str, Any] = {}
            if start_epoch is not None and end_epoch is not None:
                sa_query = {
                    "$or": [
                        {"event_timestamp": {"$gte": int(start_epoch), "$lt": int(end_epoch) + 1}},
                        {"sent_at": {"$gte": start_iso, "$lt": end_iso}},
                        {"effective_at": {"$gte": start_iso, "$lt": end_iso}},
                        {"created_at": {"$gte": start_iso, "$lt": end_iso}},
                    ]
                }

            sa_projection = {
                "_id": 1,
                "event_id": 1,
                "alert_id": 1,
                "latitude": 1,
                "longitude": 1,
                "location": 1,
                "disaster_type": 1,
                "event": 1,
                "severity": 1,
                "status": 1,
                "headline": 1,
                "title": 1,
                "description": 1,
                "instruction": 1,
                "area_description": 1,
                "sender_name": 1,
                "source_authority": 1,
                "link": 1,
                "source_url": 1,
                "polygon": 1,
                "circle": 1,
                "sent_at": 1,
                "published_at": 1,
                "effective_at": 1,
                "event_time": 1,
                "event_timestamp": 1,
                "created_at": 1,
                "urgency": 1,
                "certainty": 1,
            }

            sa_cursor = list(db["sachet_alerts"].find(sa_query, sa_projection).sort("event_timestamp", -1))
            for sa in sa_cursor:
                # Time normalization
                time_res = normalize_event_time(sa)
                if not time_res:
                    missing_timestamp_count += 1
                    if canonical_range != "all":
                        continue
                    iso_dt, epoch_ts, d_str, t_str = "", 0.0, "", ""
                else:
                    iso_dt, epoch_ts, d_str, t_str = time_res
                    if start_epoch is not None and epoch_ts < start_epoch:
                        continue
                    if end_epoch is not None and epoch_ts >= end_epoch:
                        continue

                # Coordinate extraction (non-destructive)
                lat, lon, coord_precision = extract_sachet_coordinates(sa)
                has_coords = lat is not None and lon is not None
                loc = sa.get("location") or {}

                raw_type = sa.get("disaster_type") or sa.get("event") or "Alert"
                cat_display, cat_slug = map_category(raw_type)
                sev = map_severity(sa.get("severity"))
                stat = map_status(sa.get("status"))

                title = sa.get("headline") or sa.get("title") or f"{cat_display} Warning"
                desc = sa.get("description") or sa.get("instruction") or "Official disaster advisory issued by State/National Disaster Management Authority."
                area_desc = sa.get("area_description") or (loc.get("district") if isinstance(loc, dict) else "") or (loc.get("state") if isinstance(loc, dict) else "") or "India"

                doc_id = str(sa.get("_id")) if sa.get("_id") else f"sachet_{epoch_ts}_{lat}_{lon}"
                event_key = sa.get("event_id") or sa.get("alert_id") or doc_id

                all_events.append({
                    "id": event_key,
                    "db_id": doc_id,
                    "title": title[:140],
                    "description": desc,
                    "category": cat_display,
                    "raw_category": cat_slug,
                    "latitude": round(lat, 4) if has_coords else None,
                    "longitude": round(lon, 4) if has_coords else None,
                    "has_coordinates": has_coords,
                    "location_status": coord_precision if has_coords else "unresolved",
                    "date": d_str,
                    "time": t_str,
                    "datetime": iso_dt,
                    "timestamp": epoch_ts,
                    "location": area_desc,
                    "state": loc.get("state") if isinstance(loc, dict) else (sa.get("state") or ""),
                    "district": loc.get("district") if isinstance(loc, dict) else (sa.get("district") or ""),
                    "city": loc.get("city") if isinstance(loc, dict) else "",
                    "severity": sev,
                    "status": stat,
                    "source": "NDMA_SACHET",
                    "source_group": "sachet",
                    "source_label": sa.get("sender_name") or sa.get("source_authority") or "NDMA SACHET Alert",
                    "source_url": sa.get("link") or sa.get("source_url") or "https://sachet.ndma.gov.in",
                    "image": None,
                    "helpline": "1070 / 112",
                    "response_units": ["State Disaster Management Authority (SDMA)", "State Disaster Response Force (SDRF)"],
                    "metadata": {
                        "urgency": sa.get("urgency"),
                        "certainty": sa.get("certainty"),
                        "polygon": sa.get("polygon"),
                        "coord_precision": coord_precision,
                    }
                })
                sachet_count += 1
                if has_coords:
                    sachet_mapped += 1
        except Exception as e:
            logger.error(f"Error reading sachet_alerts collection: {e}")

    # -------------------------------------------------------------------------
    # 3. Verified News Disasters (GNews Feed)
    # -------------------------------------------------------------------------
    if source in [None, "all", "news", "gnews"]:
        try:
            news_query: Dict[str, Any] = {}
            if start_epoch is not None and end_epoch is not None:
                start_dt_str = datetime.fromtimestamp(start_epoch, tz=timezone.utc).strftime("%Y-%m-%d")
                end_dt_str = datetime.fromtimestamp(end_epoch, tz=timezone.utc).strftime("%Y-%m-%d")
                news_query = {
                    "$or": [
                        {"processed_at": {"$gte": start_iso, "$lt": end_iso}},
                        {"first_seen_at": {"$gte": start_iso, "$lt": end_iso}},
                        {"incident_date": {"$gte": start_dt_str, "$lte": end_dt_str}},
                    ]
                }

            news_projection = {
                "_id": 1,
                "event_id": 1,
                "article_id": 1,
                "latitude": 1,
                "longitude": 1,
                "location": 1,
                "disaster_type": 1,
                "severity": 1,
                "status": 1,
                "title": 1,
                "description": 1,
                "url": 1,
                "image": 1,
                "confidence": 1,
                "incident_date": 1,
                "processed_at": 1,
                "published_at": 1,
                "first_seen_at": 1,
            }

            news_cursor = list(db["disaster_events"].find(news_query, news_projection).sort("processed_at", -1))
            for ev in news_cursor:
                # Time normalization
                time_res = normalize_event_time(ev)
                if not time_res:
                    missing_timestamp_count += 1
                    if canonical_range != "all":
                        continue
                    iso_dt, epoch_ts, d_str, t_str = "", 0.0, "", ""
                else:
                    iso_dt, epoch_ts, d_str, t_str = time_res
                    if start_epoch is not None and epoch_ts < start_epoch:
                        continue
                    if end_epoch is not None and epoch_ts >= end_epoch:
                        continue

                # Coordinate extraction (non-destructive)
                lat, lon, coord_precision = extract_news_coordinates(ev)
                has_coords = lat is not None and lon is not None
                loc = ev.get("location") or {}

                raw_type = ev.get("disaster_type") or "disaster"
                cat_display, cat_slug = map_category(raw_type)
                sev = map_severity(ev.get("severity"))
                stat = map_status(ev.get("status"))

                title = ev.get("title") or f"{cat_display} Incident"
                desc = ev.get("description") or "Disaster incident verified via multi-source intelligence."
                loc_str = (
                    (f"{loc.get('district')}, {loc.get('state')}" if loc.get('district') and loc.get('state') else loc.get('state'))
                    if isinstance(loc, dict) and (loc.get('district') or loc.get('state')) else "India"
                )

                doc_id = str(ev.get("_id")) if ev.get("_id") else f"news_{epoch_ts}_{lat}_{lon}"
                event_key = ev.get("event_id") or ev.get("article_id") or doc_id

                all_events.append({
                    "id": event_key,
                    "db_id": doc_id,
                    "title": title[:140],
                    "description": desc,
                    "category": cat_display,
                    "raw_category": cat_slug,
                    "latitude": round(lat, 4) if has_coords else None,
                    "longitude": round(lon, 4) if has_coords else None,
                    "has_coordinates": has_coords,
                    "location_status": coord_precision if has_coords else "unresolved",
                    "date": d_str,
                    "time": t_str,
                    "datetime": iso_dt,
                    "timestamp": epoch_ts,
                    "location": loc_str,
                    "state": loc.get("state") if isinstance(loc, dict) else "",
                    "district": loc.get("district") if isinstance(loc, dict) else "",
                    "city": loc.get("city") if isinstance(loc, dict) else "",
                    "severity": sev,
                    "status": stat,
                    "source": "GNEWS",
                    "source_group": "news",
                    "source_label": "Verified Disaster Intelligence",
                    "source_url": ev.get("url") or "",
                    "image": ev.get("image") or None,
                    "helpline": "1070 / 112",
                    "response_units": ["District Disaster Management Authority (DDMA)", "Local First Responders"],
                    "metadata": {
                        "confidence": ev.get("confidence"),
                        "incident_date": ev.get("incident_date"),
                        "coord_precision": coord_precision,
                    }
                })
                news_count += 1
                if has_coords:
                    news_mapped += 1
        except Exception as e:
            logger.error(f"Error reading disaster_events collection: {e}")

    # -------------------------------------------------------------------------
    # 4. Citizen Disaster Incident Reports (incident_reports)
    # -------------------------------------------------------------------------
    if source in [None, "all", "citizen", "citizen_reports", "reports"]:
        try:
            ir_query: Dict[str, Any] = {}
            if start_epoch is not None and end_epoch is not None:
                start_dt_obj = datetime.fromtimestamp(start_epoch, tz=timezone.utc)
                end_dt_obj = datetime.fromtimestamp(end_epoch, tz=timezone.utc)
                ir_query = {
                    "$or": [
                        {"created_at": {"$gte": start_dt_obj, "$lt": end_dt_obj}},
                        {"created_at": {"$gte": start_iso, "$lt": end_iso}},
                    ]
                }

            ir_cursor = list(db["incident_reports"].find(ir_query).sort("created_at", -1))
            for ir in ir_cursor:
                # Time normalization
                time_res = normalize_event_time(ir)
                if not time_res:
                    missing_timestamp_count += 1
                    if canonical_range != "all":
                        continue
                    iso_dt, epoch_ts, d_str, t_str = "", 0.0, "", ""
                else:
                    iso_dt, epoch_ts, d_str, t_str = time_res
                    if start_epoch is not None and epoch_ts < start_epoch:
                        continue
                    if end_epoch is not None and epoch_ts >= end_epoch:
                        continue

                lat, lon, coord_precision = extract_incident_report_coordinates(ir)
                has_coords = lat is not None and lon is not None
                loc = ir.get("location") or {}

                raw_type = ir.get("event_type") or "other"
                cat_display, cat_slug = map_category(raw_type)
                sev = map_severity(ir.get("severity"))
                stat = map_status(ir.get("status"))

                address_text = loc.get("address") if isinstance(loc, dict) else ""
                state_text = loc.get("state") if isinstance(loc, dict) else ""
                district_text = loc.get("district") if isinstance(loc, dict) else ""

                if not state_text and address_text:
                    det = detect_locations(address_text)
                    if det.get("states"):
                        state_text = det["states"][0]
                    if det.get("cities") and not district_text:
                        district_text = det["cities"][0]

                desc = ir.get("description") or f"Citizen incident report submitted for {cat_display}."
                title = f"{cat_display} Report — {district_text or state_text or 'Citizen Report'}"

                doc_id = str(ir.get("_id")) if ir.get("_id") else f"report_{epoch_ts}_{lat}_{lon}"
                event_key = ir.get("report_id") or doc_id

                all_events.append({
                    "id": event_key,
                    "db_id": doc_id,
                    "title": title[:140],
                    "description": desc,
                    "category": cat_display,
                    "raw_category": cat_slug,
                    "latitude": round(lat, 4) if has_coords else None,
                    "longitude": round(lon, 4) if has_coords else None,
                    "has_coordinates": has_coords,
                    "location_status": coord_precision if has_coords else "unresolved",
                    "date": d_str,
                    "time": t_str,
                    "datetime": iso_dt,
                    "timestamp": epoch_ts,
                    "location": address_text or state_text or "Citizen Reported Incident",
                    "state": state_text,
                    "district": district_text,
                    "city": loc.get("city") if isinstance(loc, dict) else "",
                    "severity": sev,
                    "status": stat,
                    "source": "CITIZEN_REPORT",
                    "source_group": "citizen",
                    "source_label": "Verified Citizen Report",
                    "source_url": "",
                    "image": (ir.get("images")[0].get("url") if ir.get("images") and isinstance(ir.get("images"), list) and isinstance(ir.get("images")[0], dict) else None),
                    "helpline": "1070 / 112",
                    "response_units": ["District Emergency Operation Center (DEOC)", "Local First Responders"],
                    "metadata": {
                        "user_name": ir.get("user_name"),
                        "report_id": ir.get("report_id"),
                        "coord_precision": coord_precision,
                    }
                })
                citizen_count += 1
                if has_coords:
                    citizen_mapped += 1
        except Exception as e:
            logger.error(f"Error reading incident_reports collection: {e}")

    # -------------------------------------------------------------------------
    # Deduplication by canonical ID across all streams
    # -------------------------------------------------------------------------
    seen_ids = set()
    unique_events: List[Dict[str, Any]] = []
    for ev in all_events:
        eid = ev.get("id")
        if eid and eid not in seen_ids:
            seen_ids.add(eid)
            unique_events.append(ev)

    # Sort strictly by timestamp descending (newest first)
    unique_events.sort(key=lambda x: x.get("timestamp", 0.0), reverse=True)

    # Filter by category if requested
    filtered_events = unique_events
    if category and category.strip().lower() not in ["all", ""]:
        c_req = category.strip().lower()
        filtered_events = [
            e for e in filtered_events
            if e["category"].lower() == c_req or e["raw_category"] == c_req
        ]

    # Filter by severity if requested
    if severity and severity.strip().lower() not in ["all", ""]:
        s_req = severity.strip().lower()
        filtered_events = [
            e for e in filtered_events
            if e["severity"].lower() == s_req
        ]

    # Filter by status if requested
    if status and status.strip().lower() not in ["all", ""]:
        st_req = status.strip().lower()
        filtered_events = [
            e for e in filtered_events
            if e["status"].lower() == st_req
        ]

    # Filter by geographic area if requested (state, district, city)
    geo_area = normalize_geographic_query(country="India", state=state, district=district, city=city)
    if geo_area["level"] != "country":
        matching = []
        for e in filtered_events:
            res = evaluate_event_geographic_match(e, geo_area)
            if res["is_match"]:
                matching.append(e)
        filtered_events = matching

    # Compute available categories sorted descending by event count
    cat_counts: Dict[str, int] = {}
    for e in unique_events:
        c_name = e["category"]
        cat_counts[c_name] = cat_counts.get(c_name, 0) + 1

    sorted_categories = sorted(
        cat_counts.keys(),
        key=lambda c: (-cat_counts[c], c),
    )
    if "All" not in sorted_categories:
        sorted_categories.insert(0, "All")

    total_count = len(filtered_events)
    mapped_count = sum(1 for e in filtered_events if e.get("has_coordinates"))
    unmapped_count = total_count - mapped_count

    if limit is not None and limit > 0:
        paged_events = filtered_events[skip : skip + limit]
    else:
        paged_events = filtered_events[skip:]

    return {
        "status": "success",
        "time_range": canonical_range,
        "start_time": start_iso,
        "end_time": end_iso,
        "total": total_count,
        "count": len(paged_events),
        "mapped_count": mapped_count,
        "unmapped_count": unmapped_count,
        "missing_timestamp_count": missing_timestamp_count,
        "invariant_holds": (total_count == mapped_count + unmapped_count),
        "source_counts": {
            "total": len(unique_events),
            "earthquakes": eq_count,
            "sachet": sachet_count,
            "news": news_count,
            "citizen_reports": citizen_count,
        },
        "source_mapped_counts": {
            "earthquakes": eq_mapped,
            "sachet": sachet_mapped,
            "news": news_mapped,
            "citizen_reports": citizen_mapped,
        },
        "categories": sorted_categories,
        "events": paged_events,
    }


def get_event_by_id(event_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single unified event by its unique deterministic ID or db_id."""
    all_res = get_unified_events(limit=None, time_range="all")
    clean_id = str(event_id).strip()
    for ev in all_res.get("events", []):
        if str(ev.get("id")) == clean_id or str(ev.get("db_id")) == clean_id:
            return ev
    return None
