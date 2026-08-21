import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError

# Search .env in current directory and backend root
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

load_dotenv(_backend_dir / ".env")
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
MONGO_DB = os.getenv("MONGO_DB", "DISHA")

if not MONGO_URI:
    raise RuntimeError(
        "MONGO_URI (or MONGODB_URI) is missing from .env"
    )

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
)


def init_db_indexes(database):
    """
    Creates recommended single and compound indexes for fast query resolution,
    pending AI queue handling, and event deduplication.
    """
    try:
        # disaster_events collection
        database["disaster_events"].create_index([("event_id", ASCENDING)], background=True)
        database["disaster_events"].create_index([("article_id", ASCENDING)], background=True)
        database["disaster_events"].create_index([("status", ASCENDING), ("disaster_type", ASCENDING)], background=True)
        database["disaster_events"].create_index([("location.state", ASCENDING)], background=True)
        database["disaster_events"].create_index([("location.district", ASCENDING)], background=True)
        database["disaster_events"].create_index([("location.city", ASCENDING)], background=True)
        database["disaster_events"].create_index([("incident_date", DESCENDING)], background=True)
        database["disaster_events"].create_index([("processed_at", DESCENDING)], background=True)
        database["disaster_events"].create_index([("last_updated_at", DESCENDING)], background=True)

        # rejected_news collection
        database["rejected_news"].create_index([("article_id", ASCENDING)], background=True)
        database["rejected_news"].create_index([("stage", ASCENDING), ("processed_at", DESCENDING)], background=True)
        database["rejected_news"].create_index([("stage", ASCENDING), ("reason", ASCENDING)], background=True)

        # news_temp collection
        database["news_temp"].create_index([("status", ASCENDING), ("retry_count", ASCENDING)], background=True)
        database["news_temp"].create_index([("status", ASCENDING), ("candidate_priority_score", DESCENDING)], background=True)
        database["news_temp"].create_index([("fetched_at", DESCENDING)], background=True)

        # earthquakes collection (NCS RISEQ ingestion)
        database["earthquakes"].create_index([("event_id", ASCENDING)], unique=True, background=True)
        database["earthquakes"].create_index([("origin_timestamp", DESCENDING)], background=True)
        database["earthquakes"].create_index([("origin_time", DESCENDING)], background=True)
        database["earthquakes"].create_index([("magnitude", DESCENDING)], background=True)
        database["earthquakes"].create_index([("relevance", ASCENDING)], background=True)
        database["earthquakes"].create_index([("source", ASCENDING)], background=True)
        database["earthquakes"].create_index([("event_type", ASCENDING)], background=True)
        database["earthquakes"].create_index([("status", ASCENDING)], background=True)
        database["earthquakes"].create_index([("region", ASCENDING)], background=True)
        database["earthquakes"].create_index([("created_at", DESCENDING)], background=True)
        database["earthquakes"].create_index([("last_seen_at", DESCENDING)], background=True)

        # sachet_alerts collection (NDMA SACHET CAP Ingestion)
        database["sachet_alerts"].create_index([("event_id", ASCENDING)], unique=True, background=True)
        database["sachet_alerts"].create_index([("alert_id", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("guid", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("event_timestamp", DESCENDING)], background=True)
        database["sachet_alerts"].create_index([("event_time", DESCENDING)], background=True)
        database["sachet_alerts"].create_index([("effective_at", DESCENDING)], background=True)
        database["sachet_alerts"].create_index([("expires_at", DESCENDING)], background=True)
        database["sachet_alerts"].create_index([("sent_at", DESCENDING)], background=True)
        database["sachet_alerts"].create_index([("severity", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("urgency", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("certainty", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("disaster_type", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("source", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("event_type", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("status", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("message_type", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("location.state", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("location.district", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("is_active", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("is_cancelled", ASCENDING)], background=True)
        database["sachet_alerts"].create_index([("created_at", DESCENDING)], background=True)
        database["sachet_alerts"].create_index([("last_seen_at", DESCENDING)], background=True)

        # sync_state collection for ETag and last-modified caching
        database["sync_state"].create_index([("pipeline", ASCENDING)], unique=True, background=True)

        # incident_reports collection (Citizen disaster incident submissions)
        database["incident_reports"].create_index([("report_id", ASCENDING)], unique=True, background=True)
        database["incident_reports"].create_index([("user_id", ASCENDING)], background=True)
        database["incident_reports"].create_index([("event_type", ASCENDING)], background=True)
        database["incident_reports"].create_index([("status", ASCENDING)], background=True)
        database["incident_reports"].create_index([("created_at", DESCENDING)], background=True)
        database["incident_reports"].create_index([("location.coordinates", "2dsphere")], sparse=True, background=True)

        print("[MongoDB] Indexes initialized successfully (including incident_reports)")
    except PyMongoError as err:
        print(f"[MongoDB] Index initialization notice: {err}")


try:
    client.admin.command("ping")
    print("[MongoDB] Connected to MongoDB Atlas")
    db = client[MONGO_DB]
    init_db_indexes(db)

except ConnectionFailure as e:
    print(f"[MongoDB] Connection failed: {e}")
    db = client[MONGO_DB]