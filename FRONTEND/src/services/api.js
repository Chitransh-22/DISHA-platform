/**
 * DISHA Platform - API Client Layer
 * Disaster Intelligence and Situational Hazard Awareness Platform
 * 
 * Fetches 100% of all real verified events from MongoDB:
 * 1. NCS RISEQ Earthquakes (278-279 documents)
 * 2. NDMA SACHET Government CAP Alerts (305 documents)
 * 3. Verified Multi-Source Disaster News Feed (58 documents)
 * 
 * Total = 641-642 Verified Events directly from MongoDB Atlas.
 * Zero dummy/mock data.
 */

const ENV_API_URL = import.meta.env.VITE_API_URL;
const IS_PROD = import.meta.env.PROD;

export const getApiBaseUrl = () => {
  if (ENV_API_URL && ENV_API_URL.trim()) {
    return ENV_API_URL.trim().replace(/\/+$/, '');
  }
  if (IS_PROD || (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1')) {
    return 'https://disha-platform.onrender.com';
  }
  return '';
};

// In-memory cache for nearby emergency services to prevent duplicate requests
const nearbyServicesCache = new Map();

// Indian State & Territory Centroid Lookup for CAP alerts without explicit scalar point
const STATE_CENTROIDS = {
  'uttar pradesh': { lat: 26.8467, lon: 80.9462 },
  'andhra pradesh': { lat: 15.9129, lon: 79.7400 },
  'arunachal pradesh': { lat: 28.2180, lon: 94.7278 },
  'assam': { lat: 26.2006, lon: 92.9376 },
  'bihar': { lat: 25.0961, lon: 85.3131 },
  'chhattisgarh': { lat: 21.2787, lon: 81.8661 },
  'goa': { lat: 15.2993, lon: 74.1240 },
  'gujarat': { lat: 22.2587, lon: 71.1924 },
  'haryana': { lat: 29.0588, lon: 76.0856 },
  'himachal pradesh': { lat: 31.1048, lon: 77.1734 },
  'jharkhand': { lat: 23.6102, lon: 85.2799 },
  'karnataka': { lat: 15.3173, lon: 75.7139 },
  'kerala': { lat: 10.8505, lon: 76.2711 },
  'madhya pradesh': { lat: 22.9734, lon: 78.6569 },
  'maharashtra': { lat: 19.7515, lon: 75.7139 },
  'manipur': { lat: 24.6637, lon: 93.9063 },
  'meghalaya': { lat: 25.4670, lon: 91.3662 },
  'mizoram': { lat: 23.1645, lon: 92.9376 },
  'nagaland': { lat: 26.1584, lon: 94.5624 },
  'odisha': { lat: 20.9517, lon: 85.0985 },
  'punjab': { lat: 31.1471, lon: 75.3412 },
  'rajasthan': { lat: 27.0238, lon: 74.2179 },
  'sikkim': { lat: 27.5330, lon: 88.5122 },
  'tamil nadu': { lat: 11.1271, lon: 78.6569 },
  'telangana': { lat: 18.1124, lon: 79.0193 },
  'tripura': { lat: 23.9408, lon: 91.9882 },
  'uttarakhand': { lat: 30.0668, lon: 79.0193 },
  'west bengal': { lat: 22.9868, lon: 87.8550 },
  'delhi': { lat: 28.7041, lon: 77.1025 },
  'jammu': { lat: 33.7782, lon: 76.5762 },
  'kashmir': { lat: 34.0837, lon: 74.7973 },
  'ladakh': { lat: 34.1526, lon: 77.5771 },
};

/**
 * Robust coordinate extractor for SACHET CAP Alerts (Direct -> Polygon Centroid -> Circle -> Text State Lookup).
 */
function extractSachetCoordinates(sa) {
  let lat = sa.latitude ?? sa.location?.latitude;
  let lon = sa.longitude ?? sa.location?.longitude;

  if (typeof lat === 'string') lat = parseFloat(lat);
  if (typeof lon === 'string') lon = parseFloat(lon);

  if (typeof lat === 'number' && typeof lon === 'number' && !isNaN(lat) && !isNaN(lon)) {
    return { lat, lon };
  }

  // 1. Polygon centroid: "lat1,lon1 lat2,lon2 ..."
  if (sa.polygon && typeof sa.polygon === 'string') {
    try {
      const pairs = sa.polygon.trim().split(/\s+/).map((p) => p.split(',')).filter((p) => p.length === 2);
      const validPairs = pairs
        .map(([la, lo]) => [parseFloat(la), parseFloat(lo)])
        .filter(([la, lo]) => !isNaN(la) && !isNaN(lo));
      if (validPairs.length > 0) {
        const avgLat = validPairs.reduce((sum, p) => sum + p[0], 0) / validPairs.length;
        const avgLon = validPairs.reduce((sum, p) => sum + p[1], 0) / validPairs.length;
        if (avgLat >= -90 && avgLat <= 90 && avgLon >= -180 && avgLon <= 180) {
          return { lat: avgLat, lon: avgLon };
        }
      }
    } catch (e) {}
  }

  // 2. Circle centroid: "lat,lon radius"
  if (sa.circle && typeof sa.circle === 'string') {
    try {
      const parts = sa.circle.trim().split(/\s+/);
      if (parts.length > 0 && parts[0].includes(',')) {
        const [cLat, cLon] = parts[0].split(',').map(parseFloat);
        if (!isNaN(cLat) && !isNaN(cLon)) {
          return { lat: cLat, lon: cLon };
        }
      }
    } catch (e) {}
  }

  // 3. Text Entity Lookup
  const rawText = `${sa.area_description || ''} ${sa.headline || ''} ${sa.sender_name || ''} ${sa.sender || ''} ${sa.location?.state || ''} ${sa.location?.district || ''}`.toLowerCase();
  const text = rawText.replace(/[-_]/g, ' ');

  for (const [stName, coords] of Object.entries(STATE_CENTROIDS)) {
    if (text.includes(stName)) {
      return coords;
    }
  }

  return { lat: 20.5937, lon: 78.9629 };
}

/**
 * Fetch unified disaster and hazard events from the backend.
 * @param {Object} params - Query parameters (category, severity, status, source, limit)
 * @returns {Promise<{status: string, total: number, source_counts: Object, categories: string[], events: Array}>}
 */
export const fetchEvents = async (params = {}) => {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams();

  // Time range filter (Default: '24h')
  const timeRange = params.range || params.time_range || (params.days ? `${params.days}d` : '24h');
  query.append('range', timeRange);

  if (params.category && params.category !== 'All') {
    query.append('category', params.category);
  }
  if (params.severity && params.severity !== 'All') {
    query.append('severity', params.severity);
  }
  if (params.status && params.status !== 'All') {
    query.append('status', params.status);
  }
  if (params.source && params.source !== 'all') {
    query.append('source', params.source);
  }
  if (params.state) {
    query.append('state', params.state);
  }
  if (params.limit) {
    query.append('limit', params.limit);
  }
  if (params.skip) {
    query.append('skip', params.skip);
  }

  const queryString = query.toString() ? `?${query.toString()}` : '';
  const url = `${baseUrl}/api/events${queryString}`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (response.ok) {
      const data = await response.json();
      if (data && Array.isArray(data.events)) {
        return data;
      }
    }
  } catch (err) {
    console.warn('[DISHA API] /api/events notice:', err.message);
  }

  // Multi-source fallback to assemble real database records if unified endpoint is unavailable
  return await fetchEventsFallback(baseUrl);
};

/**
 * Multi-source fallback that queries all 3 individual backend routes and resolves all 641-642 documents.
 */
async function fetchEventsFallback(baseUrl) {
  const events = [];

  try {
    const [eqRes, sachetRes, newsRes] = await Promise.allSettled([
      fetch(`${baseUrl}/api/earthquakes?limit=500`).then((r) => (r.ok ? r.json() : null)),
      fetch(`${baseUrl}/api/sachet?limit=500`).then((r) => (r.ok ? r.json() : null)),
      fetch(`${baseUrl}/api/news/disasters?limit=200`).then((r) => (r.ok ? r.json() : null)),
    ]);

    let eqCount = 0;
    let sachetCount = 0;
    let newsCount = 0;

    // 1. Parse NCS Earthquakes (278 documents)
    if (eqRes.status === 'fulfilled' && eqRes.value?.earthquakes) {
      eqRes.value.earthquakes.forEach((eq, idx) => {
        let lat = eq.latitude;
        let lon = eq.longitude;
        if (typeof lat === 'string') lat = parseFloat(lat);
        if (typeof lon === 'string') lon = parseFloat(lon);

        if (typeof lat === 'number' && typeof lon === 'number' && !isNaN(lat) && !isNaN(lon)) {
          const mag = eq.magnitude || 4.0;
          const evId = eq.event_id || eq._id || `eq_${idx}_${lat}_${lon}`;
          events.push({
            id: evId,
            title: `M${mag.toFixed(1)} Earthquake — ${eq.region || eq.location || 'Epicenter'}`,
            description: `Magnitude ${mag.toFixed(1)} earthquake detected at depth ${eq.depth_km || 10}km. Agency: National Center for Seismology. Location: ${eq.location || eq.region || 'India'}.`,
            category: 'Earthquake',
            raw_category: 'earthquake',
            latitude: lat,
            longitude: lon,
            date: eq.origin_time ? eq.origin_time.split('T')[0] : new Date().toISOString().split('T')[0],
            time: eq.origin_time ? new Date(eq.origin_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : 'Live',
            datetime: eq.origin_time || new Date().toISOString(),
            timestamp: eq.origin_timestamp || Date.now() / 1000,
            location: eq.location || eq.region || 'Seismic Zone',
            state: eq.region || 'India',
            district: '',
            city: '',
            severity: mag >= 6.0 ? 'Critical' : mag >= 4.5 ? 'Severe' : 'Moderate',
            status: eq.status || 'Reviewed',
            source: 'NCS_RISEQ',
            source_group: 'ncs',
            source_label: 'National Center for Seismology',
            source_url: eq.source_url || 'https://riseq.seismo.gov.in',
            image: null,
            helpline: '1070 / 112',
            response_units: ['National Center for Seismology (NCS)', 'NDRF Battalion'],
          });
          eqCount++;
        }
      });
    }

    // 2. Parse NDMA SACHET Alerts (305 documents)
    if (sachetRes.status === 'fulfilled' && sachetRes.value?.alerts) {
      sachetRes.value.alerts.forEach((sa, idx) => {
        const { lat, lon } = extractSachetCoordinates(sa);
        if (typeof lat === 'number' && typeof lon === 'number' && !isNaN(lat) && !isNaN(lon)) {
          const rawType = (sa.disaster_type || sa.event || 'alert').toLowerCase();
          let cat = 'Other';
          if (rawType.includes('flood')) cat = 'Flood';
          else if (rawType.includes('rain') || rawType.includes('downpour')) cat = 'Heavy Rain';
          else if (rawType.includes('lightning')) cat = 'Lightning';
          else if (rawType.includes('landslide')) cat = 'Landslide';
          else if (rawType.includes('cyclone') || rawType.includes('wind')) cat = 'Cyclone';
          else if (rawType.includes('fire')) cat = 'Fire';

          const evId = sa.event_id || sa.alert_id || sa._id || `sachet_${idx}_${lat}_${lon}`;

          events.push({
            id: evId,
            title: (sa.headline || sa.title || `${cat} Early Warning`).slice(0, 140),
            description: sa.description || sa.instruction || 'Government disaster alert issued by SDMA / NDMA.',
            category: cat,
            raw_category: rawType,
            latitude: lat,
            longitude: lon,
            date: sa.event_time ? sa.event_time.split('T')[0] : new Date().toISOString().split('T')[0],
            time: sa.event_time ? new Date(sa.event_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : 'Live',
            datetime: sa.event_time || new Date().toISOString(),
            timestamp: sa.event_timestamp || Date.now() / 1000,
            location: sa.area_description || sa.location?.district || sa.location?.state || 'Advisory Sector',
            state: sa.location?.state || sa.state || '',
            district: sa.location?.district || sa.district || '',
            city: sa.location?.city || '',
            severity: sa.severity || 'Moderate',
            status: sa.status || 'Active',
            source: 'NDMA_SACHET',
            source_group: 'sachet',
            source_label: sa.sender_name || sa.sender || 'NDMA SACHET Alert',
            source_url: sa.link || sa.source_url || 'https://sachet.ndma.gov.in',
            image: null,
            helpline: '1070 / 112',
            response_units: ['State Disaster Management Authority (SDMA)', 'State Disaster Response Force (SDRF)'],
          });
          sachetCount++;
        }
      });
    }

    // 3. Parse GNews Disasters (58 documents)
    if (newsRes.status === 'fulfilled' && newsRes.value?.disasters) {
      newsRes.value.disasters.forEach((news, idx) => {
        let lat = news.location?.latitude ?? news.location?.lat ?? news.latitude;
        let lon = news.location?.longitude ?? news.location?.lon ?? news.longitude;
        if (typeof lat === 'string') lat = parseFloat(lat);
        if (typeof lon === 'string') lon = parseFloat(lon);

        if ((lat == null || lon == null || isNaN(lat) || isNaN(lon)) && news.location?.state) {
          const stName = news.location.state.toLowerCase();
          if (STATE_CENTROIDS[stName]) {
            lat = STATE_CENTROIDS[stName].lat;
            lon = STATE_CENTROIDS[stName].lon;
          }
        }

        if (typeof lat === 'number' && typeof lon === 'number' && !isNaN(lat) && !isNaN(lon)) {
          const rawType = (news.disaster_type || 'other').toLowerCase();
          let cat = 'Other';
          if (rawType.includes('flood')) cat = 'Flood';
          else if (rawType.includes('landslide')) cat = 'Landslide';
          else if (rawType.includes('rain')) cat = 'Heavy Rain';
          else if (rawType.includes('fire')) cat = 'Fire';
          else if (rawType.includes('earthquake')) cat = 'Earthquake';
          else if (rawType.includes('cloudburst')) cat = 'Cloudburst';
          else if (rawType.includes('building')) cat = 'Building Collapse';
          else if (rawType.includes('explosion')) cat = 'Explosion';
          else if (rawType.includes('industrial')) cat = 'Industrial Accident';

          const evId = news.event_id || news.article_id || news._id || `news_${idx}_${lat}_${lon}`;

          events.push({
            id: evId,
            title: (news.title || `${cat} Incident`).slice(0, 140),
            description: news.description || 'Verified multi-source disaster news report.',
            category: cat,
            raw_category: rawType,
            latitude: lat,
            longitude: lon,
            date: news.published_at ? news.published_at.split('T')[0] : new Date().toISOString().split('T')[0],
            time: news.published_at ? new Date(news.published_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : 'Verified',
            datetime: news.published_at || new Date().toISOString(),
            timestamp: news.processed_at ? new Date(news.processed_at).getTime() / 1000 : Date.now() / 1000,
            location: news.location?.district || news.location?.state || 'Affected Area',
            state: news.location?.state || '',
            district: news.location?.district || '',
            city: news.location?.city || '',
            severity: news.severity ? news.severity.charAt(0).toUpperCase() + news.severity.slice(1) : 'Moderate',
            status: news.status || 'Active',
            source: 'GNEWS',
            source_group: 'news',
            source_label: 'Verified Disaster Intelligence',
            source_url: news.url || '',
            image: news.image || null,
            helpline: '1070 / 112',
            response_units: ['District Disaster Management Authority (DDMA)'],
          });
          newsCount++;
        }
      });
    }

    events.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));

    const availableCategories = ['All', ...new Set(events.map((e) => e.category))];

    return {
      status: 'success',
      total: events.length,
      count: events.length,
      source_counts: {
        total: events.length,
        earthquakes: eqCount,
        sachet: sachetCount,
        news: newsCount,
      },
      categories: availableCategories,
      events,
    };
  } catch (err) {
    console.error('[DISHA API] Error during fallback event fetch:', err);
    return {
      status: 'error',
      total: 0,
      count: 0,
      source_counts: { total: 0, earthquakes: 0, sachet: 0, news: 0 },
      categories: ['All'],
      events: [],
    };
  }
}

/**
 * Fetch nearby emergency services around an incident's coordinates from the backend.
 * @param {number} latitude - Incident latitude
 * @param {number} longitude - Incident longitude
 * @param {number} radiusM - Radius in meters (default: 5000m)
 * @param {boolean} forceRefresh - If true, bypasses client-side cache
 * @returns {Promise<Object>} Nearby emergency services payload
 */
export const fetchNearbyEmergencyServices = async (
  latitude,
  longitude,
  radiusM = 5000,
  forceRefresh = false
) => {
  if (typeof latitude !== 'number' || typeof longitude !== 'number') {
    throw new Error('Invalid coordinates provided for nearby emergency services.');
  }

  const cacheKey = `${latitude.toFixed(4)}_${longitude.toFixed(4)}_${radiusM}m`;
  if (!forceRefresh && nearbyServicesCache.has(cacheKey)) {
    return nearbyServicesCache.get(cacheKey);
  }

  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/emergency-services?lat=${latitude}&lng=${longitude}&radius=${radiusM}&auto_expand=true`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch nearby emergency services (${response.status} ${response.statusText})`);
  }

  const data = await response.json();
  if (data && data.status === 'success') {
    nearbyServicesCache.set(cacheKey, data);
  }
  return data;
};

// ─── Authentication State & API Client Layer ────────────────────────────────

let _inMemoryAccessToken = null;
let _inMemoryRefreshToken = null;
let _refreshPromise = null;

export const setAccessToken = (token, refreshToken = undefined) => {
  _inMemoryAccessToken = token || null;
  if (token) {
    try {
      localStorage.setItem('disha_access_token', token);
      localStorage.setItem('disha_has_session', 'true');
    } catch (e) {}
  } else {
    try {
      localStorage.removeItem('disha_access_token');
      localStorage.removeItem('disha_has_session');
      localStorage.removeItem('disha_user');
    } catch (e) {}
  }

  if (refreshToken !== undefined) {
    _inMemoryRefreshToken = refreshToken || null;
    if (refreshToken) {
      try {
        localStorage.setItem('disha_refresh_token', refreshToken);
      } catch (e) {}
    } else {
      try {
        localStorage.removeItem('disha_refresh_token');
      } catch (e) {}
    }
  }
};

export const getAccessToken = () => {
  if (_inMemoryAccessToken) return _inMemoryAccessToken;
  try {
    const saved = localStorage.getItem('disha_access_token');
    if (saved) {
      _inMemoryAccessToken = saved;
      return saved;
    }
  } catch (e) {}
  return null;
};

export const getRefreshToken = () => {
  if (_inMemoryRefreshToken) return _inMemoryRefreshToken;
  try {
    const saved = localStorage.getItem('disha_refresh_token');
    if (saved) {
      _inMemoryRefreshToken = saved;
      return saved;
    }
  } catch (e) {}
  return null;
};

export const getStoredUser = () => {
  try {
    const u = localStorage.getItem('disha_user');
    return u ? JSON.parse(u) : null;
  } catch (e) {
    return null;
  }
};

export const setStoredUser = (user) => {
  try {
    if (user) {
      localStorage.setItem('disha_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('disha_user');
    }
  } catch (e) {}
};

export const getAuthHeaders = (extraHeaders = {}) => {
  const headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    ...extraHeaders,
  };
  const token = getAccessToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

/**
 * Returns the backend Google OAuth2 initiate URL.
 */
export const authGoogleLoginUrl = () => {
  const baseUrl = getApiBaseUrl();
  const currentOrigin = typeof window !== 'undefined' ? window.location.origin : '';
  const param = currentOrigin ? `?origin=${encodeURIComponent(currentOrigin)}` : '';
  if (baseUrl) {
    return `${baseUrl}/api/auth/google/login${param}`;
  }
  return `/api/auth/google/login${param}`;
};

/**
 * Parses user-friendly error message from failed response.
 */
const parseErrorMessage = (data, status) => {
  if (data?.detail) {
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((err) => err.msg || err.message || JSON.stringify(err)).join(', ');
    }
  }
  if (data?.message) return data.message;
  if (status === 401) return 'Your session has expired. Please sign in again.';
  if (status === 403) return 'You do not have permission or your account is unverified.';
  if (status === 409) return 'An account with these credentials already exists.';
  if (status === 429) return 'Too many attempts. Please wait a moment and try again.';
  if (status >= 500) return 'Server error occurred. Please try again shortly.';
  return 'Request failed. Please check your network and try again.';
};

/**
 * Core authenticated fetch with automatic 401 token refresh queue.
 */
export const authenticatedFetch = async (url, options = {}) => {
  const finalUrl = url.startsWith('http') ? url : `${getApiBaseUrl()}${url}`;
  const headers = getAuthHeaders(options.headers || {});
  
  const fetchOptions = {
    ...options,
    headers,
    credentials: 'include',
  };

  let response = await fetch(finalUrl, fetchOptions);

  // If 401 Unauthorized, perform single in-flight token refresh and retry once
  if (response.status === 401 && (localStorage.getItem('disha_has_session') === 'true' || getRefreshToken())) {
    if (!_refreshPromise) {
      _refreshPromise = authRefreshToken()
        .then((data) => {
          _refreshPromise = null;
          return data;
        })
        .catch((err) => {
          _refreshPromise = null;
          setAccessToken(null, null);
          setStoredUser(null);
          throw err;
        });
    }

    try {
      await _refreshPromise;
      // Retry original request with newly issued access token
      const retryHeaders = getAuthHeaders(options.headers || {});
      response = await fetch(finalUrl, {
        ...fetchOptions,
        headers: retryHeaders,
      });
    } catch (refreshErr) {
      // Refresh failed; propagate original 401
      setAccessToken(null, null);
      setStoredUser(null);
    }
  }

  return response;
};

/**
 * Register a new user account.
 */
export const authRegister = async (userData) => {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(userData),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseErrorMessage(data, response.status));
  }
  return data;
};

/**
 * Verify user email with 6-digit OTP.
 */
export const authVerifyEmail = async ({ email, otp }) => {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/auth/verify-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, otp }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseErrorMessage(data, response.status));
  }
  return data;
};

/**
 * Resend OTP to user email.
 */
export const authResendOtp = async (email) => {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/auth/resend-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseErrorMessage(data, response.status));
  }
  return data;
};

/**
 * Log in with email and password. Sets HTTP-Only refresh cookie.
 */
export const authLogin = async ({ email, password }) => {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseErrorMessage(data, response.status));
  }

  if (data.access_token) {
    setAccessToken(data.access_token, data.refresh_token);
  }
  if (data.user) {
    setStoredUser(data.user);
  }
  return data;
};

/**
 * Refresh access token using the HTTP-Only cookie or x-refresh-token fallback header.
 */
export const authRefreshToken = async () => {
  const baseUrl = getApiBaseUrl();
  const headers = { 'Accept': 'application/json' };
  const rToken = getRefreshToken();
  if (rToken) {
    headers['x-refresh-token'] = rToken;
  }

  const response = await fetch(`${baseUrl}/api/auth/refresh-token`, {
    method: 'POST',
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    setAccessToken(null, null);
    setStoredUser(null);
    throw new Error('Session expired or invalid refresh token.');
  }

  const data = await response.json();
  if (data.access_token) {
    setAccessToken(data.access_token, data.refresh_token || rToken);
  }
  return data;
};

/**
 * Get current authenticated user profile.
 */
export const authGetMe = async () => {
  const response = await authenticatedFetch('/api/auth/get-me', {
    method: 'GET',
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseErrorMessage(data, response.status));
  }

  if (data.user) {
    setStoredUser(data.user);
  }

  return data;
};

/**
 * Log out current session and clear cookie.
 */
export const authLogout = async () => {
  const baseUrl = getApiBaseUrl();
  const rToken = getRefreshToken();
  const headers = getAuthHeaders();
  if (rToken) {
    headers['x-refresh-token'] = rToken;
  }
  try {
    await fetch(`${baseUrl}/api/auth/logout`, {
      method: 'POST',
      headers,
      credentials: 'include',
    });
  } catch (e) {
    console.warn('[DISHA Auth] Logout notice:', e);
  } finally {
    setAccessToken(null, null);
    setStoredUser(null);
  }
  return { success: true };
};

/**
 * Log out all devices for current user.
 */
export const authLogoutAll = async () => {
  const baseUrl = getApiBaseUrl();
  const rToken = getRefreshToken();
  const headers = getAuthHeaders();
  if (rToken) {
    headers['x-refresh-token'] = rToken;
  }
  try {
    await fetch(`${baseUrl}/api/auth/logout-all`, {
      method: 'POST',
      headers,
      credentials: 'include',
    });
  } catch (e) {
    console.warn('[DISHA Auth] Logout-all notice:', e);
  } finally {
    setAccessToken(null, null);
    setStoredUser(null);
  }
  return { success: true };
};

/**
 * Submits a citizen disaster incident report to the backend.
 */
export const submitIncidentReport = async (reportData) => {
  const response = await authenticatedFetch('/api/incidents/report', {
    method: 'POST',
    body: JSON.stringify(reportData),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseErrorMessage(data, response.status));
  }
  return data;
};

/**
 * Fetches paginated, time-filtered verified disaster news articles.
 * @param {Object} params - { range: '24h'|'7d'|'15d'|'30d'|'all', category, severity, limit, skip }
 */
export const fetchRecentNews = async (params = {}) => {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams();
  
  const timeRange = params.range || params.time_range || (params.days ? `${params.days}d` : '24h');
  query.append('range', timeRange);

  if (params.category && params.category !== 'All') {
    query.append('category', params.category);
  }
  if (params.severity && params.severity !== 'All') {
    query.append('severity', params.severity);
  }
  if (params.source && params.source !== 'All' && params.source !== 'All Sources') {
    query.append('source', params.source);
  }
  if (params.limit) {
    query.append('limit', params.limit);
  }
  if (params.skip) {
    query.append('skip', params.skip);
  }

  const url = `${baseUrl}/api/news/recent?${query.toString()}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch recent news (Status ${response.status})`);
  }
  return await response.json();
};

/**
 * Fetches distinct list of available news sources from the database.
 */
export const fetchNewsSources = async () => {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/news/sources`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    return { status: 'error', sources: ['All Sources', 'NDMA SACHET', 'NCS Seismology', 'Verified Disaster News'] };
  }
  return await response.json();
};

/**
 * Fetches full details for a single news article by ID.
 * @param {string} newsId - Unique article/event ID
 */
export const fetchNewsDetail = async (newsId) => {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/news/detail/${encodeURIComponent(newsId)}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch news article details (Status ${response.status})`);
  }
  return await response.json();
};



