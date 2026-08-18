"""
DISHA Disaster Intelligence Pipeline - Comprehensive Unit & Integration Test Suite
"""

import unittest
from datetime import datetime, timezone

from app.services.geocoding import geocode_location
from app.services.source_scorer import score_source
from app.services.evidence_detector import detect_evidence, parse_published_date
from app.services.quality_scorer import score_article
from app.services.event_clustering import (
    title_similarity,
    are_articles_same_event,
    pre_cluster_candidates,
    generate_stable_event_id,
)
from app.services.gemini_controller import parse_gemini_response
from app.services.fetch_gnews import (
    local_filter,
    detect_disaster_keywords,
    detect_locations,
)


class TestDISHAIntelligencePipeline(unittest.TestCase):

    # ========================================================
    # 1. LOCAL FILTERING TESTS
    # ========================================================
    def test_genuine_disasters_pass_filter(self):
        cases = [
            ("Floods hit 7.85 lakh people in 6 Odisha districts", "Swollen rivers submerge low-lying areas.", "flood"),
            ("Bengal hotel fire: 8 pilgrims charred to death in Birbhum", "Massive blaze broke out early morning.", "fire_accident"),
            ("Chamoli tunnel collapse: NDRF deploys sniffer dogs to rescue workers", "Search operations underway in Uttarakhand.", "building_collapse"),
            ("Heavy rains trigger massive landslides across Wayanad", "Roads blocked and homes destroyed in Kerala.", "landslide"),
            ("Toxic gas leak in chemical factory hospitalizes 25 workers in Surat", "Incident reported in industrial zone of Gujarat.", "industrial_accident"),
            ("Tremors felt across Delhi after 5.4 magnitude earthquake hits region", "Residents rushed out of high-rises.", "earthquake"),
        ]
        for title, desc, expected_disaster in cases:
            res = local_filter({"title": title, "description": desc})
            self.assertTrue(res["passed"], f"Failed on genuine incident: {title}")
            self.assertIn(expected_disaster, res["disasters"])

    def test_metaphors_and_non_disasters_rejected(self):
        cases = [
            ("Landslide victory for party in assembly bypoll election", "Historic vote share recorded."),
            ("Virat Kohli ends century drought in thrilling IPL match", "Superb innings leads team to victory."),
            ("Movie breaks box office records with explosion in ticket sales", "Film crosses 500 crore collection."),
            ("Police bust major question paper leak racket in exam", "Arrested with leaked solved answer sheets."),
            ("Indoor Air Quality Alert: Indiana Flooding in USA", "Heavy downpour across US state."),
            ("Wildfires ravage thousands of acres in southern California", "Homes evacuated across Los Angeles."),
        ]
        for title, desc in cases:
            res = local_filter({"title": title, "description": desc})
            self.assertFalse(res["passed"], f"Should have rejected non-disaster: {title}")

    # ========================================================
    # 2. EVIDENCE AND CONTEXT DETECTION TESTS
    # ========================================================
    def test_positive_evidence_extraction(self):
        text = "Flash floods kill 12 villagers as NDRF rescue teams evacuate 500 stranded residents in Assam"
        ev = detect_evidence(text)
        self.assertTrue(ev["has_ground_impact"])
        self.assertTrue(ev["has_casualties"])
        self.assertTrue(ev["has_distress"])
        self.assertTrue(ev["has_response"])
        self.assertFalse(ev["is_forecast"])

    def test_forecast_and_policy_detection(self):
        forecast_text = "IMD issues red alert warning for heavy rainfall expected in Gujarat tomorrow"
        ev_f = detect_evidence(forecast_text)
        self.assertTrue(ev_f["is_forecast"])
        self.assertFalse(ev_f["has_ground_impact"])

        policy_text = "Chief Minister holds high-level review meeting to discuss flood preparedness and relief funds"
        ev_p = detect_evidence(policy_text)
        self.assertTrue(ev_p["is_policy_only"])

    # ========================================================
    # 3. SOURCE RELIABILITY SCORING TESTS
    # ========================================================
    def test_source_scoring_tiers(self):
        self.assertEqual(score_source("IMD")["level"], "very_high")
        self.assertEqual(score_source("NDRF")["level"], "very_high")
        self.assertEqual(score_source("PTI")["level"], "high")
        self.assertEqual(score_source("The Hindu")["level"], "high")
        self.assertEqual(score_source("Assam Tribune")["level"], "normal")
        self.assertEqual(score_source("RandomBlog123.com")["level"], "low")

    # ========================================================
    # 4. QUALITY SCORER TESTS
    # ========================================================
    def test_quality_scorer_prioritization(self):
        high_quality_art = {
            "title": "Floods in Assam claim 14 lives; NDRF deploys 10 boats for rescue operations in Dibrugarh",
            "description": "Over 50,000 villagers submerged as Brahmaputra river breaches embankment.",
            "source": "PTI",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        res_hq = score_article(high_quality_art, disasters=["flood"], locations=["Assam"])
        self.assertTrue(res_hq["passed"])
        self.assertGreaterEqual(res_hq["total_score"], 8.0)

        forecast_art = {
            "title": "IMD issues yellow alert: heavy rainfall expected in isolated areas next week",
            "description": "Meteorological department warns of possible showers.",
            "source": "Local News Blog",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        res_fc = score_article(forecast_art, disasters=["heavy_rain"], locations=["Gujarat"])
        self.assertFalse(res_fc["passed"])

    # ========================================================
    # 5. PRE-CLUSTERING & DEDUPLICATION TESTS
    # ========================================================
    def test_article_clustering_same_event(self):
        art1 = {
            "_id": "id1",
            "title": "Assam floods: Brahmaputra breaches embankment in Dibrugarh, 30 villages inundated",
            "local_filter": {"disasters": ["flood"], "locations": ["Assam"]},
            "quality_score": {"total_score": 9.5},
        }
        art2 = {
            "_id": "id2",
            "title": "Dibrugarh flood situation worsens as Brahmaputra river overflows in Assam",
            "local_filter": {"disasters": ["flood"], "locations": ["Assam"]},
            "quality_score": {"total_score": 8.0},
        }
        art_other = {
            "_id": "id3",
            "title": "Massive earthquake tremors felt in Shimla Himachal Pradesh",
            "local_filter": {"disasters": ["earthquake"], "locations": ["Himachal Pradesh"]},
            "quality_score": {"total_score": 9.0},
        }

        self.assertTrue(are_articles_same_event(art1, art2))
        self.assertFalse(are_articles_same_event(art1, art_other))

        clustered = pre_cluster_candidates([art1, art2, art_other])
        # Two distinct events -> exactly 2 representatives
        self.assertEqual(len(clustered), 2)
        # Cluster representative for Assam flood should have both sibling IDs
        assam_rep = next(c for c in clustered if "Assam" in c["local_filter"]["locations"])
        self.assertEqual(len(assam_rep["cluster_sibling_ids"]), 2)

    # ========================================================
    # 6. GEOCODING RESOLUTION TESTS
    # ========================================================
    def test_geocoding_precision(self):
        # City level precision
        lat, lon, prec = geocode_location(country="India", state="Assam", city="Dibrugarh")
        self.assertAlmostEqual(lat, 27.4728, places=3)
        self.assertAlmostEqual(lon, 94.9120, places=3)
        self.assertEqual(prec, "city")

        # District level precision
        lat_w, lon_w, prec_w = geocode_location(country="India", state="Kerala", city="Wayanad")
        self.assertAlmostEqual(lat_w, 11.6854, places=3)
        self.assertEqual(prec_w, "city")

        # State centroid precision
        lat_s, lon_s, prec_s = geocode_location(country="India", state="Odisha", city=None)
        self.assertAlmostEqual(lat_s, 20.9517, places=3)
        self.assertEqual(prec_s, "state")

    # ========================================================
    # 7. GEMINI RESPONSE PARSING TESTS
    # ========================================================
    def test_gemini_json_parsing(self):
        clean_json = '{"results": [{"id": "abc123", "is_disaster": true, "confidence": 0.96, "disaster_type": "flood", "severity": "high", "state": "Assam", "city": "Guwahati", "reason": "Severe urban flooding reported"}]}'
        res_clean = parse_gemini_response(clean_json)
        self.assertEqual(len(res_clean), 1)
        self.assertEqual(res_clean[0]["id"], "abc123")
        self.assertTrue(res_clean[0]["is_disaster"])

        markdown_json = '```json\n{"results": [{"id": "xyz789", "is_disaster": false, "confidence": 0.3, "reason": "Metaphorical usage"}]}\n```'
        res_md = parse_gemini_response(markdown_json)
        self.assertEqual(len(res_md), 1)
        self.assertEqual(res_md[0]["id"], "xyz789")

    # ========================================================
    # 8. STABLE EVENT ID GENERATION
    # ========================================================
    def test_stable_event_id_format(self):
        eid = generate_stable_event_id("flood", "Assam", "Dibrugarh", "2026-08-18")
        self.assertTrue(eid.startswith("DISHA-FLOOD-ASSAM-20260818-"))
        self.assertEqual(len(eid.split("-")), 5)

    # ========================================================
    # 9. RECENCY & TIMESTAMP PARSING TESTS
    # ========================================================
    def test_timestamp_parsing_and_age_scoring(self):
        rfc_date = "Tue, 18 Aug 2026 12:00:00 GMT"
        dt = parse_published_date(rfc_date)
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 8)
        self.assertEqual(dt.day, 18)

        iso_date = "2026-08-18T14:30:00Z"
        dt_iso = parse_published_date(iso_date)
        self.assertIsNotNone(dt_iso)


if __name__ == "__main__":
    unittest.main()
