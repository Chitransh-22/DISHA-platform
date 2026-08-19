"""
DISHA Earthquake Pipeline - Comprehensive Unit & Integration Test Suite
Validates HTML parsing, timestamp conversion, deterministic event_id generation,
duplicate detection, changed event updates, 30-day filtering and cleanup,
India relevance classification, error resilience, and FastAPI route responses.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient

from app.sources.riseq import (
    parse_riseq_html,
    parse_riseq_origin_time,
    parse_float_safe,
    clean_text,
    generate_earthquake_event_id,
    classify_india_relevance,
    extract_felt_report_info,
    RISEQScraper,
    scrape_riseq_earthquakes,
)
from app.services.earthquake_service import (
    sync_earthquakes_pipeline,
    query_earthquakes,
    get_latest_earthquakes,
    get_earthquake_by_id,
    get_earthquake_statistics,
)
from main import app

# Sample Mock RISEQ HTML
MOCK_RISEQ_HTML = """
<!DOCTYPE html>
<html>
<head><title>Official Website of National Center of Seismology</title></head>
<body>
<table id="eqdatalist" class="table table-hover">
    <thead>
        <tr>
            <th>Magnitude</th>
            <th>Origin Time</th>
            <th>Lat</th>
            <th>Long</th>
            <th>Depth</th>
            <th>Region</th>
            <th>Location</th>
            <th>Type</th>
            <th>Did You Felt Quake</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>4.0</td>
            <td>2026-08-18 18:51:21</td>
            <td>34.943</td>
            <td>63.145</td>
            <td>10</td>
            <td>Afghanistan</td>
            <td>546km SE of Ashgabat, Turkmenistan</td>
            <td>Reviewed</td>
            <td><a href="https://riseq.seismo.gov.in/riseq/felt_report/index/SUl0Q2lqK2JEbDNuaW9vcGhIamNFdz09/Reviewed" class="btn btn-warning">Felt it</a></td>
        </tr>
        <tr>
            <td>3.0</td>
            <td>2026-08-18 14:12:58</td>
            <td>32.339</td>
            <td>76.398</td>
            <td>5</td>
            <td>Chamba, Himachal Pradesh</td>
            <td>15km NNE of Dharamshala, Himachal Pradesh, India</td>
            <td>Reviewed</td>
            <td><a href="https://riseq.seismo.gov.in/riseq/felt_report/index/RE4xNlBzaFdsVDMxcnMrR1FVWXMvdz09/Reviewed" class="btn btn-warning">Felt it</a></td>
        </tr>
        <tr>
            <td>5.9</td>
            <td>2026-08-18 19:51:07</td>
            <td>36.4944</td>
            <td>70.6638</td>
            <td>252.8</td>
            <td>Hindu Kush Region  Afghanistan</td>
            <td>68km S of Fayzabad, Afghanistan</td>
            <td>Unscruitnized</td>
            <td><a href="https://riseq.seismo.gov.in/riseq/felt_report/index/Zm9OSnZabVRxeUF2RE5NTndWRC81dz09/Auto" class="btn btn-warning">Felt it</a></td>
        </tr>
        <tr>
            <td>2.5</td>
            <td>2026-06-01 10:00:00</td>
            <td>28.500</td>
            <td>77.200</td>
            <td>10</td>
            <td>Delhi</td>
            <td>Delhi, India</td>
            <td>Reviewed</td>
            <td></td>
        </tr>
        <tr class="corrupt-row">
            <td>invalid_mag</td>
            <td>not_a_date</td>
            <td>999.0</td>
            <td>-</td>
            <td>unknown</td>
            <td>None</td>
            <td></td>
            <td></td>
            <td></td>
        </tr>
    </tbody>
</table>
</body>
</html>
"""


class MockMongoCollection:
    """In-memory mock for MongoDB collection to test queries, updates, and cleanup safely."""

    def __init__(self):
        self.docs = {}

    def find(self, query=None, projection=None):
        docs = list(self.docs.values())
        if query:
            filtered = []
            for d in docs:
                match = True
                if "origin_time" in query:
                    ot_filter = query["origin_time"]
                    if isinstance(ot_filter, dict):
                        if "$gte" in ot_filter and d.get("origin_time", "") < ot_filter["$gte"]:
                            match = False
                        if "$lte" in ot_filter and d.get("origin_time", "") > ot_filter["$lte"]:
                            match = False
                    elif d.get("origin_time") != ot_filter:
                        match = False
                if "magnitude" in query:
                    mag_filter = query["magnitude"]
                    if isinstance(mag_filter, dict):
                        if "$gte" in mag_filter and d.get("magnitude", 0) < mag_filter["$gte"]:
                            match = False
                        if "$lte" in mag_filter and d.get("magnitude", 0) > mag_filter["$lte"]:
                            match = False
                if "relevance" in query and d.get("relevance") != query["relevance"]:
                    match = False
                if match:
                    filtered.append(d)
            docs = filtered

        class MockCursor:
            def __init__(self, data):
                self.data = data

            def sort(self, key, direction=-1):
                reverse = direction == -1
                self.data = sorted(self.data, key=lambda x: x.get(key, ""), reverse=reverse)
                return self

            def skip(self, n):
                self.data = self.data[n:]
                return self

            def limit(self, n):
                self.data = self.data[:n]
                return self

            def __iter__(self):
                return iter(self.data)

        return MockCursor(docs)

    def find_one(self, query=None, projection=None, sort=None):
        cursor = self.find(query)
        if sort:
            key, direction = sort[0]
            cursor.sort(key, direction)
        results = list(cursor)
        return results[0] if results else None

    def count_documents(self, query=None):
        return len(list(self.find(query)))

    def update_one(self, filter_dict, update_dict, upsert=False):
        key = filter_dict.get("event_id")
        if not key:
            return MagicMock(matched_count=0, modified_count=0)

        now_existing = self.docs.get(key)
        if now_existing:
            if "$set" in update_dict:
                now_existing.update(update_dict["$set"])
            return MagicMock(matched_count=1, modified_count=1)
        elif upsert:
            new_doc = {}
            if "$setOnInsert" in update_dict:
                new_doc.update(update_dict["$setOnInsert"])
            if "$set" in update_dict:
                new_doc.update(update_dict["$set"])
            new_doc["event_id"] = key
            self.docs[key] = new_doc
            return MagicMock(matched_count=0, modified_count=0, upserted_id=key)

    def delete_many(self, query):
        to_delete = []
        if "origin_time" in query and "$lt" in query["origin_time"]:
            cutoff = query["origin_time"]["$lt"]
            for k, doc in list(self.docs.items()):
                if doc.get("origin_time", "") < cutoff:
                    to_delete.append(k)
        for k in to_delete:
            del self.docs[k]
        return MagicMock(deleted_count=len(to_delete))


class TestRISEQPipeline(unittest.TestCase):

    def setUp(self):
        self.ref_now = datetime(2026, 8, 19, 0, 0, 0, tzinfo=timezone.utc)

    # ========================================================
    # 1. HTML PARSING & DATA NORMALIZATION
    # ========================================================
    def test_parse_riseq_html_success(self):
        events = parse_riseq_html(MOCK_RISEQ_HTML, reference_now=self.ref_now)
        # Row 1 (Afghanistan, 2026-08-18), Row 2 (Himachal, 2026-08-18), Row 3 (Hindu Kush, 2026-08-18) are in 30d window
        # Row 4 (2026-06-01) is older than 30 days and filtered out
        # Row 5 is corrupt and skipped
        self.assertEqual(len(events), 3)

        ev_himachal = next(e for e in events if "Himachal" in e["region"])
        self.assertEqual(ev_himachal["magnitude"], 3.0)
        self.assertEqual(ev_himachal["latitude"], 32.339)
        self.assertEqual(ev_himachal["longitude"], 76.398)
        self.assertEqual(ev_himachal["depth_km"], 5.0)
        self.assertEqual(ev_himachal["status"], "Reviewed")
        self.assertEqual(ev_himachal["relevance"], "INDIA")
        self.assertEqual(ev_himachal["event_id"], "ncs_20260818T141258Z_32.339_76.398")
        self.assertIn("felt_report/index/RE4xNlBzaFdsVDMxcnMrR1FVWXMvdz09", ev_himachal["felt_report_url"])

    # ========================================================
    # 2. TIMESTAMP PARSING & TIMEZONE HANDLING
    # ========================================================
    def test_timestamp_parsing_utc_and_ist(self):
        # UTC Mode
        dt_utc = parse_riseq_origin_time("2026-08-18 19:51:07", timezone_mode="UTC")
        self.assertIsNotNone(dt_utc)
        self.assertEqual(dt_utc.tzinfo, timezone.utc)
        self.assertEqual(dt_utc.hour, 19)
        self.assertEqual(dt_utc.minute, 51)

        # IST Mode (convert IST -> UTC: subtract 5h30m)
        dt_ist = parse_riseq_origin_time("2026-08-19 01:21:21", timezone_mode="IST")
        self.assertIsNotNone(dt_ist)
        self.assertEqual(dt_ist.tzinfo, timezone.utc)
        self.assertEqual(dt_ist.day, 18)
        self.assertEqual(dt_ist.hour, 19)
        self.assertEqual(dt_ist.minute, 51)
        self.assertEqual(dt_ist.second, 21)

        # Invalid string
        self.assertIsNone(parse_riseq_origin_time("not-a-timestamp"))

    # ========================================================
    # 3. NUMERIC FIELD PARSING
    # ========================================================
    def test_numeric_parsing(self):
        self.assertEqual(parse_float_safe("4.5"), 4.5)
        self.assertEqual(parse_float_safe(" 10.2 km "), 10.2)
        self.assertEqual(parse_float_safe(-15.4), -15.4)
        self.assertIsNone(parse_float_safe("NaN"))
        self.assertIsNone(parse_float_safe("None"))
        self.assertIsNone(parse_float_safe("-"))
        self.assertIsNone(parse_float_safe(None))

    # ========================================================
    # 4. DETERMINISTIC EVENT ID GENERATION
    # ========================================================
    def test_deterministic_event_id(self):
        dt = datetime(2026, 8, 18, 19, 51, 7, tzinfo=timezone.utc)
        ev_id_1 = generate_earthquake_event_id(dt, 36.4944, 70.6638)
        ev_id_2 = generate_earthquake_event_id(dt, 36.4944, 70.6638)
        self.assertEqual(ev_id_1, ev_id_2)
        self.assertEqual(ev_id_1, "ncs_20260818T195107Z_36.494_70.664")

    # ========================================================
    # 5. INDIA RELEVANCE CLASSIFICATION
    # ========================================================
    def test_india_relevance_classification(self):
        # 1. Clear India location & coordinates
        rel1, det1 = classify_india_relevance(
            lat=32.339, lon=76.398,
            region="Chamba, Himachal Pradesh",
            location="15km NNE of Dharamshala, Himachal Pradesh, India",
        )
        self.assertEqual(rel1, "INDIA")

        # 2. Border proximity (Hindu Kush, Afghanistan near border)
        rel2, det2 = classify_india_relevance(
            lat=36.494, lon=70.664,
            region="Hindu Kush Region Afghanistan",
            location="68km S of Fayzabad, Afghanistan",
        )
        self.assertEqual(rel2, "INDIA_BORDER")

        # 3. Regional (Myanmar or Tibet)
        rel3, det3 = classify_india_relevance(
            lat=22.0, lon=93.5,
            region="Myanmar",
            location="Myanmar",
        )
        self.assertIn(rel3, ("INDIA_BORDER", "REGIONAL"))

        # 4. Distant global earthquake
        rel4, det4 = classify_india_relevance(
            lat=-18.0, lon=-178.0,
            region="Fiji Islands",
            location="Fiji Islands Region",
        )
        self.assertEqual(rel4, "OTHER")

    # ========================================================
    # 6. DUPLICATE DETECTION & UNCHANGED / CHANGED UPSERT
    # ========================================================
    def test_deduplication_and_upsert_logic(self):
        mock_col = MockMongoCollection()

        # Run 1: Ingest mock HTML -> 3 new records
        with patch("app.services.earthquake_service.scrape_riseq_earthquakes") as mock_scrape:
            events = parse_riseq_html(MOCK_RISEQ_HTML, reference_now=self.ref_now)
            mock_scrape.return_value = {
                "status": "success",
                "count": len(events),
                "events": events,
            }

            res1 = sync_earthquakes_pipeline(
                reference_now=self.ref_now,
                target_collection=mock_col,
            )
            self.assertEqual(res1["status"], "success")
            self.assertEqual(res1["new_count"], 3)
            self.assertEqual(res1["updated_count"], 0)
            self.assertEqual(res1["unchanged_count"], 0)
            self.assertEqual(len(mock_col.docs), 3)

        # Run 2: Ingest identical data -> 0 new, 3 unchanged, 0 updated
        with patch("app.services.earthquake_service.scrape_riseq_earthquakes") as mock_scrape:
            mock_scrape.return_value = {
                "status": "success",
                "count": len(events),
                "events": events,
            }

            res2 = sync_earthquakes_pipeline(
                reference_now=self.ref_now,
                target_collection=mock_col,
            )
            self.assertEqual(res2["status"], "success")
            self.assertEqual(res2["new_count"], 0)
            self.assertEqual(res2["unchanged_count"], 3)
            self.assertEqual(res2["updated_count"], 0)
            self.assertEqual(len(mock_col.docs), 3)

        # Run 3: NCS corrections -> Modified magnitude & status on one event
        modified_events = [dict(e) for e in events]
        modified_events[0]["magnitude"] = 4.3  # Changed from 4.0
        modified_events[0]["status"] = "Reviewed (Updated)"

        with patch("app.services.earthquake_service.scrape_riseq_earthquakes") as mock_scrape:
            mock_scrape.return_value = {
                "status": "success",
                "count": len(modified_events),
                "events": modified_events,
            }

            res3 = sync_earthquakes_pipeline(
                reference_now=self.ref_now,
                target_collection=mock_col,
            )
            self.assertEqual(res3["status"], "success")
            self.assertEqual(res3["new_count"], 0)
            self.assertEqual(res3["updated_count"], 1)
            self.assertEqual(res3["unchanged_count"], 2)

            # Verify updated record in mock DB
            updated_doc = mock_col.docs[modified_events[0]["event_id"]]
            self.assertEqual(updated_doc["magnitude"], 4.3)
            self.assertEqual(updated_doc["status"], "Reviewed (Updated)")

    # ========================================================
    # 7. 30-DAY CLEANUP LOGIC
    # ========================================================
    def test_30_day_cleanup(self):
        mock_col = MockMongoCollection()

        # Seed database with 1 recent event and 2 expired events (>30 days old)
        now_iso = self.ref_now.isoformat()
        old_time_1 = (self.ref_now - timedelta(days=35)).isoformat()
        old_time_2 = (self.ref_now - timedelta(days=50)).isoformat()

        mock_col.docs["recent_1"] = {"event_id": "recent_1", "origin_time": now_iso, "magnitude": 4.0}
        mock_col.docs["old_1"] = {"event_id": "old_1", "origin_time": old_time_1, "magnitude": 3.5}
        mock_col.docs["old_2"] = {"event_id": "old_2", "origin_time": old_time_2, "magnitude": 5.0}

        self.assertEqual(len(mock_col.docs), 3)

        # Run pipeline with 0 scraped events to test cleanup
        with patch("app.services.earthquake_service.scrape_riseq_earthquakes") as mock_scrape:
            mock_scrape.return_value = {
                "status": "success",
                "count": 0,
                "events": [],
            }

            res = sync_earthquakes_pipeline(
                reference_now=self.ref_now,
                target_collection=mock_col,
                force_cleanup=True,
            )
            self.assertEqual(res["removed_expired_count"], 2)
            self.assertEqual(len(mock_col.docs), 1)
            self.assertIn("recent_1", mock_col.docs)

    # ========================================================
    # 8. NETWORK RETRY & FAILURE HANDLING
    # ========================================================
    def test_network_retry_resilience(self):
        scraper = RISEQScraper(timeout=5)

        with patch.object(scraper.session, "post") as mock_post, patch.object(scraper.session, "get") as mock_get:
            # Simulate 500 error on POST, but success on GET fallback
            mock_post_resp = MagicMock()
            mock_post_resp.status_code = 500
            mock_post.return_value = mock_post_resp

            mock_get_resp = MagicMock()
            mock_get_resp.status_code = 200
            mock_get_resp.text = MOCK_RISEQ_HTML
            mock_get.return_value = mock_get_resp

            success, html, err = scraper.fetch_html(max_retries=1)
            self.assertTrue(success)
            self.assertIn("eqdatalist", html)

    # ========================================================
    # 9. API ENDPOINTS TEST
    # ========================================================
    def test_fastapi_earthquake_routes(self):
        client = TestClient(app)

        # 1. Health check
        health_resp = client.get("/api/health")
        self.assertEqual(health_resp.status_code, 200)

        # 2. Get list of earthquakes
        list_resp = client.get("/api/earthquakes?limit=10")
        self.assertEqual(list_resp.status_code, 200)
        data = list_resp.json()
        self.assertIn("source", data)
        self.assertIn("earthquakes", data)

        # 3. Get latest earthquakes
        latest_resp = client.get("/api/earthquakes/latest?limit=5")
        self.assertEqual(latest_resp.status_code, 200)

        # 4. Get stats
        stats_resp = client.get("/api/earthquakes/stats")
        self.assertEqual(stats_resp.status_code, 200)
        stats_data = stats_resp.json()
        self.assertIn("total_events_30d", stats_data)
        self.assertIn("by_relevance", stats_data)

        # 5. Trigger fetch in background with mocked pipeline
        with patch("app.routes.earthquakes.sync_earthquakes_pipeline") as mock_sync:
            mock_sync.return_value = {"status": "success", "new_count": 0}
            fetch_resp = client.post("/api/earthquakes/fetch")
            self.assertEqual(fetch_resp.status_code, 200)
            fetch_data = fetch_resp.json()
            self.assertEqual(fetch_data["status"], "started")

            # 6. Trigger sync route
            sync_resp = client.post("/api/earthquakes/sync")
            self.assertEqual(sync_resp.status_code, 200)

        # 7. Non-existent earthquake detail
        not_found_resp = client.get("/api/earthquakes/non_existent_event_id_123")
        self.assertEqual(not_found_resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
