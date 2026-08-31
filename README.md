# DISHA-PLATFORM

**Disaster Intelligence and Situational Hazard Awareness Platform** — a full-stack web application that aggregates, verifies, and visualizes real-time disaster and emergency data for India, combining government data feeds, AI-assisted news verification, and citizen incident reporting on an interactive map.

Live deployment: [disha-platform.vercel.app](https://disha-platform.vercel.app) (frontend) · API on Render (backend)

---

## Overview

DISHA ingests disaster-related information from multiple official and open sources — India's National Center for Seismology (earthquakes), NDMA's SACHET alert system (government warnings), and news feeds cross-checked by Google's Gemini model — and unifies them into a single, filterable event feed. It also lets signed-in citizens submit their own incident reports with location and photo evidence, and surfaces nearby emergency services (hospitals, police, fire stations) for a given location.

The project is organized as a two-service monorepo:

- **`BACKEND/`** — a Python FastAPI service that runs the data-ingestion pipelines, exposes a REST API, and talks to MongoDB.
- **`FRONTEND/`** — a React + Vite single-page application that consumes the API and renders the map, dashboards, and forms.

---

## Key Features

**Implemented and verified in the repository:**

- **Unified disaster event feed** (`/api/events`) merging earthquakes, NDMA SACHET alerts, and AI-verified news into one normalized dataset.
- **Live interactive map** on the landing page (`LiveDisasterMap.jsx`) built directly on the core [Leaflet](https://leafletjs.com/) library, with severity/category styling, time-range filtering, and an emergency-services overlay.
- **Earthquake ingestion** from the official NCS RISEQ portal (`app/sources/riseq.py`), with UTC normalization and India-relevance filtering.
- **NDMA SACHET CAP alert ingestion** (`app/sources/sachet.py`) — parses the official RSS/CAP XML feed with ETag caching and polygon extraction.
- **AI-assisted news verification pipeline** (`fetch_gnews.py` + `gemini_controller.py`) — pulls news via RSS/feedparser, then classifies/verifies candidate disaster events using the Gemini API (quota-managed with automatic model fallback), combined with a custom source-scoring and temporal-recency scoring system, and offline geocoding of Indian states/districts/known hotspots.
- **Citizen incident reporting** — authenticated users can submit incident reports (event type, description, photo evidence, geolocation) via `POST /api/incidents/report`, view their own submissions, and browse recent reports.
- **Nearby emergency services lookup** — queries the OpenStreetMap **Overpass API** for hospitals, police, and fire stations near a coordinate, with Haversine-distance ranking, multi-endpoint fallback, and in-memory TTL caching.
- **Google OAuth2 authentication** with JWT access/refresh tokens, server-side session storage in MongoDB, and refresh-token rotation.
- **Analytics/KPI overview** endpoints for a dashboard summary of disaster intelligence data (`/api/analysis/overview`, `/api/analysis/data`).

**Partially implemented / present in code but not fully wired up** (do not assume these work end-to-end):

- **Email/password authentication** — the `User` model includes a `password_hash` field, and Argon2id/bcrypt hashing utilities exist in `core/security.py`, along with an OTP model and OTP service (Brevo email API integration). However, no route in `app/routes/auth.py` exposes a password-based signup/login or OTP-verification flow — **only Google OAuth login is reachable from the API**.
- **Standalone fullscreen map page** — `FRONTEND/src/pages/ViewMapPage.jsx` is an explicit placeholder, commented in the source as *"Empty Page Container for Future Implementation."*
- **Earthquake auto-sync** — disabled by default (`RISEQ_ENABLED=false` in `.env.example`); SACHET sync is enabled by default (`SACHET_ENABLED=true`).
- **`react-leaflet`** is listed in `package.json` but is not imported anywhere in the codebase; the actual map implementation uses the core `leaflet` package directly.

---

## System Architecture

```
                     ┌───────────────────────────┐
                     │        FRONTEND           │
                     │  React 19 + Vite + Tailwind│
                     │  (Vercel)                 │
                     └─────────────┬─────────────┘
                                   │  REST calls (fetch, VITE_API_URL)
                                   ▼
                     ┌───────────────────────────┐
                     │        BACKEND            │
                     │  FastAPI (app/main.py)    │
                     │  (Render)                 │
                     │                            │
                     │  routes/ → services/ →     │
                     │  repositories/ → database/ │
                     └──┬───────┬───────┬────────┘
                        │       │       │
        ┌───────────────┘       │       └────────────────┐
        ▼                       ▼                        ▼
┌───────────────┐     ┌──────────────────┐      ┌──────────────────┐
│ MongoDB Atlas │     │ External Data     │      │ External Services│
│ (motor/pymongo)│    │ Sources:          │      │ - Google OAuth2  │
│ users, sessions│    │ - NCS RISEQ       │      │ - Gemini API      │
│ incidents,     │    │   (earthquakes)   │      │ - OSM Overpass API│
│ news, alerts   │    │ - NDMA SACHET     │      │   (emergency svcs)│
└───────────────┘     │   (CAP RSS/XML)   │      │ - Nominatim        │
                       │ - News RSS feeds  │      │   (reverse geocode)│
                       └──────────────────┘      │ - Brevo (email/OTP)│
                                                  └──────────────────┘
```

**Data flow:**
1. Background/on-demand pipelines (`services/earthquake_service.py`, `services/sachet_service.py`, `services/fetch_gnews.py`) scrape or fetch from external sources.
2. News candidates are pre-filtered, geocoded, temporally scored, and sent in batches to the Gemini API for verification/classification (`gemini_controller.py`), then deduplicated (`event_clustering.py`).
3. Verified records are written to MongoDB collections.
4. FastAPI routes (`routes/*.py`) read from MongoDB via `repositories/` and serve normalized JSON to the frontend.
5. The React frontend (`services/api.js`) fetches from these endpoints, normalizes events (`utils/eventNormalizer.js`), and renders them on the Leaflet map, analysis dashboards, and list pages.
6. Citizen-submitted incident reports flow the opposite direction: frontend form → `POST /api/incidents/report` → `IncidentRepository` → MongoDB, then surfaced back through `GET /api/incidents/recent` and the nearby-emergency-services lookup (which uses the incident's coordinates against the Overpass API).

---

## Technology Stack

**Backend**
- Python 3.11, [FastAPI](https://fastapi.tiangolo.com/), Starlette, Uvicorn
- Pydantic v2 / pydantic-settings for config and schemas
- MongoDB via `motor` (async) and `pymongo` (sync — used for legacy ingestion pipelines, per in-code comments)
- Authentication: `PyJWT`, `argon2-cffi`, `bcrypt`, `Authlib` (Google OAuth2), `itsdangerous`, `starlette.SessionMiddleware`
- Ingestion & parsing: `requests`, `beautifulsoup4`, `lxml`, `feedparser`
- Geospatial: `geopandas`, `shapely`, `pyproj`, `folium` (declared dependencies; primary in-app geospatial math — Haversine distance, centroid geocoding — is hand-implemented rather than relying on these libraries for the live API paths)
- AI verification: `google-genai` (Gemini API client)
- Testing: `pytest`, `pytest-asyncio`, `httpx`

**Frontend**
- React 19, Vite 6, TypeScript config (source files are `.jsx`)
- Tailwind CSS 4
- Leaflet (core library) for mapping
- `framer-motion` / `motion` for animation
- `lucide-react` for icons
- `@google/genai` (declared as a frontend dependency — leftover from an AI Studio–generated scaffold; the app's actual Gemini usage is backend-side)

**Infrastructure**
- Frontend hosted on **Vercel**
- Backend hosted on **Render**
- Database: **MongoDB Atlas**
- No Docker configuration or CI/CD workflows are present in the repository at this time.

---

## Project Structure

```
DISHA-platform/
├── BACKEND/
│   ├── main.py                    # Entrypoint wrapper → app.main:app
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                # FastAPI app factory, middleware, router registration
│   │   ├── core/                  # config.py, database.py, security.py
│   │   ├── database/mongodb.py    # Sync MongoDB client/index setup
│   │   ├── dependencies/          # auth.py (JWT guard), rate_limiter.py
│   │   ├── models/                # Pydantic DB models (user, incident_report, otp, session)
│   │   ├── repositories/          # MongoDB data-access layer
│   │   ├── routes/                # auth, incidents, events, earthquakes, sachet, gnews,
│   │   │                          #   emergency_services, analysis
│   │   ├── schemas/                # Request/response schemas
│   │   ├── services/               # Business logic + ingestion pipelines (see below)
│   │   ├── sources/                # riseq.py, sachet.py — raw external scrapers
│   │   └── utils/
│   ├── tests/                      # pytest suites for auth, incidents, news, pipelines
│   ├── data/                       # Sample/working CSV outputs from the news pipeline
│   └── *.xml                       # Sample CAP/SACHET payloads used in testing
├── FRONTEND/
│   ├── src/
│   │   ├── pages/                  # LandingPage, AuthPage, AlertsPage, AnalysisPage,
│   │   │                          #   ReportIncidentPage, NearbyIncidentsPage, NewsDetailPage,
│   │   │                          #   RecentNewsPage, ViewMapPage (placeholder)
│   │   ├── components/             # charts/, common/ (ErrorBoundary, NotificationToast, CitySelector)
│   │   ├── context/AuthContext.jsx
│   │   ├── services/api.js         # Central API client
│   │   ├── config/eventConfig.js
│   │   ├── utils/                  # dateTime, eventNormalizer, htmlSanitizer
│   │   └── assets/                 # logo, hero image, static India map image
│   ├── vite.config.js              # Dev proxy: /api → http://127.0.0.1:8000
│   └── vercel.json
├── requirements.txt                 # Duplicate of BACKEND/requirements.txt
├── vercel.json
└── LICENSE
```

---

## How It Works

1. **Ingestion:** Scheduled/triggerable pipelines pull data from NCS RISEQ, NDMA SACHET, and news RSS feeds.
2. **Verification:** News items pass through geocoding, source-quality scoring, temporal-recency scoring, and Gemini-based AI classification before being marked verified.
3. **Storage:** Verified events, incident reports, users, sessions, and OTP records are persisted in MongoDB Atlas.
4. **API layer:** FastAPI exposes normalized, filterable endpoints for events, earthquakes, SACHET alerts, news, incidents, and emergency services.
5. **Presentation:** The React frontend fetches from these endpoints and renders a live Leaflet map, a KPI/analytics dashboard, and list/detail views, with client-side normalization to reconcile the differing shapes of earthquake / SACHET / news documents.
6. **Citizen input loop:** Authenticated users can add their own incident reports, which become part of the same pipeline of location-tagged, categorized events.

---

## Installation

### Prerequisites
- **Node.js** (for the frontend — Vite 6 / React 19 require a recent LTS version)
- **Python 3.11** (pinned via `BACKEND/.python-version`)
- A **MongoDB** instance (MongoDB Atlas connection string, or a local MongoDB server)
- API credentials for the services you want to enable (Google OAuth2, Gemini API, Brevo — see below)

### Clone and install dependencies

```bash
git clone https://github.com/Chitransh-22/DISHA-platform.git
cd DISHA-platform
```

> **Note:** the repository's [LICENSE](#license) restricts copying, cloning, and reuse of the source code without written permission from the DISHA-PLATFORM Team — see the [License](#license) section before using this command outside of authorized access.

**Backend:**
```bash
cd BACKEND
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # then fill in your credentials
```

**Frontend:**
```bash
cd FRONTEND
npm install
cp .env.example .env           # then set VITE_API_URL if needed
```

---

## Environment Variables

Values below are taken directly from `BACKEND/.env.example` and `FRONTEND/.env.example`.

### Backend (`BACKEND/.env`)

| Variable | Purpose |
|---|---|
| `ENV`, `HOST`, `PORT`, `DEBUG` | Server runtime configuration |
| `FRONTEND_URL`, `BACKEND_URL`, `ALLOWED_ORIGINS` | CORS / deployment URL wiring |
| `MONGO_URI`, `MONGO_DB` | MongoDB Atlas connection string and database name |
| `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | JWT auth configuration |
| `OTP_EXPIRE_MINUTES`, `OTP_MAX_ATTEMPTS` | OTP settings (scaffolded — not currently exposed via a route) |
| `COOKIE_NAME`, `COOKIE_SECURE`, `COOKIE_SAMESITE`, `COOKIE_PATH` | Refresh-token cookie configuration |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | Google OAuth2 sign-in |
| `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME` | Transactional email/OTP delivery (falls back to console-logging OTPs in local dev if unset) |
| `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_BATCH_SIZE`, `NEWS_RESULTS_PER_QUERY`, `GEMINI_CONFIDENCE_THRESHOLD`, `GEMINI_AUTO_VERIFY_THRESHOLD` | AI news-verification pipeline |
| `RISEQ_ENABLED`, `SACHET_ENABLED` | Toggle earthquake / SACHET ingestion pipelines |

### Frontend (`FRONTEND/.env`)

| Variable | Purpose |
|---|---|
| `VITE_API_URL` | Base URL of the backend API. Leave empty locally to use the Vite dev proxy (`/api` → `http://127.0.0.1:8000`); set to the deployed backend URL in production. |

---

## Running Locally

**Backend** (from `BACKEND/`):
```bash
python main.py
# or
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
The API will be available at `http://127.0.0.1:8000`, with interactive docs at `/docs` (Swagger) and `/redoc`.

**Frontend** (from `FRONTEND/`):
```bash
npm run dev
```
The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000` automatically (see `vite.config.js`), so no `VITE_API_URL` is required for local development against a local backend.

---

## API Documentation

All routes are prefixed as shown; base path is the backend's root URL. Auto-generated interactive documentation is available at **`/docs`** and **`/redoc`** once the backend is running.

**General**
- `GET /` — root health/info
- `GET /health`, `GET /api/health` — health check

**Auth** — prefix `/api/auth`
- `GET /google/login`, `GET /google/callback` — Google OAuth2 flow
- `POST /refresh-token` — rotate access token using refresh token
- `GET /get-me` — current authenticated user
- `POST /logout`, `POST /logout-all`
- `GET /status` — auth status

**Incidents** — prefix `/api/incidents` (alias `/api/reports`)
- `POST /report` — submit an incident report (auth required)
- `GET /my-reports` — current user's reports (auth required)
- `GET /recent` — recent incident reports
- `GET /{report_id}` — single report by ID

**Events** — prefix `/api/events`
- `GET /` — unified list of earthquakes + SACHET alerts + verified news
- `GET /{event_id}` — event detail

**Earthquakes** — prefix `/api/earthquakes`
- `GET /` — filtered list
- `GET /latest`, `GET /stats`
- `POST /fetch`, `POST /sync` — trigger NCS RISEQ ingestion
- `GET /{event_id}` — single earthquake

**SACHET Alerts** — prefix `/api/sachet`
- `POST /fetch`, `POST /sync` — trigger NDMA SACHET ingestion
- `GET /`, `GET /latest`, `GET /stats`
- `GET /{event_id}` — single alert

**News** — prefix `/api/news`
- `GET /sources`, `GET /recent`, `GET /disasters`, `GET /rejected`, `GET /stats`
- `POST /fetch` — trigger news ingestion pipeline
- `GET /detail/{news_id}`, `GET /{news_id}` — article detail

**Emergency Services**
- `GET /api/emergency-services`, `GET /api/emergency-services/nearby`
- `GET /api/nearby-services`, `GET /api/nearby-services/nearby` (aliases)

**Analysis** — prefix `/api/analysis`
- `GET /overview` — KPI summary
- `GET /data` — multi-criteria filtered analytics data

---

## Deployment

Based on configuration present in the repository and the deployed URLs referenced in code:

- **Frontend:** Deployed on **Vercel** (`disha-platform.vercel.app`), using `FRONTEND/vercel.json`'s SPA rewrite rule to route all paths to `index.html`.
- **Backend:** Deployed on **Render**, referenced as `disha-platform.onrender.com` in `.env.example` and as the production fallback API URL in `FRONTEND/src/services/api.js`.
- **Database:** MongoDB Atlas (connection via `MONGO_URI`).
- No Dockerfiles, container orchestration, or CI/CD pipeline definitions were found in the repository — deployment appears to be configured directly through the Vercel and Render platforms rather than via in-repo automation.

---

## Screenshots / Demo

The repository does not currently include a dedicated screenshots folder. Visual assets present in the codebase are UI assets rather than demo captures: `FRONTEND/src/assets/hero.png`, `disha_logo.png` / `disha_logo.jpeg`, and a static reference map image (`india_dmaps_political_map_*.jpg`) used within the UI.

For a live demonstration of the actual application, see the deployed frontend: **[disha-platform.vercel.app](https://disha-platform.vercel.app)**.

---

## Team

Repository owner: **[Chitransh-22](https://github.com/Chitransh-22)**. The LICENSE refers to a "DISHA-PLATFORM Team" as rights holder; no additional contributor list or team roster is published in the repository at this time.

---

## License

This repository is distributed under a **custom Source-Available License** (see [`LICENSE`](./LICENSE) in the repository root), copyright the DISHA-PLATFORM Team. It is **not** an OSI-approved open-source license. In summary (the `LICENSE` file is the authoritative source — refer to it directly for full terms):

- The repository is publicly visible for **viewing, academic evaluation, portfolio presentation, and research discussion**.
- Public visibility does **not** grant rights to copy, download, redistribute, modify, fork, clone, mirror, sublicense, or commercially use the source code.
- Any reuse, modification, or redistribution requires **prior written permission** from the DISHA-PLATFORM Team.
- Third-party libraries and services used by the project remain governed by their own respective licenses.
- The software is provided **"AS IS"**, without warranty of any kind.

Please read the full [`LICENSE`](./LICENSE) file before using, referencing, or building upon any part of this codebase.

---

## Disclaimer / Limitations

- This is a hackathon/academic-style project and **should not be relied upon as an official or authoritative source of disaster or emergency information**. Always consult official government channels (NDMA, NCS, local authorities) for emergency decision-making.
- **Email/password authentication is not functional** — only Google OAuth2 login is exposed via the API, despite password-hashing and OTP scaffolding existing in the codebase.
- The **standalone fullscreen map page (`ViewMapPage`) is an unimplemented placeholder**.
- **Earthquake ingestion is disabled by default** (`RISEQ_ENABLED=false`); only SACHET ingestion runs by default.
- The AI news-verification pipeline depends on a third-party LLM (Gemini) and is subject to that provider's accuracy, availability, and rate/quota limits; verification labels should be treated as automated best-effort classification, not guaranteed fact-checking.
- Emergency-services lookup depends on OpenStreetMap/Overpass data completeness, which varies by region and may be incomplete for some areas of India.
- No automated test pipeline (CI) is currently configured, even though a `pytest` test suite exists under `BACKEND/tests/`.
- Geocoding for SACHET/news events without explicit coordinates falls back to state/district **centroid approximation**, not precise location data.