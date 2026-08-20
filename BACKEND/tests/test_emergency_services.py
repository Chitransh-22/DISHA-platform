"""
DISHA Platform - Emergency Services Unit & Integration Tests
Tests for:
1. Distance calculation and sorting (Haversine & driving time)
2. OpenStreetMap Overpass Provider & Caching
3. FastAPI endpoint /api/emergency-services and /api/nearby-services
4. Directions URL formatting with incident coordinates as origin
5. Category grouping (Medical, Police, Fire)
"""

import math
import sys
from pathlib import Path
import pytest

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi.testclient import TestClient
from main import app
from app.services.emergency_service import (
    haversine_distance_km,
    estimate_travel_time_min,
    format_travel_time,
    format_distance,
    build_directions_url,
    get_nearby_emergency_services,
    BaseEmergencyServiceProvider,
    set_emergency_service_provider,
    get_emergency_service_provider,
    OverpassEmergencyServiceProvider,
)

client = TestClient(app)


class MockEmergencyServiceProvider(BaseEmergencyServiceProvider):
    """Deterministic Mock Provider for unit testing."""
    def find_nearby_services(self, lat: float, lng: float, radius_m: int = 5000, limit_per_category: int = None):
        med = [
            {
                "id": "node_101",
                "name": "Civil Hospital",
                "category": "medical",
                "category_label": "Medical Centre / Hospital",
                "icon": "🏥",
                "latitude": lat + 0.01,
                "longitude": lng + 0.01,
                "distance_km": 1.5,
                "distance_formatted": "1.5 km",
                "estimated_time_min": 3,
                "estimated_time_formatted": "~3 min",
                "address": "Asarwa, Ahmedabad",
                "phone": "+91 79 2268 0000",
                "directions_url": build_directions_url(lat, lng, lat + 0.01, lng + 0.01),
            },
            {
                "id": "node_102",
                "name": "Apollo City Clinic",
                "category": "medical",
                "category_label": "Clinic / Health Centre",
                "icon": "🏥",
                "latitude": lat + 0.02,
                "longitude": lng + 0.02,
                "distance_km": 3.1,
                "distance_formatted": "3.1 km",
                "estimated_time_min": 5,
                "estimated_time_formatted": "~5 min",
                "address": "Ellisbridge, Ahmedabad",
                "phone": "+91 79 2657 0000",
                "directions_url": build_directions_url(lat, lng, lat + 0.02, lng + 0.02),
            },
        ]
        pol = [
            {
                "id": "node_201",
                "name": "Ellisbridge Police Station",
                "category": "police",
                "category_label": "Police Station",
                "icon": "🚔",
                "latitude": lat + 0.005,
                "longitude": lng + 0.005,
                "distance_km": 0.8,
                "distance_formatted": "800 m",
                "estimated_time_min": 2,
                "estimated_time_formatted": "~2 min",
                "address": "Ashram Road, Ahmedabad",
                "phone": "+91 79 2550 0000",
                "directions_url": build_directions_url(lat, lng, lat + 0.005, lng + 0.005),
            }
        ]
        fire = [
            {
                "id": "node_301",
                "name": "Navrangpura Fire Station",
                "category": "fire",
                "category_label": "Fire Station",
                "icon": "🚒",
                "latitude": lat + 0.015,
                "longitude": lng + 0.015,
                "distance_km": 2.2,
                "distance_formatted": "2.2 km",
                "estimated_time_min": 4,
                "estimated_time_formatted": "~4 min",
                "address": "Navrangpura, Ahmedabad",
                "phone": "101",
                "directions_url": build_directions_url(lat, lng, lat + 0.015, lng + 0.015),
            }
        ]

        if limit_per_category is not None and limit_per_category > 0:
            return {
                "medical": med[:limit_per_category],
                "police": pol[:limit_per_category],
                "fire": fire[:limit_per_category],
            }
        return {
            "medical": med,
            "police": pol,
            "fire": fire,
        }


def test_haversine_distance():
    # Distance between New Delhi (28.6139, 77.2090) and Connaught Place (28.6328, 77.2197) ~2.3 km
    dist = haversine_distance_km(28.6139, 77.2090, 28.6328, 77.2197)
    assert 2.0 <= dist <= 2.6


def test_travel_time_estimation():
    assert estimate_travel_time_min(0.1) == 1
    assert estimate_travel_time_min(3.5) == 6
    assert format_travel_time(6) == "~6 min"
    assert format_travel_time(75) == "~1 hr 15 min"


def test_format_distance():
    assert format_distance(0.45) == "450 m"
    assert format_distance(1.82) == "1.8 km"


def test_directions_url_uses_incident_coordinates():
    origin_lat, origin_lng = 23.0225, 72.5714
    dest_lat, dest_lng = 23.0521, 72.5872
    url = build_directions_url(origin_lat, origin_lng, dest_lat, dest_lng)
    
    assert "https://www.google.com/maps/dir/?api=1" in url
    assert f"origin={origin_lat:.6f},{origin_lng:.6f}" in url
    assert f"destination={dest_lat:.6f},{dest_lng:.6f}" in url


def test_api_emergency_services_with_mock():
    orig_provider = get_emergency_service_provider()
    try:
        set_emergency_service_provider(MockEmergencyServiceProvider())
        # Test default radius (5000m) and unlimited results
        response = client.get("/api/emergency-services?lat=23.0225&lng=72.5714")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["incident_coordinates"]["latitude"] == 23.0225
        assert data["incident_coordinates"]["longitude"] == 72.5714
        assert data["search_radius_km"] == 5.0
        assert "services" in data
        assert "medical" in data["services"]
        assert "police" in data["services"]
        assert "fire" in data["services"]

        med_list = data["services"]["medical"]
        assert len(med_list) == 2  # Returns all 2 mock medical facilities
        assert med_list[0]["name"] == "Civil Hospital"
        assert med_list[0]["distance_km"] <= med_list[1]["distance_km"]

        # Alias test
        alias_resp = client.get("/api/nearby-services?lat=23.0225&lng=72.5714")
        assert alias_resp.status_code == 200
        assert alias_resp.json()["status"] == "success"
    finally:
        set_emergency_service_provider(orig_provider)


def test_api_param_validation():
    # Invalid latitude
    resp = client.get("/api/emergency-services?lat=120.0&lng=72.5714")
    assert resp.status_code == 422

    # Invalid longitude
    resp = client.get("/api/emergency-services?lat=23.0&lng=200.0")
    assert resp.status_code == 422

    # Missing coordinates
    resp = client.get("/api/emergency-services")
    assert resp.status_code == 422


def test_real_overpass_provider():
    # Real live test against Overpass provider for 5 km radius around Ahmedabad coordinates
    provider = OverpassEmergencyServiceProvider()
    results = provider.find_nearby_services(23.0225, 72.5714, radius_m=5000, limit_per_category=None)
    
    assert "medical" in results
    assert "police" in results
    assert "fire" in results

    # Services should be found in a 5 km radius in a major metro city
    total_found = len(results["medical"]) + len(results["police"]) + len(results["fire"])
    assert total_found > 0

    # Verify all items are sorted by distance and within 5 km distance
    for cat in ["medical", "police", "fire"]:
        items = results[cat]
        for i in range(len(items) - 1):
            assert items[i]["distance_km"] <= items[i+1]["distance_km"]
            assert items[i]["distance_km"] <= 5.5  # Allow minor boundary tolerance
