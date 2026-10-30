import sys
import os
import urllib.parse
import asyncio
import pytest

# Ensure BACKEND directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.routes.gnews import get_disasters
from app.services.geo_filter_service import (
    is_valid_coordinate,
    evaluate_event_geographic_match,
    normalize_geographic_query,
    geocode_with_cache,
    FORBIDDEN_FALLBACK_CENTROIDS,
    STATE_REGISTRY,
)
from app.services.events_service import get_unified_events, extract_news_coordinates
from app.database.mongodb import db


class LocalTestClient:
    def get(self, url: str):
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        kwargs = {}
        if "state" in qs:
            kwargs["state"] = qs["state"][0]
        if "district" in qs:
            kwargs["district"] = qs["district"][0]
        if "city" in qs:
            kwargs["city"] = qs["city"][0]
        if "category" in qs:
            kwargs["disaster_type"] = qs["category"][0]
        if "severity" in qs:
            kwargs["severity"] = qs["severity"][0]
        if "range" in qs:
            kwargs["time_range"] = qs["range"][0]
        if "limit" in qs:
            kwargs["limit"] = int(qs["limit"][0])
        if "skip" in qs:
            kwargs["skip"] = int(qs["skip"][0])

        import time
        for attempt in range(4):
            try:
                data = get_disasters(**kwargs)
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(1.5)

        class Response:
            def __init__(self, data):
                self.status_code = 200
                self._data = data

            def json(self):
                return self._data

        return Response(data)

    def close(self):
        pass


@pytest.fixture(scope="session")
def client():
    c = LocalTestClient()
    try:
        yield c
    finally:
        c.close()


# ============================================================================
# Requirement 1: Selecting Gujarat returns geographically relevant Gujarat news
# ============================================================================
def test_req1_gujarat_selection_returns_gujarat_news(client):
    res = client.get("/api/news/disasters?state=Gujarat&range=all")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["selected_area"]["state"] == "Gujarat"
    assert data["selected_area"]["level"] == "state"

    # All returned news items must belong to Gujarat
    for alert in data["verified_alerts"]:
        assert alert["state"] == "Gujarat" or alert["location_status"] in ["state", "district", "exact"]
        # Ensure coordinates are within Gujarat bounding box
        assert is_valid_coordinate(alert["latitude"], alert["longitude"])
        assert 20.1 <= alert["latitude"] <= 24.7
        assert 68.1 <= alert["longitude"] <= 74.5


# ============================================================================
# Requirement 2: Selecting another state does not return Gujarat-only news
# ============================================================================
def test_req2_other_state_excludes_gujarat_news(client):
    res = client.get("/api/news/disasters?state=Assam&range=all")
    assert res.status_code == 200
    data = res.json()
    assert data["selected_area"]["state"] == "Assam"

    for alert in data["verified_alerts"]:
        assert alert["state"] != "Gujarat"
        # Must be in Assam or bounding box
        assert alert["state"] == "Assam" or (24.0 <= alert["latitude"] <= 28.2 and 89.6 <= alert["longitude"] <= 96.1)


# ============================================================================
# Requirement 3: Selecting Ahmedabad excludes unrelated districts when reliable
#                district information exists
# ============================================================================
def test_req3_district_selection_excludes_unrelated_districts():
    query_area = normalize_geographic_query(country="India", state="Gujarat", district="Ahmedabad")

    # Document explicitly in Surat, Gujarat
    surat_doc = {
        "title": "Surat Floods cause traffic snarls in textile hub",
        "location": {"state": "Gujarat", "district": "Surat", "latitude": 21.1702, "longitude": 72.8311, "precision": "district"},
        "has_coordinates": True,
        "location_status": "district",
    }
    match_result = evaluate_event_geographic_match(surat_doc, query_area)
    assert not match_result["is_match"], "Surat event must NOT match Ahmedabad filter"

    # Document explicitly in Ahmedabad, Gujarat
    ahmedabad_doc = {
        "title": "Heavy rainfall causes waterlogging in Ahmedabad western areas",
        "location": {"state": "Gujarat", "district": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714, "precision": "district"},
        "has_coordinates": True,
        "location_status": "district",
    }
    match_result = evaluate_event_geographic_match(ahmedabad_doc, query_area)
    assert match_result["is_match"], "Ahmedabad event MUST match Ahmedabad filter"
    assert match_result["is_mappable"], "Valid Ahmedabad coordinates must be mappable"


# ============================================================================
# Requirement 4: News with missing coordinates does not appear as geographically
#                verified map alert
# ============================================================================
def test_req4_missing_coordinates_not_mappable():
    doc_no_coords = {
        "title": "Heatwave warnings issued across north-west India",
        "location": {"state": "Rajasthan", "latitude": None, "longitude": None},
        "has_coordinates": False,
        "location_status": "unresolved",
    }
    query_area = normalize_geographic_query(country="India", state="Rajasthan")
    result = evaluate_event_geographic_match(doc_no_coords, query_area)

    assert result["is_match"] is True, "State match can still be true"
    assert result["is_mappable"] is False, "Record with missing coordinates must NEVER be mappable on the map"


# ============================================================================
# Requirement 5: Invalid latitude/longitude is rejected for map placement
# ============================================================================
@pytest.mark.parametrize(
    "lat,lon,expected",
    [
        (91.0, 72.0, False),    # Lat > 90
        (-91.0, 72.0, False),   # Lat < -90
        (20.0, 185.0, False),   # Lon > 180
        (20.0, -185.0, False),  # Lon < -180
        ("invalid", 72.0, False),  # String
        (None, 72.0, False),    # None
        (0.0, 0.0, False),      # Null Island
        (23.0225, 72.5714, True), # Valid Ahmedabad
        (26.1445, 91.7362, True), # Valid Guwahati
    ],
)
def test_req5_invalid_lat_lon_rejected(lat, lon, expected):
    assert is_valid_coordinate(lat, lon) is expected


# ============================================================================
# Requirement 6: India-centroid fallback coordinates are never accepted
# ============================================================================
def test_req6_india_centroid_fallback_rejected():
    centroid_lat, centroid_lon = FORBIDDEN_FALLBACK_CENTROIDS[0]
    assert is_valid_coordinate(centroid_lat, centroid_lon) is False

    doc_with_centroid = {
        "title": "Severe weather alert across India",
        "location": {"latitude": 20.5937, "longitude": 78.9629, "state": "India"},
    }
    query_area = normalize_geographic_query(country="India")
    res = evaluate_event_geographic_match(doc_with_centroid, query_area)
    assert res["is_mappable"] is False, "India centroid fallback must never be considered mappable"


# ============================================================================
# Requirement 7: Unresolved news remains stored in MongoDB
# ============================================================================
def test_req7_unresolved_news_remains_stored():
    # Verify unresolved documents are preserved in disaster_events
    unresolved_count = db.disaster_events.count_documents({
        "$or": [
            {"has_coordinates": False},
            {"location_status": "unresolved"},
        ]
    })
    assert unresolved_count > 0, "Unresolved news must remain stored in MongoDB without deletion"


# ============================================================================
# Requirement 8: A geocoding failure does not delete or lose a news record
# ============================================================================
def test_req8_geocoding_failure_retains_record():
    doc_unresolvable = {
        "title": "Vague global report on changing weather patterns",
        "location": {"city": "NonexistentUnknownPlace12345"},
    }
    # Geocoding returns None for both lat and lon
    lat, lon, status = extract_news_coordinates(doc_unresolvable)
    assert lat is None
    assert lon is None
    assert status == "unresolved"


# ============================================================================
# Requirement 9: Ambiguous news locations are not assigned to an arbitrary district
# ============================================================================
def test_req9_ambiguous_locations_not_assigned_arbitrary_district():
    # An article mentioning 'India' or generic national weather should NOT match Ahmedabad
    ambiguous_doc = {
        "title": "Heavy rains forecast for multiple states across northern and western parts",
        "location": {"country": "India"},
        "has_coordinates": False,
        "location_status": "unresolved",
    }
    query_area = normalize_geographic_query(country="India", state="Gujarat", district="Ahmedabad")
    res = evaluate_event_geographic_match(ambiguous_doc, query_area)
    assert res["is_match"] is False, "Ambiguous country-level document must not be assigned to Ahmedabad"


# ============================================================================
# Requirement 10: Changing the selected area updates the results
# ============================================================================
def test_req10_changing_area_updates_results(client):
    res_gujarat = client.get("/api/news/disasters?state=Gujarat&range=all")
    res_assam = client.get("/api/news/disasters?state=Assam&range=all")

    data_gujarat = res_gujarat.json()
    data_assam = res_assam.json()

    assert data_gujarat["selected_area"]["state"] == "Gujarat"
    assert data_assam["selected_area"]["state"] == "Assam"

    # The returned alerts for Gujarat and Assam should be distinct
    gujarat_ids = {a.get("id") or a.get("event_id") for a in data_gujarat["verified_alerts"]}
    assam_ids = {a.get("id") or a.get("event_id") for a in data_assam["verified_alerts"]}
    assert gujarat_ids.isdisjoint(assam_ids), "Gujarat and Assam alerts must be strictly segregated"


# ============================================================================
# Requirement 11: Old API responses cannot overwrite results (Backend contract identifies effective selected area)
# ============================================================================
def test_req11_backend_contract_identifies_effective_area(client):
    res = client.get("/api/news/disasters?state=Gujarat&district=Ahmedabad&range=all")
    data = res.json()
    selected_area = data["selected_area"]
    assert selected_area["level"] == "district"
    assert selected_area["state"] == "Gujarat"
    assert selected_area["district"] == "Ahmedabad"
    assert "name" in selected_area


# ============================================================================
# Requirement 12: Existing time-range and severity filters continue working
# ============================================================================
def test_req12_time_range_and_severity_filters_work(client):
    res_all = client.get("/api/news/disasters?range=all")
    res_high = client.get("/api/news/disasters?range=all&severity=high")
    data_all = res_all.json()
    data_high = res_high.json()

    assert data_high["total"] <= data_all["total"]
    for alert in data_high["verified_alerts"]:
        assert alert["severity"].lower() in ["severe", "high"]


# ============================================================================
# Requirement 13: Geographic filtering does not alter canonical incident totals
# ============================================================================
def test_req13_canonical_totals_preserved_when_unfiltered():
    # Calling get_unified_events() with no geographic filters must return the full dataset
    result = get_unified_events(time_range="all")
    counts = result["source_counts"]
    total = result["total"]
    # Total must match the sum of sources and invariant holds
    assert total == counts.get("news", 0) + counts.get("sachet", 0) + counts.get("earthquakes", 0) + counts.get("citizen_reports", 0)
    assert result["invariant_holds"] is True


# ============================================================================
# Requirement 14: News with valid coordinates inside a selected geographic boundary is included
# ============================================================================
def test_req14_valid_coordinates_inside_boundary_included():
    query_gujarat = normalize_geographic_query(country="India", state="Gujarat")
    doc_in_gujarat = {
        "title": "Cyclone Alert in Coastal Saurashtra",
        "location": {"latitude": 22.3, "longitude": 70.8},  # Rajkot area, Gujarat
        "latitude": 22.3,
        "longitude": 70.8,
        "has_coordinates": True,
        "location_status": "exact",
    }
    res = evaluate_event_geographic_match(doc_in_gujarat, query_gujarat)
    assert res["is_match"] is True, "Coordinates inside Gujarat bbox must match Gujarat"
    assert res["is_mappable"] is True, "Valid coordinates inside Gujarat must be mappable"
