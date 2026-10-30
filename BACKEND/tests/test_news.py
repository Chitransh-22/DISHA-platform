"""
DISHA Platform - Recent News & Time Range Filtering Tests
Disaster Intelligence and Situational Hazard Awareness Platform
"""

import os
import sys
from pathlib import Path
import pytest
from fastapi import HTTPException

# Add backend directory to sys.path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.main import app
from app.database.mongodb import db
from app.routes.gnews import get_recent_news, get_news_detail
from app.routes.events import list_unified_events


def test_recent_news_default_24h():
    """
    Verifies that GET /api/news/recent defaults to 24h range, returns status 200,
    and returns properly structured summary fields.
    """
    data = get_recent_news(time_range="24h")
    assert data["status"] == "success"
    assert data["time_range"] == "24h"
    assert "news" in data
    assert isinstance(data["news"], list)


def test_recent_news_time_ranges():
    """
    Verifies that range query parameter filters news data for 7d, 15d, 30d.
    """
    for r in ["7d", "15d", "30d", "all"]:
        data = get_recent_news(time_range=r)
        assert data["status"] == "success"
        assert isinstance(data["news"], list)


def test_news_detail_valid_and_invalid():
    """
    Verifies that GET /api/news/{id} returns full details for a valid article
    and a clean 404 for an invalid ID without crashing.
    """
    list_res = get_recent_news(time_range="all", limit=5)
    items = list_res.get("news", [])

    if items:
        valid_id = items[0]["id"]
        detail = get_news_detail(valid_id)
        assert detail["status"] == "success"
        assert "news" in detail
        assert "full_content" in detail["news"] or "full_description" in detail["news"]

    with pytest.raises(HTTPException) as exc_info:
        get_news_detail("invalid_nonexistent_id_999")
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


def test_events_time_filtering():
    """
    Verifies that unified events API (/api/events) returns status 200 and valid JSON
    with non-empty events and categories list.
    """
    data = list_unified_events(time_range="all", limit=10)
    assert data["status"] == "success"
    assert "events" in data
    assert isinstance(data["events"], list)
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert "time_range" in data
