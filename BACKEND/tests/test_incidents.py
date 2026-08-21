import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient, ASGITransport

# Add backend directory to sys.path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.main import app
from app.core.database import get_async_db, init_incident_indexes
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.incident_repository import IncidentRepository
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_incident_database_indexes_initialization():
    """
    Verifies that the incident_reports database collection and indexes
    initialize safely and idempotently without raising errors.
    """
    db = get_async_db()
    await init_incident_indexes(db)

    # Verify collection exists in MongoDB
    indexes = await db["incident_reports"].index_information()
    assert indexes is not None
    assert "uniq_incident_report_id" in indexes or "report_id_1" in indexes or any("report_id" in str(k) for k in indexes.keys())


@pytest.mark.asyncio
async def test_submit_incident_unauthenticated():
    """
    Verifies that unauthenticated requests to report an incident return 401 Unauthorized.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "event_type": "flood",
            "description": "Severe urban waterlogging and submerged roads blocking rescue vehicles.",
            "location": {
                "lat": 23.0225,
                "lng": 72.5714,
                "address": "Ahmedabad, Gujarat, India",
            },
        }
        res = await client.post("/api/incidents/report", json=payload)
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_submit_incident_authenticated_flow():
    """
    Verifies the complete authenticated incident reporting flow:
    1. Authenticated user submits incident with location and description
    2. Backend links authenticated user ID and email
    3. Document is stored in incident_reports MongoDB collection
    4. Backend returns 201 Created with unique report_id
    5. Incident can be fetched via /api/incidents/my-reports and /api/incidents/{report_id}
    """
    ts = int(time.time() * 1000)
    test_email = f"citizen_{ts}@disha.gov.in"
    test_username = f"citizen_{ts}"

    # 1. Create verified user in test database
    user_repo = UserRepository()
    session_repo = SessionRepository()
    user = await user_repo.create_user({
        "username": test_username,
        "email": test_email,
        "password_hash": "mock_hash",
        "name": "Verified Citizen",
        "verified": True,
    })
    user_id = str(user["id"])

    # 2. Create active session and issue valid JWT access token
    session = await session_repo.create_session(
        user_id=user_id,
        refresh_token_hash="mock_refresh_hash",
    )
    access_token = create_access_token(user_id=user_id, session_id=session["id"])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = {
            "event_type": "cyclone",
            "description": "High velocity wind gusts and fallen power poles blocking emergency lanes.",
            "location": {
                "lat": 19.0760,
                "lng": 72.8777,
                "address": "Mumbai Coastline, Maharashtra, India",
            },
            "images": [{"name": "evidence1.jpg", "url": "https://example.com/evidence1.jpg"}],
        }

        # 3. Submit incident report
        res = await client.post("/api/incidents/report", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["success"] is True
        assert data["message"] == "Incident reported successfully"
        report_id = data["report_id"]
        assert report_id.startswith("INC-")

        # 4. Verify MongoDB record
        inc_repo = IncidentRepository()
        db_doc = await inc_repo.get_by_id(report_id)
        assert db_doc is not None
        assert db_doc["user_id"] == user_id
        assert db_doc["user_email"] == test_email
        assert db_doc["event_type"] == "cyclone"
        assert db_doc["status"] == "submitted"
        assert db_doc["location"]["lat"] == 19.0760
        assert db_doc["location"]["coordinates"] == [72.8777, 19.0760]  # GeoJSON [lng, lat]

        # 5. Verify /api/incidents/my-reports
        my_res = await client.get("/api/incidents/my-reports", headers=headers)
        assert my_res.status_code == 200
        my_data = my_res.json()
        assert my_data["success"] is True
        assert any(r["report_id"] == report_id for r in my_data["reports"])

        # 6. Verify /api/incidents/{report_id}
        single_res = await client.get(f"/api/incidents/{report_id}", headers=headers)
        assert single_res.status_code == 200
        single_data = single_res.json()
        assert single_data["report"]["report_id"] == report_id

        # 7. Verify /api/incidents/recent
        recent_res = await client.get("/api/incidents/recent")
        assert recent_res.status_code == 200
        recent_data = recent_res.json()
        assert recent_data["success"] is True

        # Clean up test artifacts
        await inc_repo.collection.delete_one({"report_id": report_id})
        await session_repo.collection.delete_one({"_id": session["_id"] if "_id" in session else session["id"]})
        await user_repo.collection.delete_one({"_id": user["_id"]})


@pytest.mark.asyncio
async def test_submit_incident_via_alias_route():
    """
    Verifies that /api/reports alias route also creates incident reports successfully.
    """
    ts = int(time.time() * 1000)
    test_email = f"citizen_alias_{ts}@disha.gov.in"
    user_repo = UserRepository()
    session_repo = SessionRepository()
    user = await user_repo.create_user({
        "username": f"alias_{ts}",
        "email": test_email,
        "password_hash": "mock_hash",
        "name": "Alias User",
        "verified": True,
    })
    user_id = str(user["id"])
    session = await session_repo.create_session(
        user_id=user_id,
        refresh_token_hash="mock_alias_refresh_hash",
    )
    access_token = create_access_token(user_id=user_id, session_id=session["id"])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = {
            "event_type": "landslide",
            "description": "Rockfall and mudslide blocking mountain highway near highway mile 42.",
            "location": {
                "lat": 30.0668,
                "lng": 79.0193,
                "address": "Rudraprayag, Uttarakhand, India",
            },
        }

        res = await client.post("/api/reports", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["success"] is True
        report_id = data["report_id"]

        inc_repo = IncidentRepository()
        await inc_repo.collection.delete_one({"report_id": report_id})
        await session_repo.collection.delete_one({"_id": session["_id"] if "_id" in session else session["id"]})
        await user_repo.collection.delete_one({"_id": user["_id"]})
