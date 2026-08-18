"""
DISHA Temporary UI Map Generator
Pulls live disaster events from MongoDB Atlas and renders an interactive Leaflet map UI
saved to BACKEND/tests/temp_disaster_map.html.
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
    """Fetches all classified disaster events and ensures coordinate resolution."""
    raw_events = list(db["disaster_events"].find({}, {"_id": 0}))
    prepared = []

    for ev in raw_events:
        loc = ev.get("location") or {}
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        state = loc.get("state")
        city = loc.get("city")
        district = loc.get("district")

        # Resolve coordinates if missing but state/city/district available
        if (lat is None or lon is None) and (state or city or district):
            res_lat, res_lon, prec = geocode_location(country="India", state=state, city=city, district=district)
            if res_lat is not None and res_lon is not None:
                lat, lon = res_lat, res_lon
                loc["latitude"] = lat
                loc["longitude"] = lon
                loc["precision"] = prec

        if lat is not None and lon is not None:
            prepared.append(ev)

    return prepared, len(raw_events)


def build_map_html(events, total_raw_events):
    """Generates a standalone, beautiful Leaflet UI map HTML file."""
    events_json = json.dumps(events, default=str)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DISHA - Disaster Intelligence Situational Map</title>
    
    <!-- Leaflet CSS & JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --bg-primary: #0b0f19;
            --bg-secondary: #131b2e;
            --bg-card: rgba(19, 27, 46, 0.92);
            --border-color: #1f2d4d;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --accent-blue: #3b82f6;
            --accent-cyan: #06b6d4;
            --sev-critical: #ef4444;
            --sev-high: #f97316;
            --sev-medium: #eab308;
            --sev-low: #10b981;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        /* Header Navigation */
        header {{
            background: linear-gradient(180deg, #111827 0%, #0b0f19 100%);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 1000;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .brand-badge {{
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            font-weight: 800;
            font-size: 13px;
            letter-spacing: 1px;
            padding: 4px 8px;
            border-radius: 6px;
            box-shadow: 0 0 12px rgba(239, 68, 68, 0.4);
        }}

        .brand h1 {{
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.3px;
        }}

        .brand-sub {{
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 1px;
        }}

        /* Quick Stats */
        .stats-bar {{
            display: flex;
            gap: 16px;
        }}

        .stat-item {{
            background: rgba(31, 41, 55, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 6px 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .stat-value {{
            font-size: 15px;
            font-weight: 700;
            color: var(--accent-cyan);
            font-family: 'JetBrains Mono', monospace;
        }}

        .stat-label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* Main Container */
        .main-container {{
            display: flex;
            flex: 1;
            position: relative;
            height: calc(100vh - 65px);
        }}

        /* Map */
        #map {{
            flex: 1;
            height: 100%;
            background-color: #0b0f19;
        }}

        /* Control Sidebar */
        .sidebar {{
            width: 380px;
            background: var(--bg-secondary);
            border-left: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            z-index: 500;
            box-shadow: -4px 0 20px rgba(0, 0, 0, 0.3);
        }}

        .sidebar-header {{
            padding: 16px;
            border-bottom: 1px solid var(--border-color);
        }}

        .search-box {{
            width: 100%;
            background: #0b0f19;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 10px 12px;
            color: var(--text-main);
            font-size: 13px;
            outline: none;
            transition: border-color 0.2s;
        }}

        .search-box:focus {{
            border-color: var(--accent-blue);
        }}

        .filters-row {{
            display: flex;
            gap: 8px;
            margin-top: 10px;
        }}

        select {{
            flex: 1;
            background: #0b0f19;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 10px;
            color: var(--text-main);
            font-size: 12px;
            outline: none;
            cursor: pointer;
        }}

        .events-list {{
            flex: 1;
            overflow-y: auto;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .event-card {{
            background: rgba(11, 15, 25, 0.75);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .event-card:hover {{
            border-color: var(--accent-blue);
            transform: translateY(-2px);
            background: rgba(30, 41, 59, 0.8);
        }}

        .card-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}

        .type-badge {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            padding: 2px 8px;
            border-radius: 4px;
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }}

        .sev-badge {{
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            padding: 2px 6px;
            border-radius: 4px;
        }}

        .sev-critical {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }}
        .sev-high {{ background: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid rgba(249, 115, 22, 0.4); }}
        .sev-medium {{ background: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.4); }}
        .sev-low {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }}

        .card-title {{
            font-size: 13px;
            font-weight: 600;
            line-height: 1.4;
            color: #f1f5f9;
            margin-bottom: 6px;
        }}

        .card-meta {{
            font-size: 11px;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        /* Custom Leaflet Popup */
        .leaflet-popup-content-wrapper {{
            background: var(--bg-card) !important;
            backdrop-filter: blur(12px);
            color: var(--text-main) !important;
            border: 1px solid var(--border-color);
            border-radius: 12px !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
            padding: 6px;
        }}

        .leaflet-popup-tip {{
            background: var(--bg-card) !important;
            border: 1px solid var(--border-color);
        }}

        .popup-content {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 13px;
            line-height: 1.5;
            max-width: 320px;
        }}

        .popup-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 8px;
            margin-bottom: 8px;
        }}

        .popup-title {{
            font-size: 14px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 6px;
        }}

        .popup-reason {{
            font-size: 12px;
            color: #cbd5e1;
            margin-bottom: 8px;
            background: rgba(15, 23, 42, 0.5);
            padding: 6px 8px;
            border-radius: 6px;
            border-left: 3px solid var(--accent-blue);
        }}

        .popup-evidence-title {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--accent-cyan);
            margin-bottom: 4px;
        }}

        .popup-evidence-list {{
            list-style: none;
            margin-bottom: 8px;
        }}

        .popup-evidence-list li {{
            font-size: 11px;
            color: #94a3b8;
            padding-left: 12px;
            position: relative;
            margin-bottom: 2px;
        }}

        .popup-evidence-list li::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: var(--accent-cyan);
        }}

        .popup-footer {{
            border-top: 1px solid var(--border-color);
            padding-top: 6px;
            margin-top: 6px;
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: var(--text-muted);
        }}

        .popup-link {{
            color: #60a5fa;
            text-decoration: none;
            font-weight: 600;
        }}

        .popup-link:hover {{
            text-decoration: underline;
        }}

        /* Custom Markers */
        .custom-pin {{
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            border: 2px solid #ffffff;
            box-shadow: 0 0 10px rgba(0,0,0,0.5);
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0% {{ transform: scale(0.95); opacity: 0.9; }}
            50% {{ transform: scale(1.1); opacity: 1; }}
            100% {{ transform: scale(0.95); opacity: 0.9; }}
        }}
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <span class="brand-badge">DISHA</span>
            <div>
                <h1>Disaster Intelligence & Hazard Awareness Map</h1>
                <div class="brand-sub">Real-Time Situational Ground Truth & Verified Events</div>
            </div>
        </div>

        <div class="stats-bar">
            <div class="stat-item">
                <span class="stat-value" id="stat-total">0</span>
                <span class="stat-label">Mapped Events</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" id="stat-critical">0</span>
                <span class="stat-label">Critical / High</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" id="stat-states">0</span>
                <span class="stat-label">States Impacted</span>
            </div>
        </div>
    </header>

    <div class="main-container">
        <div id="map"></div>

        <div class="sidebar">
            <div class="sidebar-header">
                <input type="text" id="searchInput" class="search-box" placeholder="Search event title, district, state..." />
                
                <div class="filters-row">
                    <select id="typeFilter">
                        <option value="all">All Disaster Types</option>
                    </select>

                    <select id="severityFilter">
                        <option value="all">All Severities</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>
            </div>

            <div class="events-list" id="eventsList"></div>
        </div>
    </div>

    <script>
        const eventsData = {events_json};
        
        // Initialize Map centered on India
        const map = L.map('map', {{
            center: [22.5937, 78.9629],
            zoom: 5,
            zoomControl: true
        }});

        // Dark Theme Tile Layer
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://carto.com/">CARTO</a> | DISHA Intelligence',
            maxZoom: 18,
            subdomains: 'abcd'
        }}).addTo(map);

        const markerClusterGroup = L.markerClusterGroup({{
            chunkedLoading: true,
            maxClusterRadius: 35,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false
        }});
        map.addLayer(markerClusterGroup);

        const markersMap = new Map();

        // Helper: Get color by severity
        function getSeverityColor(sev) {{
            switch ((sev || '').toLowerCase()) {{
                case 'critical': return '#ef4444';
                case 'high': return '#f97316';
                case 'medium': return '#eab308';
                case 'low': return '#10b981';
                default: return '#3b82f6';
            }}
        }}

        // Populate Types Dropdown
        const typesSet = new Set();
        const statesSet = new Set();
        let criticalCount = 0;

        eventsData.forEach(ev => {{
            if (ev.disaster_type) typesSet.add(ev.disaster_type);
            if (ev.location && ev.location.state) statesSet.add(ev.location.state);
            const sev = (ev.severity || '').toLowerCase();
            if (sev === 'critical' || sev === 'high') criticalCount++;
        }});

        document.getElementById('stat-total').innerText = eventsData.length;
        document.getElementById('stat-critical').innerText = criticalCount;
        document.getElementById('stat-states').innerText = statesSet.size;

        const typeSelect = document.getElementById('typeFilter');
        typesSet.forEach(t => {{
            const opt = document.createElement('option');
            opt.value = t;
            opt.innerText = t.replace('_', ' ').toUpperCase();
            typeSelect.appendChild(opt);
        }});

        // Render Markers
        function renderMarkers(filteredEvents) {{
            markerClusterGroup.clearLayers();
            markersMap.clear();

            filteredEvents.forEach(ev => {{
                const lat = ev.location?.latitude;
                const lon = ev.location?.longitude;
                if (!lat || !lon) return;

                const color = getSeverityColor(ev.severity);
                
                const customIcon = L.divIcon({{
                    className: 'custom-div-icon',
                    html: `<div class="custom-pin" style="background-color: ${{color}}; width: 16px; height: 16px;"></div>`,
                    iconSize: [16, 16],
                    iconAnchor: [8, 8]
                }});

                const marker = L.marker([lat, lon], {{ icon: customIcon }});

                const evidenceListHtml = (ev.evidence || [])
                    .slice(0, 3)
                    .map(e => `<li>${{e}}</li>`)
                    .join('');

                const popupHtml = `
                    <div class="popup-content">
                        <div class="popup-header">
                            <span class="type-badge">${{ev.disaster_type?.toUpperCase() || 'DISASTER'}}</span>
                            <span class="sev-badge sev-${{ev.severity || 'unknown'}}">${{ev.severity?.toUpperCase() || 'UNKNOWN'}}</span>
                        </div>
                        <div class="popup-title">${{ev.title || 'Disaster Incident'}}</div>
                        ${{ev.reason ? `<div class="popup-reason">${{ev.reason}}</div>` : ''}}
                        ${{evidenceListHtml ? `
                            <div class="popup-evidence-title">Verified Observations:</div>
                            <ul class="popup-evidence-list">${{evidenceListHtml}}</ul>
                        ` : ''}}
                        <div class="popup-footer">
                            <span>📍 ${{ev.location?.city ? ev.location.city + ', ' : ''}}${{ev.location?.state || 'India'}}</span>
                            ${{ev.url ? `<a href="${{ev.url}}" target="_blank" class="popup-link">Source Article ↗</a>` : ''}}
                        </div>
                    </div>
                `;

                marker.bindPopup(popupHtml);
                markerClusterGroup.addLayer(marker);
                markersMap.set(ev.event_id || ev.article_id, marker);
            }});
        }}

        // Render Sidebar Cards
        function renderSidebarCards(filteredEvents) {{
            const listEl = document.getElementById('eventsList');
            listEl.innerHTML = '';

            if (filteredEvents.length === 0) {{
                listEl.innerHTML = '<div style="color: var(--text-muted); text-align: center; margin-top: 40px;">No matching disaster events found.</div>';
                return;
            }}

            filteredEvents.forEach(ev => {{
                const card = document.createElement('div');
                card.className = 'event-card';
                
                const locStr = [ev.location?.district || ev.location?.city, ev.location?.state].filter(Boolean).join(', ') || 'India';
                const dateStr = ev.incident_date || (ev.published_at ? ev.published_at.substring(0, 16) : 'Recent');

                card.innerHTML = `
                    <div class="card-top">
                        <span class="type-badge">${{ev.disaster_type?.toUpperCase() || 'EVENT'}}</span>
                        <span class="sev-badge sev-${{ev.severity || 'unknown'}}">${{ev.severity?.toUpperCase() || 'UNKNOWN'}}</span>
                    </div>
                    <div class="card-title">${{ev.title || 'Disaster Alert'}}</div>
                    <div class="card-meta">
                        <span>📍 ${{locStr}}</span>
                        <span>📅 ${{dateStr}}</span>
                    </div>
                `;

                card.onclick = () => {{
                    const m = markersMap.get(ev.event_id || ev.article_id);
                    if (m && ev.location?.latitude && ev.location?.longitude) {{
                        map.flyTo([ev.location.latitude, ev.location.longitude], 10, {{ duration: 1.2 }});
                        markerClusterGroup.zoomToShowLayer(m, () => {{
                            m.openPopup();
                        }});
                    }}
                }};

                listEl.appendChild(card);
            }});
        }}

        // Filtering Logic
        function applyFilters() {{
            const searchVal = document.getElementById('searchInput').value.toLowerCase().trim();
            const typeVal = document.getElementById('typeFilter').value;
            const sevVal = document.getElementById('severityFilter').value;

            const filtered = eventsData.filter(ev => {{
                if (typeVal !== 'all' && ev.disaster_type !== typeVal) return false;
                if (sevVal !== 'all' && (ev.severity || '').toLowerCase() !== sevVal) return false;

                if (searchVal) {{
                    const titleMatch = (ev.title || '').toLowerCase().includes(searchVal);
                    const stateMatch = (ev.location?.state || '').toLowerCase().includes(searchVal);
                    const cityMatch = (ev.location?.city || '').toLowerCase().includes(searchVal);
                    const distMatch = (ev.location?.district || '').toLowerCase().includes(searchVal);
                    const reasonMatch = (ev.reason || '').toLowerCase().includes(searchVal);
                    if (!titleMatch && !stateMatch && !cityMatch && !distMatch && !reasonMatch) return false;
                }}

                return true;
            }});

            renderMarkers(filtered);
            renderSidebarCards(filtered);
        }}

        document.getElementById('searchInput').addEventListener('input', applyFilters);
        document.getElementById('typeFilter').addEventListener('change', applyFilters);
        document.getElementById('severityFilter').addEventListener('change', applyFilters);

        // Initial Load
        renderMarkers(eventsData);
        renderSidebarCards(eventsData);
    </script>
</body>
</html>
"""
    return html


def generate_map(open_browser: bool = False):
    """Main execution to generate temp map UI."""
    print("[DISHA MAP] Fetching disaster events from MongoDB...")
    events, total_raw = fetch_and_prepare_events()
    print(f"[DISHA MAP] Retrieved {total_raw} total events, {len(events)} geocoded for map rendering.")

    output_path = Path(__file__).resolve().parent / "temp_disaster_map.html"
    html_content = build_map_html(events, total_raw)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[DISHA MAP] Successfully generated interactive UI map: {output_path}")

    if open_browser:
        webbrowser.open(f"file://{output_path.resolve()}")

    return str(output_path)


if __name__ == "__main__":
    generate_map(open_browser=False)
