# DISHA Platform — Data Consistency & Zero Event Loss Plan: Home Map & Analysis Page

## 1. Executive Summary & Mandatory Invariants

In the DISHA disaster-management platform, the **Home Page Live Disaster Map** and the **Analysis Page** must use the exact same source of truth for disaster incidents and apply the same selected time range consistently.

### Critical Requirement: Zero Event Loss Due to Missing Location
**Never discard, exclude, or silently drop a valid disaster event because its coordinates are missing, invalid, or cannot be resolved.**

For each selected time range, the following data-integrity invariant must strictly hold:
$$T = M + U$$
Where:
- $T$ = Total unique eligible incidents (from all supported collections: `earthquakes`, `sachet_alerts`, `disaster_events`, and `incident_reports`).
- $M$ = Incidents with valid geographic coordinates (eligible to be plotted as map markers).
- $U$ = Incidents without valid coordinates (`latitude: null, longitude: null`, `has_coordinates: false`, location status: `unresolved` or `missing`).

### Key Invariant Rules:
1. **The Map plots $M$ incidents**, but preserves all $T$ incidents in its underlying dataset and displays an accessible panel for the $U$ unmapped incidents (`T incidents in selected range · M mapped · U awaiting location`).
2. **Analysis totals and charts compute against $T$ incidents**, not $M$. Unmapped incidents contribute to totals, disaster type breakdowns, severity distributions, time series, and source distributions. In geographic breakdowns, unresolved locations are grouped into an explicit `"Unknown / Unresolved"` category rather than being dropped or assigned invented states.
3. **No Fake Centroids**: Never assign `20.5937, 78.9629` (India centroid) or any arbitrary coordinates to events with missing or unresolvable coordinates.
4. **No Current Time Substitution**: Never replace missing or invalid timestamps with `datetime.now()`. Exclude records with missing timestamps from time-filtered windows, but retain them when querying `"all"`, and record them in diagnostic metadata.

---

## 2. Root Cause Analysis

1. **Fatal Lexicographical String Comparison in MongoDB (`events_service.py`)**:
   In `events_service.py` (lines 548–555), `news_query` used `{"published_at": {"$gte": c_iso}}`. Because `published_at` is an RFC 2822 string (e.g. `"Thu, 22 Oct 2026..."`, `"Tue, 18 Aug 2026..."`) while `c_iso` is an ISO string (`"2026-10-27..."`), ASCII string comparison (`'T' > '2'` and `'W' > '2'`) caused all Thursday, Tuesday, and Wednesday articles to match regardless of date.
2. **Silent Current Time Substitution**:
   `normalize_event_time()` failed on RFC 2822 dates and silently defaulted to `datetime.now(timezone.utc)`. This caused all 121 news articles to be tagged with the current timestamp, placing them into the 24-hour window.
3. **Location-Based Event Discard**:
   In `events_service.py` line 381:
   `if lat is None or lon is None: continue`
   Earthquakes without coordinates were silently dropped before reaching the event list.
4. **Fake Centroid Coordinates**:
   In `events_service.py` (lines 236 and 277) and `api.js` (lines 120 and 300), alerts and news articles without coordinates were assigned `20.5937, 78.9629`, plotting fake cluster markers in central India.
5. **Split Data Flow & Dual Filtering Architecture**:
   Home Map calls `/api/events?range={timeRange}`. Analysis Page calls 10 raw endpoints in parallel requesting `range=all`, then runs a separate client-side filter `filterIncidents()`.
6. **Omission of Citizen Incident Reports**:
   The `incident_reports` collection (populated via `/api/incidents/report`) was omitted from unified events.
7. **Filter Inconsistency**:
   Map offered `24h`, `7d`, `15d`, `30d` (default `24h`), while Analysis offered `all`, `24h`, `7d`, `30d` (default `all`), with no shared context synchronization.

---

## 3. Implementation Blueprint

### Phase 1: Backend Architecture (`BACKEND/app/`)

#### 1. Robust Timestamp Normalization (`BACKEND/app/services/events_service.py`)
- Parse numeric epoch timestamps (`origin_timestamp`, `event_timestamp`, `timestamp`).
- Parse Python `datetime` / BSON Date objects (`created_at`, `updated_at`, `event_time`).
- Parse ISO 8601 strings safely.
- Parse RFC 2822 strings via `email.utils.parsedate_to_datetime()`.
- Parse date strings (`%Y-%m-%d`, `%Y-%m-%d %H:%M:%S`).
- **Zero fabrication**: If a timestamp is missing or invalid, return `None` (never substitute `now()`).
- Exclude records with missing timestamps from bounded time-ranges, but keep them in `all` and record them in `diagnostic_metadata.missing_timestamps_count`.

#### 2. Strict Inclusive-Start and Exclusive-End Filtering (`[startTime, endTime)`)
- For every range (`24h`, `7d`, `15d`, `30d`, `custom`), compute `start_epoch` and `end_epoch` (and UTC ISO boundaries).
- Enforce `timestamp >= start_epoch AND timestamp < end_epoch`.

#### 3. Zero Event Loss for Missing Location & Non-Destructive Location Extraction
- In `events_service.py`:
  - **Earthquakes**: Do NOT discard records if `latitude` or `longitude` is missing. Preserve record with `latitude: None, longitude: None`, `location_status: "missing"` or `"unresolved"`, `has_coordinates: False`.
  - **SACHET Alerts**: Try direct coords, polygon centroid, circle centroid, and validated state geocoding. If not resolvable, return `None, None, "unresolved"` with `has_coordinates: False`. Never return `20.5937, 78.9629`. Preserve original `area_description`, `headline`, `location` dictionary.
  - **Disaster News**: Try direct coords and validated state/district coords. If not resolvable, return `None, None, "unresolved"` with `has_coordinates: False`. Never return `20.5937, 78.9629`. Preserve original title, location dictionary, and text.
  - **Citizen Reports** (`incident_reports`): Ingest all records from `incident_reports`. Extract coords from `location.lat` / `location.lng` / `location.coordinates`. If missing, set `latitude: None, longitude: None`, `has_coordinates: False`. Preserve original `address`, `description`, `event_type`.

#### 4. Canonical Event Schema
Every event dictionary returned across endpoints contains:
- `id`: Unique deterministic ID (e.g. `ncs_...`, `sachet_...`, `news_...`, `INC-...`).
- `db_id`: Underlying MongoDB `_id` string.
- `title`, `description`, `category`, `raw_category`, `severity`, `status`.
- `latitude`: `float` or `None`.
- `longitude`: `float` or `None`.
- `has_coordinates`: `bool` (`True` if valid numeric coords, `False` otherwise).
- `location_status`: `"exact"` | `"approximate"` | `"unresolved"` | `"missing"`.
- `location`: Human-readable location text (or `"Unresolved Location"`).
- `state`: Clean state name or `None` (never fabricated).
- `district`: District name or `None`.
- `city`: City name or `None`.
- `date`, `time`, `datetime`, `timestamp` (UTC epoch).
- `source`: `"NCS_RISEQ"`, `"NDMA_SACHET"`, `"GNEWS"`, `"CITIZEN_REPORT"`.
- `source_group`: `"ncs"`, `"sachet"`, `"news"`, `"citizen"`.
- `source_label`: Display name of source authority.
- `source_url`: Verifiable link.

#### 5. Diagnostic Metadata & Invariant Verification in API
Return diagnostic metadata in `/api/events` and `/api/analysis/data`:
```json
{
  "status": "success",
  "time_range": "24h",
  "start_time": "2026-10-27T15:30:00+00:00",
  "end_time": "2026-10-28T15:30:00+00:00",
  "total": 1283,
  "count": 1283,
  "mapped_count": 1250,
  "unmapped_count": 33,
  "invariant_holds": true,
  "source_counts": {
    "total": 1283,
    "earthquakes": 275,
    "sachet": 880,
    "news": 121,
    "citizen_reports": 7
  },
  "events": [...]
}
```

#### 6. Analytics Endpoints Harmonization (`BACKEND/app/routes/analysis.py`)
- Refactor `/api/analysis/overview` and `/api/analysis/data` to use `get_unified_events(time_range=...)` directly as their single data engine.
- Calculate KPIs, source distributions, severity breakdowns, top states (grouping missing states under `"Unknown / Unresolved"`), and funnel metrics from the canonical filtered dataset.

#### 7. Update Unified Events Route (`BACKEND/app/routes/events.py`)
- Support `range`, `days`, `start_date`, `end_date`, `include_unmapped=True`.

---

### Phase 2: Frontend Architecture (`FRONTEND/src/`)

#### 1. Shared Time Range State Provider (`FRONTEND/src/context/TimeRangeContext.jsx`)
- Create `TimeRangeContext` providing:
  - `timeRange`: shared string (`'24h'`, `'7d'`, `'15d'`, `'30d'`, `'all'`, `'custom'`).
  - `setTimeRange(newRange)`: updates global state.
  - `customRange`: `{ startDate, endDate }`.
  - `setCustomRange(range)`.
  - `availableRanges`: `['24h', '7d', '15d', '30d', 'all']`.
- Wrap `AppContent` in `FRONTEND/src/App.jsx`.

#### 2. Update `FRONTEND/src/services/api.js`
- Remove fake centroid fallbacks (`20.5937, 78.9629`).
- Set `has_coordinates: boolean` on each returned item.
- Support `range`, `start_date`, `end_date` query params.

#### 3. Update Home Live Disaster Map (`FRONTEND/src/pages/LandingPage/components/LiveDisasterMap.jsx`)
- Use `useTimeRange()`.
- Offer synchronized options: `24 Hours`, `7 Days`, `15 Days`, `30 Days`, `All Records`.
- Separate mapped ($M$) and unmapped ($U$) incidents from total ($T$):
  - Plot markers ONLY for `has_coordinates === true` with valid coordinates.
  - Display counter in map header:
    `"{total} incidents in selected range · {mappedCount} mapped · {unmappedCount} awaiting location"`
  - Provide a slide-over / expandable drawer / panel to view the unmapped incidents with their details, titles, source, and text location.
- Add request sequence counter to prevent race conditions from delayed responses.

#### 4. Update Analysis Page & Data Service (`analysisDataService.js`, `AnalysisPage.jsx`, `AnalysisFilters.jsx`)
- In `analysisDataService.js`:
  - Derive all KPIs, graph datasets, and summaries from the canonical events dataset (`/api/events?range=...`).
  - Compute total incidents equal to $T$ (including unmapped incidents).
  - Map unmapped incidents to `"Unknown / Unresolved"` in geographic charts rather than dropping them.
  - Add support for `CITIZEN_REPORT` in source breakdown.
- In `AnalysisFilters.jsx`:
  - Connect to `useTimeRange()`.
  - Standardize options to match Map: `24h`, `7d`, `15d`, `30d`, `all`.
- In `AnalysisPage.jsx`:
  - Invalidate and refetch data immediately when `timeRange` changes.
  - Eliminate race conditions via request tracking.

---

### Phase 3: Comprehensive Test Suite (`BACKEND/tests/test_data_consistency.py`)

Add comprehensive test cases covering:
1. **Invariant $T = M + U$**: Holds strictly across every time range (`24h`, `7d`, `15d`, `30d`, `all`).
2. **Zero event loss**: Events with null coordinates are present in API response and analysis totals.
3. **No map markers for unmapped events**: Unmapped events have `has_coordinates: false` and `latitude: None`.
4. **Boundary conditions**: Inclusive start boundary (`ts == start`) included; exclusive end boundary (`ts == end`) excluded.
5. **No fake centroids**: No incident is assigned `20.5937, 78.9629` unless that is genuinely its original coordinate.
6. **No silent `now` replacement**: Missing or RFC 2822 timestamps are parsed accurately or marked invalid, never replaced with `now`.
7. **Citizen reports inclusion**: Reports from `incident_reports` appear in unified events with source `"CITIZEN_REPORT"`.
8. **Time-range switching consistency**: Switching between ranges updates both datasets with identical counts.
9. **Deduplication integrity**: Canonical IDs prevent double-counting while preserving distinct incidents.
10. **Analysis and Map reconciliation**: Analysis total equals map total $T$, mapped count equals marker count $M$.

---

## 4. Execution Protocol

Plan approved for direct execution.
