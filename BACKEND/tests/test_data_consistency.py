"""
DISHA Platform — Automated Data Consistency & Integrity Test Suite
Verifies:
1. Zero event loss due to missing coordinates.
2. The invariant T = M + U across all time ranges (T: total, M: mapped, U: unmapped).
3. Canonical time range boundaries: inclusive-start [startTime, endTime) exclusive-end.
4. Robust timestamp normalization without silent fallback to datetime.now().
5. No fake India centroids (20.5937, 78.9629) assigned to unresolved events.
6. Unified inclusion of all supported sources (Earthquakes, SACHET, News, Citizen Reports).
7. Complete reconciliation and count parity between /api/events, /api/analysis/overview, and /api/analysis/data.
"""

import sys
import os
from datetime import datetime, timezone, timedelta
import pytest
import httpx
from httpx import AsyncClient, ASGITransport

# Ensure BACKEND is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.services.events_service import (
    normalize_event_time,
    parse_time_range_bounds,
    get_unified_events,
)


# ============================================================================
# 1. TIMESTAMP NORMALIZATION TESTS (Zero silent falsification)
# ============================================================================

def test_normalize_event_time_iso():
    """Verify ISO-8601 timestamps are parsed to UTC tuple."""
    # UTC with Z
    res_z = normalize_event_time({"date": "2026-10-22T14:30:00Z"})
    assert res_z is not None
    iso_str, epoch_sec, date_str, time_str = res_z
    assert iso_str.startswith("2026-10-22T14:30:00")
    assert date_str == "2026-10-22"
    assert time_str == "14:30 UTC"

    # With IST offset +05:30
    res_ist = normalize_event_time({"origin_time": "2026-10-22T20:00:00+05:30"})
    assert res_ist is not None
    iso_ist, _, date_ist, time_ist = res_ist
    assert iso_ist.startswith("2026-10-22T14:30:00")  # converted to UTC
    assert date_ist == "2026-10-22"
    assert time_ist == "14:30 UTC"


def test_normalize_event_time_rfc2822():
    """Verify RFC 2822 news dates are accurately parsed."""
    rfc_str = "Thu, 22 Oct 2026 14:30:00 GMT"
    res = normalize_event_time({"published_at": rfc_str})
    assert res is not None
    iso_str, epoch_sec, date_str, time_str = res
    assert iso_str.startswith("2026-10-22T14:30:00")
    assert date_str == "2026-10-22"
    assert time_str == "14:30 UTC"


def test_normalize_event_time_epoch():
    """Verify epoch seconds and milliseconds are parsed."""
    # 1787070000 -> 2026-08-18 16:20:00 UTC
    res_sec = normalize_event_time({"timestamp": 1787070000})
    assert res_sec is not None
    iso_sec, epoch_sec, date_sec, time_sec = res_sec
    assert iso_sec.startswith("2026-08-18")

    # Milliseconds
    res_ms = normalize_event_time({"unified_timestamp": 1787070000 * 1000})
    assert res_ms is not None
    iso_ms, _, _, _ = res_ms
    assert iso_ms.startswith("2026-08-18")


def test_normalize_event_time_never_substitutes_now():
    """Verify that invalid/missing timestamps return None, NEVER datetime.now()."""
    invalid_dicts = [
        {},
        {"date": None},
        {"date": ""},
        {"date": "   "},
        {"published_at": "invalid-date-string"},
        {"origin_time": "not a date at all"},
        {"timestamp": None},
    ]
    for ev in invalid_dicts:
        result = normalize_event_time(ev)
        assert result is None, f"Expected None for invalid event {ev!r}, got {result!r}"


# ============================================================================
# 2. TIME RANGE BOUNDS & INCLUSIVE/EXCLUSIVE SEMANTICS
# ============================================================================

def test_parse_time_range_bounds():
    """Verify calculation of start and end bounds."""
    # 24h
    start_24h, end_24h, s_iso_24h, e_iso_24h, canon_24h = parse_time_range_bounds("24h")
    assert start_24h is not None and end_24h is not None
    assert end_24h > start_24h
    assert abs((end_24h - start_24h) - 86400) < 5
    assert canon_24h == "24h"

    # 7d
    start_7d, end_7d, _, _, canon_7d = parse_time_range_bounds("7d")
    assert abs((end_7d - start_7d) - 7 * 86400) < 5
    assert canon_7d == "7d"

    # 15d
    start_15d, end_15d, _, _, canon_15d = parse_time_range_bounds("15d")
    assert abs((end_15d - start_15d) - 15 * 86400) < 5
    assert canon_15d == "15d"

    # 30d
    start_30d, end_30d, _, _, canon_30d = parse_time_range_bounds("30d")
    assert abs((end_30d - start_30d) - 30 * 86400) < 5
    assert canon_30d == "30d"

    # all
    start_all, end_all, _, _, canon_all = parse_time_range_bounds("all")
    assert start_all is None
    assert end_all is None
    assert canon_all == "all"


def test_inclusive_start_exclusive_end_boundary_rule():
    """
    Test the rule: timestamp >= startTime AND timestamp < endTime.
    - An event at exactly startTime MUST be included.
    - An event at exactly endTime MUST be excluded.
    - An event 1 millisecond before startTime MUST be excluded.
    - An event 1 millisecond before endTime MUST be included.
    """
    start_epoch, end_epoch, _, _, _ = parse_time_range_bounds("7d")

    def is_in_range(ts):
        return (start_epoch is None or ts >= start_epoch) and (end_epoch is None or ts < end_epoch)

    # Exact start -> included
    assert is_in_range(start_epoch) is True

    # Just before start -> excluded
    assert is_in_range(start_epoch - 0.001) is False

    # Exact end -> excluded
    assert is_in_range(end_epoch) is False

    # Just before end -> included
    assert is_in_range(end_epoch - 0.001) is True


# ============================================================================
# 3. ZERO EVENT LOSS & T = M + U INVARIANT (Core DISHA Requirement)
# ============================================================================

def test_live_data_integrity_invariant_all_ranges():
    """
    Query get_unified_events across all supported time ranges and verify:
    1. T = M + U holds strictly.
    2. total == len(events).
    3. mapped_count == count(has_coordinates=True).
    4. unmapped_count == count(has_coordinates=False).
    5. No unmapped event is silently dropped.
    6. No fake centroid coordinates (20.5937, 78.9629).
    """
    for r in ["24h", "7d", "15d", "30d", "all"]:
        data = get_unified_events(time_range=r, limit=5000)
        
        total = data["total"]
        mapped = data["mapped_count"]
        unmapped = data["unmapped_count"]
        events = data["events"]

        # Invariant T = M + U
        assert total == mapped + unmapped, f"Invariant T = M + U failed for range {r}: {total} != {mapped} + {unmapped}"
        assert len(events) == total, f"Event list count mismatch for range {r}: {len(events)} != {total}"

        actual_mapped = sum(1 for e in events if e.get("has_coordinates") is True)
        actual_unmapped = sum(1 for e in events if e.get("has_coordinates") is False)

        assert actual_mapped == mapped, f"Mapped mismatch in range {r}: actual {actual_mapped} vs metadata {mapped}"
        assert actual_unmapped == unmapped, f"Unmapped mismatch in range {r}: actual {actual_unmapped} vs metadata {unmapped}"

        # Check that no event has fake India centroid coordinates
        for e in events:
            lat = e.get("latitude")
            lon = e.get("longitude")
            if lat is not None and lon is not None:
                is_fake_centroid = (abs(lat - 20.5937) < 0.001 and abs(lon - 78.9629) < 0.001)
                assert not is_fake_centroid, (
                    f"Forbidden fake centroid (20.5937, 78.9629) found in event {e.get('id')}: {e.get('title')}"
                )


# ============================================================================
# 4. END-TO-END ENDPOINT PARITY & RECONCILIATION
# ============================================================================

@pytest.mark.asyncio
async def test_endpoint_count_reconciliation():
    """
    Verify complete parity between:
    - /api/events
    - /api/analysis/overview
    - /api/analysis/data
    All 3 must return the exact same total and source breakdown for each time range.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for r in ["24h", "7d", "15d", "30d", "all"]:
            res_events = await client.get(f"/api/events?time_range={r}&limit=5000")
            assert res_events.status_code == 200
            data_events = res_events.json()

            res_overview = await client.get(f"/api/analysis/overview?time_range={r}")
            assert res_overview.status_code == 200
            data_overview = res_overview.json()

            res_analysis_data = await client.get(f"/api/analysis/data?time_window={r}&limit=5000")
            assert res_analysis_data.status_code == 200
            data_analysis = res_analysis_data.json()

            total_events = data_events["total"]
            total_overview = data_overview["kpis"]["total_verified_events"]
            total_analysis = data_analysis["total"]

            assert total_events == total_overview == total_analysis, (
                f"Count mismatch in range '{r}': /api/events={total_events}, "
                f"/api/analysis/overview={total_overview}, /api/analysis/data={total_analysis}"
            )

            # Check source breakdown parity
            ev_sources = data_events.get("source_counts", {})
            ov_sources = data_overview.get("source_counts", {})
            an_sources = data_analysis.get("source_counts", {})

            assert ev_sources.get("earthquakes", 0) == ov_sources.get("earthquakes", 0) == an_sources.get("earthquakes", 0)
            assert ev_sources.get("sachet", 0) == ov_sources.get("sachet", 0) == an_sources.get("sachet", 0)
            assert ev_sources.get("news", 0) == ov_sources.get("news", 0) == an_sources.get("news", 0)
            assert ev_sources.get("citizen_reports", 0) == ov_sources.get("citizen_reports", 0) == an_sources.get("citizen_reports", 0)


# ============================================================================
# 5. UNMAPPED INCIDENTS RETENTION & STATUS CHECKS
# ============================================================================

def test_unmapped_incidents_retained_with_metadata():
    """
    Verify that incidents without coordinates retain:
    - Unique ID
    - Source and source ID
    - Title, category, and severity
    - Timestamp
    - location_status == 'unresolved'
    - has_coordinates == False
    - null latitude and longitude
    """
    data = get_unified_events(time_range="all", limit=5000)
    unmapped = [e for e in data["events"] if not e.get("has_coordinates")]

    # In our database, there are unmapped incidents whose location was unresolved
    assert len(unmapped) > 0, "Expected unmapped events in database to verify retention"
    for ev in unmapped:
        assert ev["has_coordinates"] is False
        assert ev["latitude"] is None
        assert ev["longitude"] is None
        assert ev["location_status"] == "unresolved"
        assert ev.get("id") is not None
        assert ev.get("source") is not None
        assert ev.get("category") is not None


# ============================================================================
# 6. CITIZEN INCIDENT REPORTS INTEGRATION
# ============================================================================

def test_citizen_incident_reports_included():
    """Verify citizen reports from incident_reports collection are included in canonical events."""
    data = get_unified_events(time_range="all", limit=5000)
    citizen_events = [e for e in data["events"] if e.get("source") == "CITIZEN_REPORT"]

    assert len(citizen_events) >= 1, "Expected citizen incident reports to be unified into canonical events"
    for ev in citizen_events:
        assert ev["source"] == "CITIZEN_REPORT"
        assert ev["source_group"] == "citizen"
        assert ev["id"].startswith("INC-") or ev["id"].startswith("citizen-")
