"""
DISHA Platform - Ingestion Pipeline & News-Map Data Consistency Tests
Validates that:
1. normalize_event_time prioritizes timestamps with time-of-day over date-only strings.
2. News disasters are queried with published_at included in the $or filter.
3. Both events_service and gnews output consistent event_id, article_id, and timestamp fields.
4. Recent news with older incident_date are not rejected by the 24h filter.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pytest

# Ensure BACKEND is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.events_service import (
    normalize_event_time,
    get_unified_events,
    parse_time_range_bounds,
)
from app.routes.gnews import _format_news_summary


class TestTimestampNormalizationPriority:
    """Tests for timestamp priority in normalize_event_time."""

    def test_published_at_prioritized_over_older_incident_date(self):
        """
        When an article was published today but mentions an event that occurred 5 days ago,
        normalize_event_time must pick published_at so the fresh report is captured in 24h filters.
        """
        now = datetime.now(timezone.utc)
        recent_published = now.isoformat()
        old_incident_date = (now - timedelta(days=5)).strftime("%Y-%m-%d")

        doc = {
            "title": "Cyclone Alert in Odisha",
            "published_at": recent_published,
            "incident_date": old_incident_date,
        }

        result = normalize_event_time(doc)
        assert result is not None
        iso_str, epoch_ts, d_str, t_str = result

        # The epoch timestamp should match the published_at, not the 5-day-old incident_date
        assert abs(epoch_ts - now.timestamp()) < 5.0
        assert d_str == now.strftime("%Y-%m-%d")

    def test_processed_at_prioritized_over_date_only_string(self):
        """
        processed_at ISO timestamp must take precedence over legacy date string.
        """
        now = datetime.now(timezone.utc)
        doc = {
            "title": "Flooding Reported in Assam",
            "processed_at": now.isoformat(),
            "date": "2026-10-01",
        }

        result = normalize_event_time(doc)
        assert result is not None
        _, epoch_ts, _, _ = result
        assert abs(epoch_ts - now.timestamp()) < 5.0

    def test_numeric_epoch_takes_first_precedence(self):
        """Numeric epoch timestamps should be directly honored."""
        target_ts = 1730370000.0  # arbitrary epoch
        doc = {
            "unified_timestamp": target_ts,
            "published_at": "2026-10-31T12:00:00Z",
        }
        result = normalize_event_time(doc)
        assert result is not None
        _, epoch_ts, _, _ = result
        assert epoch_ts == target_ts


class TestPipelineConsistencyFormatting:
    """Tests for consistent identification and timestamp propagation across Map and News."""

    def test_format_news_summary_contains_traceable_ids_and_timestamps(self):
        """_format_news_summary must expose event_id, article_id, published_at, event_time, last_updated_at."""
        now = datetime.now(timezone.utc)
        doc = {
            "_id": "6723ab89c9e77b001a123456",
            "event_id": "EVT-2026-ODISHA-001",
            "article_id": "ART-ODISHA-999",
            "title": "High Waves Warning in Puri",
            "description": "Met department issues high wave warning along Puri coast.",
            "disaster_type": "Cyclone",
            "severity": "Severe",
            "status": "Active",
            "published_at": now.isoformat(),
            "processed_at": now.isoformat(),
            "first_seen_at": now.isoformat(),
            "location": {
                "district": "Puri",
                "state": "Odisha",
                "latitude": 19.8135,
                "longitude": 85.8312,
            },
        }

        summary = _format_news_summary(doc)

        assert summary["event_id"] == "EVT-2026-ODISHA-001"
        assert summary["article_id"] == "ART-ODISHA-999"
        assert summary["published_at"] == now.isoformat()
        assert summary["last_updated_at"] is not None
        assert summary["latitude"] == 19.8135
        assert summary["longitude"] == 85.8312
        assert summary["has_coordinates"] is True


class TestCombinedEventsNewsQuery:
    """Tests that get_unified_events properly queries disaster_events with published_at."""

    @patch("app.services.events_service.db")
    def test_unified_events_queries_published_at_in_or_clause(self, mock_db):
        """Verify the MongoDB query constructed in get_unified_events includes published_at."""
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = []
        mock_db.__getitem__.return_value.find.return_value = mock_cursor

        # Call with 24h time range
        get_unified_events(time_range="24h", source="news")

        # Inspect the find query passed to disaster_events
        call_args = mock_db["disaster_events"].find.call_args
        assert call_args is not None
        query, projection = call_args[0]

        assert "$or" in query
        or_clauses = query["$or"]
        # Ensure published_at is one of the query branches
        has_published_at_query = any("published_at" in clause for clause in or_clauses)
        assert has_published_at_query, "published_at filter must be included in disaster_events query"
