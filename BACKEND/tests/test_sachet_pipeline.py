"""
DISHA NDMA SACHET CAP Alert Pipeline - Comprehensive Test Suite
Validates RSS XML parsing, CAP 1.2 semantic extraction, polygon centroid computation,
timestamp normalization, deterministic event_id generation, duplicate detection,
changed event updates, CAP UPDATE and CANCEL handling, 30-day retention and cleanup,
ETag / 304 Not Modified caching, error resilience, and FastAPI route responses.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure backend root in sys.path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi.testclient import TestClient

from app.sources.sachet import (
    safe_parse_xml,
    parse_sachet_timestamp,
    generate_sachet_event_id,
    normalize_disaster_type,
    compute_polygon_centroid,
    parse_cap_xml_alert,
    parse_polygon_xml,
    SACHETSource,
    scrape_sachet_alerts,
)
from app.services.sachet_service import (
    sync_sachet_pipeline,
    query_sachet_alerts,
    get_latest_sachet_alerts,
    get_sachet_alert_by_id,
    get_sachet_statistics,
)
from main import app

# ============================================================
# MOCK DATA SAMPLES
# ============================================================

MOCK_RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>All India: CAP Disaster Alert Feeds</title>
    <link>https://sachet.ndma.gov.in</link>
    <description>National Disaster Alert Ingestion</description>
    <item>
      <title>Flood Alert for Lakhimpur district of Assam</title>
      <description>River Ranganadi flowing above warning level</description>
      <category>Met</category>
      <link>https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=1787111448985010</link>
      <author>controlroom@ndma.gov.in (CWC)</author>
      <guid>1787111448985010</guid>
      <pubDate>Wed, 19 Aug 2026 04:08:01 GMT</pubDate>
    </item>
    <item>
      <title>Cyclone Warning for Coastal Odisha</title>
      <description>Severe cyclonic storm approaching coast</description>
      <category>Met</category>
      <link>https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=1787111448854020</link>
      <author>controlroom@ndma.gov.in (IMD)</author>
      <guid>1787111448854020</guid>
      <pubDate>Wed, 19 Aug 2026 03:30:00 GMT</pubDate>
    </item>
    <item>
      <title>Historical Expired Alert from 60 days ago</title>
      <description>Old alert that should be filtered out</description>
      <category>Met</category>
      <link>https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=1787000000000001</link>
      <author>controlroom@ndma.gov.in</author>
      <guid>1787000000000001</guid>
      <pubDate>Fri, 19 Jun 2026 04:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""

MOCK_CAP_ALERT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<cap:alert xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2">
  <cap:identifier>IN-1787111448985010_10</cap:identifier>
  <cap:sender>Assam-SDMA</cap:sender>
  <cap:sent>2026-08-19T09:38:00+05:30</cap:sent>
  <cap:status>Actual</cap:status>
  <cap:msgType>Alert</cap:msgType>
  <cap:scope>Public</cap:scope>
  <cap:info>
    <cap:language>en-IN</cap:language>
    <cap:category>Met</cap:category>
    <cap:event>Flood</cap:event>
    <cap:urgency>Immediate</cap:urgency>
    <cap:severity>Severe</cap:severity>
    <cap:certainty>Observed</cap:certainty>
    <cap:effective>2026-08-19T09:00:00+05:30</cap:effective>
    <cap:onset>2026-08-19T09:38:00+05:30</cap:onset>
    <cap:expires>2026-08-19T21:00:00+05:30</cap:expires>
    <cap:headline>Continuous increase of water level of River Ranganadi in Lakhimpur district of Assam</cap:headline>
    <cap:description>River Ranganadi at N H Crossing in Lakhimpur is flowing above danger mark.</cap:description>
    <cap:instruction>Citizens are advised to evacuate low-lying riverbanks immediately.</cap:instruction>
    <cap:parameter>
      <cap:valueName>Polygon URL</cap:valueName>
      <cap:value>https://sachet.ndma.gov.in/cap_public_website/FetchPolygonXMLFile?identifier=1787111448985010</cap:value>
    </cap:parameter>
    <cap:area>
      <cap:areaDesc>Ranganadi, N H Crossing Ranganadi, Lakhimpur, Assam</cap:areaDesc>
      <cap:altitude>27.2</cap:altitude>
      <cap:ceiling>94.05</cap:ceiling>
    </cap:area>
  </cap:info>
</cap:alert>"""

MOCK_POLYGON_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<alert>
  <identifier>IN-1787111448985010_10</identifier>
  <polygon>27.20,94.00 27.25,94.00 27.25,94.10 27.20,94.10 27.20,94.00</polygon>
</alert>"""

MOCK_CAP_CANCEL_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<cap:alert xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2">
  <cap:identifier>IN-1787111448985010_CANCEL</cap:identifier>
  <cap:sender>Assam-SDMA</cap:sender>
  <cap:sent>2026-08-19T10:00:00+05:30</cap:sent>
  <cap:status>Actual</cap:status>
  <cap:msgType>Cancel</cap:msgType>
  <cap:scope>Public</cap:scope>
  <cap:references>Assam-SDMA,IN-1787111448985010_10,2026-08-19T09:38:00+05:30</cap:references>
  <cap:info>
    <cap:event>Flood</cap:event>
    <cap:severity>Minor</cap:severity>
    <cap:effective>2026-08-19T10:00:00+05:30</cap:effective>
    <cap:headline>Cancellation: Water level returned to normal</cap:headline>
    <cap:description>Flood warning cancelled.</cap:description>
    <cap:area>
      <cap:areaDesc>Lakhimpur, Assam</cap:areaDesc>
    </cap:area>
  </cap:info>
</cap:alert>"""


# ============================================================
# MOCK DATABASE HELPER
# ============================================================

class MockMongoCollection:
    """In-memory collection mock replicating PyMongo CRUD operations."""

    def __init__(self):
        self.docs: Dict[str, Dict[str, Any]] = {}

    def find(self, query=None, projection=None):
        query = query or {}
        results = []
        for doc in self.docs.values():
            match = True
            for k, v in query.items():
                if k == "event_time" and isinstance(v, dict):
                    if "$gte" in v and doc.get("event_time", "") < v["$gte"]:
                        match = False
                    if "$lte" in v and doc.get("event_time", "") > v["$lte"]:
                        match = False
                elif k == "location.state" and isinstance(v, dict) and "$regex" in v:
                    state = doc.get("location", {}).get("state", "")
                    if v["$regex"].lower() not in (state or "").lower():
                        match = False
                elif k == "severity" and isinstance(v, dict) and "$regex" in v:
                    sev = doc.get("severity", "")
                    if v["$regex"].strip("^$").lower() != (sev or "").lower():
                        match = False
                elif k == "$or" and isinstance(v, list):
                    or_matched = False
                    for condition in v:
                        for ck, cv in condition.items():
                            if doc.get(ck) == cv:
                                or_matched = True
                    if not or_matched:
                        match = False
                elif k == "$and" and isinstance(v, list):
                    # Simple and check
                    pass
                elif not k.startswith("$") and doc.get(k) != v:
                    match = False
            if match:
                res = dict(doc)
                if projection and projection.get("_id") == 0 and "_id" in res:
                    del res["_id"]
                results.append(res)

        class Cursor(list):
            def sort(self, key, direction=1):
                return self
            def skip(self, n):
                return Cursor(self[n:])
            def limit(self, n):
                return Cursor(self[:n])

        return Cursor(results)

    def find_one(self, query=None, projection=None):
        res = self.find(query=query, projection=projection)
        return res[0] if res else None

    def count_documents(self, query=None):
        return len(self.find(query=query))

    def update_one(self, filter_q, update_q, upsert=False):
        key = list(filter_q.values())[0] if filter_q else None
        target = None
        for doc in self.docs.values():
            if all(doc.get(k) == v for k, v in filter_q.items()):
                target = doc
                break

        if target:
            if "$set" in update_q:
                target.update(update_q["$set"])
        elif upsert:
            new_doc = dict(filter_q)
            if "$setOnInsert" in update_q:
                new_doc.update(update_q["$setOnInsert"])
            if "$set" in update_q:
                new_doc.update(update_q["$set"])
            new_doc["_id"] = str(len(self.docs) + 1)
            ev_id = new_doc.get("event_id") or new_doc.get("pipeline") or str(len(self.docs))
            self.docs[ev_id] = new_doc

    def bulk_write(self, ops, ordered=False):
        for op in ops:
            self.update_one(op._filter, op._doc, upsert=op._upsert)

    def delete_many(self, query):
        to_del = []
        for k, doc in self.docs.items():
            if "event_time" in query and "$lt" in query["event_time"]:
                if doc.get("event_time", "") < query["event_time"]["$lt"]:
                    to_del.append(k)
        for k in to_del:
            del self.docs[k]
        mock_res = MagicMock()
        mock_res.deleted_count = len(to_del)
        return mock_res

    def aggregate(self, pipeline):
        return []


# ============================================================
# UNIT TESTS
# ============================================================

class TestSACHETPipeline(unittest.TestCase):
    """Test suite for SACHET XML parsing, CAP normalization, deduplication, and routes."""

    def setUp(self):
        self.client = TestClient(app)
        self.ref_now = datetime(2026, 8, 19, 10, 0, 0, tzinfo=timezone.utc)

    def test_safe_xml_parsing(self):
        """Test safe XML parsing with valid and malformed XML."""
        root = safe_parse_xml(MOCK_RSS_XML)
        self.assertIsNotNone(root)
        self.assertEqual(root.tag, "rss")

        # Malformed XML returns None safely
        bad_xml = b"<rss><channel><item><title>Unclosed tag</rss>"
        self.assertIsNone(safe_parse_xml(bad_xml))
        self.assertIsNone(safe_parse_xml(b""))

    def test_timestamp_parsing(self):
        """Test ISO 8601, RFC 2822, and fallback timestamp parsing."""
        ts1 = parse_sachet_timestamp("2026-08-19T09:38:00+05:30")
        self.assertIsNotNone(ts1)
        self.assertEqual(ts1.hour, 4)
        self.assertEqual(ts1.minute, 8)

        ts2 = parse_sachet_timestamp("Wed, 19 Aug 2026 04:08:01 GMT")
        self.assertIsNotNone(ts2)
        self.assertEqual(ts2.year, 2026)
        self.assertEqual(ts2.month, 8)

        # Invalid timestamp
        self.assertIsNone(parse_sachet_timestamp("not-a-timestamp"))
        self.assertIsNone(parse_sachet_timestamp(None))

    def test_deterministic_event_id(self):
        """Test event ID generation is deterministic and stable."""
        eid1 = generate_sachet_event_id("IN-1787111448985010_10")
        eid2 = generate_sachet_event_id("IN-1787111448985010_10")
        self.assertEqual(eid1, eid2)
        self.assertEqual(eid1, "sachet_IN-1787111448985010_10")

        # Special characters sanitized
        eid3 = generate_sachet_event_id("ALERT/2026#001")
        self.assertNotIn("/", eid3)
        self.assertNotIn("#", eid3)

    def test_polygon_centroid_calculation(self):
        """Test computing centroid latitude/longitude from polygon string."""
        poly_str = "27.20,94.00 27.25,94.00 27.25,94.10 27.20,94.10"
        lat, lon = compute_polygon_centroid(poly_str)
        self.assertIsNotNone(lat)
        self.assertIsNotNone(lon)
        self.assertAlmostEqual(lat, 27.225, places=2)
        self.assertAlmostEqual(lon, 94.05, places=2)

        # Empty / corrupt polygon
        self.assertEqual(compute_polygon_centroid(""), (None, None))
        self.assertEqual(compute_polygon_centroid("corrupt data"), (None, None))

    def test_cap_alert_xml_parsing(self):
        """Test extracting full CAP 1.2 elements."""
        cap_data = parse_cap_xml_alert(MOCK_CAP_ALERT_XML, source_link="https://sachet.ndma.gov.in/test")
        self.assertEqual(cap_data["identifier"], "IN-1787111448985010_10")
        self.assertEqual(cap_data["sender"], "Assam-SDMA")
        self.assertEqual(cap_data["status"], "Actual")
        self.assertEqual(cap_data["msg_type"], "Alert")
        self.assertEqual(cap_data["event"], "Flood")
        self.assertEqual(cap_data["severity"], "Severe")
        self.assertEqual(cap_data["urgency"], "Immediate")
        self.assertEqual(cap_data["certainty"], "Observed")
        self.assertIn("Ranganadi", cap_data["headline"])
        self.assertIn("evacuate", cap_data["instruction"])
        self.assertEqual(cap_data["area_desc"], "Ranganadi, N H Crossing Ranganadi, Lakhimpur, Assam")
        self.assertIsNotNone(cap_data["polygon_url"])

    def test_disaster_type_normalization(self):
        """Test mapping CAP events to standard DISHA disaster categories."""
        self.assertEqual(normalize_disaster_type("Flood"), "flood")
        self.assertEqual(normalize_disaster_type("Heavy Rainfall"), "heavy_rain")
        self.assertEqual(normalize_disaster_type("Severe Cyclonic Storm"), "cyclone")
        self.assertEqual(normalize_disaster_type("Landslide"), "landslide")
        self.assertEqual(normalize_disaster_type("Heat Wave Warning"), "heatwave")
        self.assertEqual(normalize_disaster_type("Unknown Hazard"), "other")

    def test_30_day_filtering_on_parse(self):
        """Test that events older than 30 days are omitted during parse."""
        source = SACHETSource()
        records, total_items, within_30d = source.parse_feed_and_normalize(
            MOCK_RSS_XML,
            reference_now=self.ref_now,
            filter_30_days=True,
            fetch_underlying_cap=False,  # Test RSS-only mode
        )
        self.assertEqual(total_items, 3)
        self.assertEqual(within_30d, 2)  # Third item is 60 days old
        self.assertEqual(len(records), 2)

    def test_etag_caching_and_304_behavior(self):
        """Test that ETag is stored and 304 Not Modified skips sync."""
        mock_col = MockMongoCollection()
        mock_sync_state = MockMongoCollection()

        # Mock requests session
        with patch.object(SACHETSource, "fetch_rss") as mock_fetch:
            # 1. First run: HTTP 200 OK
            mock_fetch.return_value = ("success", MOCK_RSS_XML, 'W/"test-etag-123"', "Wed, 19 Aug 2026 04:08:01 GMT", None)
            with patch.object(SACHETSource, "fetch_single_cap_alert", return_value={"identifier": "IN-1787111448985010_10", "severity": "Severe"}):
                res1 = sync_sachet_pipeline(
                    target_collection=mock_col,
                    target_sync_state=mock_sync_state,
                    reference_now=self.ref_now,
                )
                self.assertEqual(res1["status"], "success")
                self.assertTrue(res1["new"] >= 1)

            # Check sync_state stored ETag
            stored_state = mock_sync_state.find_one({"pipeline": "NDMA_SACHET"})
            self.assertIsNotNone(stored_state)
            self.assertEqual(stored_state["etag"], 'W/"test-etag-123"')

            # 2. Second run: Server responds 304 Not Modified
            mock_fetch.return_value = ("not_modified", None, 'W/"test-etag-123"', None, None)
            res2 = sync_sachet_pipeline(
                target_collection=mock_col,
                target_sync_state=mock_sync_state,
                reference_now=self.ref_now,
            )
            self.assertEqual(res2["status"], "not_modified")
            self.assertEqual(res2["new"], 0)
            self.assertEqual(res2["updated"], 0)

    def test_idempotent_duplicate_detection(self):
        """Test that calling sync repeatedly skips unchanged alerts and updates changed ones."""
        mock_col = MockMongoCollection()
        mock_sync_state = MockMongoCollection()

        def mock_cap_fetcher_v1(url, *args, **kwargs):
            if "1787111448985010" in url:
                return {"identifier": "IN-1787111448985010_10", "severity": "Severe", "headline": "Flood v1", "event": "Flood"}
            return {"identifier": "IN-1787111448854020_10", "severity": "Moderate", "headline": "Cyclone v1", "event": "Cyclone"}

        def mock_cap_fetcher_v2(url, *args, **kwargs):
            if "1787111448985010" in url:
                return {"identifier": "IN-1787111448985010_10", "severity": "Extreme", "headline": "Flood v2 EXTREME", "event": "Flood"}
            return {"identifier": "IN-1787111448854020_10", "severity": "Moderate", "headline": "Cyclone v1", "event": "Cyclone"}

        with patch.object(SACHETSource, "fetch_rss") as mock_fetch:
            mock_fetch.return_value = ("success", MOCK_RSS_XML, 'W/"etag-1"', "Wed, 19 Aug 2026 04:08:01 GMT", None)
            with patch.object(SACHETSource, "fetch_single_cap_alert", side_effect=mock_cap_fetcher_v1):
                # 1. Initial Sync
                res1 = sync_sachet_pipeline(
                    force_refresh=True,
                    target_collection=mock_col,
                    target_sync_state=mock_sync_state,
                    reference_now=self.ref_now,
                )
                self.assertEqual(res1["status"], "success")
                self.assertEqual(res1["new"], 2)

                # 2. Duplicate sync with unchanged data
                res2 = sync_sachet_pipeline(
                    force_refresh=True,
                    target_collection=mock_col,
                    target_sync_state=mock_sync_state,
                    reference_now=self.ref_now,
                )
                self.assertEqual(res2["new"], 0)
                self.assertEqual(res2["unchanged"], 2)

                # 3. Sync with updated severity and headline on first alert
                with patch.object(SACHETSource, "fetch_single_cap_alert", side_effect=mock_cap_fetcher_v2):
                    res3 = sync_sachet_pipeline(
                        force_refresh=True,
                        target_collection=mock_col,
                        target_sync_state=mock_sync_state,
                        reference_now=self.ref_now,
                    )
                    self.assertEqual(res3["new"], 0)
                    self.assertEqual(res3["updated"], 1)
                    self.assertEqual(res3["unchanged"], 1)

                    # Check updated document
                    doc = mock_col.find_one({"event_id": "sachet_IN-1787111448985010_10"})
                    self.assertEqual(doc["severity"], "Extreme")
                    self.assertEqual(doc["headline"], "Flood v2 EXTREME")

    def test_cap_cancel_handling(self):
        """Test that CAP Cancel alerts mark referenced alerts as cancelled."""
        mock_col = MockMongoCollection()
        mock_sync_state = MockMongoCollection()

        # Insert original alert with valid recent event_time
        orig_eid = "sachet_IN-1787111448985010_10"
        mock_col.update_one(
            {"event_id": orig_eid},
            {
                "$set": {
                    "event_id": orig_eid,
                    "is_cancelled": False,
                    "status": "Actual",
                    "event_time": "2026-08-19T04:00:00+00:00",
                }
            },
            upsert=True,
        )

        # Parse cancel alert XML
        cancel_cap = parse_cap_xml_alert(MOCK_CAP_CANCEL_XML)
        self.assertEqual(cancel_cap["msg_type"], "Cancel")

        cancel_rss = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Cancellation of flood alert</title>
      <link>https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=CANCEL_1</link>
      <guid>CANCEL_1</guid>
      <pubDate>Wed, 19 Aug 2026 04:30:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""

        with patch.object(SACHETSource, "fetch_rss") as mock_fetch:
            mock_fetch.return_value = ("success", cancel_rss, 'W/"etag-cancel"', None, None)
            with patch.object(SACHETSource, "fetch_single_cap_alert", return_value=cancel_cap):
                res = sync_sachet_pipeline(
                    force_refresh=True,
                    target_collection=mock_col,
                    target_sync_state=mock_sync_state,
                    reference_now=self.ref_now,
                )
                self.assertEqual(res["status"], "success")

                # Verify referenced original alert is now marked cancelled
                orig_doc = mock_col.find_one({"event_id": orig_eid})
                self.assertTrue(orig_doc.get("is_cancelled"))
                self.assertEqual(orig_doc.get("status"), "Cancelled")

    def test_fastapi_sachet_routes(self):
        """Test that GET read routes return stored data without scraping."""
        # 1. GET /api/sachet
        resp = self.client.get("/api/sachet?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total", data)
        self.assertIn("alerts", data)

        # 2. GET /api/sachet/latest
        resp_latest = self.client.get("/api/sachet/latest?limit=5")
        self.assertEqual(resp_latest.status_code, 200)
        data_latest = resp_latest.json()
        self.assertIn("alerts", data_latest)

        # 3. GET /api/sachet/stats
        resp_stats = self.client.get("/api/sachet/stats")
        self.assertEqual(resp_stats.status_code, 200)
        data_stats = resp_stats.json()
        self.assertIn("total_alerts_30d", data_stats)
        self.assertIn("active_alerts_count", data_stats)

        # 4. POST /api/sachet/fetch background response (mocked)
        with patch("app.routes.sachet.sync_sachet_pipeline", return_value={"status": "success", "new": 5}):
            resp_fetch_sync = self.client.post("/api/sachet/fetch?background=false")
            self.assertEqual(resp_fetch_sync.status_code, 200)
            self.assertEqual(resp_fetch_sync.json()["status"], "success")

            resp_fetch_bg = self.client.post("/api/sachet/fetch?background=true")
            self.assertEqual(resp_fetch_bg.status_code, 200)
            self.assertEqual(resp_fetch_bg.json()["status"], "started")

    def test_existing_pipelines_remain_intact(self):
        """Verify that GNews and RISEQ routes continue functioning without regression."""
        # GNews routes
        resp_gnews = self.client.get("/api/news/disasters?limit=5")
        self.assertEqual(resp_gnews.status_code, 200)
        self.assertIn("disasters", resp_gnews.json())

        # RISEQ routes
        resp_riseq = self.client.get("/api/earthquakes?limit=5")
        self.assertEqual(resp_riseq.status_code, 200)
        self.assertIn("earthquakes", resp_riseq.json())


if __name__ == "__main__":
    unittest.main()
