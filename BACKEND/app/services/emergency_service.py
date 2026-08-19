"""
DISHA Platform - Nearby Emergency Services Service
Disaster Intelligence and Situational Hazard Awareness Platform

Provides modular geographic discovery for emergency facilities:
1. Medical Centres / Hospitals (amenity=hospital, amenity=clinic, emergency=ambulance_station)
2. Police Stations (amenity=police)
3. Fire Stations (amenity=fire_station)

Features:
- Incident-centric search using incident latitude & longitude (Incident -> Emergency Service)
- Accurate Haversine distance computation in kilometers
- Emergency response driving time estimation (~min)
- Multi-endpoint fallback for high availability
- In-memory TTL caching to eliminate redundant external calls
- Clean data structure and provider abstraction
"""

import math
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
import requests

logger = logging.getLogger("disha.emergency_service")
logger.setLevel(logging.INFO)

# Public Overpass API mirrors for high availability fallback
OVERPASS_ENDPOINTS = [
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# In-memory TTL Cache
# Key: (round(lat, 3), round(lng, 3), radius_m) -> Value: (timestamp, data)
_CACHE: Dict[Tuple[float, float, int], Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour cache


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two coordinate pairs using Haversine formula.
    Returns distance in kilometers rounded to 2 decimal places.
    """
    r = 6371.0  # Earth's mean radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)


def estimate_travel_time_min(distance_km: float) -> int:
    """
    Estimates emergency vehicle travel time in minutes based on typical Indian urban/rural speeds (~35 km/h avg).
    Minimum is 1 minute.
    """
    if distance_km <= 0.2:
        return 1
    avg_speed_kmh = 35.0
    minutes = round((distance_km / avg_speed_kmh) * 60.0)
    return max(1, minutes)


def format_travel_time(minutes: int) -> str:
    """Formats estimated travel time nicely (e.g., '~6 min' or '~1 hr 15 min')."""
    if minutes < 60:
        return f"~{minutes} min"
    hrs = minutes // 60
    rem_min = minutes % 60
    if rem_min == 0:
        return f"~{hrs} hr"
    return f"~{hrs} hr {rem_min} min"


def format_distance(distance_km: float) -> str:
    """Formats distance string nicely."""
    if distance_km < 1.0:
        meters = int(distance_km * 1000)
        return f"{meters} m"
    return f"{distance_km:.1f} km"


def build_directions_url(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> str:
    """
    Generates standard Google Maps navigation URL with incident coordinates as origin
    and emergency service coordinates as destination.
    """
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={origin_lat:.6f},{origin_lng:.6f}"
        f"&destination={dest_lat:.6f},{dest_lng:.6f}"
    )


def extract_phone(tags: Dict[str, Any]) -> Optional[str]:
    """Extracts first available contact or emergency phone number from OSM tags."""
    phone_keys = [
        "phone",
        "contact:phone",
        "emergency:phone",
        "phone:emergency",
        "mobile",
        "contact:mobile",
        "telephone",
    ]
    for key in phone_keys:
        val = tags.get(key)
        if val and isinstance(val, str) and val.strip():
            cleaned = val.strip().replace(" ", "").replace("-", "")
            # Quick check that it contains digits
            if any(c.isdigit() for c in cleaned):
                return val.strip()
    return None


def extract_address(tags: Dict[str, Any]) -> Optional[str]:
    """Extracts or constructs readable address from OSM tags."""
    if tags.get("addr:full"):
        return tags["addr:full"].strip()

    parts = []
    if tags.get("addr:housenumber"):
        parts.append(tags["addr:housenumber"].strip())
    if tags.get("addr:street"):
        parts.append(tags["addr:street"].strip())
    if tags.get("addr:suburb") or tags.get("addr:neighbourhood"):
        parts.append((tags.get("addr:suburb") or tags.get("addr:neighbourhood")).strip())
    if tags.get("addr:district") or tags.get("addr:city"):
        parts.append((tags.get("addr:district") or tags.get("addr:city")).strip())
    if tags.get("addr:state"):
        parts.append(tags["addr:state"].strip())

    if parts:
        return ", ".join(parts)
    
    if tags.get("operator"):
        return f"Operated by {tags['operator'].strip()}"
    
    return None


class BaseEmergencyServiceProvider:
    """Abstract base provider class for emergency services lookup."""
    def find_nearby_services(
        self,
        lat: float,
        lng: float,
        radius_m: int = 5000,
        limit_per_category: Optional[int] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        raise NotImplementedError


class OverpassEmergencyServiceProvider(BaseEmergencyServiceProvider):
    """
    Production-grade OpenStreetMap Overpass API implementation.
    Discovers nearby hospitals, clinics, police stations, and fire stations around incident coordinates.
    """

    def _build_overpass_query(self, lat: float, lng: float, radius_m: int) -> str:
        """
        Constructs ultra-fast indexed Overpass QL bounding-box query.
        Uses spatial R-Tree index to prevent Overpass slot queue throttling and 504 timeouts.
        """
        radius_km = radius_m / 1000.0
        delta_lat = radius_km / 111.0
        cos_lat = math.cos(math.radians(lat))
        delta_lng = radius_km / (111.0 * max(0.01, cos_lat))

        south = lat - delta_lat
        north = lat + delta_lat
        west = lng - delta_lng
        east = lng + delta_lng

        return f"""[out:json][timeout:10][bbox:{south:.5f},{west:.5f},{north:.5f},{east:.5f}];
(
  node["amenity"~"^(hospital|clinic|doctors|police|fire_station)$"];
  way["amenity"~"^(hospital|clinic|doctors|police|fire_station)$"];
  node["emergency"~"^(ambulance_station|fire_service)$"];
  way["emergency"~"^(ambulance_station|fire_service)$"];
);
out center body;"""

    def _execute_overpass_query(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Executes query with multi-endpoint fallback and timeout safety."""
        headers = {
            "User-Agent": "DISHA-Emergency-Services-Platform/1.0 (Disaster Situational Intelligence)"
        }
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                resp = requests.post(
                    endpoint,
                    data={"data": query},
                    headers=headers,
                    timeout=5,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    elements = data.get("elements", [])
                    return elements
                else:
                    logger.debug(f"Overpass endpoint {endpoint} returned status {resp.status_code}")
            except Exception as e:
                logger.debug(f"Overpass endpoint {endpoint} failed: {e}")
                continue
        return None

    def find_nearby_services(
        self,
        lat: float,
        lng: float,
        radius_m: int = 5000,
        limit_per_category: Optional[int] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discovers nearby emergency services from incident coordinates (lat, lng).
        Returns dictionary with keys: 'medical', 'police', 'fire', sorted by distance ascending.
        If limit_per_category is None, returns ALL facilities found within radius_m.
        """
        # 1. Check in-memory TTL cache
        cache_key = (round(lat, 3), round(lng, 3), radius_m)
        now = time.time()
        if cache_key in _CACHE:
            cached_time, cached_data = _CACHE[cache_key]
            if now - cached_time < _CACHE_TTL_SECONDS:
                # Return freshly sliced results according to limit
                if limit_per_category is not None and limit_per_category > 0:
                    return {
                        cat: items[:limit_per_category]
                        for cat, items in cached_data.items()
                    }
                return {
                    cat: list(items)
                    for cat, items in cached_data.items()
                }

        # 2. Build and execute query
        query = self._build_overpass_query(lat, lng, radius_m)
        elements = self._execute_overpass_query(query)

        medical_list: List[Dict[str, Any]] = []
        police_list: List[Dict[str, Any]] = []
        fire_list: List[Dict[str, Any]] = []

        if not elements:
            logger.info(f"No Overpass elements returned for ({lat}, {lng}) within {radius_m}m")
            return {"medical": [], "police": [], "fire": []}

        seen_keys = set()

        for el in elements:
            tags = el.get("tags") or {}
            
            # Coordinate extraction (node has lat/lon; way has center.lat/center.lon)
            if "lat" in el and "lon" in el:
                s_lat = float(el["lat"])
                s_lon = float(el["lon"])
            elif "center" in el and "lat" in el["center"] and "lon" in el["center"]:
                s_lat = float(el["center"]["lat"])
                s_lon = float(el["center"]["lon"])
            else:
                continue

            amenity = tags.get("amenity", "").lower()
            emergency = tags.get("emergency", "").lower()

            # Determine category
            category = None
            category_label = ""
            icon = ""

            if amenity in ["hospital", "clinic", "doctors"] or emergency == "ambulance_station":
                category = "medical"
                if amenity == "hospital":
                    category_label = "Medical Centre / Hospital"
                    icon = "🏥"
                elif amenity == "clinic":
                    category_label = "Clinic / Health Centre"
                    icon = "🏥"
                else:
                    category_label = "Ambulance / Medical Unit"
                    icon = "🏥"
            elif amenity == "police":
                category = "police"
                category_label = "Police Station"
                icon = "🚔"
            elif amenity == "fire_station" or emergency == "fire_service":
                category = "fire"
                category_label = "Fire Station"
                icon = "🚒"

            if not category:
                continue

            # Name extraction
            name = (
                tags.get("name")
                or tags.get("name:en")
                or tags.get("official_name")
                or tags.get("alt_name")
            )
            if not name or not name.strip():
                if category == "medical":
                    name = "Medical Centre / Hospital"
                elif category == "police":
                    name = "Police Station"
                elif category == "fire":
                    name = "Fire Station"
            else:
                name = name.strip()

            # Deduplication key (name + rounded coords)
            dedup_key = (name.lower(), round(s_lat, 3), round(s_lon, 3))
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            # Distance & Travel Time
            dist_km = haversine_distance_km(lat, lng, s_lat, s_lon)
            if dist_km > (radius_m / 1000.0):
                continue

            time_min = estimate_travel_time_min(dist_km)
            phone = extract_phone(tags)
            address = extract_address(tags)
            directions_url = build_directions_url(lat, lng, s_lat, s_lon)

            item = {
                "id": f"{el.get('type', 'node')}_{el.get('id', '')}",
                "name": name,
                "category": category,
                "category_label": category_label,
                "icon": icon,
                "latitude": s_lat,
                "longitude": s_lon,
                "distance_km": dist_km,
                "distance_formatted": format_distance(dist_km),
                "estimated_time_min": time_min,
                "estimated_time_formatted": format_travel_time(time_min),
                "address": address,
                "phone": phone,
                "directions_url": directions_url,
            }

            if category == "medical":
                medical_list.append(item)
            elif category == "police":
                police_list.append(item)
            elif category == "fire":
                fire_list.append(item)

        # Sort all lists strictly by distance ascending (Nearest -> Farthest)
        medical_list.sort(key=lambda x: x["distance_km"])
        police_list.sort(key=lambda x: x["distance_km"])
        fire_list.sort(key=lambda x: x["distance_km"])

        full_results = {
            "medical": medical_list,
            "police": police_list,
            "fire": fire_list,
        }

        # Cache full results
        _CACHE[cache_key] = (now, full_results)

        if limit_per_category is not None and limit_per_category > 0:
            return {
                "medical": medical_list[:limit_per_category],
                "police": police_list[:limit_per_category],
                "fire": fire_list[:limit_per_category],
            }

        return {
            "medical": medical_list,
            "police": police_list,
            "fire": fire_list,
        }


# Default provider instance (modular and swappable)
_provider: BaseEmergencyServiceProvider = OverpassEmergencyServiceProvider()


def get_emergency_service_provider() -> BaseEmergencyServiceProvider:
    """Returns currently configured emergency service provider."""
    return _provider


def set_emergency_service_provider(provider: BaseEmergencyServiceProvider):
    """Allows swapping emergency service provider (e.g. for testing or alternative POI APIs)."""
    global _provider
    _provider = provider


def get_nearby_emergency_services(
    lat: float,
    lng: float,
    radius_m: int = 5000,
    limit: Optional[int] = None,
    auto_expand: bool = True,
) -> Dict[str, Any]:
    """
    Main entrypoint function to fetch nearby emergency services for given incident coordinates.
    If auto_expand is True and initial radius yields 0 facilities (e.g. rural epicenters),
    it automatically performs adaptive search expanding to 15km and 25km.
    """
    provider = get_emergency_service_provider()
    actual_radius_m = radius_m
    results = provider.find_nearby_services(
        lat=lat,
        lng=lng,
        radius_m=actual_radius_m,
        limit_per_category=limit,
    )

    total_count = sum(len(items) for items in results.values())

    # Adaptive Advanced Expansion for rural/remote locations
    if total_count == 0 and auto_expand and radius_m <= 5000:
        for expand_r in [15000, 25000]:
            expanded_res = provider.find_nearby_services(
                lat=lat,
                lng=lng,
                radius_m=expand_r,
                limit_per_category=limit,
            )
            exp_total = sum(len(items) for items in expanded_res.values())
            if exp_total > 0:
                results = expanded_res
                actual_radius_m = expand_r
                total_count = exp_total
                break

    zone_label = (
        "5 km Local Area"
        if actual_radius_m <= 5000
        else ("15 km District Zone" if actual_radius_m <= 15000 else "25 km Regional Sector")
    )

    return {
        "status": "success",
        "incident_coordinates": {
            "latitude": lat,
            "longitude": lng,
        },
        "search_radius_km": round(actual_radius_m / 1000.0, 1),
        "zone_label": zone_label,
        "counts": {
            "medical": len(results.get("medical", [])),
            "police": len(results.get("police", [])),
            "fire": len(results.get("fire", [])),
            "total": total_count,
        },
        "services": results,
    }
