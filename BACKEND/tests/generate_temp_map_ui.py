"""
DISHA Platform - Operational Disaster Intelligence & Emergency Response Map
Institutional Command-Center Grade Situational Awareness System.

Ingests & Visualizes:
1. NCS RISEQ Earthquakes (National Center for Seismology)
2. NDMA SACHET CAP Alerts (National Disaster Management Authority)
3. GNews Ingested Disaster Incidents (AI-Classified News)
4. Live Adaptive Nearby Emergency Rescue Facilities (Hospitals, Police, Fire)

Architecture & Design System:
- Fullscreen Central GIS Workspace with Floating Glassmorphic Telemetry HUDs
- Multi-Source Timeline Ingestion with Recent-First Sorting
- Semantic Severity Stratification (Critical, High, Moderate, Low)
- Real-Time Map Intelligence Metric Calculations
- Adaptive Multi-Tier Emergency Service Search & Interactive Map Plotting
- Integrated Distance Measurement, Multi-Basemaps, Metric Scale & Cinematic Viewport Transitions
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
    """Generates an institutional-grade disaster intelligence map HTML."""
    events_json = json.dumps(events, default=str)
    total_events_count = len(events)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>DISHA - Operational Disaster Intelligence & Emergency Response Map</title>
    
    <!-- Leaflet & MarkerCluster CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    
    <!-- Leaflet & MarkerCluster JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

    <!-- Google Fonts: Inter & JetBrains Mono -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

    <style>
        :root {{
            --bg-base: #090e17;
            --bg-surface: rgba(15, 23, 42, 0.88);
            --bg-surface-solid: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.7);
            --bg-card-hover: rgba(51, 65, 85, 0.8);
            --border: rgba(51, 65, 85, 0.6);
            --border-highlight: #3b82f6;

            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;

            --sev-critical: #ef4444;
            --sev-high: #f97316;
            --sev-moderate: #f59e0b;
            --sev-low: #10b981;

            --svc-medical: #0284c7;
            --svc-police: #6366f1;
            --svc-fire: #ea580c;

            --radius-hud: 8px;
            --radius-btn: 6px;
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
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            position: relative;
        }}

        /* Fullscreen GIS Map Canvas */
        #map {{
            width: 100vw;
            height: 100vh;
            position: absolute;
            top: 0;
            left: 0;
            z-index: 1;
            background: #090e17;
        }}

        /* Top Floating Command Bar */
        .top-command-bar {{
            position: absolute;
            top: 12px;
            left: 16px;
            right: 16px;
            height: 52px;
            z-index: 1000;
            background: var(--bg-surface);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: var(--radius-hud);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 14px;
            gap: 12px;
            pointer-events: auto;
        }}

        .brand-section {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-shrink: 0;
        }}

        .brand-pill {{
            background: #2563eb;
            color: #ffffff;
            font-weight: 800;
            font-size: 13px;
            letter-spacing: 1px;
            padding: 4px 8px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);
        }}

        .brand-title {{
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .status-badge {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 9px;
            font-weight: 700;
            color: #4ade80;
            background: rgba(34, 197, 94, 0.15);
            border: 1px solid rgba(34, 197, 94, 0.3);
            padding: 2px 6px;
            border-radius: 4px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            letter-spacing: 0.5px;
        }}

        .status-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 6px #22c55e;
            animation: pulse-dot 1.8s infinite;
        }}

        @keyframes pulse-dot {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.4; transform: scale(0.8); }}
        }}

        /* Search Input */
        .search-container {{
            flex: 1;
            max-width: 320px;
            position: relative;
        }}

        .search-box {{
            width: 100%;
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: #ffffff;
            font-size: 11.5px;
            padding: 6px 28px 6px 10px;
            outline: none;
            transition: all 0.15s ease;
        }}

        .search-box:focus {{
            border-color: #38bdf8;
            background: rgba(30, 41, 59, 0.95);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
        }}

        .search-box::placeholder {{
            color: var(--text-muted);
        }}

        /* Command Controls Group */
        .controls-group {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-shrink: 0;
        }}

        .nav-btn {{
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--border);
            color: var(--text-primary);
            font-size: 11px;
            font-weight: 600;
            padding: 6px 10px;
            border-radius: var(--radius-btn);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            transition: all 0.15s ease;
            user-select: none;
        }}

        .nav-btn:hover {{
            background: rgba(51, 65, 85, 0.9);
            border-color: #94a3b8;
            color: #ffffff;
        }}

        .nav-btn.active {{
            background: #2563eb;
            border-color: #3b82f6;
            color: #ffffff;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
        }}

        /* Left Floating Situational Intelligence & Incident Feed HUD */
        .left-hud-panel {{
            position: absolute;
            top: 74px;
            left: 16px;
            bottom: 20px;
            width: 380px;
            max-width: calc(100vw - 32px);
            z-index: 900;
            background: var(--bg-surface);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: var(--radius-hud);
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: transform 0.25s ease, opacity 0.25s ease;
        }}

        .left-hud-panel.collapsed {{
            transform: translateX(-400px);
            opacity: 0;
            pointer-events: none;
        }}

        .hud-toggle-btn {{
            position: absolute;
            top: 74px;
            left: 16px;
            z-index: 890;
            background: var(--bg-surface);
            border: 1px solid var(--border);
            color: var(--text-primary);
            width: 34px;
            height: 34px;
            border-radius: 6px;
            display: none;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }}

        .left-hud-panel.collapsed + .hud-toggle-btn {{
            display: flex;
        }}

        /* HUD Header Tabs */
        .hud-tabs-header {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            background: rgba(15, 23, 42, 0.9);
            border-bottom: 1px solid var(--border);
            padding: 4px;
            gap: 4px;
        }}

        .hud-tab {{
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 11px;
            font-weight: 700;
            padding: 8px 6px;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: all 0.15s ease;
        }}

        .hud-tab.active {{
            background: #1e293b;
            color: #ffffff;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3);
        }}

        .hud-tab-badge {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 9.5px;
            font-weight: 700;
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            padding: 1px 5px;
            border-radius: 3px;
        }}

        /* Filter Pills & Stream Controls */
        .stream-controls {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 8px;
            background: rgba(15, 23, 42, 0.6);
        }}

        .source-pill-grid {{
            display: grid;
            grid-template-columns: 1fr 1.1fr 1.2fr 1fr;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border);
            padding: 2px;
            border-radius: 6px;
            gap: 2px;
        }}

        .source-btn {{
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 10px;
            font-weight: 600;
            padding: 5px 2px;
            border-radius: 4px;
            cursor: pointer;
            text-align: center;
            transition: all 0.15s ease;
        }}

        .source-btn.active {{
            background: #2563eb;
            color: #ffffff;
        }}

        .filter-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 6px;
        }}

        .filter-select {{
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid var(--border);
            color: var(--text-primary);
            font-size: 10.5px;
            padding: 4px 6px;
            border-radius: 4px;
            outline: none;
            cursor: pointer;
        }}

        /* Active Filter Chips */
        .active-chips-bar {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            padding: 6px 12px;
            background: rgba(15, 23, 42, 0.4);
            border-bottom: 1px solid var(--border);
            min-height: 28px;
            align-items: center;
        }}

        .filter-chip {{
            font-size: 9.5px;
            font-weight: 600;
            background: rgba(56, 189, 248, 0.14);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 3px;
            padding: 1px 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }}

        .chip-remove {{
            cursor: pointer;
            font-size: 10px;
            color: #94a3b8;
        }}
        .chip-remove:hover {{
            color: #ffffff;
        }}

        /* Incident Feed List */
        .feed-scroll-container {{
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
            border-left: 3.5px solid #3b82f6;
            border-radius: 6px;
            padding: 9px 11px;
            cursor: pointer;
            transition: all 0.15s ease;
            position: relative;
        }}

        .event-card:hover {{
            background: var(--bg-card-hover);
            border-color: #64748b;
            transform: translateX(2px);
        }}

        .event-card.selected {{
            border-color: #38bdf8;
            background: rgba(30, 41, 59, 0.95);
            box-shadow: 0 0 0 1px #38bdf8;
        }}

        .event-card.card-ncs {{ border-left-color: #ea580c; }}
        .event-card.card-sachet {{ border-left-color: #a855f7; }}
        .event-card.card-gnews {{ border-left-color: #0284c7; }}

        .card-meta-row {{
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

        .tag-ncs {{ background: rgba(234, 88, 12, 0.15); color: #fb923c; border: 1px solid rgba(234, 88, 12, 0.3); }}
        .tag-sachet {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }}
        .tag-gnews {{ background: rgba(2, 132, 199, 0.15); color: #38bdf8; border: 1px solid rgba(2, 132, 199, 0.3); }}

        .sev-critical {{ background: #ef4444; color: #ffffff; }}
        .sev-high {{ background: #f97316; color: #ffffff; }}
        .sev-moderate {{ background: #f59e0b; color: #ffffff; }}
        .sev-low {{ background: #10b981; color: #ffffff; }}

        /* Map Intelligence View */
        .intelligence-view {{
            flex: 1;
            overflow-y: auto;
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .intel-metric-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }}

        .intel-metric-card {{
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}

        .intel-metric-card.full-width {{
            grid-column: span 2;
        }}

        .intel-lbl {{
            font-size: 9.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
        }}

        .intel-val {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 20px;
            font-weight: 800;
            color: #ffffff;
        }}

        .intel-sub {{
            font-size: 10.5px;
            color: var(--text-muted);
            margin-top: 2px;
        }}

        /* Severity Breakdown Stack Bar */
        .severity-stack-bar {{
            height: 8px;
            border-radius: 4px;
            display: flex;
            overflow: hidden;
            margin: 6px 0 2px 0;
            background: #1e293b;
        }}

        .stack-segment {{
            height: 100%;
            transition: width 0.3s ease;
        }}

        /* Right Floating Incident & Emergency Response Command Panel */
        .incident-command-panel {{
            position: absolute;
            top: 74px;
            right: 16px;
            bottom: 20px;
            width: 400px;
            max-width: calc(100vw - 32px);
            background: var(--bg-surface);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: var(--radius-hud);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.55);
            display: flex;
            flex-direction: column;
            z-index: 950;
            transform: translateX(450px);
            transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
            opacity: 0;
            pointer-events: none;
            overflow: hidden;
        }}

        .incident-command-panel.open {{
            transform: translateX(0);
            opacity: 1;
            pointer-events: auto;
        }}

        .panel-header {{
            padding: 12px 14px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            background: rgba(15, 23, 42, 0.8);
            gap: 8px;
        }}

        .panel-title {{
            font-size: 13.5px;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.3;
            margin-top: 3px;
        }}

        .panel-close-btn {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            border-radius: 6px;
            width: 26px;
            height: 26px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.15s ease;
            flex-shrink: 0;
        }}

        .panel-close-btn:hover {{
            background: #ef4444;
            color: #ffffff;
            border-color: #ef4444;
        }}

        .panel-body {{
            flex: 1;
            overflow-y: auto;
            padding: 12px 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .telemetry-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
        }}

        .telemetry-box {{
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 7px 9px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}

        .telemetry-lbl {{
            font-size: 9px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
        }}

        .telemetry-val {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11.5px;
            font-weight: 700;
            color: #f8fafc;
        }}

        /* Rescue Network Sub-Panel */
        .rescue-sector-bar {{
            background: rgba(14, 165, 233, 0.09);
            border: 1px solid rgba(14, 165, 233, 0.3);
            border-radius: 6px;
            padding: 8px 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .rescue-sector-title {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 10.5px;
            font-weight: 700;
            color: #38bdf8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .radius-selector-bar {{
            display: flex;
            align-items: center;
            gap: 3px;
        }}

        .radius-btn {{
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 9px;
            font-weight: 700;
            padding: 3px 6px;
            border-radius: 3px;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .radius-btn:hover, .radius-btn.active {{
            background: #38bdf8;
            color: #0b1120;
            border-color: #38bdf8;
        }}

        .rescue-filter-tabs {{
            display: flex;
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 2px;
            gap: 2px;
        }}

        .rescue-tab-btn {{
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 9.5px;
            font-weight: 700;
            padding: 5px 2px;
            border-radius: 4px;
            cursor: pointer;
            text-align: center;
            transition: all 0.15s ease;
        }}

        .rescue-tab-btn.active {{
            background: #2563eb;
            color: #ffffff;
        }}

        .facility-card {{
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 9px 10px;
            display: flex;
            flex-direction: column;
            gap: 5px;
            transition: all 0.15s ease;
            cursor: pointer;
        }}

        .facility-card:hover, .facility-card.highlighted {{
            border-color: #38bdf8;
            background: rgba(30, 41, 59, 0.95);
            transform: translateY(-1px);
        }}

        .facility-top {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 6px;
        }}

        .facility-name {{
            font-size: 11.5px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.3;
            flex: 1;
        }}

        .facility-dist-tag {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            font-weight: 700;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.14);
            padding: 2px 5px;
            border-radius: 3px;
            white-space: nowrap;
        }}

        .btn-facility-action {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 10px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 4px;
            text-decoration: none;
            cursor: pointer;
            border: none;
            transition: opacity 0.15s ease;
        }}
        .btn-facility-action:hover {{ opacity: 0.9; }}
        .btn-facility-nav {{ background: #2563eb; color: #ffffff; flex: 1; justify-content: center; }}
        .btn-facility-call {{ background: #16a34a; color: #ffffff; }}

        /* Floating Expandable Legend */
        .map-legend-hud {{
            position: absolute;
            bottom: 24px;
            left: 410px;
            z-index: 800;
            background: var(--bg-surface);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: var(--radius-hud);
            padding: 8px 12px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.4);
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 10px;
            font-weight: 600;
            color: var(--text-secondary);
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        .legend-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}

        /* Reticle Pulse on Selected Incident */
        .selected-incident-marker {{
            z-index: 1000 !important;
            position: relative;
        }}
        .selected-incident-marker::after {{
            content: '';
            position: absolute;
            top: -7px;
            left: -7px;
            right: -7px;
            bottom: -7px;
            border-radius: 50%;
            border: 2px solid #ffffff;
            box-shadow: 0 0 0 2px #2563eb, 0 4px 10px rgba(0,0,0,0.5);
            animation: reticle-pulse 1.8s infinite ease-out;
            pointer-events: none;
        }}

        @keyframes reticle-pulse {{
            0% {{ transform: scale(0.95); opacity: 1; }}
            60% {{ transform: scale(1.35); opacity: 0.5; }}
            100% {{ transform: scale(1.6); opacity: 0; }}
        }}

        /* High-Contrast Emergency Service Pins */
        .emergency-service-pin {{
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            border: 2px solid #ffffff;
            box-shadow: 0 3px 10px rgba(0,0,0,0.5);
            font-size: 13px;
            cursor: pointer;
            transition: transform 0.15s ease;
        }}
        .emergency-service-pin:hover {{ transform: scale(1.25); }}
        .med-service-pin {{ background: var(--svc-medical); }}
        .police-service-pin {{ background: var(--svc-police); }}
        .fire-service-pin {{ background: var(--svc-fire); }}

        .leaflet-measure-tip {{
            background: #0f172a !important;
            border: 1px solid #38bdf8 !important;
            color: #ffffff !important;
            font-size: 10.5px !important;
            font-family: 'JetBrains Mono', monospace !important;
            padding: 4px 8px !important;
            border-radius: 4px !important;
        }}

        /* Responsive Mobile Layout */
        @media (max-width: 768px) {{
            .top-command-bar {{
                top: 8px; left: 8px; right: 8px;
                height: 48px;
                padding: 0 8px;
            }}
            .search-container {{
                display: none;
            }}
            .left-hud-panel {{
                top: 62px; left: 8px; right: 8px;
                width: auto;
                max-height: 45vh;
            }}
            .incident-command-panel {{
                top: auto; bottom: 8px; left: 8px; right: 8px;
                width: auto;
                max-height: 55vh;
                transform: translateY(110%);
            }}
            .incident-command-panel.open {{
                transform: translateY(0);
            }}
            .map-legend-hud {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <!-- Main Fullscreen GIS Map -->
    <div id="map"></div>

    <!-- Top Floating Command Bar -->
    <header class="top-command-bar">
        <div class="brand-section">
            <span class="brand-pill">DISHA</span>
            <div class="brand-title">
                <span>OPERATIONAL DISASTER INTELLIGENCE</span>
                <span class="status-badge"><span class="status-dot"></span>LIVE INGESTION</span>
            </div>
        </div>

        <div class="search-container">
            <input type="text" id="searchInput" class="search-box" placeholder="Search region, state, hazard..." oninput="handleSearchInput()" />
        </div>

        <div class="controls-group">
            <!-- Basemap Selector -->
            <button class="nav-btn active" id="btn-basemap-dark" onclick="switchBaseMap('dark', this)" title="Tactical Night Dark Basemap">🌙 Dark</button>
            <button class="nav-btn" id="btn-basemap-sat" onclick="switchBaseMap('sat', this)" title="Satellite Photorealistic Imagery">🛰️ Sat</button>
            <button class="nav-btn" id="btn-basemap-topo" onclick="switchBaseMap('topo', this)" title="Topographic Elevation Map">🏔️ Topo</button>
            <button class="nav-btn" id="btn-basemap-street" onclick="switchBaseMap('street', this)" title="High-Contrast Street Map">🗺️ Street</button>

            <!-- Tools -->
            <button class="nav-btn" id="btn-measure" onclick="toggleMeasureTool(this)" title="Measure Distance Between 2 Points">📏 Measure</button>
            <button class="nav-btn" id="btn-recenter" onclick="recenterIndia()" title="Recenter India National Overview">🇮🇳 Overview</button>
            <button class="nav-btn" onclick="toggleLeftHud()" title="Toggle Incident Stream / Intelligence">📊 HUD</button>
            <button class="nav-btn" onclick="toggleFullscreen()" title="Toggle Fullscreen Canvas">⛶</button>
        </div>
    </header>

    <!-- Left Floating Situational Intelligence & Incident Feed HUD -->
    <aside class="left-hud-panel" id="leftHudPanel">
        <div class="hud-tabs-header">
            <button class="hud-tab active" id="tab-feed-btn" onclick="switchHudTab('feed')">
                <span>⚡ Live Feed</span>
                <span class="hud-tab-badge" id="feedCountBadge">{total_events_count}</span>
            </button>
            <button class="hud-tab" id="tab-intel-btn" onclick="switchHudTab('intel')">
                <span>📊 Intelligence</span>
            </button>
        </div>

        <!-- TAB 1: Live Feed View -->
        <div id="hudFeedSection" style="display: flex; flex-direction: column; flex: 1; overflow: hidden;">
            <div class="stream-controls">
                <div class="source-pill-grid">
                    <button class="source-btn active" id="src-all" onclick="filterBySource('ALL')">All</button>
                    <button class="source-btn" id="src-ncs" onclick="filterBySource('NCS_RISEQ')">Quakes</button>
                    <button class="source-btn" id="src-sachet" onclick="filterBySource('NDMA_SACHET')">SACHET</button>
                    <button class="source-btn" id="src-news" onclick="filterBySource('GNEWS')">News</button>
                </div>

                <div class="filter-row">
                    <select id="timeFilter" class="filter-select" onchange="applyAllFilters()">
                        <option value="ALL">All Time (30d)</option>
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

                    <label style="font-size: 10px; color: var(--text-secondary); display: flex; align-items: center; gap: 4px; cursor: pointer;">
                        <input type="checkbox" id="clusterToggle" checked onchange="toggleClustering()" />
                        <span>Cluster</span>
                    </label>
                </div>
            </div>

            <!-- Active Chips Bar -->
            <div class="active-chips-bar" id="activeChipsBar"></div>

            <!-- Scrollable Incident Stream -->
            <div class="feed-scroll-container" id="feedList"></div>
        </div>

        <!-- TAB 2: Map Intelligence View -->
        <div id="hudIntelSection" class="intelligence-view" style="display: none;">
            <div class="intel-metric-grid">
                <div class="intel-metric-card">
                    <span class="intel-lbl">Total Incidents</span>
                    <span class="intel-val" style="color: #38bdf8;" id="intel-total">{total_events_count}</span>
                    <span class="intel-sub">Past 30 Days Ingestion</span>
                </div>
                <div class="intel-metric-card">
                    <span class="intel-lbl">Affected Regions</span>
                    <span class="intel-val" style="color: #4ade80;" id="intel-regions">--</span>
                    <span class="intel-sub">States & Territories</span>
                </div>
                <div class="intel-metric-card full-width">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="intel-lbl">Severity Stratification</span>
                        <span style="font-family: 'JetBrains Mono'; font-size: 10px; color: #ef4444;" id="intel-crit-count">0 Critical</span>
                    </div>
                    <div class="severity-stack-bar">
                        <div class="stack-segment sev-critical" id="stack-crit" style="width: 10%;"></div>
                        <div class="stack-segment sev-high" id="stack-high" style="width: 25%;"></div>
                        <div class="stack-segment sev-moderate" id="stack-mod" style="width: 35%;"></div>
                        <div class="stack-segment sev-low" id="stack-low" style="width: 30%;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 9.5px; color: var(--text-muted); margin-top: 4px;">
                        <span>🔴 Crit: <strong id="lbl-crit">0</strong></span>
                        <span>🟠 High: <strong id="lbl-high">0</strong></span>
                        <span>🟡 Mod: <strong id="lbl-mod">0</strong></span>
                        <span>🟢 Low: <strong id="lbl-low">0</strong></span>
                    </div>
                </div>
                <div class="intel-metric-card full-width">
                    <span class="intel-lbl">Dominant Hazard</span>
                    <span class="intel-val" style="font-size: 15px; color: #facc15;" id="intel-hazard">Seismic Activity</span>
                    <span class="intel-sub" id="intel-hazard-desc">NCS Network & NDMA Bulletins</span>
                </div>
            </div>
        </div>
    </aside>

    <button class="hud-toggle-btn" onclick="toggleLeftHud()" title="Open Feed HUD">⚡</button>

    <!-- Right Floating Incident & Emergency Response Command Panel -->
    <aside class="incident-command-panel" id="incidentCommandPanel">
        <div class="panel-header">
            <div style="flex: 1; min-width: 0;">
                <div id="panelSourceBadge" style="display: flex; align-items: center; gap: 6px; margin-bottom: 2px;"></div>
                <div class="panel-title" id="panelTitle">Incident Title</div>
                <div id="panelLocation" style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">📍 Location</div>
            </div>
            <button class="panel-close-btn" onclick="closeIncidentCommandPanel()" title="Close Panel">✕</button>
        </div>

        <div class="panel-body">
            <!-- Telemetry Grid -->
            <div class="telemetry-grid" id="panelTelemetry"></div>

            <!-- External Link -->
            <div id="panelLinkContainer"></div>

            <!-- Rescue Sector Bar -->
            <div class="rescue-sector-bar">
                <div class="rescue-sector-title">
                    <span class="status-dot" style="background: #38bdf8; box-shadow: 0 0 6px #38bdf8;"></span>
                    <span>Emergency Response Network</span>
                </div>
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
                <button class="rescue-tab-btn" id="filter-btn-medical" onclick="filterRescueCategory('medical', this)">🏥 Med (<span id="count-med">0</span>)</button>
                <button class="rescue-tab-btn" id="filter-btn-police" onclick="filterRescueCategory('police', this)">🚔 Police (<span id="count-pol">0</span>)</button>
                <button class="rescue-tab-btn" id="filter-btn-fire" onclick="filterRescueCategory('fire', this)">🚒 Fire (<span id="count-fire">0</span>)</button>
            </div>

            <!-- Nearest Response Route Card -->
            <div id="panelClosestCallout"></div>

            <!-- Discovered Facility Cards -->
            <div id="panelFacilityList" style="display: flex; flex-direction: column; gap: 6px;"></div>
        </div>
    </aside>

    <!-- Floating Expandable Map Legend -->
    <div class="map-legend-hud">
        <div class="legend-item"><span class="legend-dot" style="background: var(--sev-critical);"></span><span>Critical</span></div>
        <div class="legend-item"><span class="legend-dot" style="background: var(--sev-high);"></span><span>High</span></div>
        <div class="legend-item"><span class="legend-dot" style="background: var(--sev-moderate);"></span><span>Mod</span></div>
        <div class="legend-item"><span class="legend-dot" style="background: var(--sev-low);"></span><span>Low</span></div>
        <span style="color: var(--border);">|</span>
        <div class="legend-item"><span>🏥 Med</span></div>
        <div class="legend-item"><span>🚔 Police</span></div>
        <div class="legend-item"><span>🚒 Fire</span></div>
    </div>

    <!-- Client-Side Runtime JavaScript -->
    <script>
        const rawEvents = {events_json};

        // Utility: Extract epoch ms from normalized event
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
            if (sev === 'CRITICAL') return '#ef4444';
            if (sev === 'HIGH') return '#f97316';
            if (sev === 'MODERATE') return '#f59e0b';
            return '#10b981';
        }}

        // Initialize Map
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
            document.querySelectorAll('.controls-group .nav-btn').forEach(b => {{
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
            L.circleMarker(e.latlng, {{ radius: 5, color: '#38bdf8', fillColor: '#ffffff', fillOpacity: 1 }}).addTo(measureLayer);

            if (measurePoints.length === 2) {{
                const p1 = measurePoints[0];
                const p2 = measurePoints[1];
                const dKm = haversineKm(p1.lat, p1.lng, p2.lat, p2.lng);
                L.polyline([p1, p2], {{ color: '#38bdf8', weight: 2.5, dashArray: '6, 6' }}).addTo(measureLayer);

                const midLat = (p1.lat + p2.lat) / 2;
                const midLng = (p1.lng + p2.lng) / 2;

                L.tooltip({{ permanent: true, className: 'leaflet-measure-tip' }})
                    .setLatLng([midLat, midLng])
                    .setContent(`📏 <strong>${{dKm.toFixed(2)}} km</strong> (~${{estimateTravelTimeMin(dKm)}} min drive)`)
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

        function toggleLeftHud() {{
            const hud = document.getElementById('leftHudPanel');
            hud.classList.toggle('collapsed');
        }}

        function switchHudTab(tab) {{
            document.getElementById('tab-feed-btn').className = 'hud-tab ' + (tab === 'feed' ? 'active' : '');
            document.getElementById('tab-intel-btn').className = 'hud-tab ' + (tab === 'intel' ? 'active' : '');
            document.getElementById('hudFeedSection').style.display = tab === 'feed' ? 'flex' : 'none';
            document.getElementById('hudIntelSection').style.display = tab === 'intel' ? 'flex' : 'none';
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

        // Haversine Distance & Travel Estimation
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
                            let icon = '';

                            if (amenity === 'hospital' || amenity === 'clinic' || amenity === 'doctors' || emergency === 'ambulance_station') {{
                                category = 'medical';
                                categoryLabel = amenity === 'hospital' ? 'Hospital / Medical Centre' : 'Clinic / Health Centre';
                                icon = '🏥';
                            }} else if (amenity === 'police') {{
                                category = 'police';
                                categoryLabel = 'Police Station';
                                icon = '🚔';
                            }} else if (amenity === 'fire_station' || emergency === 'fire_service') {{
                                category = 'fire';
                                categoryLabel = 'Fire Station';
                                icon = '🚒';
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
                                icon: icon,
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
                        console.warn('Overpass try error:', ep, e);
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
                const pinIcon = svc.icon || (isMed ? '🏥' : (isPol ? '🚔' : '🚒'));

                const icon = L.divIcon({{
                    className: '',
                    html: `
                        <div class="emergency-service-pin ${{pinClass}}" id="pin-${{svc.id}}" style="width: 28px; height: 28px;">
                            <span>${{pinIcon}}</span>
                        </div>
                    `,
                    iconSize: [28, 28],
                    iconAnchor: [14, 14]
                }});

                const m = L.marker([svc.latitude, svc.longitude], {{ icon: icon, zIndexOffset: 600 }});
                m.bindTooltip(`<strong>${{pinIcon}} ${{svc.name}}</strong><br/><span style="color: #38bdf8; font-family: 'JetBrains Mono'; font-size: 10px;">${{svc.distance_formatted}} from epicenter</span>`, {{
                    direction: 'top',
                    offset: [0, -14],
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

        // Incident Command Panel Controller
        function openIncidentCommandPanel(ev) {{
            currentActiveIncident = ev;
            const lat = ev.latitude || ev.location?.latitude;
            const lon = ev.longitude || ev.location?.longitude;
            if (!lat || !lon) return;

            const safeId = (ev.event_id || ev.alert_id || ev.article_id || ('ev_' + Math.random().toString(36).substring(2, 9))).replace(/[^a-zA-Z0-9_-]/g, '_');

            // Reticle Highlight
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
            const sevColor = getSeverityColor(sev);

            const panel = document.getElementById('incidentCommandPanel');
            panel.classList.add('open');

            const title = isEq ? (ev.region || 'Seismic Incident') : (ev.headline || ev.title || 'Disaster Alert');
            const loc = isEq ? (ev.location_desc || ev.region) : (ev.area_description || [ev.location?.city, ev.location?.state].filter(Boolean).join(', '));

            document.getElementById('panelTitle').textContent = title;
            document.getElementById('panelLocation').textContent = '📍 ' + (loc || 'India');

            let badgeHtml = '';
            if (isEq) {{
                const mag = ev.magnitude || 0;
                badgeHtml = `<span class="tag" style="background: ${{sevColor}}; color: #ffffff;">M ${{mag.toFixed(1)}}</span> <span class="tag tag-ncs">NCS RISEQ</span> <span class="tag ${{ev.relevance === 'INDIA' ? 'tag-ncs' : ''}}">${{ev.relevance || 'REGIONAL'}}</span>`;
            }} else if (isSachet) {{
                badgeHtml = `<span class="tag tag-sachet">NDMA SACHET</span> <span class="tag" style="background: ${{sevColor}}; color: #ffffff;">${{sev}}</span>`;
            }} else {{
                const dType = ev.disaster_type || 'Disaster';
                badgeHtml = `<span class="tag tag-gnews">${{dType.toUpperCase()}}</span> <span class="tag" style="background: ${{sevColor}}; color: #ffffff;">${{sev}}</span>`;
            }}
            document.getElementById('panelSourceBadge').innerHTML = badgeHtml;

            // Telemetry Grid
            let telemetryHtml = '';
            if (isEq) {{
                telemetryHtml = `
                    <div class="telemetry-box"><span class="telemetry-lbl">Hypocenter Depth</span><span class="telemetry-val">${{ev.depth_km}} km</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Review Status</span><span class="telemetry-val" style="color: #38bdf8;">${{ev.status || 'Reviewed'}}</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Coordinates</span><span class="telemetry-val">${{lat.toFixed(3)}}°N, ${{lon.toFixed(3)}}°E</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Time (IST)</span><span class="telemetry-val">${{formatIST12Hour(evEpochMs, ev.origin_time)}}</span></div>
                `;
            }} else if (isSachet) {{
                telemetryHtml = `
                    <div class="telemetry-box"><span class="telemetry-lbl">Hazard Event</span><span class="telemetry-val" style="color: #c084fc;">${{ev.event || ev.disaster_type || 'Alert'}}</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Urgency / Certainty</span><span class="telemetry-val">${{ev.urgency || 'Expected'}} / ${{ev.certainty || 'Likely'}}</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Coordinates</span><span class="telemetry-val">${{lat.toFixed(3)}}°N, ${{lon.toFixed(3)}}°E</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Effective (IST)</span><span class="telemetry-val">${{formatIST12Hour(evEpochMs, ev.effective_at || ev.sent_at)}}</span></div>
                `;
            }} else {{
                telemetryHtml = `
                    <div class="telemetry-box"><span class="telemetry-lbl">Disaster Hazard</span><span class="telemetry-val" style="color: #38bdf8;">${{ev.disaster_type || 'Disaster'}}</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Severity Level</span><span class="telemetry-val">${{sev}}</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Coordinates</span><span class="telemetry-val">${{lat.toFixed(3)}}°N, ${{lon.toFixed(3)}}°E</span></div>
                    <div class="telemetry-box"><span class="telemetry-lbl">Reported (IST)</span><span class="telemetry-val">${{formatIST12Hour(evEpochMs, ev.incident_date || ev.published_at)}}</span></div>
                `;
            }}
            document.getElementById('panelTelemetry').innerHTML = telemetryHtml;

            // Link Container
            let linkHtml = '';
            if (isEq && ev.felt_report_url) {{
                linkHtml = `<a href="${{ev.felt_report_url}}" target="_blank" style="font-size: 11px; color: #38bdf8; text-decoration: none; font-weight: 600;">NCS Felt Report Source &rarr;</a>`;
            }} else if (isSachet && ev.link) {{
                linkHtml = `<a href="${{ev.link}}" target="_blank" style="font-size: 11px; color: #c084fc; text-decoration: none; font-weight: 600;">CAP Alert XML Source &rarr;</a>`;
            }} else if (ev.url) {{
                linkHtml = `<a href="${{ev.url}}" target="_blank" style="font-size: 11px; color: #38bdf8; text-decoration: none; font-weight: 600;">View Source News &rarr;</a>`;
            }}
            document.getElementById('panelLinkContainer').innerHTML = linkHtml;

            loadEmergencyServicesForCommandPanel(lat, lon, currentActiveRadiusM);
        }}

        function closeIncidentCommandPanel() {{
            const panel = document.getElementById('incidentCommandPanel');
            panel.classList.remove('open');
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
                listEl.innerHTML = `<div style="color: var(--text-muted); font-size: 11px; text-align: center; padding: 12px 0;">No ${{currentActiveCategoryFilter}} facilities in this search zone.</div>`;
                return;
            }}

            listEl.innerHTML = items.map(svc => `
                <div class="facility-card" id="fcard-${{svc.id}}" onclick="focusFacilityPin('${{svc.id}}')">
                    <div class="facility-top">
                        <div class="facility-name">${{svc.icon || '🏥'}} ${{svc.name}}</div>
                        <span class="facility-dist-tag">${{svc.distance_formatted}}</span>
                    </div>
                    <div style="font-size: 10px; color: #38bdf8; font-family: 'JetBrains Mono';">🚗 ~${{svc.estimated_time_formatted}} drive from epicenter</div>
                    ${{svc.address ? `<div style="font-size: 10px; color: var(--text-muted); line-height: 1.3;">📍 ${{svc.address}}</div>` : ''}}
                    <div style="display: flex; gap: 6px; margin-top: 2px;">
                        <a href="${{svc.directions_url}}" target="_blank" class="btn-facility-action btn-facility-nav" onclick="event.stopPropagation()">
                            📍 Navigation & Route
                        </a>
                        ${{svc.phone ? `<a href="tel:${{svc.phone.replace(/[^0-9+]/g, '')}}" class="btn-facility-action btn-facility-call" onclick="event.stopPropagation()">📞 Call</a>` : ''}}
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
                <div style="display: flex; align-items: center; gap: 8px; padding: 10px; background: rgba(30, 41, 59, 0.5); border-radius: 6px; font-size: 11px; color: var(--text-secondary);">
                    <span class="status-dot" style="background: #38bdf8; box-shadow: 0 0 6px #38bdf8;"></span>
                    <span>Discovering rescue facilities around epicenter...</span>
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
                    weight: 1.5,
                    opacity: 0.75,
                    fillColor: '#0284c7',
                    fillOpacity: 0.07,
                    dashArray: '5, 5'
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
                        <div style="font-size: 11px; color: var(--text-primary); background: rgba(30, 41, 59, 0.6); border-left: 3px solid #0284c7; padding: 7px 10px; border-radius: 0 4px 4px 0; line-height: 1.4;">
                            <strong>🚀 Nearest Response Hub:</strong> ${{closest.icon || '🏥'}} ${{closest.name}}<br/>
                            <span style="color: #38bdf8; font-family: 'JetBrains Mono'; font-size: 10px;">📍 ${{closest.distance_formatted}} from epicenter • 🚗 ~${{closest.estimated_time_formatted}} drive</span>
                        </div>
                    `;
                }} else {{
                    document.getElementById('panelClosestCallout').innerHTML = '';
                }}

                renderPanelFacilityList();

                if (emergencyLayer.getLayers().length > 0) {{
                    const group = L.featureGroup([L.marker([lat, lon]), ...emergencyLayer.getLayers()]);
                    map.flyToBounds(group.getBounds().pad(0.25), {{
                        paddingTopLeft: [20, 20],
                        paddingBottomRight: [420, 20],
                        duration: 1.0,
                        easeLinearity: 0.25,
                        maxZoom: 14
                    }});
                }}
            }} else {{
                listEl.innerHTML = `
                    <div style="padding: 10px; background: rgba(220, 38, 38, 0.12); border: 1px solid rgba(220, 38, 38, 0.35); border-radius: 6px; color: #fca5a5; font-size: 11px;">
                        <span>Rescue services could not be retrieved for this sector.</span>
                    </div>
                `;
            }}
        }}

        // Render Map Markers
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
                    const size = Math.max(13, Math.min(26, Math.round(mag * 4.5)));

                    const customIcon = L.divIcon({{
                        className: 'clean-pin',
                        html: `
                            <div style="width: ${{size}}px; height: ${{size}}px; border-radius: 50%; background: ${{sevColor}}; border: 2px solid #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.55); display: flex; align-items: center; justify-content: center; font-size: ${{size > 18 ? 10 : 8}}px; font-weight: 800; color: #ffffff; font-family: 'JetBrains Mono';">
                                ${{mag >= 3.0 ? mag.toFixed(1) : ''}}
                            </div>
                        `,
                        iconSize: [size, size],
                        iconAnchor: [size / 2, size / 2]
                    }});

                    const marker = L.marker([lat, lon], {{ icon: customIcon }});
                    marker.bindTooltip(`<strong>M ${{mag.toFixed(1)}} Earthquake</strong><br/>${{ev.region || 'Seismic Event'}}<br/><span style="color: #38bdf8; font-size: 9.5px;">⚡ Click for Emergency Command Panel</span>`, {{
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
                        className: 'sachet-pin',
                        html: `<div style="width: 18px; height: 18px; border-radius: 4px; background: ${{sevColor}}; border: 2px solid #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.55); display: flex; align-items: center; justify-content: center; font-size: 10px; color: #ffffff; font-weight: 800;">!</div>`,
                        iconSize: [18, 18],
                        iconAnchor: [9, 9]
                    }});

                    const marker = L.marker([lat, lon], {{ icon: customIcon }});
                    marker.bindTooltip(`<strong>NDMA SACHET: ${{ev.headline || dType}}</strong><br/>${{ev.area_description || 'India'}}<br/><span style="color: #c084fc; font-size: 9.5px;">⚡ Click for Emergency Command Panel</span>`, {{
                        direction: 'top',
                        offset: [0, -9],
                        className: 'leaflet-measure-tip'
                    }});

                    marker.on('click', () => openIncidentCommandPanel(ev));

                    if (useClustering) clusterGroup.addLayer(marker);
                    else plainGroup.addLayer(marker);

                    markersMap.set(ev.event_id || ev.alert_id, marker);

                }} else {{
                    const dType = ev.disaster_type || 'Disaster';
                    const customIcon = L.divIcon({{
                        className: 'news-pin',
                        html: `<div style="width: 14px; height: 14px; border-radius: 50%; background: ${{sevColor}}; border: 2px solid #ffffff; box-shadow: 0 2px 5px rgba(0,0,0,0.5);"></div>`,
                        iconSize: [14, 14],
                        iconAnchor: [7, 7]
                    }});

                    const marker = L.marker([lat, lon], {{ icon: customIcon }});
                    marker.bindTooltip(`<strong>${{dType.toUpperCase()}}: ${{ev.title || 'Incident'}}</strong><br/><span style="color: #38bdf8; font-size: 9.5px;">⚡ Click for Emergency Command Panel</span>`, {{
                        direction: 'top',
                        offset: [0, -7],
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
            document.getElementById('feedCountBadge').innerText = `${{items.length}}`;

            if (items.length === 0) {{
                list.innerHTML = '<div style="color: var(--text-muted); text-align: center; margin-top: 30px; font-size: 11px;">No incidents matching active filters.</div>';
                return;
            }}

            items.forEach(ev => {{
                const isEq = ev.source_group === 'NCS_RISEQ';
                const isSachet = ev.source_group === 'NDMA_SACHET';
                const sev = getEventSeverity(ev);
                const sevColor = getSeverityColor(sev);

                const card = document.createElement('div');
                card.className = 'event-card ' + (isEq ? 'card-ncs' : (isSachet ? 'card-sachet' : 'card-gnews'));

                let sourceTag = 'GNews AI';
                let tagClass = 'tag-gnews';
                if (isEq) {{ sourceTag = 'NCS RISEQ'; tagClass = 'tag-ncs'; }}
                else if (isSachet) {{ sourceTag = 'NDMA SACHET'; tagClass = 'tag-sachet'; }}

                const title = isEq ? (ev.region || 'Seismic Incident') : (ev.headline || ev.title || 'Disaster Alert');
                const loc = isEq ? (ev.location_desc || ev.region) : (ev.area_description || [ev.location?.city, ev.location?.state].filter(Boolean).join(', '));
                
                const evEpochMs = getEventTimeEpoch(ev);
                const istCardTime = formatIST12Hour(evEpochMs, ev.unified_time);
                const timeAgo = formatTimeAgo(evEpochMs, istCardTime);

                let badgeHtml = '';
                if (isEq) {{
                    badgeHtml = `<span class="tag" style="background: ${{sevColor}}; color: #ffffff;">M ${{Number(ev.magnitude || 0).toFixed(1)}}</span>`;
                }} else {{
                    badgeHtml = `<span class="tag" style="background: ${{sevColor}}; color: #ffffff;">${{sev}}</span>`;
                }}

                card.innerHTML = `
                    <div class="card-meta-row">
                        <span class="tag ${{tagClass}}">${{sourceTag}}</span>
                        <span style="font-size: 9.5px; color: #38bdf8; font-family: 'JetBrains Mono';">${{timeAgo}}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px; margin-top: 3px;">
                        ${{badgeHtml}}
                        <div style="font-weight: 700; font-size: 11.5px; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1;">
                            ${{title}}
                        </div>
                    </div>
                    <div style="font-size: 10px; color: var(--text-secondary); margin-top: 3px;">📍 ${{loc || 'India'}}</div>
                `;

                card.onclick = () => {{
                    document.querySelectorAll('.event-card').forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    openIncidentCommandPanel(ev);
                }};

                list.appendChild(card);
            }});
        }}

        // Calculate & Render Situational Intelligence
        function updateSituationalIntelligence(items) {{
            let crit = 0, high = 0, mod = 0, low = 0;
            const stateSet = new Set();
            const hazardCounts = {{}};

            items.forEach(ev => {{
                const sev = getEventSeverity(ev);
                if (sev === 'CRITICAL') crit++;
                else if (sev === 'HIGH') high++;
                else if (sev === 'MODERATE') mod++;
                else low++;

                const loc = ev.location || {{}};
                const state = loc.state || ev.region;
                if (state) stateSet.add(state.trim());

                const hazard = ev.disaster_type || (ev.source_group === 'NCS_RISEQ' ? 'Earthquake' : (ev.event || 'Hazard'));
                hazardCounts[hazard] = (hazardCounts[hazard] || 0) + 1;
            }});

            const total = items.length;
            document.getElementById('intel-total').textContent = total;
            document.getElementById('intel-regions').textContent = stateSet.size;
            document.getElementById('intel-crit-count').textContent = `${{crit}} Critical`;

            document.getElementById('lbl-crit').textContent = crit;
            document.getElementById('lbl-high').textContent = high;
            document.getElementById('lbl-mod').textContent = mod;
            document.getElementById('lbl-low').textContent = low;

            if (total > 0) {{
                document.getElementById('stack-crit').style.width = `${{(crit / total) * 100}}%`;
                document.getElementById('stack-high').style.width = `${{(high / total) * 100}}%`;
                document.getElementById('stack-mod').style.width = `${{(mod / total) * 100}}%`;
                document.getElementById('stack-low').style.width = `${{(low / total) * 100}}%`;
            }}

            let topHazard = 'Seismic Activity';
            let maxHCount = 0;
            for (const [h, count] of Object.entries(hazardCounts)) {{
                if (count > maxHCount) {{
                    maxHCount = count;
                    topHazard = h;
                }}
            }}
            document.getElementById('intel-hazard').textContent = topHazard;
            document.getElementById('intel-hazard-desc').textContent = `${{maxHCount}} active records in current scope`;
        }}

        function filterBySource(src) {{
            activeSource = src;
            document.querySelectorAll('.source-pill-grid .source-btn').forEach(b => b.classList.remove('active'));
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

            const chips = [];
            if (activeSource !== 'ALL') chips.push({{ label: activeSource, type: 'source' }});
            if (timeVal !== 'ALL') chips.push({{ label: timeVal, type: 'time' }});
            if (sevVal !== 'ALL') chips.push({{ label: sevVal, type: 'sev' }});
            if (search) chips.push({{ label: `"${{search}}"`, type: 'search' }});

            const chipsBar = document.getElementById('activeChipsBar');
            if (chips.length > 0) {{
                chipsBar.innerHTML = chips.map(c => `
                    <span class="filter-chip">
                        <span>${{c.label}}</span>
                    </span>
                `).join('') + `<span class="chip-remove" onclick="clearFilters()" style="margin-left: auto; font-size: 10px; font-weight: 700; color: #38bdf8;">Clear All</span>`;
            }} else {{
                chipsBar.innerHTML = `<span style="font-size: 9.5px; color: var(--text-muted);">All ${{rawEvents.length}} records active in current view</span>`;
            }}

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
            updateSituationalIntelligence(filtered);
        }}

        function clearFilters() {{
            document.getElementById('searchInput').value = '';
            document.getElementById('timeFilter').value = 'ALL';
            document.getElementById('severityFilter').value = 'ALL';
            activeSource = 'ALL';
            document.querySelectorAll('.source-pill-grid .source-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('src-all').classList.add('active');
            applyAllFilters();
        }}

        // Initial Load
        renderMarkers(rawEvents);
        renderFeed(rawEvents);
        updateSituationalIntelligence(rawEvents);
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
