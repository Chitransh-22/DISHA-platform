import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError

# Search .env in current directory and backend root
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent.parent
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
        database["earthquakes"].create_index([("origin_time", DESCENDING)], background=True)
        database["earthquakes"].create_index([("magnitude", DESCENDING)], background=True)
        database["earthquakes"].create_index([("relevance", ASCENDING)], background=True)
        database["earthquakes"].create_index([("source", ASCENDING)], background=True)
        database["earthquakes"].create_index([("event_type", ASCENDING)], background=True)
        database["earthquakes"].create_index([("status", ASCENDING)], background=True)
        database["earthquakes"].create_index([("region", ASCENDING)], background=True)
        database["earthquakes"].create_index([("created_at", DESCENDING)], background=True)
        database["earthquakes"].create_index([("last_seen_at", DESCENDING)], background=True)

        print("[MongoDB] Indexes initialized successfully")
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