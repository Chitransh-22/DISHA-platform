"""
DISHA - Multi-Source Geospatial Disaster & Earthquake Intelligence Map Generator
Produces an executive, government-grade situational awareness map with clean clustering,
institutional cartography, multi-source filtering, and in-depth seismic analytics.
Saved to BACKEND/tests/temp_disaster_map.html.
"""

import os
import json
import webbrowser
import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure .env is loaded and backend directory in sys.path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")
load_dotenv()

from app.database.mongodb import db
from app.services.geocoding import geocode_location


def fetch_and_prepare_events():
    """
    Fetches both GNews disaster events and NCS RISEQ 30-day earthquakes from MongoDB.
    Normalizes coordinates and attributes for unified map visualization.
    """
    # 1. Fetch GNews Disasters
    news_cursor = list(db["disaster_events"].find({}, {"_id": 0}))
    prepared_news = []

    for ev in news_cursor:
        loc = ev.get("location") or {}
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        state = loc.get("state")
        city = loc.get("city")
        district = loc.get("district")

        if (lat is None or lon is None) and (state or city or district):
            res_lat, res_lon, prec = geocode_location(country="India", state=state, city=city, district=district)
            if res_lat is not None and res_lon is not None:
                lat, lon = res_lat, res_lon
                loc["latitude"] = lat
                loc["longitude"] = lon
                loc["precision"] = prec

        if lat is not None and lon is not None:
            ev["source_group"] = "GNEWS"
            ev["event_category"] = "news_disaster"
            prepared_news.append(ev)

    # 2. Fetch NCS RISEQ Earthquakes
    eq_cursor = list(db["earthquakes"].find({}, {"_id": 0}))
    prepared_eq = []

    for eq in eq_cursor:
        lat = eq.get("latitude")
        lon = eq.get("longitude")
        if lat is not None and lon is not None:
            eq["source_group"] = "NCS_RISEQ"
            eq["event_category"] = "earthquake"
            if "location" not in eq or not isinstance(eq["location"], dict):
                eq["location_desc"] = str(eq.get("location", ""))
                eq["location"] = {
                    "latitude": lat,
                    "longitude": lon,
                    "state": eq.get("region", "Unknown"),
                    "city": "",
                    "district": "",
                }
            prepared_eq.append(eq)

    combined = prepared_eq + prepared_news
    combined.sort(
        key=lambda x: x.get("origin_time") or x.get("incident_date") or x.get("published_at") or "",
        reverse=True,
    )

    return combined, len(eq_cursor), len(news_cursor)


def build_map_html(events, total_eq_count, total_news_count):
    """Generates an executive, institutional-grade disaster map HTML."""
    events_json = json.dumps(events, default=str)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DISHA - National Disaster & Earthquake Situational Map</title>
    
    <!-- Leaflet & MarkerCluster -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --bg-canvas: #090d16;
            --bg-surface: #0f172a;
            --bg-elevated: #1e293b;
            --bg-card: #131d31;
            --border: #24324d;
            --border-light: rgba(255, 255, 255, 0.08);
            --text-main: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            
            --brand-primary: #0284c7;
            --brand-accent: #0ea5e9;

            --mag-6: #dc2626;
            --mag-5: #ea580c;
            --mag-4: #d97706;
            --mag-3: #2563eb;
            --mag-2: #16a34a;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-canvas);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            -webkit-font-smoothing: antialiased;
        }}

        /* Header */
        header {{
            background: #0b1120;
            border-bottom: 1px solid var(--border);
            padding: 10px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 1000;
            flex-shrink: 0;
        }}

        .brand-block {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .brand-logo {{
            background: #0284c7;
            color: #ffffff;
            font-weight: 800;
            font-size: 13px;
            letter-spacing: 1px;
            padding: 4px 8px;
            border-radius: 4px;
        }}

        .brand-title {{
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -0.2px;
            color: #ffffff;
        }}

        .brand-subtitle {{
            font-size: 11px;
            color: var(--text-secondary);
        }}

        .header-kpi {{
            display: flex;
            align-items: center;
            gap: 20px;
            background: #111c30;
            border: 1px solid var(--border);
            padding: 6px 18px;
            border-radius: 6px;
        }}

        .kpi-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: var(--text-secondary);
        }}

        .kpi-num {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            color: #ffffff;
        }}

        .btn-header {{
            background: #1e293b;
            border: 1px solid var(--border);
            color: #cbd5e1;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .btn-header:hover {{
            background: #334155;
            color: #ffffff;
        }}

        /* Main Workspace */
        .workspace {{
            display: flex;
            flex: 1;
            height: calc(100vh - 58px);
            position: relative;
        }}

        /* Sidebar Control & Feed */
        .sidebar {{
            width: 360px;
            background-color: var(--bg-surface);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            z-index: 500;
            flex-shrink: 0;
        }}

        .controls-pane {{
            padding: 12px 14px;
            background-color: #0b1120;
            border-bottom: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .source-tabs {{
            display: flex;
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 2px;
            gap: 2px;
        }}

        .source-tab {{
            flex: 1;
            padding: 5px 8px;
            font-size: 11px;
            font-weight: 600;
            text-align: center;
            border-radius: 4px;
            cursor: pointer;
            background: transparent;
            color: var(--text-secondary);
            border: none;
            transition: all 0.15s;
        }}
        .source-tab.active {{
            background: #1e293b;
            color: #ffffff;
            font-weight: 700;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }}

        .search-input {{
            width: 100%;
            background-color: #131d31;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 7px 10px;
            color: #ffffff;
            font-size: 12px;
            outline: none;
            font-family: inherit;
        }}
        .search-input:focus {{
            border-color: #38bdf8;
        }}

        .filter-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
        }}

        .filter-dropdown {{
            background-color: #131d31;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 6px 8px;
            color: #cbd5e1;
            font-size: 11px;
            font-weight: 500;
            outline: none;
            cursor: pointer;
            font-family: inherit;
        }}
        .filter-dropdown option {{
            background-color: #0f172a;
            color: #f1f5f9;
        }}

        .toggle-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
            color: var(--text-secondary);
            padding: 2px 2px 0 2px;
        }}

        .feed-container {{
            flex: 1;
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        /* Event Card */
        .event-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 10px 12px;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .event-card:hover {{
            background-color: #1a2742;
            border-color: #38bdf8;
        }}

        .card-top {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 4px;
        }}

        .card-title {{
            font-size: 12px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.3;
            margin-bottom: 2px;
        }}

        .card-location {{
            font-size: 11px;
            color: var(--text-secondary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .card-footer {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 6px;
            padding-top: 4px;
            border-top: 1px solid var(--border-light);
            font-family: 'JetBrains Mono', monospace;
        }}

        /* Clean Badges */
        .tag {{
            font-size: 9px;
            font-weight: 700;
            padding: 2px 5px;
            border-radius: 3px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        .tag-ncs {{ background: rgba(234, 88, 12, 0.15); color: #fb923c; border: 1px solid rgba(234, 88, 12, 0.3); }}
        .tag-gnews {{ background: rgba(2, 132, 199, 0.15); color: #38bdf8; border: 1px solid rgba(2, 132, 199, 0.3); }}
        .tag-india {{ background: rgba(22, 163, 74, 0.15); color: #4ade80; border: 1px solid rgba(22, 163, 74, 0.3); }}
        .tag-border {{ background: rgba(217, 119, 6, 0.15); color: #fbbf24; border: 1px solid rgba(217, 119, 6, 0.3); }}
        
        .mag-pill {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 11px;
            padding: 1px 5px;
            border-radius: 3px;
            color: #ffffff;
        }}

        /* Map */
        #map {{
            flex: 1;
            height: 100%;
            background-color: #090d16;
        }}

        /* Leaflet Popups */
        .leaflet-popup-content-wrapper {{
            background: #0f172a !important;
            color: #f1f5f9 !important;
            border: 1px solid #334155 !important;
            border-radius: 6px !important;
            padding: 0 !important;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.6) !important;
        }}
        .leaflet-popup-tip {{
            background: #0f172a !important;
        }}
        .popup-container {{
            padding: 12px 14px;
            min-width: 250px;
            max-width: 300px;
            font-family: 'Inter', sans-serif;
        }}
        .popup-row {{
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: var(--text-secondary);
            margin-bottom: 3px;
        }}
        .popup-link {{
            display: block;
            text-align: center;
            background: #1e293b;
            border: 1px solid var(--border);
            color: #38bdf8;
            padding: 5px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-decoration: none;
            margin-top: 8px;
        }}
        .popup-link:hover {{
            background: #334155;
        }}

        /* Clean Clusters */
        .marker-cluster-small, .marker-cluster-medium, .marker-cluster-large {{
            background-color: rgba(15, 23, 42, 0.8) !important;
            border: 1px solid #38bdf8 !important;
            border-radius: 50% !important;
        }}
        .marker-cluster div {{
            background-color: #1e293b !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 11px !important;
            border-radius: 50% !important;
        }}

        /* Modal */
        .modal-bg {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            padding: 20px;
        }}
        .modal-bg.open {{
            display: flex;
        }}
        .modal-box {{
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 8px;
            width: 100%;
            max-width: 680px;
            max-height: 85vh;
            overflow-y: auto;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <!-- Top Executive Header -->
    <header>
        <div class="brand-block">
            <span class="brand-logo">DISHA</span>
            <div>
                <h1 class="brand-title">Situational Intelligence Map</h1>
                <div class="brand-subtitle">National Center for Seismology (NCS) & Multi-Source Hazard Ingestion</div>
            </div>
        </div>

        <div class="header-kpi">
            <div class="kpi-item">
                <span>NCS Quakes (30d):</span>
                <span class="kpi-num" style="color: #fb923c;" id="stat-eq">{total_eq_count}</span>
            </div>
            <span style="color: var(--border)">|</span>
            <div class="kpi-item">
                <span>India Territory:</span>
                <span class="kpi-num" style="color: #4ade80;" id="stat-india">--</span>
            </div>
            <span style="color: var(--border)">|</span>
            <div class="kpi-item">
                <span>Max Magnitude:</span>
                <span class="kpi-num" style="color: #f87171;" id="stat-max">--</span>
            </div>
            <span style="color: var(--border)">|</span>
            <div class="kpi-item">
                <span>News Incidents:</span>
                <span class="kpi-num" style="color: #38bdf8;" id="stat-news">{total_news_count}</span>
            </div>
        </div>

        <button class="btn-header" onclick="toggleModal()">
            Analytics Overview
        </button>
    </header>

    <!-- Main Workspace -->
    <div class="workspace">
        <!-- Sidebar -->
        <aside class="sidebar">
            <div class="controls-pane">
                <!-- Source Tabs -->
                <div class="source-tabs">
                    <button class="source-tab active" id="tab-all" onclick="filterBySource('ALL')">All Sources</button>
                    <button class="source-tab" id="tab-ncs" onclick="filterBySource('NCS_RISEQ')">NCS Earthquakes</button>
                    <button class="source-tab" id="tab-news" onclick="filterBySource('GNEWS')">News Disasters</button>
                </div>

                <!-- Search -->
                <input type="text" id="searchInput" class="search-input" placeholder="Search state, district, region..." />

                <!-- Multi-criteria Dropdowns -->
                <div class="filter-grid">
                    <select id="relFilter" class="filter-dropdown">
                        <option value="ALL">All Regions</option>
                        <option value="INDIA">India Territory Only</option>
                        <option value="INDIA_BORDER">Border Zone (~200km)</option>
                        <option value="REGIONAL">Regional (S. Asia)</option>
                    </select>

                    <select id="magFilter" class="filter-dropdown">
                        <option value="ALL">All Magnitudes</option>
                        <option value="3.0">M ≥ 3.0 (Felt)</option>
                        <option value="4.0">M ≥ 4.0 (Moderate)</option>
                        <option value="5.0">M ≥ 5.0 (Strong)</option>
                    </select>
                </div>

                <div class="toggle-row">
                    <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
                        <input type="checkbox" id="clusterToggle" checked onchange="toggleClustering()" />
                        <span>Cluster Map Markers</span>
                    </label>
                    <span id="filteredCount" style="font-family: 'JetBrains Mono'; font-size: 11px;">{len(events)} events</span>
                </div>
            </div>

            <!-- Feed Items -->
            <div class="feed-container" id="feedList"></div>
        </aside>

        <!-- Map Container -->
        <div id="map"></div>
    </div>

    <!-- Analytics Modal -->
    <div class="modal-bg" id="analyticsModal" onclick="if(event.target===this) toggleModal()">
        <div class="modal-box">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 16px;">
                <h2 style="font-size: 16px; font-weight: 700;">30-Day Earthquake & Hazard Analysis</h2>
                <button onclick="toggleModal()" style="background: transparent; border: none; color: var(--text-muted); font-size: 18px; cursor: pointer;">✕</button>
            </div>

            <div id="analyticsBody"></div>
        </div>
    </div>

    <script>
        const rawEvents = {events_json};

        // Initialize Map
        const map = L.map('map', {{
            center: [22.5, 82.0],
            zoom: 5,
            zoomControl: false
        }});

        L.control.zoom({{ position: 'bottomright' }}).addTo(map);

        // Professional Clean Dark Basemap
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; CARTO &copy; OpenStreetMap',
            maxZoom: 19
        }}).addTo(map);

        const clusterGroup = L.markerClusterGroup({{
            chunkedLoading: true,
            maxClusterRadius: 35,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false
        }}).addTo(map);

        const plainGroup = L.layerGroup();
        const markersMap = new Map();

        let activeSource = 'ALL';
        let useClustering = true;

        function getMagColor(mag) {{
            if (mag >= 6.0) return '#dc2626';
            if (mag >= 5.0) return '#ea580c';
            if (mag >= 4.0) return '#d97706';
            if (mag >= 3.0) return '#2563eb';
            return '#16a34a';
        }}

        // Summary Calculations
        let indiaCount = 0;
        let maxMag = 0;
        let maxMagRegion = '';
        const magCounts = {{ u3: 0, m3: 0, m4: 0, m5: 0, m6: 0 }};

        rawEvents.forEach(ev => {{
            if (ev.source_group === 'NCS_RISEQ') {{
                if (ev.relevance === 'INDIA') indiaCount++;
                const m = ev.magnitude || 0;
                if (m > maxMag) {{
                    maxMag = m;
                    maxMagRegion = ev.region || 'Seismic Event';
                }}
                if (m < 3.0) magCounts.u3++;
                else if (m < 4.0) magCounts.m3++;
                else if (m < 5.0) magCounts.m4++;
                else if (m < 6.0) magCounts.m5++;
                else magCounts.m6++;
            }}
        }});

        document.getElementById('stat-india').innerText = indiaCount;
        document.getElementById('stat-max').innerText = maxMag > 0 ? 'M ' + maxMag.toFixed(1) : '--';

        // Render Map Markers
        function renderMarkers(items) {{
            clusterGroup.clearLayers();
            plainGroup.clearLayers();
            markersMap.clear();

            items.forEach(ev => {{
                const lat = ev.latitude || ev.location?.latitude;
                const lon = ev.longitude || ev.location?.longitude;
                if (!lat || !lon) return;

                const isEq = ev.source_group === 'NCS_RISEQ';

                if (isEq) {{
                    const mag = ev.magnitude || 0;
                    const color = getMagColor(mag);
                    const size = Math.max(12, Math.min(26, Math.round(mag * 4.5)));

                    const customIcon = L.divIcon({{
                        className: 'clean-pin',
                        html: `
                            <div style="width: ${{size}}px; height: ${{size}}px; border-radius: 50%; background: ${{color}}; border: 2px solid #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; font-size: ${{size > 18 ? 10 : 8}}px; font-weight: 700; color: #ffffff; font-family: 'JetBrains Mono';">
                                ${{mag >= 3.0 ? mag.toFixed(1) : ''}}
                            </div>
                        `,
                        iconSize: [size, size],
                        iconAnchor: [size / 2, size / 2]
                    }});

                    const marker = L.marker([lat, lon], {{ icon: customIcon }});

                    const popup = `
                        <div class="popup-container">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span class="mag-pill" style="background: ${{color}};">M ${{mag.toFixed(1)}}</span>
                                <span class="tag tag-ncs">NCS RISEQ</span>
                                <span class="tag ${{ev.relevance === 'INDIA' ? 'tag-india' : 'tag-border'}}">${{ev.relevance || 'REGIONAL'}}</span>
                            </div>
                            <div style="font-size: 13px; font-weight: 700; color: #ffffff; margin-bottom: 2px;">${{ev.region || 'Seismic Incident'}}</div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 8px;">${{ev.location_desc || ev.region}}</div>
                            
                            <div class="popup-row"><span>Hypocenter Depth:</span> <strong style="color: #ffffff;">${{ev.depth_km}} km</strong></div>
                            <div class="popup-row"><span>Review Status:</span> <strong style="color: #38bdf8;">${{ev.status || 'Reviewed'}}</strong></div>
                            <div class="popup-row"><span>Coordinates:</span> <strong style="color: #ffffff;">${{lat.toFixed(3)}}°N, ${{lon.toFixed(3)}}°E</strong></div>
                            <div class="popup-row"><span>Origin (UTC):</span> <strong style="color: #ffffff;">${{(ev.origin_time || '').substring(0, 16)}}</strong></div>

                            ${{ev.felt_report_url ? `<a href="${{ev.felt_report_url}}" target="_blank" class="popup-link">NCS Felt Report &rarr;</a>` : ''}}
                        </div>
                    `;

                    marker.bindPopup(popup);

                    if (useClustering) clusterGroup.addLayer(marker);
                    else plainGroup.addLayer(marker);

                    markersMap.set(ev.event_id || ev.article_id, marker);

                }} else {{
                    const dType = ev.disaster_type || 'Disaster';
                    const customIcon = L.divIcon({{
                        className: 'news-pin',
                        html: `<div style="width: 14px; height: 14px; border-radius: 50%; background: #0284c7; border: 2px solid #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.5);"></div>`,
                        iconSize: [14, 14],
                        iconAnchor: [7, 7]
                    }});

                    const marker = L.marker([lat, lon], {{ icon: customIcon }});

                    const popup = `
                        <div class="popup-container">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span class="tag tag-gnews">${{dType.toUpperCase()}}</span>
                                <span style="font-size: 10px; color: var(--text-muted);">${{ev.severity || 'Medium'}}</span>
                            </div>
                            <div style="font-size: 13px; font-weight: 700; color: #ffffff; margin-bottom: 4px;">${{ev.title || 'Disaster Incident'}}</div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">📍 ${{ev.location?.city ? ev.location.city + ', ' : ''}}${{ev.location?.state || 'India'}}</div>
                            ${{ev.url ? `<a href="${{ev.url}}" target="_blank" class="popup-link">View Source News &rarr;</a>` : ''}}
                        </div>
                    `;

                    marker.bindPopup(popup);

                    if (useClustering) clusterGroup.addLayer(marker);
                    else plainGroup.addLayer(marker);

                    markersMap.set(ev.event_id || ev.article_id, marker);
                }}
            }});

            if (!useClustering) map.addLayer(plainGroup);
        }}

        // Render Feed
        function renderFeed(items) {{
            const list = document.getElementById('feedList');
            list.innerHTML = '';
            document.getElementById('filteredCount').innerText = `${{items.length}} events`;

            if (items.length === 0) {{
                list.innerHTML = '<div style="color: var(--text-muted); text-align: center; margin-top: 30px; font-size: 12px;">No matching records found.</div>';
                return;
            }}

            items.forEach(ev => {{
                const isEq = ev.source_group === 'NCS_RISEQ';
                const card = document.createElement('div');
                card.className = 'event-card';

                const mag = ev.magnitude;
                const magColor = mag != null ? getMagColor(mag) : '#0284c7';
                const title = isEq ? (ev.region || 'Seismic Incident') : (ev.title || 'Disaster Alert');
                const loc = isEq ? (ev.location_desc || ev.region) : [ev.location?.city, ev.location?.state].filter(Boolean).join(', ');
                const timeStr = (ev.origin_time || ev.incident_date || ev.published_at || '').substring(0, 16);

                card.innerHTML = `
                    <div class="card-top">
                        <span class="tag ${{isEq ? 'tag-ncs' : 'tag-gnews'}}">${{isEq ? 'NCS RISEQ' : 'GNews AI'}}</span>
                        ${{ev.relevance ? `<span class="tag ${{ev.relevance === 'INDIA' ? 'tag-india' : 'tag-border'}}">${{ev.relevance}}</span>` : ''}}
                        <span style="font-size: 10px; color: var(--text-muted); font-family: 'JetBrains Mono';">${{timeStr}}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
                        ${{isEq ? `<span class="mag-pill" style="background: ${{magColor}};">M ${{mag.toFixed(1)}}</span>` : '<span class="tag tag-gnews">NEWS</span>'}}
                        <div style="font-weight: 700; font-size: 12px; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1;">
                            ${{title}}
                        </div>
                    </div>
                    <div class="card-location" style="margin-top: 2px;">📍 ${{loc || 'India'}}</div>
                    ${{isEq ? `<div class="card-footer"><span>Depth: ${{ev.depth_km}} km</span><span>Status: ${{ev.status || 'Reviewed'}}</span></div>` : ''}}
                `;

                card.onclick = () => {{
                    const lat = ev.latitude || ev.location?.latitude;
                    const lon = ev.longitude || ev.location?.longitude;
                    if (lat && lon) {{
                        map.flyTo([lat, lon], 8, {{ duration: 1.0 }});
                        const m = markersMap.get(ev.event_id || ev.article_id);
                        if (m) {{
                            setTimeout(() => m.openPopup(), 300);
                        }}
                    }}
                }};

                list.appendChild(card);
            }});
        }}

        function filterBySource(src) {{
            activeSource = src;
            document.getElementById('tab-all').className = 'source-tab ' + (src === 'ALL' ? 'active' : '');
            document.getElementById('tab-ncs').className = 'source-tab ' + (src === 'NCS_RISEQ' ? 'active' : '');
            document.getElementById('tab-news').className = 'source-tab ' + (src === 'GNEWS' ? 'active' : '');
            applyAllFilters();
        }}

        function toggleClustering() {{
            useClustering = document.getElementById('clusterToggle').checked;
            if (useClustering) {{
                map.removeLayer(plainGroup);
                map.addLayer(clusterGroup);
            }} else {{
                map.removeLayer(clusterGroup);
                map.addLayer(plainGroup);
            }}
            applyAllFilters();
        }}

        function applyAllFilters() {{
            const search = document.getElementById('searchInput').value.toLowerCase().trim();
            const rel = document.getElementById('relFilter').value;
            const mag = document.getElementById('magFilter').value;

            const filtered = rawEvents.filter(ev => {{
                if (activeSource !== 'ALL' && ev.source_group !== activeSource) return false;
                if (rel !== 'ALL' && ev.relevance !== rel) return false;
                if (mag !== 'ALL') {{
                    const minMag = parseFloat(mag);
                    if ((ev.magnitude || 0) < minMag) return false;
                }}
                if (search) {{
                    const title = (ev.title || ev.region || '').toLowerCase();
                    const loc = (ev.location_desc || ev.location?.state || '').toLowerCase();
                    if (!title.includes(search) && !loc.includes(search)) return false;
                }}
                return true;
            }});

            renderMarkers(filtered);
            renderFeed(filtered);
        }}

        document.getElementById('searchInput').addEventListener('input', applyAllFilters);
        document.getElementById('relFilter').addEventListener('change', applyAllFilters);
        document.getElementById('magFilter').addEventListener('change', applyAllFilters);

        function toggleModal() {{
            const el = document.getElementById('analyticsModal');
            el.classList.toggle('open');
            if (el.classList.contains('open')) {{
                buildAnalytics();
            }}
        }}

        function buildAnalytics() {{
            const body = document.getElementById('analyticsBody');
            const totalEq = {total_eq_count};
            body.innerHTML = `
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 16px;">
                    <div style="background: #1e293b; padding: 12px; border-radius: 6px; border: 1px solid var(--border);">
                        <div style="font-size: 11px; color: var(--text-secondary);">30-Day Earthquakes</div>
                        <div style="font-size: 22px; font-weight: 700; color: #fb923c; font-family: 'JetBrains Mono';">${{totalEq}}</div>
                    </div>
                    <div style="background: #1e293b; padding: 12px; border-radius: 6px; border: 1px solid var(--border);">
                        <div style="font-size: 11px; color: var(--text-secondary);">India Territory Epicenters</div>
                        <div style="font-size: 22px; font-weight: 700; color: #4ade80; font-family: 'JetBrains Mono';">${{indiaCount}}</div>
                    </div>
                    <div style="background: #1e293b; padding: 12px; border-radius: 6px; border: 1px solid var(--border);">
                        <div style="font-size: 11px; color: var(--text-secondary);">Max Magnitude</div>
                        <div style="font-size: 22px; font-weight: 700; color: #f87171; font-family: 'JetBrains Mono';">M ${{maxMag.toFixed(1)}}</div>
                    </div>
                </div>

                <div style="background: #131d31; padding: 14px; border-radius: 6px; border: 1px solid var(--border);">
                    <div style="font-size: 12px; font-weight: 700; color: #ffffff; margin-bottom: 10px;">Magnitude Stratification</div>
                    <div style="display: flex; flex-direction: column; gap: 6px; font-size: 11px;">
                        <div style="display: flex; justify-content: space-between;"><span>Strong (M ≥ 6.0):</span> <strong>${{magCounts.m6}}</strong></div>
                        <div style="display: flex; justify-content: space-between;"><span>Moderate (M 5.0 - 5.9):</span> <strong>${{magCounts.m5}}</strong></div>
                        <div style="display: flex; justify-content: space-between;"><span>Light (M 4.0 - 4.9):</span> <strong>${{magCounts.m4}}</strong></div>
                        <div style="display: flex; justify-content: space-between;"><span>Minor (M 3.0 - 3.9):</span> <strong>${{magCounts.m3}}</strong></div>
                        <div style="display: flex; justify-content: space-between;"><span>Micro (&lt; 3.0):</span> <strong>${{magCounts.u3}}</strong></div>
                    </div>
                </div>
            `;
        }}

        // Initial Load
        renderMarkers(rawEvents);
        renderFeed(rawEvents);
    </script>
</body>
</html>
"""
    return html


def generate_map(open_browser: bool = False):
    """Main execution to generate temp map UI."""
    print("[DISHA MAP] Fetching multi-source events from MongoDB...")
    events, total_eq, total_news = fetch_and_prepare_events()
    print(f"[DISHA MAP] Retrieved {total_eq} NCS Earthquakes, {total_news} News Disasters ({len(events)} total geocoded).")

    output_path = Path(__file__).resolve().parent / "temp_disaster_map.html"
    html_content = build_map_html(events, total_eq, total_news)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[DISHA MAP] Successfully generated interactive UI map: {output_path}")

    if open_browser:
        webbrowser.open(f"file://{output_path.resolve()}")

    return str(output_path)


if __name__ == "__main__":
    generate_map(open_browser=False)
