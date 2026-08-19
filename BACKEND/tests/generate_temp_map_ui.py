"""
DISHA Platform - Interactive Multi-Source Disaster & Hazard Situational Map
Visualizes:
1. NCS RISEQ 30-Day Earthquakes (National Center for Seismology)
2. GNews Ingested Disaster Incidents (AI-Classified News)
3. NDMA SACHET CAP Alerts & Bulletins (National Disaster Management Authority)

Enforces strict recent-first chronological sorting across all feeds and multi-criteria time filtering.
"""

import os
import sys
import json
import webbrowser
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Ensure backend root in sys.path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

load_dotenv(_backend_dir / ".env")
load_dotenv()

from app.database.mongodb import db
from app.services.geocoding import geocode_location


def normalize_event_time(ev: dict):
    """
    Computes a standardized ISO 8601 UTC string and Unix epoch timestamp in seconds
    for any disaster incident, earthquake, or NDMA SACHET alert.
    """
    # 1. Check existing numeric timestamp
    if ev.get("unified_timestamp") is not None:
        try:
            ts = float(ev["unified_timestamp"])
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(), ts
        except Exception:
            pass

    if ev.get("origin_timestamp") is not None:
        try:
            ts = float(ev["origin_timestamp"])
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(), ts
        except Exception:
            pass

    if ev.get("event_timestamp") is not None:
        try:
            ts = float(ev["event_timestamp"])
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(), ts
        except Exception:
            pass

    # 2. Check candidate string fields
    candidate_strs = [
        ev.get("event_time"),
        ev.get("effective_at"),
        ev.get("origin_time"),
        ev.get("incident_date"),
        ev.get("published_at"),
        ev.get("article_date"),
        ev.get("sent_at"),
        ev.get("created_at"),
        ev.get("first_seen_at"),
    ]

    for raw in candidate_strs:
        if not raw or not isinstance(raw, str):
            continue
        s = raw.strip()
        if not s:
            continue

        # Try ISO 8601
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.isoformat(), dt.timestamp()
        except Exception:
            pass

        # Try space-separated format (e.g. '2026-08-18 18:51:21')
        try:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat(), dt.timestamp()
        except Exception:
            pass

        # Try date-only format (e.g. '2026-08-18')
        try:
            dt = datetime.strptime(s, "%Y-%m-%d")
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat(), dt.timestamp()
        except Exception:
            pass

    return "", 0.0


def fetch_and_prepare_events():
    """
    Fetches GNews disaster events, NCS RISEQ earthquakes, and NDMA SACHET CAP alerts from MongoDB.
    Normalizes coordinates, assigns unified timestamps, and sorts strictly recent-first.
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
            iso_t, epoch_t = normalize_event_time(ev)
            ev["unified_time"] = iso_t
            ev["unified_timestamp"] = epoch_t
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
            iso_t, epoch_t = normalize_event_time(eq)
            eq["unified_time"] = iso_t
            eq["unified_timestamp"] = epoch_t
            prepared_eq.append(eq)

    # 3. Fetch NDMA SACHET CAP Alerts
    sachet_cursor = list(db["sachet_alerts"].find({}, {"_id": 0}))
    prepared_sachet = []

    for sa in sachet_cursor:
        lat = sa.get("latitude")
        lon = sa.get("longitude")
        loc = sa.get("location") or {}
        state = loc.get("state")
        city = loc.get("city")
        district = loc.get("district")

        if (lat is None or lon is None) and (state or district or city):
            res_lat, res_lon, prec = geocode_location(country="India", state=state, city=city, district=district)
            if res_lat is not None and res_lon is not None:
                lat, lon = res_lat, res_lon
                sa["latitude"] = lat
                sa["longitude"] = lon
                loc["latitude"] = lat
                loc["longitude"] = lon
                loc["precision"] = prec

        if lat is not None and lon is not None:
            sa["source_group"] = "NDMA_SACHET"
            sa["event_category"] = "sachet_alert"
            iso_t, epoch_t = normalize_event_time(sa)
            sa["unified_time"] = iso_t
            sa["unified_timestamp"] = epoch_t
            prepared_sachet.append(sa)

    combined = prepared_eq + prepared_news + prepared_sachet
    
    # Sort strictly recent-first (descending by epoch timestamp)
    combined.sort(
        key=lambda x: x.get("unified_timestamp", 0.0),
        reverse=True,
    )

    return combined, len(eq_cursor), len(news_cursor), len(sachet_cursor)


def build_map_html(events, total_eq_count, total_news_count, total_sachet_count=0):
    """Generates an executive, institutional-grade disaster map HTML."""
    events_json = json.dumps(events, default=str)
    total_events_count = len(events)

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

    <!-- Typography -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">

    <style>
        :root {{
            --bg-base: #090d16;
            --bg-surface: #0f172a;
            --bg-card: #1e293b;
            --bg-hover: #334155;
            --border: #1e293b;
            --border-highlight: #334155;

            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;

            --brand-primary: #0284c7;
            --brand-accent: #0ea5e9;
            --brand-sachet: #a855f7;

            --mag-6: #dc2626;
            --mag-5: #ea580c;
            --mag-4: #d97706;
            --mag-3: #2563eb;
            --mag-2: #16a34a;
        }}

        .tag-sachet {{
            background: rgba(168, 85, 247, 0.18);
            color: #c084fc;
            border: 1px solid rgba(168, 85, 247, 0.35);
        }}

        .sev-extreme {{ background: #dc2626; color: #ffffff; }}
        .sev-severe {{ background: #ea580c; color: #ffffff; }}
        .sev-moderate {{ background: #d97706; color: #ffffff; }}
        .sev-minor {{ background: #2563eb; color: #ffffff; }}
        .sev-unknown {{ background: #64748b; color: #ffffff; }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-base);
            color: var(--text-primary);
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}

        /* Header Bar */
        header {{
            height: 52px;
            background: #0b1120;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            z-index: 1000;
        }}

        .brand-block {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .brand-logo {{
            background: linear-gradient(135deg, #0284c7, #38bdf8);
            color: #ffffff;
            font-weight: 800;
            font-size: 13px;
            letter-spacing: 1px;
            padding: 4px 8px;
            border-radius: 4px;
        }}

        .brand-title {{
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}

        .brand-subtitle {{
            font-size: 11px;
            color: var(--text-secondary);
        }}

        .header-kpi {{
            display: flex;
            align-items: center;
            gap: 14px;
            font-size: 11px;
        }}

        .kpi-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--text-secondary);
        }}

        .kpi-num {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            color: var(--text-primary);
        }}

        .btn-header {{
            background: #1e293b;
            border: 1px solid var(--border-highlight);
            color: var(--text-primary);
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .btn-header:hover {{
            background: #334155;
        }}

        /* Workspace Grid */
        .workspace {{
            flex: 1;
            display: grid;
            grid-template-columns: 380px 1fr;
            overflow: hidden;
            position: relative;
        }}

        /* Sidebar Feed */
        .sidebar {{
            background: var(--bg-surface);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow: hidden;
        }}

        .controls-pane {{
            padding: 12px;
            border-bottom: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 8px;
            background: #0c1424;
        }}

        .source-tabs {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1.1fr;
            background: #070b13;
            padding: 2px;
            border-radius: 6px;
            border: 1px solid var(--border);
            gap: 2px;
        }}

        .source-tab {{
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 10px;
            font-weight: 600;
            padding: 6px 2px;
            border-radius: 4px;
            cursor: pointer;
            text-align: center;
            transition: all 0.15s ease;
        }}

        .source-tab.active {{
            background: #1e293b;
            color: #ffffff;
        }}

        .search-input {{
            width: 100%;
            background: #131d31;
            border: 1px solid var(--border-highlight);
            color: var(--text-primary);
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 11px;
            outline: none;
        }}

        .search-input:focus {{
            border-color: var(--brand-accent);
        }}

        .filter-grid {{
            display: grid;
            grid-template-columns: 1.15fr 1fr 1fr;
            gap: 6px;
        }}

        .filter-dropdown {{
            background: #131d31;
            border: 1px solid var(--border-highlight);
            color: var(--text-primary);
            padding: 6px 8px;
            border-radius: 4px;
            font-size: 11px;
            outline: none;
            cursor: pointer;
        }}

        .toggle-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 2px;
        }}

        /* Event Feed List */
        .feed-container {{
            flex: 1;
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .event-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 10px 12px;
            cursor: pointer;
            transition: transform 0.1s ease, border-color 0.15s ease;
            position: relative;
        }}

        .event-card:hover {{
            border-color: var(--brand-accent);
            transform: translateY(-1px);
            background: #243248;
        }}

        .card-top {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 6px;
            margin-bottom: 4px;
        }}

        .tag {{
            font-size: 9px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 3px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}

        .tag-ncs {{
            background: rgba(251, 146, 60, 0.15);
            color: #fb923c;
            border: 1px solid rgba(251, 146, 60, 0.3);
        }}

        .tag-gnews {{
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }}

        .tag-india {{
            background: rgba(74, 222, 128, 0.15);
            color: #4ade80;
            border: 1px solid rgba(74, 222, 128, 0.3);
        }}

        .tag-border {{
            background: rgba(250, 204, 21, 0.15);
            color: #facc15;
            border: 1px solid rgba(250, 204, 21, 0.3);
        }}

        .mag-pill {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 800;
            font-size: 11px;
            padding: 1px 6px;
            border-radius: 3px;
            color: #ffffff;
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
            justify-content: space-between;
            align-items: center;
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 10px;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }}

        /* Map */
        #map {{
            width: 100%;
            height: 100%;
            background: #090d16;
        }}

        /* Popups */
        .leaflet-popup-content-wrapper {{
            background: #0f172a !important;
            border: 1px solid var(--border-highlight) !important;
            border-radius: 6px !important;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.6) !important;
            color: #ffffff !important;
            padding: 0 !important;
        }}

        .leaflet-popup-content {{
            margin: 0 !important;
            line-height: 1.4 !important;
        }}

        .leaflet-popup-tip {{
            background: #0f172a !important;
        }}

        .popup-container {{
            padding: 12px 14px;
            font-size: 12px;
            min-width: 240px;
        }}

        .popup-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 3px;
            font-size: 11px;
            color: var(--text-secondary);
        }}

        .popup-link {{
            display: inline-block;
            margin-top: 8px;
            color: var(--brand-accent);
            text-decoration: none;
            font-weight: 600;
            font-size: 11px;
        }}

        .popup-link:hover {{
            text-decoration: underline;
        }}

        /* Modal */
        .modal-bg {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.7);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 2000;
        }}

        .modal-bg.open {{
            display: flex;
        }}

        .modal-box {{
            background: var(--bg-surface);
            border: 1px solid var(--border-highlight);
            border-radius: 8px;
            width: 580px;
            max-width: 90vw;
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
                <div class="brand-subtitle">Multi-Source Hazard Ingestion: NCS RISEQ, NDMA SACHET & GNews AI</div>
            </div>
        </div>

        <div class="header-kpi">
            <div class="kpi-item">
                <span>NCS Quakes (30d):</span>
                <span class="kpi-num" style="color: #fb923c;" id="stat-eq">{total_eq_count}</span>
            </div>
            <span style="color: var(--border)">|</span>
            <div class="kpi-item">
                <span>News Incidents:</span>
                <span class="kpi-num" style="color: #38bdf8;" id="stat-news">{total_news_count}</span>
            </div>
            <span style="color: var(--border)">|</span>
            <div class="kpi-item">
                <span>NDMA Alerts:</span>
                <span class="kpi-num" style="color: #c084fc;" id="stat-sachet">{total_sachet_count}</span>
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
                    <button class="source-tab" id="tab-ncs" onclick="filterBySource('NCS_RISEQ')">NCS Quakes</button>
                    <button class="source-tab" id="tab-news" onclick="filterBySource('GNEWS')">News Disasters</button>
                    <button class="source-tab" id="tab-sachet" onclick="filterBySource('NDMA_SACHET')">NDMA SACHET</button>
                </div>

                <!-- Search -->
                <input type="text" id="searchInput" class="search-input" placeholder="Search state, district, region..." />

                <!-- Multi-criteria Dropdowns -->
                <div class="filter-grid">
                    <select id="timeFilter" class="filter-dropdown">
                        <option value="ALL">🕒 All Times (30d)</option>
                        <option value="24h">Last 24 Hours</option>
                        <option value="48h">Last 48 Hours</option>
                        <option value="7d">Last 7 Days</option>
                        <option value="14d">Last 14 Days</option>
                    </select>

                    <select id="relFilter" class="filter-dropdown">
                        <option value="ALL">All Regions</option>
                        <option value="INDIA">India Territory</option>
                        <option value="INDIA_BORDER">Border Zone</option>
                        <option value="REGIONAL">Regional</option>
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
                        <span>Cluster Markers</span>
                    </label>
                    <span id="filteredCount" style="font-family: 'JetBrains Mono'; font-size: 11px; color: #38bdf8;">{total_events_count} events</span>
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 14px; border-bottom: 1px solid var(--border); font-size: 11px; background: #0c1424;">
                <span style="font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8;">Incident Feed</span>
                <span style="color: #38bdf8; font-family: 'JetBrains Mono'; font-size: 10px; font-weight: 600;">⚡ Newest First</span>
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

        function getEventTimeEpoch(ev) {{
            if (ev.unified_timestamp != null && !isNaN(ev.unified_timestamp) && Number(ev.unified_timestamp) > 0) {{
                return Number(ev.unified_timestamp) * 1000;
            }}
            if (ev.origin_timestamp != null && !isNaN(ev.origin_timestamp) && Number(ev.origin_timestamp) > 0) {{
                return Number(ev.origin_timestamp) * 1000;
            }}
            if (ev.event_timestamp != null && !isNaN(ev.event_timestamp) && Number(ev.event_timestamp) > 0) {{
                return Number(ev.event_timestamp) * 1000;
            }}
            const tStr = ev.unified_time || ev.event_time || ev.effective_at || ev.origin_time || ev.incident_date || ev.published_at || ev.created_at || '';
            if (!tStr) return 0;
            const parsed = Date.parse(tStr);
            return isNaN(parsed) ? 0 : parsed;
        }}

        function formatIST12Hour(epochMs, fallbackStr) {{
            if (!epochMs || epochMs <= 0) {{
                if (!fallbackStr) return '--';
                const parsed = Date.parse(fallbackStr);
                if (isNaN(parsed)) return fallbackStr.substring(0, 16);
                epochMs = parsed;
            }}
            const d = new Date(epochMs);
            try {{
                const parts = new Intl.DateTimeFormat('en-IN', {{
                    timeZone: 'Asia/Kolkata',
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: true
                }}).formatToParts(d);

                let day = '', month = '', year = '', hour = '', minute = '', dayPeriod = '';
                parts.forEach(p => {{
                    if (p.type === 'day') day = p.value;
                    else if (p.type === 'month') month = p.value;
                    else if (p.type === 'year') year = p.value;
                    else if (p.type === 'hour') hour = p.value;
                    else if (p.type === 'minute') minute = p.value;
                    else if (p.type === 'dayPeriod') dayPeriod = p.value.toUpperCase();
                }});
                return `${{day}} ${{month}} ${{year}}, ${{hour}}:${{minute}} ${{dayPeriod}} IST`;
            }} catch(e) {{
                return d.toLocaleString('en-IN', {{ timeZone: 'Asia/Kolkata', hour12: true }}) + ' IST';
            }}
        }}

        function formatISTCardTime(epochMs, fallbackStr) {{
            if (!epochMs || epochMs <= 0) {{
                if (!fallbackStr) return '--';
                const parsed = Date.parse(fallbackStr);
                if (isNaN(parsed)) return fallbackStr.substring(0, 16);
                epochMs = parsed;
            }}
            const d = new Date(epochMs);
            try {{
                const parts = new Intl.DateTimeFormat('en-IN', {{
                    timeZone: 'Asia/Kolkata',
                    day: '2-digit',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: true
                }}).formatToParts(d);

                let day = '', month = '', hour = '', minute = '', dayPeriod = '';
                parts.forEach(p => {{
                    if (p.type === 'day') day = p.value;
                    else if (p.type === 'month') month = p.value;
                    else if (p.type === 'hour') hour = p.value;
                    else if (p.type === 'minute') minute = p.value;
                    else if (p.type === 'dayPeriod') dayPeriod = p.value.toUpperCase();
                }});
                return `${{day}} ${{month}}, ${{hour}}:${{minute}} ${{dayPeriod}} IST`;
            }} catch(e) {{
                return d.toLocaleTimeString('en-IN', {{ timeZone: 'Asia/Kolkata', hour12: true }}) + ' IST';
            }}
        }}

        function formatTimeAgo(epochMs, fallbackStr) {{
            if (!epochMs || epochMs <= 0) return fallbackStr ? fallbackStr.substring(0, 16) : '--';
            const diffSec = Math.floor((Date.now() - epochMs) / 1000);
            if (diffSec < 0) return 'Just now';
            if (diffSec < 60) return `${{diffSec}}s ago`;
            const diffMin = Math.floor(diffSec / 60);
            if (diffMin < 60) return `${{diffMin}}m ago`;
            const diffHr = Math.floor(diffMin / 60);
            if (diffHr < 24) return `${{diffHr}}h ago`;
            const diffDays = Math.floor(diffHr / 24);
            if (diffDays === 1) return '1d ago';
            if (diffDays <= 30) return `${{diffDays}}d ago`;
            return fallbackStr ? fallbackStr.substring(0, 10) : `${{diffDays}}d ago`;
        }}

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
        }});

        const plainGroup = L.layerGroup();
        map.addLayer(clusterGroup);

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
                const evEpochMs = getEventTimeEpoch(ev);

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
                            <div class="popup-row"><span>Time (IST):</span> <strong style="color: #ffffff;">${{formatIST12Hour(evEpochMs, ev.origin_time)}}</strong></div>

                            ${{ev.felt_report_url ? `<a href="${{ev.felt_report_url}}" target="_blank" class="popup-link">NCS Felt Report &rarr;</a>` : ''}}
                        </div>
                    `;

                    marker.bindPopup(popup);

                    if (useClustering) clusterGroup.addLayer(marker);
                    else plainGroup.addLayer(marker);

                    markersMap.set(ev.event_id || ev.article_id, marker);

                }} else if (ev.source_group === 'NDMA_SACHET') {{
                    const sev = (ev.severity || 'Unknown').toLowerCase();
                    const dType = ev.disaster_type || 'Alert';
                    const sevClass = 'sev-' + sev;
                    
                    const customIcon = L.divIcon({{
                        className: 'sachet-pin',
                        html: `<div style="width: 16px; height: 16px; border-radius: 50%; background: #a855f7; border: 2px solid #ffffff; box-shadow: 0 2px 5px rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; font-size: 9px; color: #ffffff; font-weight: 800;">!</div>`,
                        iconSize: [16, 16],
                        iconAnchor: [8, 8]
                    }});

                    const marker = L.marker([lat, lon], {{ icon: customIcon }});

                    const popup = `
                        <div class="popup-container">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span class="tag tag-sachet">NDMA SACHET</span>
                                <span class="tag ${{sevClass}}">${{ev.severity || 'Alert'}}</span>
                            </div>
                            <div style="font-size: 13px; font-weight: 700; color: #ffffff; margin-bottom: 4px;">${{ev.headline || ev.title || 'Government Alert'}}</div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">📍 ${{ev.area_description || ev.location?.state || 'India'}}</div>
                            <div class="popup-row"><span>Hazard / Event:</span> <strong style="color: #c084fc;">${{ev.event || dType}}</strong></div>
                            <div class="popup-row"><span>Urgency / Certainty:</span> <strong style="color: #ffffff;">${{ev.urgency || 'Expected'}} / ${{ev.certainty || 'Likely'}}</strong></div>
                            <div class="popup-row"><span>Effective (IST):</span> <strong style="color: #ffffff;">${{formatIST12Hour(evEpochMs, ev.effective_at || ev.sent_at)}}</strong></div>
                            ${{ev.instruction ? `<div style="margin-top: 6px; font-size: 11px; color: #94a3b8; background: #131d31; padding: 6px; border-radius: 4px;">⚠️ ${{ev.instruction}}</div>` : ''}}
                            ${{ev.link ? `<a href="${{ev.link}}" target="_blank" class="popup-link">CAP Alert XML &rarr;</a>` : ''}}
                        </div>
                    `;

                    marker.bindPopup(popup);

                    if (useClustering) clusterGroup.addLayer(marker);
                    else plainGroup.addLayer(marker);

                    markersMap.set(ev.event_id || ev.alert_id, marker);

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
                            <div class="popup-row"><span>Reported (IST):</span> <strong style="color: #ffffff;">${{formatIST12Hour(evEpochMs, ev.incident_date || ev.published_at)}}</strong></div>
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

        // Render Feed strictly recent-first
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
                const isSachet = ev.source_group === 'NDMA_SACHET';
                const card = document.createElement('div');
                card.className = 'event-card';

                const mag = ev.magnitude;
                const magColor = mag != null ? getMagColor(mag) : '#0284c7';
                
                let sourceTag = 'GNews AI';
                let tagClass = 'tag-gnews';
                if (isEq) {{ sourceTag = 'NCS RISEQ'; tagClass = 'tag-ncs'; }}
                else if (isSachet) {{ sourceTag = 'NDMA SACHET'; tagClass = 'tag-sachet'; }}

                const title = isEq ? (ev.region || 'Seismic Incident') : (ev.headline || ev.title || 'Disaster Alert');
                const loc = isEq ? (ev.location_desc || ev.region) : (ev.area_description || [ev.location?.city, ev.location?.state].filter(Boolean).join(', '));
                
                const evEpochMs = getEventTimeEpoch(ev);
                const istCardTime = formatISTCardTime(evEpochMs, ev.unified_time);
                const timeAgo = formatTimeAgo(evEpochMs, istCardTime);

                let badgeHtml = '<span class="tag tag-gnews">NEWS</span>';
                if (isEq) {{
                    badgeHtml = `<span class="mag-pill" style="background: ${{magColor}};">M ${{mag.toFixed(1)}}</span>`;
                }} else if (isSachet) {{
                    const sev = (ev.severity || 'Alert').toLowerCase();
                    badgeHtml = `<span class="tag sev-${{sev}}">${{ev.severity || 'ALERT'}}</span>`;
                }}

                card.innerHTML = `
                    <div class="card-top">
                        <span class="tag ${{tagClass}}">${{sourceTag}}</span>
                        ${{ev.relevance ? `<span class="tag ${{ev.relevance === 'INDIA' ? 'tag-india' : 'tag-border'}}">${{ev.relevance}}</span>` : ''}}
                        <span style="font-size: 10px; color: #38bdf8; font-family: 'JetBrains Mono'; background: rgba(56, 189, 248, 0.12); padding: 1px 5px; border-radius: 3px;">${{timeAgo}}</span>
                        <span style="font-size: 10px; color: var(--text-muted); font-family: 'JetBrains Mono'; margin-left: auto;">${{istCardTime}}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
                        ${{badgeHtml}}
                        <div style="font-weight: 700; font-size: 12px; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1;">
                            ${{title}}
                        </div>
                    </div>
                    <div class="card-location" style="margin-top: 2px;">📍 ${{loc || 'India'}}</div>
                    ${{isEq ? `<div class="card-footer"><span>Depth: ${{ev.depth_km}} km</span><span>Status: ${{ev.status || 'Reviewed'}}</span></div>` : ''}}
                    ${{isSachet ? `<div class="card-footer"><span>Agency: ${{ev.sender || 'NDMA'}}</span><span>Certainty: ${{ev.certainty || 'Likely'}}</span></div>` : ''}}
                `;

                card.onclick = () => {{
                    const lat = ev.latitude || ev.location?.latitude;
                    const lon = ev.longitude || ev.location?.longitude;
                    if (lat && lon) {{
                        map.flyTo([lat, lon], 8, {{ duration: 1.0 }});
                        const m = markersMap.get(ev.event_id || ev.alert_id || ev.article_id);
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
            document.getElementById('tab-sachet').className = 'source-tab ' + (src === 'NDMA_SACHET' ? 'active' : '');
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
            const timeVal = document.getElementById('timeFilter').value;

            const nowMs = Date.now();
            let maxAgeMs = Infinity;
            if (timeVal === '24h') maxAgeMs = 24 * 60 * 60 * 1000;
            else if (timeVal === '48h') maxAgeMs = 48 * 60 * 60 * 1000;
            else if (timeVal === '7d') maxAgeMs = 7 * 24 * 60 * 60 * 1000;
            else if (timeVal === '14d') maxAgeMs = 14 * 24 * 60 * 60 * 1000;

            const filtered = rawEvents.filter(ev => {{
                // 1. Time Filter
                const evEpochMs = getEventTimeEpoch(ev);
                if (maxAgeMs !== Infinity && evEpochMs > 0) {{
                    if (nowMs - evEpochMs > maxAgeMs) return false;
                }}

                // 2. Source Filter
                if (activeSource !== 'ALL' && ev.source_group !== activeSource) return false;

                // 3. Region Filter
                if (rel !== 'ALL' && ev.relevance !== rel) return false;

                // 4. Magnitude Filter
                if (mag !== 'ALL') {{
                    const minMag = parseFloat(mag);
                    if ((ev.magnitude || 0) < minMag) return false;
                }}

                // 5. Search text filter
                if (search) {{
                    const title = (ev.title || ev.headline || ev.region || '').toLowerCase();
                    const loc = (ev.area_description || ev.location_desc || ev.location?.state || ev.location?.city || '').toLowerCase();
                    if (!title.includes(search) && !loc.includes(search)) return false;
                }}
                return true;
            }});

            // CRITICAL: SORT STRICTLY RECENT-FIRST (NEWEST TO OLDEST) IRRESPECTIVE OF SOURCE OR EVENT TYPE
            filtered.sort((a, b) => getEventTimeEpoch(b) - getEventTimeEpoch(a));

            renderMarkers(filtered);
            renderFeed(filtered);
        }}

        document.getElementById('searchInput').addEventListener('input', applyAllFilters);
        document.getElementById('relFilter').addEventListener('change', applyAllFilters);
        document.getElementById('magFilter').addEventListener('change', applyAllFilters);
        document.getElementById('timeFilter').addEventListener('change', applyAllFilters);

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
                        <div style="font-size: 22px; font-weight: 700; color: #f87171; font-family: 'JetBrains Mono';">M ${{maxMag > 0 ? maxMag.toFixed(1) : '--'}}</div>
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
    events, total_eq, total_news, total_sachet = fetch_and_prepare_events()
    print(f"[DISHA MAP] Retrieved {total_eq} NCS Earthquakes, {total_news} News Disasters, {total_sachet} NDMA SACHET Alerts ({len(events)} total geocoded).")

    output_path = Path(__file__).resolve().parent / "temp_disaster_map.html"
    html_content = build_map_html(events, total_eq, total_news, total_sachet)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[DISHA MAP] Successfully generated interactive UI map: {output_path}")

    if open_browser:
        webbrowser.open(f"file://{output_path.resolve()}")

    return str(output_path)


if __name__ == "__main__":
    generate_map(open_browser=False)
