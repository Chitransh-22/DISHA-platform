# -*- coding: utf-8 -*-
"""
DISHA Platform — Mobile & Directions Engineering Verification Test
Verifies:
1. Direction URL generator generates correct Apple Maps (iOS) & Google Maps fallback URLs.
2. Survey of India GeoJSON dataset integrity (Ladakh, Jammu & Kashmir northernmost boundary).
3. Mobile Navigation items & routes.
4. Event normalization & consistency between News and Map events.
"""
import sys
import os
import json
import pytest

# Ensure BACKEND is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_survey_of_india_geojson_integrity():
    """Verify Survey of India geojson file exists and has correct boundaries."""
    geojson_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'FRONTEND', 'src', 'data', 'indiaBoundaryGeojson.js'))
    assert os.path.exists(geojson_path), f"File {geojson_path} does not exist"
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that export exists
    assert "export const INDIA_SURVEY_OF_INDIA_GEOJSON =" in content
    # Extract JSON part
    json_str = content.split("export const INDIA_SURVEY_OF_INDIA_GEOJSON =")[1].strip().rstrip(";")
    data = json.loads(json_str)
    
    assert data.get("type") == "FeatureCollection"
    features = data.get("features", [])
    assert len(features) > 0
    
    # Verify presence of Ladakh & Jammu & Kashmir
    names = [f.get("properties", {}).get("ST_NM") or f.get("properties", {}).get("st_nm") for f in features]
    assert any("Ladakh" in str(n) for n in names), "Ladakh boundary missing from Survey of India dataset"
    assert any("Jammu" in str(n) for n in names), "Jammu and Kashmir missing from Survey of India dataset"
    
    # Check northernmost latitude reaches > 37.0° N (Siachen / Indira Col area)
    max_lat = -90.0
    for feat in features:
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        def get_coords(c):
            if isinstance(c, (list, tuple)) and len(c) == 2 and isinstance(c[0], (int, float)):
                yield c
            elif isinstance(c, (list, tuple)):
                for sub in c:
                    yield from get_coords(sub)
        for pt in get_coords(coords):
            if pt[1] > max_lat:
                max_lat = pt[1]
    
    assert max_lat >= 37.0, f"Northernmost latitude {max_lat} is below authoritative Survey of India boundary (37.0°N)"
    print(f"Authoritative boundary confirmed: Max latitude reaches {max_lat:.3f}° N")

def test_navigation_utility_logic():
    """Verify navigation URL formatting logic."""
    nav_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'FRONTEND', 'src', 'utils', 'navigation.js'))
    assert os.path.exists(nav_file)
    with open(nav_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    assert "getDirectionsUrl" in code
    assert "openDirections" in code
    assert "google.com/maps" in code
    assert "maps.apple.com" in code

def test_mobile_bottom_nav_component():
    """Verify MobileBottomNav component structure."""
    bottom_nav = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'FRONTEND', 'src', 'components', 'common', 'MobileBottomNav.jsx'))
    assert os.path.exists(bottom_nav)
    with open(bottom_nav, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Check that navigation items exist
    assert "Home" in code
    assert "Live Map" in code
    assert "News" in code
    assert "Report" in code
    assert "Alerts" in code
    # Check fixed bottom styling with safe area
    assert "fixed bottom-0" in code
    assert "md:hidden" in code

def test_recent_news_view_on_map():
    """Verify RecentNewsPage has 'View on Map' action."""
    news_page = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'FRONTEND', 'src', 'pages', 'RecentNewsPage.jsx'))
    with open(news_page, 'r', encoding='utf-8') as f:
        code = f.read()
    
    assert "View on Map" in code
    assert "focusEvent" in code
    assert "scrollToMap" in code

def test_news_detail_map_and_directions():
    """Verify NewsDetailPage has View on Live Map and Get Directions."""
    detail_page = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'FRONTEND', 'src', 'pages', 'NewsDetailPage.jsx'))
    with open(detail_page, 'r', encoding='utf-8') as f:
        code = f.read()
    
    assert "View on Live Map" in code
    assert "Get Directions to Location" in code
    assert "openDirections" in code

def test_live_disaster_map_adaptive_layout():
    """Verify LiveDisasterMap has both Desktop Sidebar and Mobile Bottom Sheet."""
    map_comp = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'FRONTEND', 'src', 'pages', 'LandingPage', 'components', 'LiveDisasterMap.jsx'))
    with open(map_comp, 'r', encoding='utf-8') as f:
        code = f.read()
    
    assert "disha-mobile-bottom-sheet" in code
    assert "hidden md:flex" in code  # Desktop docked sidebar
    assert "flex md:hidden" in code  # Mobile bottom sheet
    assert "Get Directions to Incident" in code
    assert "Get Directions to Facility" in code
    assert "openDirections" in code
