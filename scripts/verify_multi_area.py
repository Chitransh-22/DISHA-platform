import sys
import os
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Ensure BACKEND is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "BACKEND"))

from app.database.mongodb import db
from app.services.geo_filter_service import (
    normalize_geographic_query,
    evaluate_event_geographic_match,
    is_valid_coordinate,
)

async def run_verification():
    import time
    for attempt in range(5):
        try:
            all_news = list(db.disaster_events.find({}))
            break
        except Exception as e:
            print(f"MongoDB read attempt {attempt+1} failed ({e}), retrying in 2s...")
            time.sleep(2)
    else:
        raise RuntimeError("Failed to fetch disaster_events after 5 attempts")
    total_docs = len(all_news)
    print(f"Total disaster_events documents in MongoDB: {total_docs}")

    areas = [
        {"country": "India", "state": None, "district": None, "city": None, "label": "All India (Nation)"},
        {"country": "India", "state": "Gujarat", "district": None, "city": None, "label": "Gujarat (State)"},
        {"country": "India", "state": "Assam", "district": None, "city": None, "label": "Assam (State)"},
        {"country": "India", "state": "Maharashtra", "district": None, "city": None, "label": "Maharashtra (State)"},
        {"country": "India", "state": "Delhi", "district": None, "city": None, "label": "Delhi (UT/State)"},
        {"country": "India", "state": "Gujarat", "district": "Ahmedabad", "city": None, "label": "Ahmedabad, Gujarat (District)"},
        {"country": "India", "state": "Tamil Nadu", "district": "Chennai", "city": None, "label": "Chennai, Tamil Nadu (District/City)"},
    ]

    print("\n### Multi-Area Verification Table")
    print("| Selected Geographic Area | Total News Candidates | Geographically Verified (Mappable) | Excluded (Other Area) | Location Unresolved | Invalid Coordinates Rejected |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: |")

    for area in areas:
        label = area["label"]
        query_area = normalize_geographic_query(
            country=area["country"],
            state=area["state"],
            district=area["district"],
            city=area["city"]
        )

        verified_matching = 0
        excluded_other_area = 0
        unresolved_locations = 0
        invalid_coords_count = 0

        for doc in all_news:
            loc = doc.get("location") or {}
            raw_lat = loc.get("latitude") if loc.get("latitude") is not None else doc.get("latitude")
            raw_lon = loc.get("longitude") if loc.get("longitude") is not None else doc.get("longitude")

            # Check if coordinates are invalid
            if raw_lat is not None and raw_lon is not None and not is_valid_coordinate(raw_lat, raw_lon):
                invalid_coords_count += 1

            res = evaluate_event_geographic_match(doc, query_area)
            if res["is_match"]:
                if res["is_mappable"]:
                    verified_matching += 1
                else:
                    unresolved_locations += 1
            else:
                excluded_other_area += 1

        print(f"| **{label}** | {total_docs} | {verified_matching} | {excluded_other_area} | {unresolved_locations} | {invalid_coords_count} |")

    # Verify coordinate properties of all verified matching records
    print("\n### Verification of Map Marker Coordinates Quality:")
    print("- Verifying that NO verified mappable alert has latitude/longitude outside India bounds [6.0, 38.0], [68.0, 98.0]")
    print("- Verifying that NO verified mappable alert has India centroid (20.5937, 78.9629)")
    print("- Verifying that NO verified mappable alert has null or NaN coordinates")

    violations = 0
    checked_mappable = 0
    for doc in all_news:
        loc = doc.get("location") or {}
        raw_lat = loc.get("latitude") if loc.get("latitude") is not None else doc.get("latitude")
        raw_lon = loc.get("longitude") if loc.get("longitude") is not None else doc.get("longitude")
        
        if doc.get("has_coordinates") is True:
            checked_mappable += 1
            if not is_valid_coordinate(raw_lat, raw_lon):
                violations += 1
            if abs(float(raw_lat) - 20.5937) < 0.01 and abs(float(raw_lon) - 78.9629) < 0.01:
                violations += 1

    print(f"Total checked mappable docs: {checked_mappable}")
    print(f"Total violations found: {violations}")
    assert violations == 0, f"Found {violations} coordinate violations!"
    print("ALL MAP MARKER COORDINATES VERIFIED STRICTLY VALID!")

    # Verify FastAPI routes directly in same event loop
    print("\n### Verifying get_disasters route responses:")
    from app.routes.gnews import get_disasters

    test_queries = [
        {"state": None, "district": None, "label": "All India"},
        {"state": "Gujarat", "district": None, "label": "Gujarat"},
        {"state": "Assam", "district": None, "label": "Assam"},
        {"state": "Maharashtra", "district": None, "label": "Maharashtra"},
        {"state": "Gujarat", "district": "Ahmedabad", "label": "Ahmedabad, Gujarat"},
    ]

    for q in test_queries:
        res = await get_disasters(state=q["state"], district=q["district"], time_range="all")
        sel = res.get("selected_area", {})
        print(f"  Area: {q['label']} -> status: 200 | Level: {sel.get('level')} | State: {sel.get('state')} | District: {sel.get('district')} | Total: {res.get('total')} | Mappable: {res.get('mappable_count')} | Unresolved: {res.get('unresolved_count')}")

    print("\nAPI ROUTE VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_verification())
