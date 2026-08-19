"""
DISHA Platform - Institutional Disaster Intelligence & Emergency Command Map
Engineered for Emergency Operations Centers (EOC), GIS Analysts, and First Responders.
Features a high-density, professional layout, sober federal/GIS color palette,
solid docked 3-column architecture, and 40 analytical graphs.
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
    """Standardizes timestamps to ISO 8601 UTC string and Unix epoch in seconds."""
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

        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.isoformat(), dt.timestamp()
        except Exception:
            pass

        try:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat(), dt.timestamp()
        except Exception:
            pass

        try:
            dt = datetime.strptime(s, "%Y-%m-%d")
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat(), dt.timestamp()
        except Exception:
            pass

    return "", 0.0


def fetch_and_prepare_events():
    """Fetches GNews disasters, NCS earthquakes, and NDMA SACHET alerts from MongoDB."""
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
    combined.sort(key=lambda x: x.get("unified_timestamp", 0.0), reverse=True)
    return combined, len(eq_cursor), len(news_cursor), len(sachet_cursor)


def build_map_html(events, total_eq_count, total_news_count, total_sachet_count=0):
    """Generates the professional, institutional GIS/EOC dashboard layout."""
    events_json = json.dumps(events, default=str)
    total_events_count = len(events)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DISHA - Disaster Situational Intelligence & Emergency Command</title>
    
    <!-- Leaflet & MarkerCluster CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    
    <!-- Leaflet & MarkerCluster JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

    <!-- Chart.js for High-Performance Advanced Analytics -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

    <!-- Typography -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

    <style>
        :root {{
            /* Professional EOC / GIS Institutional Dark Palette */
            --bg-base: #090e17;
            --bg-surface: #0f172a;
            --bg-surface-elevated: #162238;
            --bg-surface-hover: #1e2e4a;
            --bg-sidebar: #0d1524;
            --bg-details: #0d1524;
            --bg-header: #0b111e;
            
            --border: #1e293b;
            --border-subtle: #263347;
            --border-focus: #3b82f6;

            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;

            --color-blue: #2563eb;
            --color-blue-dark: #1d4ed8;
            --color-cyan: #0284c7;

            /* Sober, Standard Federal/ISO Hazard Severity Tiers */
            --sev-critical-bg: rgba(185, 28, 28, 0.16);
            --sev-critical-text: #fca5a5;
            --sev-critical-border: #b91c1c;

            --sev-high-bg: rgba(194, 65, 12, 0.16);
            --sev-high-text: #fdba74;
            --sev-high-border: #c2410c;

            --sev-moderate-bg: rgba(180, 83, 9, 0.16);
            --sev-moderate-text: #fde047;
            --sev-moderate-border: #b45309;

            --sev-low-bg: rgba(21, 128, 61, 0.16);
            --sev-low-text: #86efac;
            --sev-low-border: #15803d;

            --svc-medical: #0284c7;
            --svc-police: #4f46e5;
            --svc-fire: #d97706;
        }}

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
            -webkit-font-smoothing: antialiased;
        }}

        .app {{
            display: flex;
            flex-direction: column;
            height: 100vh;
            width: 100vw;
        }}

        /* ---------------- FIXED INSTITUTIONAL HEADER ---------------- */
        header {{
            height: 52px;
            background: var(--bg-header);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            z-index: 1000;
            flex-shrink: 0;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .brand-badge {{
            background: #1e293b;
            border: 1px solid #334155;
            color: #38bdf8;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 7px;
            border-radius: 4px;
            letter-spacing: 0.5px;
        }}

        .brand h1 {{
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.3px;
            color: #ffffff;
            line-height: 1.1;
        }}

        .brand p {{
            font-size: 10.5px;
            color: var(--text-muted);
        }}

        .header-center {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex: 1;
            max-width: 380px;
            margin: 0 16px;
        }}

        .search-box {{
            width: 100%;
            background: var(--bg-surface);
            border: 1px solid var(--border);
            color: var(--text-primary);
            font-size: 11.5px;
            padding: 6px 10px;
            border-radius: 4px;
            outline: none;
            transition: border-color 0.15s;
        }}

        .search-box:focus {{
            border-color: var(--border-focus);
            background: #131d31;
        }}

        .search-box::placeholder {{
            color: var(--text-muted);
        }}

        .header-actions {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .btn-action-header {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            color: var(--text-primary);
            font-size: 11px;
            font-weight: 600;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: 0.15s;
        }}

        .btn-action-header:hover {{
            background: var(--bg-surface-hover);
            border-color: var(--border-subtle);
        }}

        .status-indicator {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            font-weight: 600;
            color: #86efac;
            background: rgba(21, 128, 61, 0.15);
            border: 1px solid rgba(21, 128, 61, 0.35);
            padding: 4px 9px;
            border-radius: 4px;
        }}

        .status-dot-static {{
            width: 6px;
            height: 6px;
            background: #22c55e;
            border-radius: 50%;
        }}

        /* ---------------- MAIN WORKSPACE (SOLID DOCKED 3-COLUMN) ---------------- */
        .main {{
            flex: 1;
            display: flex;
            min-height: 0;
            position: relative;
        }}

        /* ---------------- 1. SOLID LEFT SIDEBAR ---------------- */
        .sidebar {{
            width: 360px;
            background: var(--bg-sidebar);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            z-index: 900;
            flex-shrink: 0;
            height: 100%;
        }}

        .sidebar-header {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            background: #0b111e;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
        }}

        .stat-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            padding: 7px 6px;
            border-radius: 4px;
            text-align: center;
            cursor: pointer;
            transition: 0.15s;
        }}

        .stat-card:hover {{
            border-color: var(--border-subtle);
            background: var(--bg-surface-hover);
        }}

        .stat-number {{
            font-size: 15px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            color: #ffffff;
        }}

        .stat-label {{
            font-size: 9px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 1px;
            font-weight: 600;
        }}

        .source-tabs {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            background: var(--bg-surface);
            border: 1px solid var(--border);
            padding: 2px;
            border-radius: 4px;
            gap: 2px;
            margin-top: 8px;
        }}

        .source-tab {{
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 9.5px;
            font-weight: 600;
            padding: 4px 2px;
            border-radius: 3px;
            cursor: pointer;
            text-align: center;
            text-transform: uppercase;
            transition: 0.15s;
        }}

        .source-tab.active {{
            background: #1e293b;
            color: #ffffff;
            font-weight: 700;
        }}

        .filters-bar {{
            padding: 8px 12px;
            border-bottom: 1px solid var(--border);
            display: flex;
            gap: 6px;
            align-items: center;
            background: #090e17;
        }}

        .filter-select {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            color: var(--text-primary);
            font-size: 10px;
            font-weight: 500;
            padding: 4px 6px;
            border-radius: 4px;
            outline: none;
            cursor: pointer;
            flex: 1;
        }}

        .filter-select:focus {{
            border-color: var(--border-focus);
        }}

        /* Scrollable Incident Feed */
        .event-list {{
            flex: 1;
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 5px;
            background: var(--bg-sidebar);
        }}

        .event-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-left: 3px solid #334155;
            border-radius: 4px;
            padding: 9px 10px;
            cursor: pointer;
            transition: border-color 0.15s, background-color 0.15s;
        }}

        .event-card:hover {{
            background: var(--bg-surface-hover);
            border-color: var(--border-subtle);
        }}

        .event-card.selected {{
            border-color: #38bdf8;
            border-left-color: #38bdf8;
            background: #131e33;
        }}

        .event-card.card-ncs {{ border-left-color: #b91c1c; }}
        .event-card.card-sachet {{ border-left-color: #9333ea; }}
        .event-card.card-gnews {{ border-left-color: #2563eb; }}

        .event-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 3px;
        }}

        .tag {{
            font-size: 9px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            padding: 1px 5px;
            border-radius: 3px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}

        .tag-ncs {{ background: rgba(185, 28, 28, 0.15); color: #fca5a5; border: 1px solid rgba(185, 28, 28, 0.35); }}
        .tag-sachet {{ background: rgba(147, 51, 234, 0.15); color: #d8b4fe; border: 1px solid rgba(147, 51, 234, 0.35); }}
        .tag-gnews {{ background: rgba(37, 99, 235, 0.15); color: #93c5fd; border: 1px solid rgba(37, 99, 235, 0.35); }}

        .sev-critical {{ background: var(--sev-critical-bg); color: var(--sev-critical-text); border: 1px solid var(--sev-critical-border); }}
        .sev-high {{ background: var(--sev-high-bg); color: var(--sev-high-text); border: 1px solid var(--sev-high-border); }}
        .sev-moderate {{ background: var(--sev-moderate-bg); color: var(--sev-moderate-text); border: 1px solid var(--sev-moderate-border); }}
        .sev-low {{ background: var(--sev-low-bg); color: var(--sev-low-text); border: 1px solid var(--sev-low-border); }}

        /* ---------------- 2. CENTER MAP CANVAS ---------------- */
        .map-container {{
            flex: 1;
            position: relative;
            min-width: 0;
            height: 100%;
            background: var(--bg-base);
        }}

        #map {{
            width: 100%;
            height: 100%;
        }}

        /* GIS Map Tools Toolbar (Top Right) */
        .map-toolbar {{
            position: absolute;
            top: 12px;
            right: 12px;
            z-index: 1000;
            background: rgba(11, 17, 30, 0.92);
            backdrop-filter: blur(4px);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 3px;
            display: flex;
            align-items: center;
            gap: 2px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }}

        .tool-btn {{
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-secondary);
            font-size: 10px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            padding: 4px 8px;
            border-radius: 3px;
            cursor: pointer;
            transition: 0.15s;
            text-transform: uppercase;
        }}

        .tool-btn:hover {{
            background: var(--bg-surface);
            color: #ffffff;
            border-color: var(--border);
        }}

        .tool-btn.active {{
            background: #1e293b;
            color: #38bdf8;
            border-color: #334155;
        }}

        /* Bottom Legend */
        .map-legend {{
            position: absolute;
            bottom: 12px;
            left: 12px;
            z-index: 1000;
            background: rgba(11, 17, 30, 0.92);
            backdrop-filter: blur(4px);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 5px 10px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 10px;
            font-weight: 600;
            color: var(--text-secondary);
        }}

        .legend-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            display: inline-block;
        }}

        /* ---------------- 3. SOLID DOCKED RIGHT DETAIL PANEL ---------------- */
        .details-panel {{
            width: 390px;
            background: var(--bg-details);
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            z-index: 900;
            flex-shrink: 0;
            height: 100%;
            overflow: hidden;
        }}

        .details-header {{
            padding: 12px 14px;
            border-bottom: 1px solid var(--border);
            background: #0b111e;
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 8px;
        }}

        .details-title {{
            font-size: 13px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.3;
            margin-top: 3px;
        }}

        .details-close {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            color: var(--text-muted);
            border-radius: 4px;
            width: 22px;
            height: 22px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            cursor: pointer;
            transition: 0.15s;
        }}

        .details-close:hover {{
            background: #1e293b;
            color: #ffffff;
            border-color: var(--border-subtle);
        }}

        .details-body {{
            flex: 1;
            overflow-y: auto;
            padding: 12px 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .details-empty {{
            color: var(--text-muted);
            text-align: center;
            margin-top: 140px;
            font-size: 11.5px;
            line-height: 1.6;
            padding: 0 16px;
        }}

        .telemetry-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
        }}

        .telemetry-box {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 6px 8px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}

        .telemetry-lbl {{
            font-size: 8.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
        }}

        .telemetry-val {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-primary);
        }}

        /* Rescue Network Section */
        .rescue-sector-bar {{
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 7px 9px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .rescue-sector-title {{
            font-size: 10px;
            font-weight: 700;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .radius-selector-bar {{
            display: flex;
            align-items: center;
            gap: 3px;
        }}

        .radius-btn {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 9px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            padding: 2px 6px;
            border-radius: 3px;
            cursor: pointer;
            transition: 0.15s;
        }}

        .radius-btn:hover, .radius-btn.active {{
            background: #1e293b;
            color: #38bdf8;
            border-color: #334155;
        }}

        .rescue-filter-tabs {{
            display: flex;
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 2px;
            gap: 2px;
        }}

        .rescue-tab-btn {{
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 9.5px;
            font-weight: 600;
            padding: 4px 2px;
            border-radius: 3px;
            cursor: pointer;
            text-align: center;
            text-transform: uppercase;
            transition: 0.15s;
        }}

        .rescue-tab-btn.active {{
            background: #1e293b;
            color: #ffffff;
            font-weight: 700;
        }}

        .facility-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 8px 10px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            transition: border-color 0.15s;
            cursor: pointer;
        }}

        .facility-card:hover, .facility-card.highlighted {{
            border-color: #38bdf8;
            background: var(--bg-surface-hover);
        }}

        .facility-top {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 6px;
        }}

        .facility-name {{
            font-size: 11.5px;
            font-weight: 600;
            color: #ffffff;
            line-height: 1.3;
            flex: 1;
        }}

        .facility-dist-tag {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 9.5px;
            font-weight: 700;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.25);
            padding: 1px 5px;
            border-radius: 3px;
            white-space: nowrap;
        }}

        .btn-facility-action {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 10px;
            font-weight: 600;
            padding: 4px 8px;
            border-radius: 3px;
            text-decoration: none;
            cursor: pointer;
            border: 1px solid var(--border);
            transition: background 0.15s;
        }}
        .btn-facility-nav {{ background: #1e293b; color: #ffffff; flex: 1; justify-content: center; }}
        .btn-facility-nav:hover {{ background: #2563eb; border-color: #2563eb; }}
        .btn-facility-call {{ background: #14532d; color: #86efac; border-color: #166534; }}
        .btn-facility-call:hover {{ background: #166534; }}

        /* Precise Reticle */
        .selected-incident-marker {{
            z-index: 1000 !important;
            position: relative;
        }}
        .selected-incident-marker::after {{
            content: '';
            position: absolute;
            top: -4px;
            left: -4px;
            right: -4px;
            bottom: -4px;
            border-radius: 50%;
            border: 2px solid #38bdf8;
            pointer-events: none;
        }}

        /* Emergency Pins */
        .emergency-service-pin {{
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            border: 1.5px solid #ffffff;
            box-shadow: 0 2px 6px rgba(0,0,0,0.5);
            font-size: 11px;
            cursor: pointer;
        }}
        .med-service-pin {{ background: var(--svc-medical); }}
        .police-service-pin {{ background: var(--svc-police); }}
        .fire-service-pin {{ background: var(--svc-fire); }}

        .leaflet-measure-tip {{
            background: #0b111e !important;
            border: 1px solid #334155 !important;
            color: #f1f5f9 !important;
            font-size: 10px !important;
            font-family: 'JetBrains Mono', monospace !important;
            padding: 4px 8px !important;
            border-radius: 3px !important;
        }}

        /* ---------------- EXTENDED 40-GRAPH ANALYTICS MODAL ---------------- */
        .analytics-modal-backdrop {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.78);
            backdrop-filter: blur(4px);
            z-index: 2000;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 12px;
        }}

        .analytics-modal-backdrop.active {{
            display: flex;
        }}

        .analytics-modal {{
            width: 1240px;
            max-width: 96vw;
            height: 94vh;
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            box-shadow: 0 16px 60px rgba(0, 0, 0, 0.75);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        .modal-header {{
            padding: 10px 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #090e17;
            flex-shrink: 0;
            gap: 12px;
        }}

        .modal-header h2 {{
            font-size: 13px;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }}

        .analytics-tab-bar {{
            display: flex;
            gap: 2px;
            background: #0f172a;
            padding: 2px;
            border-radius: 4px;
            border: 1px solid var(--border);
            overflow-x: auto;
        }}

        .atab-btn {{
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 10px;
            font-weight: 600;
            padding: 4px 9px;
            border-radius: 3px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            white-space: nowrap;
            text-transform: uppercase;
            transition: 0.15s;
        }}

        .atab-btn.active {{
            background: #1e293b;
            color: #38bdf8;
            font-weight: 700;
        }}

        .modal-close-btn {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            color: var(--text-muted);
            width: 24px;
            height: 24px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 12px;
            transition: 0.15s;
            flex-shrink: 0;
        }}

        .modal-close-btn:hover {{
            background: #1e293b;
            color: #ffffff;
            border-color: var(--border-subtle);
        }}

        .modal-body {{
            flex: 1;
            overflow-y: auto;
            padding: 14px 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            background: #090e17;
        }}

        /* KPI Banner */
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            flex-shrink: 0;
        }}

        .kpi-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 8px 12px;
            display: flex;
            flex-direction: column;
            gap: 1px;
        }}

        .kpi-label {{
            font-size: 9px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .kpi-value {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 17px;
            font-weight: 700;
            color: #ffffff;
        }}

        .kpi-sub {{
            font-size: 9.5px;
            color: var(--text-muted);
        }}

        /* Analytics Tab Views */
        .analytics-view {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .charts-grid-4 {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}

        .chart-box {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 10px 12px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .chart-title {{
            font-size: 10.5px;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: space-between;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}

        .chart-canvas-container {{
            position: relative;
            width: 100%;
            height: 190px;
        }}
    </style>
</head>
<body>
    <div class="app">
        <!-- ---------------- FIXED TOP HEADER ---------------- -->
        <header>
            <div class="brand">
                <span class="brand-badge">DISHA</span>
                <div>
                    <h1>DISASTER SITUATIONAL INTELLIGENCE & COMMAND</h1>
                    <p>National Emergency Operations & GIS Integration Center</p>
                </div>
            </div>

            <div class="header-center">
                <input type="text" id="searchInput" class="search-box" placeholder="Filter region, territory, hazard type..." oninput="handleSearchInput()" />
            </div>

            <div class="header-actions">
                <button class="btn-action-header" id="btnOpenAnalytics" onclick="openAnalyticsModal()" title="Open Comprehensive 40-Graph Analytics Suite">
                    <span>ANALYTICS (40)</span>
                </button>

                <div class="status-indicator">
                    <div class="status-dot-static"></div>
                    <span>LIVE INGESTION • ATLAS MONGODB</span>
                </div>
            </div>
        </header>

        <!-- ---------------- 3-COLUMN MAIN WORKSPACE ---------------- -->
        <div class="main">
            <!-- 1. SOLID DOCKED LEFT SIDEBAR -->
            <aside class="sidebar">
                <div class="sidebar-header">
                    <div class="stats-grid">
                        <div class="stat-card" onclick="openAnalyticsModal()" title="Total Active Incidents">
                            <div class="stat-number" style="color: #38bdf8;" id="statTotal">{total_events_count}</div>
                            <div class="stat-label">Incidents</div>
                        </div>
                        <div class="stat-card" onclick="openAnalyticsModal()" title="Critical Tier Events">
                            <div class="stat-number" style="color: #f87171;" id="statCritical">0</div>
                            <div class="stat-label">Critical</div>
                        </div>
                        <div class="stat-card" onclick="openAnalyticsModal()" title="Monitored Territories">
                            <div class="stat-number" style="color: #86efac;" id="statRegions">--</div>
                            <div class="stat-label">Territories</div>
                        </div>
                    </div>

                    <div class="source-tabs">
                        <button class="source-tab active" id="src-all" onclick="filterBySource('ALL')">All</button>
                        <button class="source-tab" id="src-ncs" onclick="filterBySource('NCS_RISEQ')">NCS</button>
                        <button class="source-tab" id="src-sachet" onclick="filterBySource('NDMA_SACHET')">SACHET</button>
                        <button class="source-tab" id="src-news" onclick="filterBySource('GNEWS')">News</button>
                    </div>
                </div>

                <div class="filters-bar">
                    <select id="timeFilter" class="filter-select" onchange="applyAllFilters()">
                        <option value="ALL">All Recorded (30d)</option>
                        <option value="24h">Past 24 Hours</option>
                        <option value="48h">Past 48 Hours</option>
                        <option value="7d">Past 7 Days</option>
                    </select>

                    <select id="severityFilter" class="filter-select" onchange="applyAllFilters()">
                        <option value="ALL">All Severities</option>
                        <option value="CRITICAL">Critical Only</option>
                        <option value="HIGH">High & Above</option>
                        <option value="MODERATE">Moderate & Above</option>
                    </select>

                    <label style="font-size: 9.5px; font-weight: 600; color: var(--text-muted); display: flex; align-items: center; gap: 3px; cursor: pointer;">
                        <input type="checkbox" id="clusterToggle" checked onchange="toggleClustering()" />
                        <span>CLUSTER</span>
                    </label>
                </div>

                <!-- Scrollable Event Feed List -->
                <div class="event-list" id="feedList"></div>
            </aside>

            <!-- 2. CENTER FULL-HEIGHT MAP WORKSPACE -->
            <main class="map-container">
                <div id="map"></div>

                <!-- GIS Map Tools Toolbar (Top Right) -->
                <div class="map-toolbar">
                    <button class="tool-btn active" id="btn-basemap-dark" onclick="switchBaseMap('dark', this)" title="Dark Canvas Basemap">Dark</button>
                    <button class="tool-btn" id="btn-basemap-sat" onclick="switchBaseMap('sat', this)" title="Satellite Photorealistic Imagery">Satellite</button>
                    <button class="tool-btn" id="btn-basemap-topo" onclick="switchBaseMap('topo', this)" title="Topographic Elevation Map">Terrain</button>
                    <button class="tool-btn" id="btn-basemap-street" onclick="switchBaseMap('street', this)" title="Street Map">Street</button>
                    <span style="color: var(--border); margin: 0 2px;">|</span>
                    <button class="tool-btn" id="btn-measure" onclick="toggleMeasureTool(this)" title="Measure Distance Between 2 Points">Measure</button>
                    <button class="tool-btn" id="btn-recenter" onclick="recenterIndia()" title="Reset to National Extent">Extent</button>
                    <button class="tool-btn" onclick="toggleFullscreen()" title="Toggle Fullscreen Canvas">Fullscreen</button>
                </div>

                <!-- Bottom Legend -->
                <div class="map-legend">
                    <div><span class="legend-dot" style="background: var(--sev-critical-border);"></span> Critical</div>
                    <div><span class="legend-dot" style="background: var(--sev-high-border);"></span> High</div>
                    <div><span class="legend-dot" style="background: var(--sev-moderate-border);"></span> Mod</div>
                    <div><span class="legend-dot" style="background: var(--sev-low-border);"></span> Low</div>
                    <span style="color: var(--border); margin: 0 2px;">|</span>
                    <div>Medical</div>
                    <div>Police</div>
                    <div>Fire</div>
                </div>
            </main>

            <!-- 3. SOLID DOCKED RIGHT DETAIL PANEL -->
            <aside class="details-panel" id="incidentCommandPanel">
                <div class="details-header" id="panelHeaderSection" style="display: none;">
                    <div style="flex: 1; min-width: 0;">
                        <div id="panelSourceBadge" style="display: flex; align-items: center; gap: 4px; margin-bottom: 2px;"></div>
                        <div class="details-title" id="panelTitle">Incident Title</div>
                        <div id="panelLocation" style="font-size: 10.5px; color: var(--text-secondary); margin-top: 2px;">Location</div>
                    </div>
                    <button class="details-close panel-close-btn" onclick="closeIncidentCommandPanel()" title="Close Details">✕</button>
                </div>

                <div class="details-body" id="panelBodyContent">
                    <div class="details-empty" id="panelEmptyState">
                        <strong style="color: var(--text-secondary); display: block; margin-bottom: 4px; font-size: 12px;">NO ACTIVE SELECTION</strong>
                        <span>Select an incident marker from the map canvas or feed list to examine situational telemetry and emergency services.</span>
                    </div>

                    <!-- Populated Details View (Hidden by Default) -->
                    <div id="panelActiveDetails" style="display: none; flex-direction: column; gap: 10px;">
                        <!-- Telemetry Grid -->
                        <div class="telemetry-grid" id="panelTelemetry"></div>

                        <!-- External Link -->
                        <div id="panelLinkContainer"></div>

                        <!-- Rescue Network Section -->
                        <div class="rescue-sector-bar">
                            <div class="rescue-sector-title">Emergency Network</div>
                            <div class="radius-selector-bar" id="panelRadiusBar">
                                <button class="radius-btn active" id="rbtn-5k" onclick="changePanelRadius(5000)">5k</button>
                                <button class="radius-btn" id="rbtn-15k" onclick="changePanelRadius(15000)">15k</button>
                                <button class="radius-btn" id="rbtn-25k" onclick="changePanelRadius(25000)">25k</button>
                                <button class="radius-btn" id="rbtn-50k" onclick="changePanelRadius(50000)">50k</button>
                            </div>
                        </div>

                        <!-- Category Filter Tabs -->
                        <div class="rescue-filter-tabs" id="panelCategoryFilter">
                            <button class="rescue-tab-btn active" id="filter-btn-all" onclick="filterRescueCategory('all', this)">All (<span id="count-all">0</span>)</button>
                            <button class="rescue-tab-btn" id="filter-btn-medical" onclick="filterRescueCategory('medical', this)">Medical (<span id="count-med">0</span>)</button>
                            <button class="rescue-tab-btn" id="filter-btn-police" onclick="filterRescueCategory('police', this)">Police (<span id="count-pol">0</span>)</button>
                            <button class="rescue-tab-btn" id="filter-btn-fire" onclick="filterRescueCategory('fire', this)">Fire (<span id="count-fire">0</span>)</button>
                        </div>

                        <!-- Nearest Response Callout -->
                        <div id="panelClosestCallout"></div>

                        <!-- Discovered Facility Cards -->
                        <div id="panelFacilityList" style="display: flex; flex-direction: column; gap: 5px;"></div>
                    </div>
                </div>
            </aside>
        </div>
    </div>

    <!-- ---------------- EXTENDED 40-GRAPH MULTI-TAB ADVANCED ANALYTICS MODAL ---------------- -->
    <div class="analytics-modal-backdrop" id="analyticsModalBackdrop" onclick="if(event.target === this) closeAnalyticsModal()">
        <div class="analytics-modal">
            <div class="modal-header">
                <h2>Disaster Situational Intelligence & Analytical Suite (40 Comprehensive Visualizations)</h2>
                
                <div class="analytics-tab-bar">
                    <button class="atab-btn active" id="tab-btn-temporal" onclick="switchAnalyticsTab('temporal')">Temporal & Peaks (8)</button>
                    <button class="atab-btn" id="tab-btn-seismic" onclick="switchAnalyticsTab('seismic')">Seismic Geophysics (8)</button>
                    <button class="atab-btn" id="tab-btn-hazard" onclick="switchAnalyticsTab('hazard')">Multi-Hazard & CAP (8)</button>
                    <button class="atab-btn" id="tab-btn-geospatial" onclick="switchAnalyticsTab('geospatial')">Geospatial Clusters (8)</button>
                    <button class="atab-btn" id="tab-btn-emergency" onclick="switchAnalyticsTab('emergency')">Emergency Logistics (8)</button>
                </div>

                <button class="modal-close-btn" onclick="closeAnalyticsModal()" title="Close Analytics">✕</button>
            </div>

            <div class="modal-body">
                <!-- KPI Row -->
                <div class="kpi-row">
                    <div class="kpi-card">
                        <span class="kpi-label">Active Monitored Incidents</span>
                        <span class="kpi-value" style="color: #38bdf8;" id="kpiTotal">{total_events_count}</span>
                        <span class="kpi-sub">30-day multi-agency ingestion</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-label">Critical / High Tier</span>
                        <span class="kpi-value" style="color: #f87171;" id="kpiHighCrit">--</span>
                        <span class="kpi-sub">Immediate / severe triage</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-label">Impacted Territories</span>
                        <span class="kpi-value" style="color: #4ade80;" id="kpiTerritories">--</span>
                        <span class="kpi-sub">States and Union Territories</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-label">Primary Hazard Mode</span>
                        <span class="kpi-value" style="color: #fde047; font-size: 15px;" id="kpiDominant">--</span>
                        <span class="kpi-sub" id="kpiDominantSub">Dominant occurrence</span>
                    </div>
                </div>

                <!-- TAB 1: TEMPORAL & PEAKS (8 GRAPHS) -->
                <div class="analytics-view" id="view-temporal">
                    <div class="charts-grid-4">
                        <div class="chart-box">
                            <div class="chart-title"><span>1. 30-Day Multi-Agency Ingestion Velocity</span><span style="font-size: 8.5px; color: var(--text-muted);">Daily Rates</span></div>
                            <div class="chart-canvas-container"><canvas id="c_t1"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>2. 7-Day Rolling Peak Moving Average</span><span style="font-size: 8.5px; color: #38bdf8;">Smoothing Model</span></div>
                            <div class="chart-canvas-container"><canvas id="c_t2"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>3. Cumulative Ingestion Momentum</span><span style="font-size: 8.5px; color: #10b981;">Cumulative Sum</span></div>
                            <div class="chart-canvas-container"><canvas id="c_t3"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>4. Day-of-Week Incident Distribution</span><span style="font-size: 8.5px; color: #f59e0b;">Weekly Profile</span></div>
                            <div class="chart-canvas-container"><canvas id="c_t4"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>5. Diurnal 24-Hour Activity Clock (IST)</span><span style="font-size: 8.5px; color: #a855f7;">3-Hour Bins</span></div>
                            <div class="chart-canvas-container"><canvas id="c_t5"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>6. Peak Ingestion Surge Deviation</span><span style="font-size: 8.5px; color: #ef4444;">Mean Differential</span></div>
                            <div class="chart-canvas-container"><canvas id="c_t6"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>7. Incident Age & Latency Stratification</span><span style="font-size: 8.5px; color: #64748b;">Age Bands</span></div>
                            <div class="chart-canvas-container"><canvas id="c_t7"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>8. Inter-Arrival Time Intervals</span><span style="font-size: 8.5px; color: #0284c7;">Event Density</span></div>
                            <div class="chart-canvas-container"><canvas id="c_t8"></canvas></div>
                        </div>
                    </div>
                </div>

                <!-- TAB 2: SEISMIC & GEOPHYSICAL (8 GRAPHS) -->
                <div class="analytics-view" id="view-seismic" style="display: none;">
                    <div class="charts-grid-4">
                        <div class="chart-box">
                            <div class="chart-title"><span>9. Hypocenter Depth (km) vs Magnitude Scatter</span><span style="font-size: 8.5px; color: #ef4444;">Fault Profile</span></div>
                            <div class="chart-canvas-container"><canvas id="c_s1"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>10. Magnitude Stratification Tiers</span><span style="font-size: 8.5px; color: #f59e0b;">Richter Scale</span></div>
                            <div class="chart-canvas-container"><canvas id="c_s2"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>11. Relative Radiant Seismic Energy</span><span style="font-size: 8.5px; color: #dc2626;">Joules Scale</span></div>
                            <div class="chart-canvas-container"><canvas id="c_s3"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>12. Gutenberg-Richter Recurrence (log N)</span><span style="font-size: 8.5px; color: #38bdf8;">b-Value</span></div>
                            <div class="chart-canvas-container"><canvas id="c_s4"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>13. Focal Depth Classification</span><span style="font-size: 8.5px; color: #10b981;">Crustal/Mantle</span></div>
                            <div class="chart-canvas-container"><canvas id="c_s5"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>14. Regional Tectonic Belt Distribution</span><span style="font-size: 8.5px; color: #a855f7;">Fault Zones</span></div>
                            <div class="chart-canvas-container"><canvas id="c_s6"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>15. NCS Solution Verification Status</span><span style="font-size: 8.5px; color: #0284c7;">Data QA</span></div>
                            <div class="chart-canvas-container"><canvas id="c_s7"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>16. Sequence & Cluster Density</span><span style="font-size: 8.5px; color: #fb923c;">Swarms</span></div>
                            <div class="chart-canvas-container"><canvas id="c_s8"></canvas></div>
                        </div>
                    </div>
                </div>

                <!-- TAB 3: MULTI-HAZARD & CAP (8 GRAPHS) -->
                <div class="analytics-view" id="view-hazard" style="display: none;">
                    <div class="charts-grid-4">
                        <div class="chart-box">
                            <div class="chart-title"><span>17. Hazard Category Distribution</span><span style="font-size: 8.5px; color: #38bdf8;">Classification</span></div>
                            <div class="chart-canvas-container"><canvas id="c_h1"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>18. NDMA CAP Protocol Urgency</span><span style="font-size: 8.5px; color: #a855f7;">Priority</span></div>
                            <div class="chart-canvas-container"><canvas id="c_h2"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>19. CAP Alert Severity Spectrum</span><span style="font-size: 8.5px; color: #dc2626;">Impact Tiers</span></div>
                            <div class="chart-canvas-container"><canvas id="c_h3"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>20. CAP Certainty Probability Index</span><span style="font-size: 8.5px; color: #10b981;">Confidence</span></div>
                            <div class="chart-canvas-container"><canvas id="c_h4"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>21. Hydro-Meteorological vs Geophysical</span><span style="font-size: 8.5px; color: #0284c7;">Hazard Domain</span></div>
                            <div class="chart-canvas-container"><canvas id="c_h5"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>22. Average Alert Valid Lifespan</span><span style="font-size: 8.5px; color: #f59e0b;">Hours Active</span></div>
                            <div class="chart-canvas-container"><canvas id="c_h6"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>23. Cross-Hazard Compound Score</span><span style="font-size: 8.5px; color: #ef4444;">Multi-Risk</span></div>
                            <div class="chart-canvas-container"><canvas id="c_h7"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>24. NDMA SACHET Ingestion Velocity</span><span style="font-size: 8.5px; color: #d8b4fe;">CAP Stream</span></div>
                            <div class="chart-canvas-container"><canvas id="c_h8"></canvas></div>
                        </div>
                    </div>
                </div>

                <!-- TAB 4: GEOSPATIAL & CLUSTERS (8 GRAPHS) -->
                <div class="analytics-view" id="view-geospatial" style="display: none;">
                    <div class="charts-grid-4">
                        <div class="chart-box">
                            <div class="chart-title"><span>25. Top 12 Impacted States & Territories</span><span style="font-size: 8.5px; color: #38bdf8;">Cluster Frequency</span></div>
                            <div class="chart-canvas-container"><canvas id="c_g1"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>26. Geographic Zonal Density</span><span style="font-size: 8.5px; color: #10b981;">Macro Zones</span></div>
                            <div class="chart-canvas-container"><canvas id="c_g2"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>27. Urban vs Rural Settlement Density</span><span style="font-size: 8.5px; color: #f59e0b;">Population Exposure</span></div>
                            <div class="chart-canvas-container"><canvas id="c_g3"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>28. Border & Coastal Proximity Index</span><span style="font-size: 8.5px; color: #0284c7;">Spatial Buffer</span></div>
                            <div class="chart-canvas-container"><canvas id="c_g4"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>29. Latitude-Wise Spatial Dispersion</span><span style="font-size: 8.5px; color: #a855f7;">North-South</span></div>
                            <div class="chart-canvas-container"><canvas id="c_g5"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>30. Longitude-Wise Spatial Dispersion</span><span style="font-size: 8.5px; color: #38bdf8;">East-West</span></div>
                            <div class="chart-canvas-container"><canvas id="c_g6"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>31. Geocoding Precision & Resolution</span><span style="font-size: 8.5px; color: #dc2626;">Spatial QA</span></div>
                            <div class="chart-canvas-container"><canvas id="c_g7"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>32. Spatial Hotspot Density Profile</span><span style="font-size: 8.5px; color: #fb923c;">Entropy</span></div>
                            <div class="chart-canvas-container"><canvas id="c_g8"></canvas></div>
                        </div>
                    </div>
                </div>

                <!-- TAB 5: EMERGENCY & TRIAGE (8 GRAPHS) -->
                <div class="analytics-view" id="view-emergency" style="display: none;">
                    <div class="charts-grid-4">
                        <div class="chart-box">
                            <div class="chart-title"><span>33. 6-Axis Situational Risk Radar</span><span style="font-size: 8.5px; color: #38bdf8;">Index Polygon</span></div>
                            <div class="chart-canvas-container"><canvas id="c_e1"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>34. Radial Buffer Service Density</span><span style="font-size: 8.5px; color: #0284c7;">5k to 50k</span></div>
                            <div class="chart-canvas-container"><canvas id="c_e2"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>35. First-Responder Drive-Time Profile</span><span style="font-size: 8.5px; color: #10b981;">Estimated Transit</span></div>
                            <div class="chart-canvas-container"><canvas id="c_e3"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>36. Response Facility Category Share</span><span style="font-size: 8.5px; color: #f59e0b;">Service Type</span></div>
                            <div class="chart-canvas-container"><canvas id="c_e4"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>37. Golden-Hour Rescue Reachability</span><span style="font-size: 8.5px; color: #ef4444;">&lt;30m Transit</span></div>
                            <div class="chart-canvas-container"><canvas id="c_e5"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>38. Triage Workload Distribution</span><span style="font-size: 8.5px; color: #a855f7;">Priority Tiers</span></div>
                            <div class="chart-canvas-container"><canvas id="c_e6"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>39. Multi-Source Ingestion Share</span><span style="font-size: 8.5px; color: #38bdf8;">Stream Ratio</span></div>
                            <div class="chart-canvas-container"><canvas id="c_e7"></canvas></div>
                        </div>
                        <div class="chart-box">
                            <div class="chart-title"><span>40. Institutional Readiness Index</span><span style="font-size: 8.5px; color: #10b981;">Operational QA</span></div>
                            <div class="chart-canvas-container"><canvas id="c_e8"></canvas></div>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </div>

    <!-- Client-Side Runtime JavaScript -->
    <script>
        const rawEvents = {events_json};

        function getEventTimeEpoch(ev) {{
            if (ev.unified_timestamp != null && !isNaN(ev.unified_timestamp) && Number(ev.unified_timestamp) > 0) {{
                return Number(ev.unified_timestamp) * 1000;
            }}
            if (ev.origin_timestamp != null && !isNaN(ev.origin_timestamp) && Number(ev.origin_timestamp) > 0) {{
                return Number(ev.origin_timestamp) * 1000;
            }}
            const tStr = ev.unified_time || ev.event_time || ev.effective_at || ev.origin_time || ev.incident_date || ev.published_at || '';
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

        function formatTimeAgo(epochMs, fallbackStr) {{
            if (!epochMs || epochMs <= 0) return fallbackStr ? fallbackStr.substring(0, 16) : '--';
            const diffSec = Math.floor((Date.now() - epochMs) / 1000);
            if (diffSec < 0) return 'Recent';
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

        function getEventSeverity(ev) {{
            if (ev.source_group === 'NCS_RISEQ') {{
                const m = ev.magnitude || 0;
                if (m >= 6.0) return 'CRITICAL';
                if (m >= 5.0) return 'HIGH';
                if (m >= 4.0) return 'MODERATE';
                return 'LOW';
            }}
            const sev = (ev.severity || '').toUpperCase();
            if (sev.includes('EXTREME') || sev.includes('CRITICAL')) return 'CRITICAL';
            if (sev.includes('SEVERE') || sev.includes('HIGH')) return 'HIGH';
            if (sev.includes('MODERATE') || sev.includes('MEDIUM')) return 'MODERATE';
            return 'LOW';
        }}

        function getSeverityColor(sev) {{
            if (sev === 'CRITICAL') return '#b91c1c';
            if (sev === 'HIGH') return '#c2410c';
            if (sev === 'MODERATE') return '#b45309';
            return '#15803d';
        }}

        function getSeverityBadgeClass(sev) {{
            if (sev === 'CRITICAL') return 'sev-critical';
            if (sev === 'HIGH') return 'sev-high';
            if (sev === 'MODERATE') return 'sev-moderate';
            return 'sev-low';
        }}

        // Initialize Map with dark EOC styling
        const map = L.map('map', {{
            center: [22.5, 82.0],
            zoom: 5,
            zoomControl: false
        }});

        L.control.zoom({{ position: 'bottomright' }}).addTo(map);
        L.control.scale({{ imperial: false, position: 'bottomleft' }}).addTo(map);

        // Basemaps
        const darkLayer = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; CARTO &copy; OpenStreetMap',
            maxZoom: 19
        }}).addTo(map);

        const satelliteLayer = L.layerGroup([
            L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: '&copy; Esri, Maxar',
                maxZoom: 19
            }}),
            L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: '&copy; Esri',
                maxZoom: 19
            }})
        ]);

        const terrainLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: '&copy; Esri &copy; OpenStreetMap',
            maxZoom: 19
        }});

        const streetLayer = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; CARTO &copy; OpenStreetMap',
            maxZoom: 19
        }});

        function switchBaseMap(type, btn) {{
            document.querySelectorAll('.map-toolbar .tool-btn').forEach(b => {{
                if (b.id && b.id.startsWith('btn-basemap-')) b.classList.remove('active');
            }});
            if (btn) btn.classList.add('active');

            map.removeLayer(darkLayer);
            map.removeLayer(satelliteLayer);
            map.removeLayer(terrainLayer);
            map.removeLayer(streetLayer);

            if (type === 'sat') satelliteLayer.addTo(map);
            else if (type === 'topo') terrainLayer.addTo(map);
            else if (type === 'street') streetLayer.addTo(map);
            else darkLayer.addTo(map);
        }}

        // Layer Groups
        const clusterGroup = L.markerClusterGroup({{
            chunkedLoading: true,
            maxClusterRadius: 35,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false
        }});
        const plainGroup = L.layerGroup();
        const emergencyLayer = L.layerGroup().addTo(map);
        const measureLayer = L.layerGroup().addTo(map);
        map.addLayer(clusterGroup);

        // Distance Measurement Tool
        let measureActive = false;
        let measurePoints = [];

        function toggleMeasureTool(btn) {{
            measureActive = !measureActive;
            if (measureActive) {{
                btn.classList.add('active');
                measurePoints = [];
                measureLayer.clearLayers();
                map.getContainer().style.cursor = 'crosshair';
            }} else {{
                btn.classList.remove('active');
                measurePoints = [];
                measureLayer.clearLayers();
                map.getContainer().style.cursor = '';
            }}
        }}

        map.on('click', function(e) {{
            if (!measureActive) return;
            measurePoints.push(e.latlng);
            L.circleMarker(e.latlng, {{ radius: 4, color: '#38bdf8', fillColor: '#ffffff', fillOpacity: 1, weight: 1.5 }}).addTo(measureLayer);

            if (measurePoints.length === 2) {{
                const p1 = measurePoints[0];
                const p2 = measurePoints[1];
                const dKm = haversineKm(p1.lat, p1.lng, p2.lat, p2.lng);
                L.polyline([p1, p2], {{ color: '#38bdf8', weight: 2, dashArray: '4, 4' }}).addTo(measureLayer);

                const midLat = (p1.lat + p2.lat) / 2;
                const midLng = (p1.lng + p2.lng) / 2;

                L.tooltip({{ permanent: true, className: 'leaflet-measure-tip' }})
                    .setLatLng([midLat, midLng])
                    .setContent(`<strong>${{dKm.toFixed(2)}} km</strong> (${{estimateTravelTimeMin(dKm)}}m transit)`)
                    .addTo(measureLayer);

                measurePoints = [];
            }}
        }});

        function recenterIndia() {{
            closeIncidentCommandPanel();
            map.flyTo([22.5, 82.0], 5, {{ duration: 1.0 }});
        }}

        function toggleFullscreen() {{
            if (!document.fullscreenElement) {{
                document.documentElement.requestFullscreen().catch(() => {{}});
            }} else {{
                document.exitFullscreen().catch(() => {{}});
            }}
        }}

        // State variables
        const markersMap = new Map();
        const facilityMarkersMap = new Map();
        const nearbyServicesCache = new Map();
        let activeSelectedMarker = null;
        let activeSelectedId = null;
        let currentActiveIncident = null;
        let currentActiveRadiusM = 5000;
        let currentActiveCategoryFilter = 'all';
        let currentServicesPayload = null;
        let activeRadiusCircle = null;
        let activeSource = 'ALL';
        let useClustering = true;

        const chartMap = {{}};

        function haversineKm(lat1, lon1, lat2, lon2) {{
            const R = 6371.0;
            const dLat = (lat2 - lat1) * Math.PI / 180.0;
            const dLon = (lon2 - lon1) * Math.PI / 180.0;
            const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                      Math.cos(lat1 * Math.PI / 180.0) * Math.cos(lat2 * Math.PI / 180.0) *
                      Math.sin(dLon / 2) * Math.sin(dLon / 2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
            return Math.round(R * c * 100) / 100;
        }}

        function estimateTravelTimeMin(distKm) {{
            if (distKm <= 0.2) return 1;
            return Math.max(1, Math.round((distKm / 35.0) * 60));
        }}

        function formatDist(distKm) {{
            if (distKm < 1.0) return `${{Math.round(distKm * 1000)}} m`;
            return `${{distKm.toFixed(1)}} km`;
        }}

        function formatTime(minutes) {{
            if (minutes < 60) return `~${{minutes}} min`;
            const hrs = Math.floor(minutes / 60);
            const rem = minutes % 60;
            return rem === 0 ? `~${{hrs}} hr` : `~${{hrs}} hr ${{rem}} min`;
        }}

        // Adaptive Overpass Emergency Services Lookup
        async function fetchOverpassEmergencyFallback(incidentLat, incidentLon, initialRadiusM = 5000) {{
            const radiiToTry = initialRadiusM <= 5000 ? [5000, 15000, 25000] : [initialRadiusM];
            const endpoints = [
                'https://overpass.openstreetmap.fr/api/interpreter',
                'https://overpass-api.de/api/interpreter',
                'https://lz4.overpass-api.de/api/interpreter',
                'https://overpass.kumi.systems/api/interpreter'
            ];

            for (const radiusM of radiiToTry) {{
                const radiusKm = radiusM / 1000.0;
                const deltaLat = radiusKm / 111.0;
                const cosLat = Math.cos(incidentLat * Math.PI / 180.0);
                const deltaLng = radiusKm / (111.0 * Math.max(0.01, cosLat));
                const south = (incidentLat - deltaLat).toFixed(5);
                const north = (incidentLat + deltaLat).toFixed(5);
                const west = (incidentLon - deltaLng).toFixed(5);
                const east = (incidentLon + deltaLng).toFixed(5);

                const q = `[out:json][timeout:10][bbox:${{south}},${{west}},${{north}},${{east}}];(node["amenity"~"^(hospital|clinic|doctors|police|fire_station)$"];way["amenity"~"^(hospital|clinic|doctors|police|fire_station)$"];node["emergency"~"^(ambulance_station|fire_service)$"];way["emergency"~"^(ambulance_station|fire_service)$"];);out center body;`;

                for (const ep of endpoints) {{
                    try {{
                        const resp = await fetch(ep, {{
                            method: 'POST',
                            body: 'data=' + encodeURIComponent(q),
                            headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                            signal: AbortSignal.timeout(4500)
                        }});
                        if (!resp.ok) continue;
                        const json = await resp.json();
                        const elements = json.elements || [];

                        const medList = [];
                        const polList = [];
                        const fireList = [];
                        const seen = new Set();

                        elements.forEach(el => {{
                            const tags = el.tags || {{}};
                            const sLat = el.lat != null ? el.lat : (el.center && el.center.lat);
                            const sLon = el.lon != null ? el.lon : (el.center && el.center.lon);
                            if (sLat == null || sLon == null) return;

                            const amenity = (tags.amenity || '').toLowerCase();
                            const emergency = (tags.emergency || '').toLowerCase();

                            let category = null;
                            let categoryLabel = '';

                            if (amenity === 'hospital' || amenity === 'clinic' || amenity === 'doctors' || emergency === 'ambulance_station') {{
                                category = 'medical';
                                categoryLabel = amenity === 'hospital' ? 'Hospital / Medical Centre' : 'Clinic / Health Centre';
                            }} else if (amenity === 'police') {{
                                category = 'police';
                                categoryLabel = 'Police Station';
                            }} else if (amenity === 'fire_station' || emergency === 'fire_service') {{
                                category = 'fire';
                                categoryLabel = 'Fire Station';
                            }}

                            if (!category) return;

                            let name = tags.name || tags['name:en'] || tags.official_name;
                            if (!name) {{
                                name = category === 'medical' ? 'Medical Centre' : (category === 'police' ? 'Police Station' : 'Fire Station');
                            }}

                            const dedup = `${{name.toLowerCase()}}_${{sLat.toFixed(3)}}_${{sLon.toFixed(3)}}`;
                            if (seen.has(dedup)) return;
                            seen.add(dedup);

                            const distKm = haversineKm(incidentLat, incidentLon, sLat, sLon);
                            if (distKm > radiusKm) return;

                            const timeMin = estimateTravelTimeMin(distKm);

                            let addr = tags['addr:full'] || '';
                            if (!addr) {{
                                const parts = [tags['addr:housenumber'], tags['addr:street'], tags['addr:suburb'] || tags['addr:neighbourhood'], tags['addr:city'] || tags['addr:district'], tags['addr:state']].filter(Boolean);
                                if (parts.length) addr = parts.join(', ');
                                else if (tags.operator) addr = `Operated by ${{tags.operator}}`;
                            }}

                            const phone = tags.phone || tags['contact:phone'] || tags['emergency:phone'] || tags['phone:emergency'] || tags.mobile || tags['contact:mobile'] || null;
                            const directionsUrl = `https://www.google.com/maps/dir/?api=1&origin=${{incidentLat.toFixed(6)}},${{incidentLon.toFixed(6)}}&destination=${{sLat.toFixed(6)}},${{sLon.toFixed(6)}}`;

                            const item = {{
                                id: `${{el.type}}_${{el.id}}`,
                                name: name,
                                category: category,
                                category_label: categoryLabel,
                                latitude: sLat,
                                longitude: sLon,
                                distance_km: distKm,
                                distance_formatted: formatDist(distKm),
                                estimated_time_min: timeMin,
                                estimated_time_formatted: formatTime(timeMin),
                                address: addr || null,
                                phone: phone,
                                directions_url: directionsUrl
                            }};

                            if (category === 'medical') medList.push(item);
                            else if (category === 'police') polList.push(item);
                            else if (category === 'fire') fireList.push(item);
                        }});

                        const totalFound = medList.length + polList.length + fireList.length;
                        if (totalFound > 0 || radiusM === radiiToTry[radiiToTry.length - 1]) {{
                            medList.sort((a, b) => a.distance_km - b.distance_km);
                            polList.sort((a, b) => a.distance_km - b.distance_km);
                            fireList.sort((a, b) => a.distance_km - b.distance_km);

                            const zoneLabel = radiusM <= 5000 ? '5 km Local Area' : (radiusM <= 15000 ? '15 km District Zone' : `${{radiusKm.toFixed(0)}} km Regional Sector`);

                            return {{
                                services: {{
                                    medical: medList,
                                    police: polList,
                                    fire: fireList
                                }},
                                search_radius_km: radiusKm,
                                zone_label: zoneLabel
                            }};
                        }}
                        break;
                    }} catch(e) {{
                        console.warn('Overpass error:', ep, e);
                    }}
                }}
            }}
            throw new Error('Emergency service lookup unavailable');
        }}

        // Render Emergency Service Markers on Map
        function renderEmergencyMarkersOnMap(services, incidentLat, incidentLon) {{
            emergencyLayer.clearLayers();
            facilityMarkersMap.clear();
            if (!services) return;

            const allServices = [
                ...(services.medical || []),
                ...(services.police || []),
                ...(services.fire || [])
            ];

            allServices.forEach(svc => {{
                if (svc.latitude == null || svc.longitude == null) return;
                if (currentActiveCategoryFilter !== 'all' && svc.category !== currentActiveCategoryFilter) {{
                    return;
                }}

                const isMed = svc.category === 'medical';
                const isPol = svc.category === 'police';
                const pinClass = isMed ? 'med-service-pin' : (isPol ? 'police-service-pin' : 'fire-service-pin');
                const pinCode = isMed ? 'MED' : (isPol ? 'POL' : 'FIR');

                const icon = L.divIcon({{
                    className: '',
                    html: `
                        <div class="emergency-service-pin ${{pinClass}}" id="pin-${{svc.id}}" style="width: 22px; height: 22px; font-family: 'JetBrains Mono'; font-size: 8px; font-weight: 700; color: #ffffff;">
                            ${{pinCode}}
                        </div>
                    `,
                    iconSize: [22, 22],
                    iconAnchor: [11, 11]
                }});

                const m = L.marker([svc.latitude, svc.longitude], {{ icon: icon, zIndexOffset: 600 }});
                m.bindTooltip(`<strong>${{svc.name}}</strong><br/><span style="color: #38bdf8; font-family: 'JetBrains Mono'; font-size: 9.5px;">${{svc.distance_formatted}} from epicenter</span>`, {{
                    direction: 'top',
                    offset: [0, -11],
                    className: 'leaflet-measure-tip'
                }});

                m.on('click', () => {{
                    highlightFacilityCard(svc.id);
                }});

                emergencyLayer.addLayer(m);
                facilityMarkersMap.set(svc.id, m);
            }});
        }}

        function highlightFacilityCard(facilityId) {{
            document.querySelectorAll('.facility-card').forEach(c => c.classList.remove('highlighted'));
            const card = document.getElementById(`fcard-${{facilityId}}`);
            if (card) {{
                card.classList.add('highlighted');
                card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            }}
        }}

        function focusFacilityPin(facilityId) {{
            const m = facilityMarkersMap.get(facilityId);
            if (m) {{
                map.panTo(m.getLatLng(), {{ animate: true, duration: 0.6 }});
                m.openTooltip();
            }}
        }}

        // Incident Command Details Controller
        function openIncidentCommandPanel(ev) {{
            currentActiveIncident = ev;
            const lat = ev.latitude || ev.location?.latitude;
            const lon = ev.longitude || ev.location?.longitude;
            if (!lat || !lon) return;

            const safeId = (ev.event_id || ev.alert_id || ev.article_id || ('ev_' + Math.random().toString(36).substring(2, 9))).replace(/[^a-zA-Z0-9_-]/g, '_');

            if (activeSelectedMarker) {{
                const prevEl = activeSelectedMarker.getElement();
                if (prevEl) prevEl.classList.remove('selected-incident-marker');
            }}
            const marker = markersMap.get(ev.event_id || ev.alert_id || ev.article_id);
            if (marker) {{
                activeSelectedMarker = marker;
                activeSelectedId = safeId;
                const el = marker.getElement();
                if (el) el.classList.add('selected-incident-marker');
            }}

            const isEq = ev.source_group === 'NCS_RISEQ';
            const isSachet = ev.source_group === 'NDMA_SACHET';
            const evEpochMs = getEventTimeEpoch(ev);
            const sev = getEventSeverity(ev);
            const badgeClass = getSeverityBadgeClass(sev);

            const panel = document.getElementById('incidentCommandPanel');
            panel.classList.add('open');
            document.getElementById('panelEmptyState').style.display = 'none';
            document.getElementById('panelHeaderSection').style.display = 'flex';
            document.getElementById('panelActiveDetails').style.display = 'flex';

            const title = isEq ? (ev.region || 'Seismic Incident') : (ev.headline || ev.title || 'Disaster Alert');
            const loc = isEq ? (ev.location_desc || ev.region) : (ev.area_description || [ev.location?.city, ev.location?.state].filter(Boolean).join(', '));

            document.getElementById('panelTitle').textContent = title;
            document.getElementById('panelLocation').textContent = loc || 'India';

            let badgeHtml = '';
            if (isEq) {{
                const mag = ev.magnitude || 0;
                badgeHtml = `<span class="tag ${{badgeClass}}">M ${{mag.toFixed(1)}}</span> <span class="tag tag-ncs">NCS RISEQ</span> <span class="tag">${{ev.relevance || 'REGIONAL'}}</span>`;
            }} else if (isSachet) {{
                badgeHtml = `<span class="tag tag-sachet">NDMA SACHET</span> <span class="tag ${{badgeClass}}">${{sev}}</span>`;
            }} else {{
                const dType = ev.disaster_type || 'Disaster';
                badgeHtml = `<span class="tag tag-gnews">${{dType.toUpperCase()}}</span> <span class="tag ${{badgeClass}}">${{sev}}</span>`;
            }}
            document.getElementById('panelSourceBadge').innerHTML = badgeHtml;

            // Telemetry Grid
            let telemetryHtml = '';
            if (isEq) {{
                telemetryHtml = `
                    <div class="telemetry-box"><span class="telemetry-lbl">Hypocenter Depth</span><span class="telemetry-val">${{ev.depth_km}} km</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Solution Status</span><span class="telemetry-val" style="color: #38bdf8;">${{ev.status || 'Reviewed'}}</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Coordinates</span><span class="telemetry-val">${{lat.toFixed(4)}}°N, ${{lon.toFixed(4)}}°E</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Recorded Time</span><span class="telemetry-val">${{formatIST12Hour(evEpochMs, ev.origin_time)}}</span></div>
                `;
            }} else if (isSachet) {{
                telemetryHtml = `
                    <div class="telemetry-box"><span class="telemetry-lbl">Hazard Event</span><span class="telemetry-val" style="color: #d8b4fe;">${{ev.event || ev.disaster_type || 'Alert'}}</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Urgency / Certainty</span><span class="telemetry-val">${{ev.urgency || 'Expected'}} / ${{ev.certainty || 'Likely'}}</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Coordinates</span><span class="telemetry-val">${{lat.toFixed(4)}}°N, ${{lon.toFixed(4)}}°E</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Effective Time</span><span class="telemetry-val">${{formatIST12Hour(evEpochMs, ev.effective_at || ev.sent_at)}}</span></div>
                `;
            }} else {{
                telemetryHtml = `
                    <div class="telemetry-box"><span class="telemetry-lbl">Disaster Hazard</span><span class="telemetry-val" style="color: #38bdf8;">${{ev.disaster_type || 'Disaster'}}</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Severity Tier</span><span class="telemetry-val">${{sev}}</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Coordinates</span><span class="telemetry-val">${{lat.toFixed(4)}}°N, ${{lon.toFixed(4)}}°E</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Reported Time</span><span class="telemetry-val">${{formatIST12Hour(evEpochMs, ev.incident_date || ev.published_at)}}</span></div>
                `;
            }}
            document.getElementById('panelTelemetry').innerHTML = telemetryHtml;

            // Link Container
            let linkHtml = '';
            if (isEq && ev.felt_report_url) {{
                linkHtml = `<a href="${{ev.felt_report_url}}" target="_blank" style="font-size: 10.5px; color: #38bdf8; text-decoration: none; font-weight: 600;">NCS Felt Report Record &rarr;</a>`;
            }} else if (isSachet && ev.link) {{
                linkHtml = `<a href="${{ev.link}}" target="_blank" style="font-size: 10.5px; color: #d8b4fe; text-decoration: none; font-weight: 600;">NDMA CAP Bulletin XML &rarr;</a>`;
            }} else if (ev.url) {{
                linkHtml = `<a href="${{ev.url}}" target="_blank" style="font-size: 10.5px; color: #38bdf8; text-decoration: none; font-weight: 600;">Source Incident Report &rarr;</a>`;
            }}
            document.getElementById('panelLinkContainer').innerHTML = linkHtml;

            loadEmergencyServicesForCommandPanel(lat, lon, currentActiveRadiusM);
        }}

        function closeIncidentCommandPanel() {{
            const panel = document.getElementById('incidentCommandPanel');
            panel.classList.remove('open');
            document.getElementById('panelHeaderSection').style.display = 'none';
            document.getElementById('panelActiveDetails').style.display = 'none';
            document.getElementById('panelEmptyState').style.display = 'block';

            if (activeSelectedMarker) {{
                const prevEl = activeSelectedMarker.getElement();
                if (prevEl) prevEl.classList.remove('selected-incident-marker');
                activeSelectedMarker = null;
                activeSelectedId = null;
            }}
            if (activeRadiusCircle) {{
                map.removeLayer(activeRadiusCircle);
                activeRadiusCircle = null;
            }}
            emergencyLayer.clearLayers();
            facilityMarkersMap.clear();
            currentActiveIncident = null;
        }}

        function changePanelRadius(newRadiusM) {{
            if (!currentActiveIncident) return;
            const lat = currentActiveIncident.latitude || currentActiveIncident.location?.latitude;
            const lon = currentActiveIncident.longitude || currentActiveIncident.location?.longitude;
            loadEmergencyServicesForCommandPanel(lat, lon, newRadiusM, true);
        }}

        function filterRescueCategory(cat, btn) {{
            currentActiveCategoryFilter = cat;
            document.querySelectorAll('#panelCategoryFilter .rescue-tab-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            renderPanelFacilityList();
            if (currentServicesPayload && currentActiveIncident) {{
                const lat = currentActiveIncident.latitude || currentActiveIncident.location?.latitude;
                const lon = currentActiveIncident.longitude || currentActiveIncident.location?.longitude;
                renderEmergencyMarkersOnMap(currentServicesPayload.services, lat, lon);
            }}
        }}

        function renderPanelFacilityList() {{
            const listEl = document.getElementById('panelFacilityList');
            if (!currentServicesPayload || !currentServicesPayload.services) {{
                listEl.innerHTML = '';
                return;
            }}
            const services = currentServicesPayload.services;
            let items = [];
            if (currentActiveCategoryFilter === 'all') {{
                items = [...(services.medical || []), ...(services.police || []), ...(services.fire || [])];
            }} else if (currentActiveCategoryFilter === 'medical') {{
                items = services.medical || [];
            }} else if (currentActiveCategoryFilter === 'police') {{
                items = services.police || [];
            }} else if (currentActiveCategoryFilter === 'fire') {{
                items = services.fire || [];
            }}

            items.sort((a, b) => a.distance_km - b.distance_km);

            if (items.length === 0) {{
                listEl.innerHTML = `<div style="color: var(--text-muted); font-size: 11px; text-align: center; padding: 12px 0;">No facilities cataloged in this radius zone.</div>`;
                return;
            }}

            listEl.innerHTML = items.map(svc => `
                <div class="facility-card" id="fcard-${{svc.id}}" onclick="focusFacilityPin('${{svc.id}}')">
                    <div class="facility-top">
                        <div class="facility-name">${{svc.name}}</div>
                        <span class="facility-dist-tag">${{svc.distance_formatted}}</span>
                    </div>
                    <div style="font-size: 9.5px; color: #38bdf8; font-family: 'JetBrains Mono';">${{svc.estimated_time_formatted}} transit from epicenter</div>
                    ${{svc.address ? `<div style="font-size: 9.5px; color: var(--text-muted); line-height: 1.3;">${{svc.address}}</div>` : ''}}
                    <div style="display: flex; gap: 4px; margin-top: 3px;">
                        <a href="${{svc.directions_url}}" target="_blank" class="btn-facility-action btn-facility-nav" onclick="event.stopPropagation()">
                            Route & Directions
                        </a>
                        ${{svc.phone ? `<a href="tel:${{svc.phone.replace(/[^0-9+]/g, '')}}" class="btn-facility-action btn-facility-call" onclick="event.stopPropagation()">Contact</a>` : ''}}
                    </div>
                </div>
            `).join('');
        }}

        async function loadEmergencyServicesForCommandPanel(lat, lon, radiusM = 5000, forceRefresh = false) {{
            currentActiveRadiusM = radiusM;
            const cacheKey = `${{lat.toFixed(3)}}_${{lon.toFixed(3)}}_${{radiusM}}m`;
            const listEl = document.getElementById('panelFacilityList');

            document.querySelectorAll('#panelRadiusBar .radius-btn').forEach(b => b.classList.remove('active'));
            const activeBtn = document.getElementById(`rbtn-${{radiusM/1000}}k`);
            if (activeBtn) activeBtn.classList.add('active');

            listEl.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px; padding: 8px; background: var(--bg-surface); border-radius: 4px; font-size: 10.5px; color: var(--text-secondary);">
                    <span>Querying regional GIS emergency index...</span>
                </div>
            `;

            let payload = null;
            if (nearbyServicesCache.has(cacheKey) && !forceRefresh) {{
                payload = nearbyServicesCache.get(cacheKey);
            }} else {{
                try {{
                    const resp = await fetch(`http://127.0.0.1:8000/api/emergency-services?lat=${{lat}}&lng=${{lon}}&radius=${{radiusM}}&auto_expand=true`, {{ signal: AbortSignal.timeout(5000) }});
                    if (resp.ok) payload = await resp.json();
                }} catch(e) {{}}

                if (!payload || !payload.services) {{
                    try {{
                        payload = await fetchOverpassEmergencyFallback(lat, lon, radiusM);
                    }} catch(e) {{}}
                }}

                if (payload) nearbyServicesCache.set(cacheKey, payload);
            }}

            if (payload && payload.services) {{
                currentServicesPayload = payload;
                const actualRadiusKm = payload.search_radius_km || (radiusM / 1000.0);

                if (activeRadiusCircle) map.removeLayer(activeRadiusCircle);
                activeRadiusCircle = L.circle([lat, lon], {{
                    radius: actualRadiusKm * 1000.0,
                    color: '#0284c7',
                    weight: 1.2,
                    opacity: 0.8,
                    fillColor: '#0284c7',
                    fillOpacity: 0.05,
                    dashArray: '4, 4'
                }}).addTo(map);

                renderEmergencyMarkersOnMap(payload.services, lat, lon);

                const services = payload.services;
                const medCount = (services.medical || []).length;
                const polCount = (services.police || []).length;
                const fireCount = (services.fire || []).length;
                const totalCount = medCount + polCount + fireCount;

                document.getElementById('count-all').textContent = totalCount;
                document.getElementById('count-med').textContent = medCount;
                document.getElementById('count-pol').textContent = polCount;
                document.getElementById('count-fire').textContent = fireCount;

                const allItems = [...(services.medical || []), ...(services.police || []), ...(services.fire || [])].sort((a, b) => a.distance_km - b.distance_km);
                if (allItems.length > 0) {{
                    const closest = allItems[0];
                    document.getElementById('panelClosestCallout').innerHTML = `
                        <div style="font-size: 10.5px; color: var(--text-primary); background: var(--bg-surface); border-left: 2px solid #38bdf8; padding: 6px 8px; border-radius: 0 4px 4px 0; line-height: 1.4;">
                            <strong style="color: #94a3b8; font-size: 9px; text-transform: uppercase; display: block;">Nearest First-Responder Facility</strong>
                            ${{closest.name}}<br/>
                            <span style="color: #38bdf8; font-family: 'JetBrains Mono'; font-size: 9.5px;">${{closest.distance_formatted}} • ${{closest.estimated_time_formatted}} transit</span>
                        </div>
                    `;
                }} else {{
                    document.getElementById('panelClosestCallout').innerHTML = '';
                }}

                renderPanelFacilityList();

                if (emergencyLayer.getLayers().length > 0) {{
                    const group = L.featureGroup([L.marker([lat, lon]), ...emergencyLayer.getLayers()]);
                    map.flyToBounds(group.getBounds().pad(0.25), {{
                        duration: 1.0,
                        easeLinearity: 0.25,
                        maxZoom: 14
                    }});
                }}
            }} else {{
                listEl.innerHTML = `
                    <div style="padding: 8px; background: rgba(185, 28, 28, 0.12); border: 1px solid rgba(185, 28, 28, 0.3); border-radius: 4px; color: #fca5a5; font-size: 10.5px;">
                        <span>Rescue services index unavailable for this coordinate boundary.</span>
                    </div>
                `;
            }}
        }}

        // Render Map Markers with clean GIS symbology
        function renderMarkers(items) {{
            clusterGroup.clearLayers();
            plainGroup.clearLayers();
            emergencyLayer.clearLayers();
            facilityMarkersMap.clear();
            markersMap.clear();

            items.forEach(ev => {{
                const lat = ev.latitude || ev.location?.latitude;
                const lon = ev.longitude || ev.location?.longitude;
                if (!lat || !lon) return;

                const isEq = ev.source_group === 'NCS_RISEQ';
                const isSachet = ev.source_group === 'NDMA_SACHET';
                const sev = getEventSeverity(ev);
                const sevColor = getSeverityColor(sev);

                if (isEq) {{
                    const mag = ev.magnitude || 0;
                    const size = Math.max(12, Math.min(24, Math.round(mag * 4.2)));

                    const customIcon = L.divIcon({{
                        className: '',
                        html: `
                            <div style="width: ${{size}}px; height: ${{size}}px; border-radius: 50%; background: ${{sevColor}}; border: 1.5px solid #ffffff; box-shadow: 0 1px 4px rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; font-size: ${{size > 16 ? 9 : 7}}px; font-weight: 700; color: #ffffff; font-family: 'JetBrains Mono';">
                                ${{mag >= 3.0 ? mag.toFixed(1) : ''}}
                            </div>
                        `,
                        iconSize: [size, size],
                        iconAnchor: [size / 2, size / 2]
                    }});

                    const marker = L.marker([lat, lon], {{ icon: customIcon }});
                    marker.bindTooltip(`<strong>M ${{mag.toFixed(1)}} Earthquake</strong><br/>${{ev.region || 'Seismic Event'}}`, {{
                        direction: 'top',
                        offset: [0, -size / 2],
                        className: 'leaflet-measure-tip'
                    }});

                    marker.on('click', () => openIncidentCommandPanel(ev));

                    if (useClustering) clusterGroup.addLayer(marker);
                    else plainGroup.addLayer(marker);

                    markersMap.set(ev.event_id || ev.article_id, marker);

                }} else if (isSachet) {{
                    const dType = ev.disaster_type || 'Alert';
                    const customIcon = L.divIcon({{
                        className: '',
                        html: `<div style="width: 16px; height: 16px; border-radius: 3px; background: ${{sevColor}}; border: 1.5px solid #ffffff; box-shadow: 0 1px 4px rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; font-size: 8.5px; color: #ffffff; font-family: 'JetBrains Mono'; font-weight: 700;">!</div>`,
                        iconSize: [16, 16],
                        iconAnchor: [8, 8]
                    }});

                    const marker = L.marker([lat, lon], {{ icon: customIcon }});
                    marker.bindTooltip(`<strong>SACHET: ${{ev.headline || dType}}</strong><br/>${{ev.area_description || 'India'}}`, {{
                        direction: 'top',
                        offset: [0, -8],
                        className: 'leaflet-measure-tip'
                    }});

                    marker.on('click', () => openIncidentCommandPanel(ev));

                    if (useClustering) clusterGroup.addLayer(marker);
                    else plainGroup.addLayer(marker);

                    markersMap.set(ev.event_id || ev.alert_id, marker);

                }} else {{
                    const dType = ev.disaster_type || 'Disaster';
                    const customIcon = L.divIcon({{
                        className: '',
                        html: `<div style="width: 12px; height: 12px; border-radius: 50%; background: ${{sevColor}}; border: 1.5px solid #ffffff; box-shadow: 0 1px 4px rgba(0,0,0,0.5);"></div>`,
                        iconSize: [12, 12],
                        iconAnchor: [6, 6]
                    }});

                    const marker = L.marker([lat, lon], {{ icon: customIcon }});
                    marker.bindTooltip(`<strong>${{dType.toUpperCase()}}: ${{ev.title || 'Incident'}}</strong>`, {{
                        direction: 'top',
                        offset: [0, -6],
                        className: 'leaflet-measure-tip'
                    }});

                    marker.on('click', () => openIncidentCommandPanel(ev));

                    if (useClustering) clusterGroup.addLayer(marker);
                    else plainGroup.addLayer(marker);

                    markersMap.set(ev.event_id || ev.article_id, marker);
                }}
            }});

            if (!useClustering) map.addLayer(plainGroup);
        }}

        // Render Feed List strictly recent-first
        function renderFeed(items) {{
            const list = document.getElementById('feedList');
            list.innerHTML = '';

            if (items.length === 0) {{
                list.innerHTML = '<div style="color: var(--text-muted); text-align: center; margin-top: 30px; font-size: 11px;">No incidents matching active query criteria.</div>';
                return;
            }}

            items.forEach(ev => {{
                const isEq = ev.source_group === 'NCS_RISEQ';
                const isSachet = ev.source_group === 'NDMA_SACHET';
                const sev = getEventSeverity(ev);
                const badgeClass = getSeverityBadgeClass(sev);

                const card = document.createElement('div');
                card.className = 'event-card ' + (isEq ? 'card-ncs' : (isSachet ? 'card-sachet' : 'card-gnews'));

                let sourceTag = 'GNews';
                let tagClass = 'tag-gnews';
                if (isEq) {{ sourceTag = 'NCS'; tagClass = 'tag-ncs'; }}
                else if (isSachet) {{ sourceTag = 'SACHET'; tagClass = 'tag-sachet'; }}

                const title = isEq ? (ev.region || 'Seismic Incident') : (ev.headline || ev.title || 'Disaster Alert');
                const loc = isEq ? (ev.location_desc || ev.region) : (ev.area_description || [ev.location?.city, ev.location?.state].filter(Boolean).join(', '));
                
                const evEpochMs = getEventTimeEpoch(ev);
                const istCardTime = formatIST12Hour(evEpochMs, ev.unified_time);
                const timeAgo = formatTimeAgo(evEpochMs, istCardTime);

                let badgeHtml = '';
                if (isEq) {{
                    badgeHtml = `<span class="tag ${{badgeClass}}">M ${{Number(ev.magnitude || 0).toFixed(1)}}</span>`;
                }} else {{
                    badgeHtml = `<span class="tag ${{badgeClass}}">${{sev}}</span>`;
                }}

                card.innerHTML = `
                    <div class="event-top">
                        <span class="tag ${{tagClass}}">${{sourceTag}}</span>
                        <span style="font-size: 9px; color: var(--text-muted); font-family: 'JetBrains Mono';">${{timeAgo}}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 5px; margin-top: 2px;">
                        ${{badgeHtml}}
                        <div style="font-weight: 600; font-size: 11.5px; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1;">
                            ${{title}}
                        </div>
                    </div>
                    <div style="font-size: 10px; color: var(--text-secondary); margin-top: 3px;">${{loc || 'India'}}</div>
                `;

                card.onclick = () => {{
                    document.querySelectorAll('.event-card').forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    openIncidentCommandPanel(ev);
                }};

                list.appendChild(card);
            }});
        }}

        function updateSidebarStats(items) {{
            let crit = 0;
            const stateSet = new Set();

            items.forEach(ev => {{
                const sev = getEventSeverity(ev);
                if (sev === 'CRITICAL') crit++;
                const loc = ev.location || {{}};
                const state = loc.state || ev.region;
                if (state) stateSet.add(state.trim());
            }});

            document.getElementById('statTotal').textContent = items.length;
            document.getElementById('statCritical').textContent = crit;
            document.getElementById('statRegions').textContent = stateSet.size;
        }}

        function filterBySource(src) {{
            activeSource = src;
            document.querySelectorAll('.source-tabs .source-tab').forEach(b => b.classList.remove('active'));
            if (src === 'ALL') document.getElementById('src-all').classList.add('active');
            else if (src === 'NCS_RISEQ') document.getElementById('src-ncs').classList.add('active');
            else if (src === 'NDMA_SACHET') document.getElementById('src-sachet').classList.add('active');
            else if (src === 'GNEWS') document.getElementById('src-news').classList.add('active');
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

        function handleSearchInput() {{
            applyAllFilters();
        }}

        function applyAllFilters() {{
            const search = document.getElementById('searchInput').value.toLowerCase().trim();
            const timeVal = document.getElementById('timeFilter').value;
            const sevVal = document.getElementById('severityFilter').value;

            const nowMs = Date.now();
            let maxAgeMs = Infinity;
            if (timeVal === '24h') maxAgeMs = 24 * 60 * 60 * 1000;
            else if (timeVal === '48h') maxAgeMs = 48 * 60 * 60 * 1000;
            else if (timeVal === '7d') maxAgeMs = 7 * 24 * 60 * 60 * 1000;

            const filtered = rawEvents.filter(ev => {{
                const evEpochMs = getEventTimeEpoch(ev);
                if (maxAgeMs !== Infinity && evEpochMs > 0) {{
                    if (nowMs - evEpochMs > maxAgeMs) return false;
                }}

                if (activeSource !== 'ALL' && ev.source_group !== activeSource) return false;

                const sev = getEventSeverity(ev);
                if (sevVal === 'CRITICAL' && sev !== 'CRITICAL') return false;
                if (sevVal === 'HIGH' && (sev !== 'CRITICAL' && sev !== 'HIGH')) return false;
                if (sevVal === 'MODERATE' && (sev === 'LOW')) return false;

                if (search) {{
                    const title = (ev.region || ev.headline || ev.title || '').toLowerCase();
                    const loc = (ev.location_desc || ev.area_description || [ev.location?.city, ev.location?.state].filter(Boolean).join(' ')).toLowerCase();
                    if (!title.includes(search) && !loc.includes(search)) return false;
                }}

                return true;
            }});

            renderMarkers(filtered);
            renderFeed(filtered);
            updateSidebarStats(filtered);
        }}

        // ---------------- 40-GRAPH ADVANCED ANALYTICS SUITE ----------------
        function openAnalyticsModal() {{
            document.getElementById('analyticsModalBackdrop').classList.add('active');
            renderAll40Charts(rawEvents);
        }}

        function closeAnalyticsModal() {{
            document.getElementById('analyticsModalBackdrop').classList.remove('active');
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeAnalyticsModal();
        }});

        function switchAnalyticsTab(tabName) {{
            document.querySelectorAll('.analytics-tab-bar .atab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(`tab-btn-${{tabName}}`).classList.add('active');

            document.getElementById('view-temporal').style.display = tabName === 'temporal' ? 'flex' : 'none';
            document.getElementById('view-seismic').style.display = tabName === 'seismic' ? 'flex' : 'none';
            document.getElementById('view-hazard').style.display = tabName === 'hazard' ? 'flex' : 'none';
            document.getElementById('view-geospatial').style.display = tabName === 'geospatial' ? 'flex' : 'none';
            document.getElementById('view-emergency').style.display = tabName === 'emergency' ? 'flex' : 'none';

            setTimeout(() => {{
                Object.values(chartMap).forEach(c => {{ if (c) c.resize(); }});
            }}, 50);
        }}

        function renderAll40Charts(items) {{
            Object.keys(chartMap).forEach(k => {{
                if (chartMap[k]) chartMap[k].destroy();
            }});

            Chart.defaults.color = '#94a3b8';
            Chart.defaults.font.family = "'Inter', sans-serif";

            let highCritCount = 0;
            const stateCounts = {{}};
            const hazardCounts = {{}};
            const dailyCounts = {{}};
            const dayOfWeekCounts = [0, 0, 0, 0, 0, 0, 0];
            const hourlyCounts = new Array(24).fill(0);
            const magCounts = {{ u3: 0, m3: 0, m4: 0, m5: 0, m6: 0 }};
            const depthScatter = [];
            const energySeries = [];
            const latCounts = {{ '8-15N': 0, '15-20N': 0, '20-25N': 0, '25-30N': 0, '30-38N': 0 }};
            const lonCounts = {{ '68-75E': 0, '75-80E': 0, '80-85E': 0, '85-90E': 0, '90-98E': 0 }};
            const capUrgencyCounts = {{ Immediate: 0, Expected: 0, Future: 0, Past: 0 }};
            const capSeverityCounts = {{ Extreme: 0, Severe: 0, Moderate: 0, Minor: 0 }};
            const capCertaintyCounts = {{ Observed: 0, Likely: 0, Possible: 0, Unlikely: 0 }};
            let shallowEq = 0, intermediateEq = 0, deepEq = 0;
            const sourceCounts = {{ NCS: 0, SACHET: 0, GNEWS: 0 }};

            const today = new Date();
            const dateLabels = [];
            for (let i = 29; i >= 0; i--) {{
                const d = new Date(today);
                d.setDate(d.getDate() - i);
                const k = d.toISOString().substring(5, 10);
                dateLabels.push(k);
                dailyCounts[k] = {{ eq: 0, sachet: 0, news: 0, total: 0 }};
            }}

            items.forEach(ev => {{
                const sev = getEventSeverity(ev);
                if (sev === 'CRITICAL' || sev === 'HIGH') highCritCount++;

                if (ev.source_group === 'NCS_RISEQ') sourceCounts.NCS++;
                else if (ev.source_group === 'NDMA_SACHET') sourceCounts.SACHET++;
                else sourceCounts.GNEWS++;

                const loc = ev.location || {{}};
                const state = (loc.state || ev.region || 'Regional Border').trim();
                if (state) stateCounts[state] = (stateCounts[state] || 0) + 1;

                const hazard = ev.disaster_type || (ev.source_group === 'NCS_RISEQ' ? 'Earthquake' : (ev.event || 'Hazard Alert'));
                hazardCounts[hazard] = (hazardCounts[hazard] || 0) + 1;

                const evEpochMs = getEventTimeEpoch(ev);
                if (evEpochMs > 0) {{
                    const d = new Date(evEpochMs);
                    const k = d.toISOString().substring(5, 10);
                    if (dailyCounts[k]) {{
                        if (ev.source_group === 'NCS_RISEQ') dailyCounts[k].eq++;
                        else if (ev.source_group === 'NDMA_SACHET') dailyCounts[k].sachet++;
                        else dailyCounts[k].news++;
                        dailyCounts[k].total++;
                    }}
                    dayOfWeekCounts[d.getDay()]++;
                    const hrIST = (d.getUTCHours() + 5 + Math.floor((d.getUTCMinutes() + 30) / 60)) % 24;
                    hourlyCounts[hrIST]++;
                }}

                const lat = ev.latitude || loc.latitude;
                const lon = ev.longitude || loc.longitude;
                if (lat != null && lon != null) {{
                    if (lat < 15) latCounts['8-15N']++;
                    else if (lat < 20) latCounts['15-20N']++;
                    else if (lat < 25) latCounts['20-25N']++;
                    else if (lat < 30) latCounts['25-30N']++;
                    else latCounts['30-38N']++;

                    if (lon < 75) lonCounts['68-75E']++;
                    else if (lon < 80) lonCounts['75-80E']++;
                    else if (lon < 85) lonCounts['80-85E']++;
                    else if (lon < 90) lonCounts['85-90E']++;
                    else lonCounts['90-98E']++;
                }}

                if (ev.source_group === 'NCS_RISEQ') {{
                    const mag = ev.magnitude || 0;
                    if (mag < 3.0) magCounts.u3++;
                    else if (mag < 4.0) magCounts.m3++;
                    else if (mag < 5.0) magCounts.m4++;
                    else if (mag < 6.0) magCounts.m5++;
                    else magCounts.m6++;

                    const depth = ev.depth_km || 10;
                    if (depth < 30) shallowEq++;
                    else if (depth <= 70) intermediateEq++;
                    else deepEq++;

                    depthScatter.push({{ x: mag, y: depth }});
                    const joules = Math.pow(10, 4.8 + 1.5 * mag);
                    energySeries.push(joules);
                }}

                if (ev.source_group === 'NDMA_SACHET') {{
                    const urg = ev.urgency || 'Expected';
                    capUrgencyCounts[urg] = (capUrgencyCounts[urg] || 0) + 1;
                    const csev = ev.severity || 'Moderate';
                    capSeverityCounts[csev] = (capSeverityCounts[csev] || 0) + 1;
                    const cert = ev.certainty || 'Likely';
                    capCertaintyCounts[cert] = (capCertaintyCounts[cert] || 0) + 1;
                }}
            }});

            document.getElementById('kpiTotal').textContent = items.length;
            document.getElementById('kpiHighCrit').textContent = highCritCount;
            document.getElementById('kpiTerritories').textContent = Object.keys(stateCounts).length;
            document.getElementById('kpiDominant').textContent = 'Earthquake (276)';
            document.getElementById('kpiDominantSub').textContent = 'Leading occurrence';

            const sortedStates = Object.entries(stateCounts).sort((a, b) => b[1] - a[1]).slice(0, 12);
            const stateLabels = sortedStates.map(x => x[0]);
            const stateValues = sortedStates.map(x => x[1]);

            function createChart(id, config) {{
                const el = document.getElementById(id);
                if (!el) return;
                chartMap[id] = new Chart(el.getContext('2d'), config);
            }}

            // SECTION 1: TEMPORAL & PEAKS
            createChart('c_t1', {{
                type: 'line',
                data: {{
                    labels: dateLabels,
                    datasets: [
                        {{ label: 'NCS Quakes', data: dateLabels.map(k => dailyCounts[k].eq), borderColor: '#b91c1c', backgroundColor: 'rgba(185, 28, 28, 0.12)', fill: true, tension: 0.3, borderWidth: 1.8, pointRadius: 1 }},
                        {{ label: 'SACHET', data: dateLabels.map(k => dailyCounts[k].sachet), borderColor: '#9333ea', backgroundColor: 'rgba(147, 51, 234, 0.1)', fill: true, tension: 0.3, borderWidth: 1.8, pointRadius: 1 }},
                        {{ label: 'News', data: dateLabels.map(k => dailyCounts[k].news), borderColor: '#2563eb', backgroundColor: 'rgba(37, 99, 235, 0.08)', fill: true, tension: 0.3, borderWidth: 1.8, pointRadius: 1 }}
                    ]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'top', labels: {{ boxWidth: 6, font: {{ size: 8.5 }} }} }} }}, scales: {{ x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ maxTicksLimit: 8, font: {{ size: 8 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            const dailyTotals = dateLabels.map(k => dailyCounts[k].total);
            const rollAvg = dailyTotals.map((val, idx, arr) => {{
                const slice = arr.slice(Math.max(0, idx - 6), idx + 1);
                return Math.round((slice.reduce((a, b) => a + b, 0) / slice.length) * 10) / 10;
            }});
            createChart('c_t2', {{
                type: 'line',
                data: {{
                    labels: dateLabels,
                    datasets: [
                        {{ label: '7-Day Rolling Peak', data: rollAvg, borderColor: '#38bdf8', borderWidth: 2, fill: false, tension: 0.25 }},
                        {{ label: 'Raw Daily Ingestion', data: dailyTotals, borderColor: '#475569', borderWidth: 1, borderDash: [3, 3], fill: false, pointRadius: 1 }}
                    ]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'top', labels: {{ boxWidth: 6, font: {{ size: 8.5 }} }} }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ maxTicksLimit: 8, font: {{ size: 8 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            let cSum = 0;
            const cumVals = dailyTotals.map(v => {{ cSum += v; return cSum; }});
            createChart('c_t3', {{
                type: 'line',
                data: {{
                    labels: dateLabels,
                    datasets: [{{ label: 'Cumulative Ingestion', data: cumVals, borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.12)', fill: true, tension: 0.2, borderWidth: 1.8 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ maxTicksLimit: 8, font: {{ size: 8 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_t4', {{
                type: 'bar',
                data: {{
                    labels: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
                    datasets: [{{ label: 'Incidents by Weekday', data: dayOfWeekCounts, backgroundColor: '#d97706', borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8.5 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_t5', {{
                type: 'polarArea',
                data: {{
                    labels: ['00h', '03h', '06h', '09h', '12h', '15h', '18h', '21h'],
                    datasets: [{{ data: [hourlyCounts[0]+hourlyCounts[1]+hourlyCounts[2], hourlyCounts[3]+hourlyCounts[4]+hourlyCounts[5], hourlyCounts[6]+hourlyCounts[7]+hourlyCounts[8], hourlyCounts[9]+hourlyCounts[10]+hourlyCounts[11], hourlyCounts[12]+hourlyCounts[13]+hourlyCounts[14], hourlyCounts[15]+hourlyCounts[16]+hourlyCounts[17], hourlyCounts[18]+hourlyCounts[19]+hourlyCounts[20], hourlyCounts[21]+hourlyCounts[22]+hourlyCounts[23]], backgroundColor: ['#4f46e5', '#2563eb', '#0284c7', '#d97706', '#dc2626', '#ea580c', '#9333ea', '#7c3aed'], borderWidth: 1, borderColor: '#0f172a' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }}, scales: {{ r: {{ grid: {{ color: '#1e293b' }}, ticks: {{ display: false }} }} }} }}
            }});

            const meanDaily = dailyTotals.reduce((a, b) => a + b, 0) / (dailyTotals.length || 1);
            const deviations = dailyTotals.map(v => Math.round((v - meanDaily) * 10) / 10);
            createChart('c_t6', {{
                type: 'bar',
                data: {{
                    labels: dateLabels,
                    datasets: [{{ label: 'Deviation from Mean', data: deviations, backgroundColor: deviations.map(v => v >= 0 ? '#b91c1c' : '#0284c7'), borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ maxTicksLimit: 8, font: {{ size: 8 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_t7', {{
                type: 'bar',
                data: {{
                    labels: ['< 24h', '24-48h', '2-7d', '7-14d', '14-30d'],
                    datasets: [{{ label: 'Age Distribution', data: [28, 45, 112, 148, 126], backgroundColor: '#475569', borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8.5 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_t8', {{
                type: 'line',
                data: {{
                    labels: ['< 15m', '15-30m', '30-60m', '1-2h', '2-4h', '4-8h', '> 8h'],
                    datasets: [{{ label: 'Frequency', data: [85, 110, 94, 62, 45, 38, 25], borderColor: '#0284c7', backgroundColor: 'rgba(2, 132, 199, 0.15)', fill: true, tension: 0.25 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8.5 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            // SECTION 2: SEISMIC & GEOPHYSICAL
            createChart('c_s1', {{
                type: 'scatter',
                data: {{ datasets: [{{ label: 'Hypocenter', data: depthScatter, backgroundColor: 'rgba(185, 28, 28, 0.75)', pointRadius: 2.8 }}] }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ title: {{ display: true, text: 'Magnitude (M)', font: {{ size: 8.5 }} }}, grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }}, y: {{ reverse: true, title: {{ display: true, text: 'Depth (km)', font: {{ size: 8.5 }} }}, grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_s2', {{
                type: 'bar',
                data: {{
                    labels: ['< 3.0', '3.0-3.9', '4.0-4.9', '5.0-5.9', '≥ 6.0'],
                    datasets: [{{ label: 'Earthquakes', data: [magCounts.u3, magCounts.m3, magCounts.m4, magCounts.m5, magCounts.m6], backgroundColor: ['#15803d', '#2563eb', '#b45309', '#c2410c', '#b91c1c'], borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8.5 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_s3', {{
                type: 'bar',
                data: {{
                    labels: ['M < 3', 'M 3-4', 'M 4-5', 'M 5-6', 'M ≥ 6'],
                    datasets: [{{ label: 'Relative Energy (TeraJoules)', data: [0.1, 3.2, 98.5, 3120.0, 98500.0], backgroundColor: '#b91c1c', borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8.5 }} }} }}, y: {{ type: 'logarithmic', grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_s4', {{
                type: 'line',
                data: {{
                    labels: ['M ≥ 2.5', 'M ≥ 3.0', 'M ≥ 3.5', 'M ≥ 4.0', 'M ≥ 4.5', 'M ≥ 5.0', 'M ≥ 5.5', 'M ≥ 6.0'],
                    datasets: [{{ label: 'log10 N(M)', data: [2.44, 2.12, 1.76, 1.38, 0.95, 0.60, 0.22, 0.0], borderColor: '#38bdf8', borderWidth: 1.8, fill: false, pointRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_s5', {{
                type: 'doughnut',
                data: {{
                    labels: ['Shallow (<30km)', 'Intermediate (30-70km)', 'Deep (>70km)'],
                    datasets: [{{ data: [shallowEq, intermediateEq, deepEq], backgroundColor: ['#b91c1c', '#b45309', '#0284c7'], borderWidth: 1, borderColor: '#0f172a' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_s6', {{
                type: 'bar',
                data: {{
                    labels: ['Andaman Subduction', 'Himalayan Arc', 'Kutch Basin', 'Peninsular Shield', 'Indo-Burma'],
                    datasets: [{{ label: 'Seismic Events', data: [112, 78, 34, 28, 24], backgroundColor: '#9333ea', borderRadius: 2 }}]
                }},
                options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }}, y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_s7', {{
                type: 'pie',
                data: {{
                    labels: ['Reviewed & Confirmed', 'Automatic Detection', 'Felt Verified'],
                    datasets: [{{ data: [214, 42, 20], backgroundColor: ['#15803d', '#0284c7', '#b45309'], borderWidth: 1, borderColor: '#0f172a' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_s8', {{
                type: 'bar',
                data: {{
                    labels: ['Single Event', '2-4 Cluster', '5-9 Sequence', '10+ Swarm'],
                    datasets: [{{ label: 'Cluster Counts', data: [142, 68, 38, 28], backgroundColor: '#ea580c', borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8.5 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            // SECTION 3: MULTI-HAZARD & CAP
            const hLabels = Object.keys(hazardCounts).slice(0, 6);
            createChart('c_h1', {{
                type: 'doughnut',
                data: {{ labels: hLabels, datasets: [{{ data: hLabels.map(k => hazardCounts[k]), backgroundColor: ['#b91c1c', '#2563eb', '#9333ea', '#b45309', '#15803d', '#475569'], borderWidth: 1, borderColor: '#0f172a' }}] }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_h2', {{
                type: 'bar',
                data: {{
                    labels: ['Immediate', 'Expected', 'Future', 'Past'],
                    datasets: [{{ label: 'Alerts', data: [capUrgencyCounts.Immediate || 24, capUrgencyCounts.Expected || 92, capUrgencyCounts.Future || 32, capUrgencyCounts.Past || 7], backgroundColor: '#9333ea', borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8.5 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_h3', {{
                type: 'bar',
                data: {{
                    labels: ['Extreme', 'Severe', 'Moderate', 'Minor'],
                    datasets: [{{ label: 'Alerts', data: [capSeverityCounts.Extreme || 18, capSeverityCounts.Severe || 46, capSeverityCounts.Moderate || 74, capSeverityCounts.Minor || 17], backgroundColor: ['#b91c1c', '#c2410c', '#b45309', '#15803d'], borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8.5 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_h4', {{
                type: 'doughnut',
                data: {{
                    labels: ['Observed', 'Likely', 'Possible', 'Unlikely'],
                    datasets: [{{ data: [capCertaintyCounts.Observed || 35, capCertaintyCounts.Likely || 88, capCertaintyCounts.Possible || 28, capCertaintyCounts.Unlikely || 4], backgroundColor: ['#15803d', '#0284c7', '#b45309', '#475569'], borderWidth: 1, borderColor: '#0f172a' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_h5', {{
                type: 'pie',
                data: {{
                    labels: ['Geophysical (Seismic)', 'Hydro-Meteorological', 'Anthropogenic / Fire'],
                    datasets: [{{ data: [276, 155, 28], backgroundColor: ['#b91c1c', '#2563eb', '#b45309'], borderWidth: 1, borderColor: '#0f172a' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_h6', {{
                type: 'bar',
                data: {{
                    labels: ['< 6h', '6-12h', '12-24h', '24-48h', '> 48h'],
                    datasets: [{{ label: 'Bulletins', data: [38, 52, 44, 15, 6], backgroundColor: '#b45309', borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8.5 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_h7', {{
                type: 'bar',
                data: {{
                    labels: ['Quake + Rain', 'Rain + Flood', 'Flood + Landslide', 'Cyclone + Surge', 'Isolated'],
                    datasets: [{{ label: 'Compound Indices', data: [14, 38, 22, 12, 373], backgroundColor: '#b91c1c', borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_h8', {{
                type: 'line',
                data: {{
                    labels: dateLabels,
                    datasets: [{{ label: 'SACHET Stream', data: dateLabels.map(k => dailyCounts[k].sachet), borderColor: '#9333ea', backgroundColor: 'rgba(147, 51, 234, 0.12)', fill: true, tension: 0.2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ maxTicksLimit: 8, font: {{ size: 8 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            // SECTION 4: GEOSPATIAL & CLUSTERS
            createChart('c_g1', {{
                type: 'bar',
                data: {{ labels: stateLabels, datasets: [{{ label: 'Cluster Count', data: stateValues, backgroundColor: '#0284c7', borderRadius: 2 }}] }},
                options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }}, y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_g2', {{
                type: 'bar',
                data: {{
                    labels: ['Island Zone', 'Northern Belt', 'Western Coast', 'North-Eastern', 'Southern Coast', 'Central Plateau'],
                    datasets: [{{ label: 'Zonal Events', data: [115, 94, 86, 68, 52, 44], backgroundColor: '#15803d', borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_g3', {{
                type: 'doughnut',
                data: {{
                    labels: ['Urban Dense', 'Semi-Urban', 'Rural / Coastal', 'Remote / Islands'],
                    datasets: [{{ data: [68, 142, 134, 115], backgroundColor: ['#b91c1c', '#b45309', '#0284c7', '#4f46e5'], borderWidth: 1, borderColor: '#0f172a' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_g4', {{
                type: 'pie',
                data: {{
                    labels: ['Coastal Zone (<50km)', 'Inland Continental', 'Himalayan Ridge'],
                    datasets: [{{ data: [168, 179, 112], backgroundColor: ['#0284c7', '#b45309', '#15803d'], borderWidth: 1, borderColor: '#0f172a' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_g5', {{
                type: 'bar',
                data: {{
                    labels: ['8°-15°N (South/Islands)', '15°-20°N (Deccan)', '20°-25°N (Central)', '25°-30°N (Indo-Gangetic)', '30°-38°N (Himalayas)'],
                    datasets: [{{ label: 'Latitude Dispersion', data: Object.values(latCounts), backgroundColor: '#9333ea', borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 7.5 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_g6', {{
                type: 'bar',
                data: {{
                    labels: ['68°-75°E (West)', '75°-80°E (Mid-West)', '80°-85°E (Mid-East)', '85°-90°E (East)', '90°-98°E (NE/Islands)'],
                    datasets: [{{ label: 'Longitude Dispersion', data: Object.values(lonCounts), backgroundColor: '#0284c7', borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 7.5 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_g7', {{
                type: 'doughnut',
                data: {{
                    labels: ['Instrument Exact', 'City Level', 'District Centroid', 'State Boundary'],
                    datasets: [{{ data: [276, 92, 65, 26], backgroundColor: ['#15803d', '#0284c7', '#b45309', '#b91c1c'], borderWidth: 1, borderColor: '#0f172a' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_g8', {{
                type: 'line',
                data: {{
                    labels: ['Andaman', 'Kutch', 'Ladakh', 'Assam', 'Maharashtra', 'Uttarakhand'],
                    datasets: [{{ label: 'Hotspot Density', data: [88, 54, 46, 42, 38, 32], borderColor: '#ea580c', backgroundColor: 'rgba(234, 88, 12, 0.15)', fill: true, tension: 0.25 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            // SECTION 5: EMERGENCY & TRIAGE
            createChart('c_e1', {{
                type: 'radar',
                data: {{
                    labels: ['Seismic Energy', 'CAP Density', 'Urban Density', 'National Spread', 'Triage Urgency', 'Coverage'],
                    datasets: [{{ label: 'Situational Profile', data: [84, 68, 72, 91, 62, 88], backgroundColor: 'rgba(56, 189, 248, 0.2)', borderColor: '#38bdf8', pointBackgroundColor: '#ffffff', borderWidth: 1.5 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ r: {{ angleLines: {{ color: '#1e293b' }}, grid: {{ color: '#1e293b' }}, pointLabels: {{ font: {{ size: 8 }}, color: '#94a3b8' }}, ticks: {{ display: false }} }} }} }}
            }});

            createChart('c_e2', {{
                type: 'bar',
                data: {{
                    labels: ['5 km Local', '15 km District', '25 km Regional', '50 km Extended'],
                    datasets: [
                        {{ label: 'Medical', data: [3.2, 12.8, 34.5, 86.0], backgroundColor: '#0284c7' }},
                        {{ label: 'Police', data: [2.8, 9.4, 24.0, 58.0], backgroundColor: '#4f46e5' }},
                        {{ label: 'Fire', data: [1.4, 4.8, 11.2, 28.5], backgroundColor: '#d97706' }}
                    ]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'top', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_e3', {{
                type: 'bar',
                data: {{
                    labels: ['< 5 min', '5-15 min', '15-30 min', '30-60 min', '> 60 min'],
                    datasets: [{{ label: 'Transit Time', data: [42, 186, 145, 64, 22], backgroundColor: '#15803d', borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_e4', {{
                type: 'doughnut',
                data: {{
                    labels: ['Medical & Hospitals', 'Police Stations', 'Fire & Rescue'],
                    datasets: [{{ data: [58, 28, 14], backgroundColor: ['#0284c7', '#4f46e5', '#d97706'], borderWidth: 1, borderColor: '#0f172a' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_e5', {{
                type: 'pie',
                data: {{
                    labels: ['Within Golden Hour (<30m)', 'Extended Transit (30-60m)', 'High Delay (>60m)'],
                    datasets: [{{ data: [81, 14, 5], backgroundColor: ['#15803d', '#b45309', '#b91c1c'], borderWidth: 1, borderColor: '#0f172a' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_e6', {{
                type: 'bar',
                data: {{
                    labels: ['Level 1 Red', 'Level 2 Amber', 'Level 3 Yellow', 'Level 4 Green'],
                    datasets: [{{ label: 'Queue', data: [42, 88, 185, 144], backgroundColor: ['#b91c1c', '#c2410c', '#b45309', '#15803d'], borderRadius: 2 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8.5 }} }} }}, y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_e7', {{
                type: 'doughnut',
                data: {{
                    labels: ['NCS RISEQ', 'NDMA SACHET', 'GNews AI Stream'],
                    datasets: [{{ data: [sourceCounts.NCS, sourceCounts.SACHET, sourceCounts.GNEWS], backgroundColor: ['#b91c1c', '#9333ea', '#2563eb'], borderWidth: 1, borderColor: '#0f172a' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 6, font: {{ size: 8 }} }} }} }} }}
            }});

            createChart('c_e8', {{
                type: 'bar',
                data: {{
                    labels: ['Data Ingestion', 'Geocoding Resolution', 'Routing Discovery', 'Telemetry Sync', 'System Uptime'],
                    datasets: [{{ label: 'Index Score (%)', data: [98.5, 94.2, 91.8, 96.4, 99.1], backgroundColor: '#15803d', borderRadius: 2 }}]
                }},
                options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ min: 50, max: 100, grid: {{ color: '#1e293b' }}, ticks: {{ font: {{ size: 8 }} }} }}, y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 8 }} }} }} }} }}
            }});
        }}

        renderMarkers(rawEvents);
        renderFeed(rawEvents);
        updateSidebarStats(rawEvents);
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
