"""
DISHA Disaster Intelligence Pipeline - Comprehensive Unit & Regression Test Suite
Validates True Recency, Impact Extraction, Local Filtering, Quality Scoring,
Event Identity Deduplication, Gemini Response Validation, and Regression Cases.
"""

import unittest
from datetime import datetime, timezone, timedelta

from app.services.temporal_extractor import (
    parse_published_date,
    extract_incident_date,
    evaluate_freshness,
)
from app.services.geocoding import geocode_location, detect_locations
from app.services.source_scorer import score_source
from app.services.evidence_detector import detect_evidence
from app.services.quality_scorer import score_article
from app.services.event_clustering import (
    title_similarity,
    are_articles_same_event,
    pre_cluster_candidates,
    generate_stable_event_id,
    find_matching_active_event,
)
from app.services.gemini_controller import (
    parse_gemini_response,
    validate_and_retry_gemini_batch,
    QuotaController,
)
from app.services.fetch_gnews import (
    local_filter,
    detect_disaster_keywords,
    normalize_url,
    generate_article_id,
)


class TestDISHATrueRecencyPipeline(unittest.TestCase):

    # ========================================================
    # 1. TRUE RECENCY & INCIDENT DATE EXTRACTION TESTS
    # ========================================================
    def test_current_vs_old_incident_extraction(self):
        # 2026-08-18 is a Tuesday
        ref_now = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)

        # Case 1: Current incident published today
        inc_dt1, method1, is_hist1 = extract_incident_date("Uttarakhand landslide kills 7", ref_now, ref_now)
        self.assertFalse(is_hist1)
        self.assertEqual(inc_dt1.date(), ref_now.date())

        # Case 2: Old incident published today ("last week")
        inc_dt2, method2, is_hist2 = extract_incident_date("Uttarakhand landslide that killed 7 last week", ref_now, ref_now)
        self.assertFalse(is_hist2)
        self.assertEqual((ref_now.date() - inc_dt2.date()).days, 7)

        # Case 3: Retrospective / Historical anniversary
        inc_dt3, method3, is_hist3 = extract_incident_date("Remembering the 2024 Kerala landslide", ref_now, ref_now)
        self.assertTrue(is_hist3)

        # Case 4: Historical NCRB statistics from past year
        inc_dt4, method4, is_hist4 = extract_incident_date("Lightning strikes took over 2,500 lives in 2023: NCRB data", ref_now, ref_now)
        self.assertTrue(is_hist4)
        self.assertEqual(inc_dt4.year, 2023)

        # Case 5: Relative weekday ("on Monday" when published on Tuesday)
        inc_dt5, method5, is_hist5 = extract_incident_date("Assam flood: 3 drowned on Monday in Dibrugarh", ref_now, ref_now)
        self.assertFalse(is_hist5)
        self.assertEqual((ref_now.date() - inc_dt5.date()).days, 1)

    def test_freshness_evaluation_tiers(self):
        now_utc = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)

        # Breaking (6h old)
        fresh_breaking = evaluate_freshness(
            published_dt=now_utc - timedelta(hours=6),
            incident_dt=now_utc - timedelta(hours=6),
            now_utc=now_utc,
        )
        self.assertEqual(fresh_breaking["freshness_tier"], "BREAKING")
        self.assertFalse(fresh_breaking["is_old_incident_in_recent_article"])
        self.assertGreaterEqual(fresh_breaking["pub_recency_score"], 4.0)

        # Old incident in recent article (Published 4h ago, but incident happened 10 days ago)
        fresh_old_inc = evaluate_freshness(
            published_dt=now_utc - timedelta(hours=4),
            incident_dt=now_utc - timedelta(days=10),
            now_utc=now_utc,
        )
        self.assertTrue(fresh_old_inc["is_historical"])
        self.assertEqual(fresh_old_inc["freshness_tier"], "HISTORICAL")

    # ========================================================
    # 2. FORECAST VS ACTUAL INCIDENT TESTS
    # ========================================================
    def test_forecast_only_vs_forecast_with_impact(self):
        ref_now = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)

        # Forecast Only -> Should be tagged FORECAST_ONLY and rejected from active disasters
        forecast_text = "IMD predicts heavy rain tomorrow in Gujarat; yellow alert sounded"
        ev_forecast = detect_evidence(forecast_text, published_dt=ref_now, now_utc=ref_now)
        self.assertTrue(ev_forecast["is_forecast_only"])
        self.assertFalse(ev_forecast["has_ground_impact"])
        self.assertEqual(ev_forecast["article_type"], "FORECAST_ONLY")

        # Forecast + Impact -> Should be tagged CURRENT_INCIDENT and accepted
        impact_text = "Red alert issued as heavy rain floods 20 villages in Gujarat, NDRF deployed"
        ev_impact = detect_evidence(impact_text, published_dt=ref_now, now_utc=ref_now)
        self.assertFalse(ev_impact["is_forecast_only"])
        self.assertTrue(ev_impact["is_forecast_plus_impact"])
        self.assertTrue(ev_impact["has_ground_impact"])
        self.assertEqual(ev_impact["article_type"], "CURRENT_INCIDENT")

        # Rain warning after roads submerged
        submerged_text = "Rain warning issued after roads and houses were submerged in Ahmedabad"
        ev_submerged = detect_evidence(submerged_text, published_dt=ref_now, now_utc=ref_now)
        self.assertTrue(ev_submerged["has_ground_impact"])
        self.assertEqual(ev_submerged["article_type"], "CURRENT_INCIDENT")

    # ========================================================
    # 3. HIGH RECALL LOCAL FILTER TESTS
    # ========================================================
    def test_high_recall_genuine_incidents(self):
        """Articles involving missing workers, collapsed structures, or rescues pass without rigid keywords."""
        cases = [
            # Trapped workers in tunnel
            {"title": "Search continues for two workers missing after Chamoli tunnel accident", "description": "Rescuers clear rubble in Uttarakhand."},
            # Bridge washed away without keyword 'flood'
            {"title": "Seven killed as bridge washed away following cloudburst in Mandi Himachal", "description": "SDRF team on site."},
            # Fire fatalities
            {"title": "Bengal hotel fire: 8 pilgrims charred to death in Birbhum", "description": "Massive blaze broke out early morning."},
            # Chemical leak
            {"title": "Toxic gas leak in chemical factory hospitalizes 25 workers in Surat", "description": "Emergency services deployed in Gujarat."},
            # Bus plunges into gorge
            {"title": "Bus falls into deep gorge in Kullu; 12 dead, 15 injured", "description": "Rescue teams rushed to spot in Himachal Pradesh."},
            # Waterlogging and submerged streets
            {"title": "Heavy rainfall causes waterlogging in Bhalesa, residents warned of landslide risks", "description": "Roads cut off in J&K."},
        ]

        for case in cases:
            res = local_filter(case)
            self.assertTrue(res["passed"], f"Failed to pass genuine candidate: {case['title']}")

    def test_rejection_of_non_disasters_and_metaphors(self):
        cases = [
            {"title": "Landslide victory for party in assembly bypoll election", "description": "Historic vote share recorded."},
            {"title": "Virat Kohli ends century drought in thrilling IPL match", "description": "Superb innings leads team to victory."},
            {"title": "Movie breaks box office records with explosion in ticket sales", "description": "Film crosses 500 crore collection."},
            {"title": "Police bust major question paper leak racket in exam", "description": "Arrested with leaked solved answer sheets."},
            {"title": "Indoor Air Quality Alert: Indiana Flooding in USA", "description": "Heavy downpour across US state."},
            {"title": "Wildfires ravage thousands of acres in southern California", "description": "Homes evacuated across Los Angeles."},
            {"title": "8 days under rubble: How one man survived after Venezuela earthquake", "description": "Disaster in South America."},
        ]

        for case in cases:
            res = local_filter(case)
            self.assertFalse(res["passed"], f"Should have rejected non-disaster/foreign: {case['title']}")

    # ========================================================
    # 4. LOCATION DETECTION & GEOCODING TESTS
    # ========================================================
    def test_indian_geographic_entity_detection(self):
        # District level recognition
        loc1 = detect_locations("Chamoli tunnel collapse rescue operation")
        self.assertTrue(loc1["has_india"])
        self.assertIn("Uttarakhand", loc1["states"])
        self.assertIn("Chamoli", loc1["cities"])

        # City / District in Kerala
        loc2 = detect_locations("Landslide disaster in Wayanad leaves dozens injured")
        self.assertTrue(loc2["has_india"])
        self.assertIn("Kerala", loc2["states"])
        self.assertIn("Wayanad", loc2["cities"])

        # Geocoding precision
        lat, lon, prec = geocode_location(state="Kerala", city="Wayanad")
        self.assertAlmostEqual(lat, 11.6854, places=3)
        self.assertEqual(prec, "city")

    # ========================================================
    # 5. QUALITY SCORER & CANDIDATE PRIORITY RANKING
    # ========================================================
    def test_quality_scorer_prioritizes_casualties_and_trapped(self):
        ref_now = datetime.now(timezone.utc)

        # High-impact current incident
        high_impact_art = {
            "title": "Floods in Assam claim 14 lives; NDRF deploys 10 boats for rescue operations in Dibrugarh",
            "description": "Over 50,000 villagers submerged as Brahmaputra river breaches embankment.",
            "source": "PTI",
            "published_at": ref_now.isoformat(),
        }
        res_hi = score_article(high_impact_art, disasters=["flood"], locations=["Assam", "Dibrugarh"], now=ref_now)
        self.assertTrue(res_hi["passed"])
        self.assertGreaterEqual(res_hi["candidate_priority_score"], 14.0)

        # Unknown regional source with strong ground impact should still pass
        local_source_art = {
            "title": "Three workers trapped inside collapsed mine in Jharkhand, rescue underway",
            "description": "SDRF personnel deployed to extricate trapped laborers.",
            "source": "LocalJharkhandExpress.in",
            "published_at": ref_now.isoformat(),
        }
        res_loc = score_article(local_source_art, disasters=["building_collapse"], locations=["Jharkhand"], now=ref_now)
        self.assertTrue(res_loc["passed"])
        self.assertGreaterEqual(res_loc["candidate_priority_score"], 10.0)

        # Retrospective 2024 story published today should be rejected
        old_story_art = {
            "title": "Remembering the 2024 Kerala landslides: Two years after tragedy",
            "description": "Retrospective look at the lessons learned from the calamity.",
            "source": "The Hindu",
            "published_at": ref_now.isoformat(),
        }
        res_old = score_article(old_story_art, disasters=["landslide"], locations=["Kerala"], now=ref_now)
        self.assertFalse(res_old["passed"])
        self.assertIn("historical_or_anniversary_story", res_old["rejection_reasons"])

    # ========================================================
    # 6. EVENT DEDUPLICATION ACROSS DIFFERENT DISTRICTS
    # ========================================================
    def test_distinct_districts_do_not_merge(self):
        """Barpeta flood must NOT merge with Dibrugarh flood."""
        art_dibrugarh = {
            "_id": "art_dib",
            "title": "Assam floods: Brahmaputra breaches embankment in Dibrugarh, 30 villages inundated",
            "local_filter": {"disasters": ["flood"], "locations": ["Assam", "Dibrugarh"]},
            "quality_score": {"total_score": 12.0},
            "candidate_priority_score": 12.0,
        }

        art_barpeta = {
            "_id": "art_bar",
            "title": "Assam floods: Water levels rise in Barpeta district, thousands affected",
            "local_filter": {"disasters": ["flood"], "locations": ["Assam", "Barpeta"]},
            "quality_score": {"total_score": 11.5},
            "candidate_priority_score": 11.5,
        }

        # Sibling article about the same Dibrugarh incident
        art_dibrugarh_2 = {
            "_id": "art_dib_2",
            "title": "Dibrugarh flood situation worsens as Brahmaputra river overflows in Assam",
            "local_filter": {"disasters": ["flood"], "locations": ["Assam", "Dibrugarh"]},
            "quality_score": {"total_score": 10.0},
            "candidate_priority_score": 10.0,
        }

        # Dibrugarh 1 and Dibrugarh 2 SHOULD cluster together
        self.assertTrue(are_articles_same_event(art_dibrugarh, art_dibrugarh_2))

        # Dibrugarh and Barpeta MUST NOT cluster together
        self.assertFalse(are_articles_same_event(art_dibrugarh, art_barpeta))

        # Pre-clustering should produce 2 distinct clusters
        clustered = pre_cluster_candidates([art_dibrugarh, art_barpeta, art_dibrugarh_2])
        self.assertEqual(len(clustered), 2)

    # ========================================================
    # 7. URL NORMALIZATION & ID GENERATION
    # ========================================================
    def test_url_normalization(self):
        url1 = "https://www.thehindu.com/news/national/floods-in-assam?utm_source=rss&utm_medium=feed"
        url2 = "https://www.thehindu.com/news/national/floods-in-assam"
        norm1 = normalize_url(url1)
        norm2 = normalize_url(url2)
        self.assertEqual(norm1, norm2)

        id1 = generate_article_id({"url": url1})
        id2 = generate_article_id({"url": url2})
        self.assertEqual(id1, id2)

    # ========================================================
    # 8. GEMINI RESPONSE PARSING & VALIDATION
    # ========================================================
    def test_gemini_json_parsing(self):
        raw_json = '{"results": [{"id": "id101", "is_disaster": true, "is_current": true, "confidence": 0.95, "disaster_type": "flood", "state": "Assam", "district": "Dibrugarh", "reason": "Brahmaputra embankment breach caused severe flooding"}]}'
        parsed = parse_gemini_response(raw_json)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["id"], "id101")
        self.assertTrue(parsed[0]["is_disaster"])
        self.assertTrue(parsed[0]["is_current"])

    # ========================================================
    # 9. STABLE EVENT ID GENERATION
    # ========================================================
    def test_stable_event_id_format(self):
        eid = generate_stable_event_id("flood", "Assam", district="Dibrugarh", incident_date="2026-08-18")
        self.assertTrue(eid.startswith("DISHA-FLOOD-ASSAM_DIBRUGARH-20260818-"))
        self.assertEqual(len(eid.split("-")), 5)

    # ========================================================
    # 10. TIMESTAMP PARSING ACROSS FORMATS
    # ========================================================
    def test_timestamp_parsing(self):
        rfc_date = "Tue, 18 Aug 2026 12:00:00 GMT"
        dt = parse_published_date(rfc_date)
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 8)
        self.assertEqual(dt.day, 18)

    # ========================================================
    # 11. CLUSTERING REPRESENTATIVE SELECTION EVIDENCE HIERARCHY
    # ========================================================
    def test_clustering_representative_selection_evidence_hierarchy(self):
        """
        Ensures representative article selection prioritizes strongest evidence:
        casualties > missing/trapped > physical damage > rescue/evacuation > official source > generic report.
        """
        art_generic = {
            "_id": "art_gen",
            "title": "Heavy rains hit Wayanad district in Kerala",
            "description": "Continuous downpour witnessed across hilly areas.",
            "source": "LocalBlog",
            "local_filter": {"disasters": ["landslide"], "locations": ["Kerala", "Wayanad"]},
            "candidate_priority_score": 7.0,
        }

        art_rescue = {
            "_id": "art_rescue",
            "title": "Wayanad rains: NDRF and SDRF teams deployed for rescue operations in Kerala",
            "description": "Emergency services mobilized to assist affected people.",
            "source": "LocalBlog",
            "local_filter": {"disasters": ["landslide"], "locations": ["Kerala", "Wayanad"]},
            "candidate_priority_score": 8.0,
        }

        art_damage = {
            "_id": "art_damage",
            "title": "Wayanad landslide: Bridge collapsed and several houses destroyed in Kerala",
            "description": "Massive property damage and roads blocked.",
            "source": "LocalBlog",
            "local_filter": {"disasters": ["landslide"], "locations": ["Kerala", "Wayanad"]},
            "candidate_priority_score": 9.0,
        }

        art_casualties = {
            "_id": "art_cas",
            "title": "Kerala landslide: 6 dead and 4 missing under rubble in Wayanad",
            "description": "Fatalities confirmed and rescue teams hunt for trapped workers.",
            "source": "LocalBlog",
            "local_filter": {"disasters": ["landslide"], "locations": ["Kerala", "Wayanad"]},
            "candidate_priority_score": 10.0,
        }

        art_blog_cas = {
            "_id": "art_blog_cas",
            "title": "Kerala landslide: 6 dead in Wayanad district",
            "description": "Six fatalities confirmed following heavy hill collapse.",
            "source": "LocalBlog",
            "local_filter": {"disasters": ["landslide"], "locations": ["Kerala", "Wayanad"]},
            "candidate_priority_score": 10.0,
        }

        art_official_cas = {
            "_id": "art_off_cas",
            "title": "Kerala landslide: 6 dead in Wayanad district",
            "description": "Six fatalities confirmed following heavy hill collapse.",
            "source": "PTI",
            "local_filter": {"disasters": ["landslide"], "locations": ["Kerala", "Wayanad"]},
            "candidate_priority_score": 10.0,
        }

        # Case 1: Cluster with generic, rescue, damage, casualties -> Casualties article must win
        clustered = pre_cluster_candidates([art_generic, art_rescue, art_damage, art_casualties])
        self.assertEqual(len(clustered), 1)
        self.assertEqual(clustered[0]["_id"], "art_cas")
        self.assertEqual(clustered[0]["cluster_sibling_count"], 4)

        # Case 2: Cluster without casualties: Damage vs Rescue -> Damage article must win
        clustered_no_cas = pre_cluster_candidates([art_generic, art_rescue, art_damage])
        self.assertEqual(len(clustered_no_cas), 1)
        self.assertEqual(clustered_no_cas[0]["_id"], "art_damage")

        # Case 3: Official source vs non-official with same ground evidence -> Official source wins
        clustered_source = pre_cluster_candidates([art_blog_cas, art_official_cas])
        self.assertEqual(len(clustered_source), 1)
        self.assertEqual(clustered_source[0]["_id"], "art_off_cas")

    # ========================================================
    # 12. GEMINI SELECTIVE MISSING-ID RETRY TESTS
    # ========================================================
    def test_gemini_selective_missing_id_retry(self):
        """
        Validates that if only some IDs are missing from Gemini response,
        ONLY those missing IDs are retried.
        """
        from unittest.mock import patch, MagicMock

        articles = [
            {"id": "art_1", "title": "Article 1"},
            {"id": "art_2", "title": "Article 2"},
            {"id": "art_3", "title": "Article 3"},
        ]

        mock_qc = MagicMock()
        mock_qc.can_make_request.return_value = True

        call_payloads = []

        def mock_call_gemini_api(payload, max_retries=3):
            call_payloads.append(payload)
            arts = payload.get("articles", [])
            art_ids = [a["id"] for a in arts]

            if len(art_ids) == 3:
                # First call: returns only art_1 and art_2 (art_3 is missing)
                return '{"results": [{"id": "art_1", "is_disaster": true}, {"id": "art_2", "is_disaster": true}]}'
            elif len(art_ids) == 1 and art_ids[0] == "art_3":
                # Second call: receives ONLY art_3 and returns it
                return '{"results": [{"id": "art_3", "is_disaster": true}]}'
            return '{"results": []}'

        with patch("app.services.gemini_controller.call_gemini_api", side_effect=mock_call_gemini_api):
            results, calls_made = validate_and_retry_gemini_batch(articles, mock_qc, max_missing_retries=2)

            self.assertEqual(len(results), 3)
            self.assertEqual(calls_made, 2)
            self.assertEqual(len(call_payloads), 2)
            # The second call MUST only contain the missing article art_3
            self.assertEqual(len(call_payloads[1]["articles"]), 1)
            self.assertEqual(call_payloads[1]["articles"][0]["id"], "art_3")


if __name__ == "__main__":
    unittest.main()
