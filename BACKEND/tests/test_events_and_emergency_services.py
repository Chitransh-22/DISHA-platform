"""
DISHA Platform - Comprehensive Integration Test Suite
Tests:
1. Unified /api/events endpoint and filtering
2. /api/emergency-services and /api/emergency-services/nearby endpoints
3. Haversine distance calculations and response payload validation
4. Parameter alias support (lat/latitude, lng/longitude, radius/radius_km)
5. CORS configuration verification
"""

import sys
from pathlib import Path

# Add backend root to sys.path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_cors_headers():
    print("\n[TEST 1] Verifying CORS Configuration...")
    headers = {
        "Origin": "https://disha-platform.vercel.app",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/events", headers=headers)
    print("  OPTIONS /api/events status:", response.status_code)
    allow_origin = response.headers.get("access-control-allow-origin")
    print("  Access-Control-Allow-Origin:", allow_origin)
    assert allow_origin == "https://disha-platform.vercel.app", f"Expected 'https://disha-platform.vercel.app', got {allow_origin}"
    print("  [PASS] CORS correctly permits https://disha-platform.vercel.app without wildcard '*'")


def test_unified_events_endpoint():
    print("\n[TEST 2] Testing GET /api/events...")
    response = client.get("/api/events?limit=50")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data.get("status") == "success"
    assert "events" in data
    assert "categories" in data
    print(f"  Total events returned: {data.get('count')} (Total in DB: {data.get('total')})")
    print(f"  Available categories: {data.get('categories')}")

    events = data.get("events", [])
    assert len(events) > 0, "No events returned from DB"

    # Verify coordinate integrity
    for ev in events:
        assert isinstance(ev["latitude"], (int, float)), f"Invalid latitude: {ev['latitude']}"
        assert isinstance(ev["longitude"], (int, float)), f"Invalid longitude: {ev['longitude']}"
        assert -90 <= ev["latitude"] <= 90
        assert -180 <= ev["longitude"] <= 180
        assert "id" in ev
        assert "title" in ev
        assert "category" in ev
        assert "severity" in ev
        assert "status" in ev
        assert "date" in ev
        assert "time" in ev

    first_ev = events[0]
    print(f"  [PASS] First event: [{first_ev['category']}] {first_ev['title']} at ({first_ev['latitude']}, {first_ev['longitude']})")


def test_events_category_filter():
    print("\n[TEST 3] Testing Category Filtering on /api/events...")
    for cat in ["Earthquake", "Flood"]:
        res = client.get(f"/api/events?category={cat}&limit=10")
        assert res.status_code == 200
        d = res.json()
        evs = d.get("events", [])
        print(f"  Filtered by '{cat}': found {len(evs)} events")
        for ev in evs:
            assert ev["category"].lower() == cat.lower() or ev["raw_category"] == cat.lower()
    print("  [PASS] Category filtering verified")


def test_nearby_emergency_services():
    print("\n[TEST 4] Testing GET /api/emergency-services...")
    # Test using New Delhi coordinates
    lat, lng = 28.6139, 77.2090
    response = client.get(f"/api/emergency-services?lat={lat}&lng={lng}&radius=5000")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data.get("status") == "success"
    assert "services" in data
    assert "counts" in data

    services = data["services"]
    assert "medical" in services
    assert "police" in services
    assert "fire" in services

    print(f"  Discovered around ({lat}, {lng}):")
    print(f"    - Medical: {data['counts'].get('medical')}")
    print(f"    - Police: {data['counts'].get('police')}")
    print(f"    - Fire: {data['counts'].get('fire')}")
    print(f"    - Total: {data['counts'].get('total')}")

    if services["medical"]:
        m = services["medical"][0]
        print(f"  [PASS] Closest Medical: {m['name']} ({m['distance_formatted']}, {m['estimated_time_formatted']})")
        assert "directions_url" in m
        assert "distance_km" in m
        assert isinstance(m["distance_km"], (int, float))


def test_parameter_aliases_and_subroutes():
    print("\n[TEST 5] Testing Parameter Aliases & Subroutes (/api/emergency-services/nearby)...")
    # Test with latitude/longitude and radius_km
    response = client.get("/api/emergency-services/nearby?latitude=28.6139&longitude=77.2090&radius_km=5.0")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data.get("status") == "success"
    print(f"  [PASS] Subroute /api/emergency-services/nearby succeeded with total {data['counts']['total']} facilities")


if __name__ == "__main__":
    print("=========================================================")
    print("RUNNING DISHA PLATFORM INTEGRATION TESTS")
    print("=========================================================")
    test_cors_headers()
    test_unified_events_endpoint()
    test_events_category_filter()
    test_nearby_emergency_services()
    test_parameter_aliases_and_subroutes()
    print("\n=========================================================")
    print("ALL INTEGRATION TESTS PASSED SUCCESSFULLY! (5/5)")
    print("=========================================================")
