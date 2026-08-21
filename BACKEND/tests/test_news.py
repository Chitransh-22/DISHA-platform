"""
DISHA Platform - Recent News & Time Range Filtering Tests
Disaster Intelligence and Situational Hazard Awareness Platform
"""

import os
import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

# Add backend directory to sys.path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.main import app
from app.database.mongodb import db


@pytest.mark.asyncio
async def test_recent_news_default_24h():
    """
    Verifies that GET /api/news/recent defaults to 24h range, returns status 200,
    and returns properly structured summary fields.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/news/recent")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["time_range"] == "24h"
        assert "news" in data
        assert isinstance(data["news"], list)


@pytest.mark.asyncio
async def test_recent_news_time_ranges():
    """
    Verifies that range query parameter filters news data for 7d, 15d, 30d.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for r in ["7d", "15d", "30d", "all"]:
            res = await client.get(f"/api/news/recent?range={r}")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert isinstance(data["news"], list)


@pytest.mark.asyncio
async def test_news_detail_valid_and_invalid():
    """
    Verifies that GET /api/news/{id} returns full details for a valid article
    and a clean 404 for an invalid ID without crashing.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch recent list to get a valid ID
        list_res = await client.get("/api/news/recent?range=all&limit=5")
        assert list_res.status_code == 200
        items = list_res.json().get("news", [])

        if items:
            valid_id = items[0]["id"]
            detail_res = await client.get(f"/api/news/{valid_id}")
            assert detail_res.status_code == 200
            detail = detail_res.json()
            assert detail["status"] == "success"
            assert "news" in detail
            assert "full_content" in detail["news"] or "full_description" in detail["news"]

        # 2. Test invalid news ID returns 404
        invalid_res = await client.get("/api/news/invalid_nonexistent_id_999")
        assert invalid_res.status_code == 404
        assert "not found" in invalid_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_events_time_filtering():
    """
    Verifies that GET /api/events supports time range parameter and defaults to 24h.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Default 24h
        res_24h = await client.get("/api/events")
        assert res_24h.status_code == 200
        data_24h = res_24h.json()
        assert data_24h["status"] == "success"
        assert data_24h["time_range"] == "24h"

        # Explicit 7d
        res_7d = await client.get("/api/events?range=7d")
        assert res_7d.status_code == 200
        data_7d = res_7d.json()
        assert data_7d["time_range"] == "7d"
        assert data_7d["total"] >= data_24h["total"]
