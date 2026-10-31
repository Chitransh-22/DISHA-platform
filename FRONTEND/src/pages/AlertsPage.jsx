import React, { useState, useEffect, useRef, useMemo } from 'react';
import L from 'leaflet';
import {
  ArrowLeft,
  Bell,
  MapPin,
  ShieldAlert,
  Clock,
  Compass,
  AlertTriangle,
  RefreshCw,
  Sliders,
  CheckCircle,
  Navigation,
  Phone,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Globe,
  Layers,
  HelpCircle,
  FileText,
  AlertCircle,
  Info,
  Calendar,
  Search,
  Maximize2,
  Minimize2,
  Crosshair,
  Filter,
  Eye,
  Columns,
  List,
  Map as MapIcon,
  Radio,
  Flame,
  Check,
  X,
} from 'lucide-react';
import { fetchDisasterNews } from '../services/api';
import { EVENT_CONFIG, getCategoryConfig, SEVERITY_CONFIG } from '../config/eventConfig';
import { formatDateTimeIST } from '../utils/dateTime';
import { normalizeEvent } from '../utils/eventNormalizer';
import { CitySelector, COUNTRY_OPTION } from '../components/common/CitySelector';
import { INDIA_SURVEY_OF_INDIA_GEOJSON } from '../data/indiaBoundaryGeojson';

// Haversine formula to compute great-circle distance between two GPS coordinates in kilometers
function calculateHaversineDistanceKm(lat1, lon1, lat2, lon2) {
  if (lat1 == null || lon1 == null || lat2 == null || lon2 == null) return null;
  const R = 6371; // Radius of the Earth in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

// Default initial area: All India
const DEFAULT_AREA = {
  name: 'All India',
  level: 'country',
  state: null,
  district: null,
  lat: 22.5937,
  lng: 78.9629,
  isGps: false,
};

export const AlertsPage = ({ onNavigate }) => {
  // Selected Geographic Area State
  const [selectedArea, setSelectedArea] = useState(DEFAULT_AREA);
  const [effectiveArea, setEffectiveArea] = useState(null);
  const [locationStatus, setLocationStatus] = useState('manual'); // 'manual', 'locating', 'granted', 'denied'
  const [locationError, setLocationError] = useState(null);

  // Filter & Search States
  const [selectedTimeRange, setSelectedTimeRange] = useState('30d');
  const [selectedSeverity, setSelectedSeverity] = useState('All');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [maxRadiusKm, setMaxRadiusKm] = useState(0); // 0 means entire scope

  // View Mode: 'split' (side-by-side on desktop), 'feed' (alerts only), 'map' (map focus)
  const [viewMode, setViewMode] = useState('split');
  // Feed Tab: 'verified' (geographically mapped threats) or 'unresolved' (location unverified news)
  const [activeTab, setActiveTab] = useState('verified');

  const [expandedAlertId, setExpandedAlertId] = useState(null);
  const [isMapFullscreen, setIsMapFullscreen] = useState(false);

  // Alerts Data State
  const [verifiedAlerts, setVerifiedAlerts] = useState([]);
  const [unresolvedNews, setUnresolvedNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState(null);
  const [lastSyncTime, setLastSyncTime] = useState(
    new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  );

  // Request & Race-condition tracking
  const abortControllerRef = useRef(null);
  const requestIdRef = useRef(0);

  // Leaflet Map & Markers Refs
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);
  const markerMapRef = useRef(new Map());

  // 1. Fetch Active Disaster News with Strict Area Filtering & Race-Condition Cancellation
  const loadAlerts = async (
    area = selectedArea,
    cat = selectedCategory,
    sev = selectedSeverity,
    range = selectedTimeRange
  ) => {
    // Cancel any pending request
    if (abortControllerRef.current) {
      try {
        abortControllerRef.current.abort();
      } catch (e) {}
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const currentReqId = ++requestIdRef.current;

    // Clear stale news immediately upon area selection
    setLoading(true);
    setVerifiedAlerts([]);
    setUnresolvedNews([]);
    setApiError(null);

    try {
      const isCountry = !area || area.level === 'country' || area.name === 'All India';
      const stateParam = isCountry ? null : area.state || (area.level === 'state' ? area.name : null);
      const districtParam = isCountry || area.level === 'state' ? null : area.district || null;

      const params = {
        range: range || '30d',
      };
      if (stateParam) params.state = stateParam;
      if (districtParam) params.district = districtParam;
      if (cat !== 'All') params.category = cat;
      if (sev !== 'All') params.severity = sev;

      const data = await fetchDisasterNews(params, { signal: controller.signal });

      // Outdated response check
      if (currentReqId !== requestIdRef.current) return;

      if (data && data.status === 'success') {
        const verified = (data.verified_alerts || []).map((ev) => normalizeEvent(ev)).filter(Boolean);
        const unresolved = (data.unresolved_news || []).map((ev) => normalizeEvent(ev)).filter(Boolean);

        setVerifiedAlerts(verified);
        setUnresolvedNews(unresolved);
        setEffectiveArea(data.selected_area || null);
        setLastSyncTime(
          new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        );
      } else {
        setVerifiedAlerts([]);
        setUnresolvedNews([]);
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('[AlertsPage] Error loading alerts:', err);
      if (currentReqId === requestIdRef.current) {
        setApiError('Unable to load disaster news for the selected area. Please try again.');
      }
    } finally {
      if (currentReqId === requestIdRef.current) {
        setLoading(false);
      }
    }
  };

  // Refetch whenever selected area, category, severity, or time range changes
  useEffect(() => {
    loadAlerts(selectedArea, selectedCategory, selectedSeverity, selectedTimeRange);
  }, [selectedArea, selectedCategory, selectedSeverity, selectedTimeRange]);

  // 2. Request Browser Geolocation
  const requestGeolocation = () => {
    if (!navigator.geolocation) {
      setLocationStatus('denied');
      setLocationError('Geolocation is not supported by your browser.');
      return;
    }

    setLocationStatus('locating');
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        const gpsArea = {
          lat,
          lng,
          name: `${lat.toFixed(2)}°N, ${lng.toFixed(2)}°E (Your GPS)`,
          level: 'district',
          state: null,
          district: null,
          isGps: true,
        };
        setSelectedArea(gpsArea);
        setLocationStatus('granted');
      },
      (err) => {
        console.warn('[AlertsPage] Geolocation permission denied or unavailable:', err.message);
        setLocationStatus('denied');
        setLocationError('Location permission denied. Please select your State or District from the list.');
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
    );
  };

  // Handle Area Selection from Searchable CitySelector
  const handleSelectArea = (area) => {
    setSelectedArea({
      name: area.name,
      level: area.level || (area.name === 'All India' ? 'country' : area.district ? 'district' : 'state'),
      state: area.state || (area.level === 'state' ? area.name : null),
      district: area.district || null,
      lat: area.lat,
      lng: area.lng,
      isGps: false,
    });
    setLocationStatus('manual');
    if (area.unresolved) {
      setLocationError(`Filtering by query "${area.name}".`);
    } else {
      setLocationError(null);
    }
  };

  // Quick Area Switcher
  const selectQuickArea = (level, name) => {
    if (level === 'country') {
      setSelectedArea(DEFAULT_AREA);
      setMaxRadiusKm(0);
    } else if (level === 'state') {
      setSelectedArea({
        name,
        level: 'state',
        state: name,
        district: null,
        lat: null,
        lng: null,
        isGps: false,
      });
      setMaxRadiusKm(0);
    }
  };

  // 3. Process & Compute Distances for Verified Alerts
  const processedVerifiedAlerts = useMemo(() => {
    let items = verifiedAlerts.map((ev) => {
      let distanceKm = null;
      if (selectedArea && selectedArea.lat != null && ev.latitude != null) {
        distanceKm = calculateHaversineDistanceKm(
          selectedArea.lat,
          selectedArea.lng,
          ev.latitude,
          ev.longitude
        );
      }
      return {
        ...ev,
        distanceKm,
      };
    });

    // Radius filter if distance is known and radius is set
    if (maxRadiusKm !== 0) {
      items = items.filter((ev) => ev.distanceKm != null && ev.distanceKm <= maxRadiusKm);
    }

    // Text Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      items = items.filter((ev) => {
        const title = (ev.title || '').toLowerCase();
        const desc = (ev.description || '').toLowerCase();
        const loc = (ev.location || '').toLowerCase();
        const state = (ev.state || '').toLowerCase();
        const dist = (ev.district || '').toLowerCase();
        const cat = (ev.category || '').toLowerCase();
        return (
          title.includes(q) ||
          desc.includes(q) ||
          loc.includes(q) ||
          state.includes(q) ||
          dist.includes(q) ||
          cat.includes(q)
        );
      });
    }

    // Sort: Distance if available, else timestamp descending
    return items.sort((a, b) => {
      if (a.distanceKm != null && b.distanceKm != null) {
        return a.distanceKm - b.distanceKm;
      }
      return (b.timestamp || 0) - (a.timestamp || 0);
    });
  }, [verifiedAlerts, selectedArea, maxRadiusKm, searchQuery]);

  // Filtered Unresolved News by Search Query
  const processedUnresolvedNews = useMemo(() => {
    if (!searchQuery.trim()) return unresolvedNews;
    const q = searchQuery.toLowerCase().trim();
    return unresolvedNews.filter((ev) => {
      const title = (ev.title || '').toLowerCase();
      const desc = (ev.description || '').toLowerCase();
      const loc = (ev.location || '').toLowerCase();
      return title.includes(q) || desc.includes(q) || loc.includes(q);
    });
  }, [unresolvedNews, searchQuery]);

  // Telemetry Counts
  const criticalCount = useMemo(() => {
    return verifiedAlerts.filter(
      (a) => a.severity === 'Critical' || a.severity === 'Severe'
    ).length;
  }, [verifiedAlerts]);

  // Distinct categories available in current verified dataset
  const availableCategories = useMemo(() => {
    const cats = new Set();
    verifiedAlerts.forEach((a) => {
      if (a.category) cats.add(a.category);
    });
    return Array.from(cats);
  }, [verifiedAlerts]);

  // 4. Initialize and Manage Embedded Alert Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (mapContainerRef.current._leaflet_id) {
      try {
        delete mapContainerRef.current._leaflet_id;
      } catch (e) {}
    }

    const map = L.map(mapContainerRef.current, {
      center: [22.5937, 78.9629],
      zoom: 5,
      minZoom: 4,
      maxZoom: 18,
      zoomControl: false,
      attributionControl: true,
    });
    mapInstanceRef.current = map;

    // Use OpenStreetMap standard tiles (completely free, reliable, NO API KEY required!)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors | DISHA Platform',
      subdomains: ['a', 'b', 'c'],
      maxZoom: 19,
    }).addTo(map);

    // Dedicated pane for Survey of India boundaries below alert markers
    if (!map.getPane('soiBoundaryPane')) {
      const soiPane = map.createPane('soiBoundaryPane');
      soiPane.style.zIndex = '350';
      soiPane.style.pointerEvents = 'none';
    }

    try {
      L.geoJSON(INDIA_SURVEY_OF_INDIA_GEOJSON, {
        pane: 'soiBoundaryPane',
        style: (feature) => {
          const name = feature?.properties?.st_nm || feature?.properties?.NAME_1 || '';
          const isLadakh = name.toLowerCase().includes('ladakh');
          const isJK = name.toLowerCase().includes('jammu');
          const isNorthernUT = isLadakh || isJK;
          return {
            color: isNorthernUT ? '#d97706' : '#ea580c',
            weight: isNorthernUT ? 2.5 : 1.8,
            opacity: 0.95,
            fillColor: isNorthernUT ? '#f59e0b' : '#ea580c',
            fillOpacity: isNorthernUT ? 0.08 : 0.02,
            interactive: false,
          };
        },
      }).addTo(map);
    } catch (err) {
      console.warn('[AlertsPage] Survey of India boundary error:', err);
    }

    const markersLayer = L.layerGroup().addTo(map);
    markersLayerRef.current = markersLayer;

    // Force size invalidation
    requestAnimationFrame(() => {
      try {
        map.invalidateSize();
      } catch (e) {}
    });

    let resizeObserver = null;
    try {
      if (mapContainerRef.current) {
        resizeObserver = new ResizeObserver(() => {
          requestAnimationFrame(() => {
            try {
              mapInstanceRef.current?.invalidateSize({ debounceMoveend: true });
            } catch (e) {}
          });
        });
        resizeObserver.observe(mapContainerRef.current);
      }
    } catch (e) {}

    return () => {
      if (resizeObserver) {
        try {
          resizeObserver.disconnect();
        } catch (e) {}
      }
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
        } catch (e) {}
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Handle Map Resize when View Mode changes
  useEffect(() => {
    if (mapInstanceRef.current) {
      setTimeout(() => {
        mapInstanceRef.current.invalidateSize();
      }, 200);
    }
  }, [viewMode, isMapFullscreen]);

  // 5. Update Map Markers when verified alerts or selected area changes
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;
    const map = mapInstanceRef.current;
    const layer = markersLayerRef.current;

    layer.clearLayers();
    markerMapRef.current.clear();

    const validMarkers = [];

    processedVerifiedAlerts.forEach((alert) => {
      // Strict geographic eligibility for map
      if (
        alert.latitude == null ||
        alert.longitude == null ||
        typeof alert.latitude !== 'number' ||
        typeof alert.longitude !== 'number' ||
        isNaN(alert.latitude) ||
        isNaN(alert.longitude) ||
        alert.latitude < -90 ||
        alert.latitude > 90 ||
        alert.longitude < -180 ||
        alert.longitude > 180
      ) {
        return;
      }

      // Reject legacy fallback centroids
      if (Math.abs(alert.latitude - 20.5937) < 0.01 && Math.abs(alert.longitude - 78.9629) < 0.01) {
        return;
      }
      if (alert.latitude === 0 && alert.longitude === 0) {
        return;
      }

      const config = getCategoryConfig(alert.category);
      const isCritical = alert.severity === 'Critical';
      const isSevere = alert.severity === 'Severe';
      const markerColor = isCritical ? '#dc2626' : isSevere ? '#ea580c' : '#2563eb';
      const pulseColor = isCritical ? 'rgba(220, 38, 38, 0.4)' : isSevere ? 'rgba(234, 88, 12, 0.4)' : 'rgba(37, 99, 235, 0.4)';

      const markerHtml = `
        <div class="relative flex items-center justify-center cursor-pointer group" style="width: 36px; height: 36px;">
          <div class="absolute inset-0 rounded-full animate-ping-slow" style="background-color: ${pulseColor};"></div>
          <div class="relative w-8 h-8 rounded-full border-2 border-white shadow-lg flex items-center justify-center text-white text-xs font-bold transition-transform duration-200 group-hover:scale-110" style="background-color: ${markerColor};">
            ${config.icon || '⚠️'}
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'custom-leaflet-marker',
        html: markerHtml,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
        popupAnchor: [0, -18],
      });

      const marker = L.marker([alert.latitude, alert.longitude], { icon: customIcon });

      const popupHtml = `
        <div class="p-3.5 space-y-2 text-slate-100 max-w-[270px] font-sans">
          <div class="flex items-center justify-between gap-2 border-b border-white/10 pb-2">
            <span class="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/10 text-slate-200">
              ${config.label || alert.category}
            </span>
            <span class="text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
              isCritical
                ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                : isSevere
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
            }">
              ${alert.severity || 'Moderate'}
            </span>
          </div>
          <h4 class="text-xs font-bold text-white leading-snug line-clamp-2">${alert.title}</h4>
          <div class="text-[11px] text-slate-400 flex items-center gap-1.5">
            <span>📍 ${alert.location || 'India'}</span>
            ${alert.state ? `<span class="text-slate-500">(${alert.state})</span>` : ''}
          </div>
          <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-1 border-t border-white/5">
            <span>${alert.latitude.toFixed(3)}°N, ${alert.longitude.toFixed(3)}°E</span>
            ${alert.distanceKm != null ? `<span class="text-orange-400 font-bold">${alert.distanceKm} km away</span>` : ''}
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml, { className: 'custom-leaflet-popup' });
      marker.addTo(layer);
      validMarkers.push([alert.latitude, alert.longitude]);
      markerMapRef.current.set(alert.id, marker);
    });

    // Auto-fit bounds or center on selected area
    if (validMarkers.length > 0 && selectedArea.level !== 'country') {
      try {
        const bounds = L.latLngBounds(validMarkers);
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
      } catch (e) {
        if (selectedArea.lat != null && selectedArea.lng != null) {
          map.setView([selectedArea.lat, selectedArea.lng], selectedArea.level === 'state' ? 7 : 10);
        }
      }
    } else if (selectedArea.lat != null && selectedArea.lng != null) {
      if (selectedArea.level === 'country' || selectedArea.name === 'All India') {
        map.setView([22.5937, 78.9629], 5);
      } else if (selectedArea.level === 'state') {
        map.setView([selectedArea.lat, selectedArea.lng], 7);
      } else {
        map.setView([selectedArea.lat, selectedArea.lng], 10);
      }
    } else {
      map.setView([22.5937, 78.9629], 5);
    }
  }, [processedVerifiedAlerts, selectedArea]);

  // Locate an alert on map smoothly & open its popup
  const handleFocusAlertOnMap = (alert) => {
    if (!mapInstanceRef.current || alert.latitude == null || alert.longitude == null) return;
    const map = mapInstanceRef.current;

    // If mobile or in feed-only mode, switch to split or map
    if (viewMode === 'feed') {
      setViewMode('split');
    }

    map.flyTo([alert.latitude, alert.longitude], 12, {
      duration: 1.2,
      easeLinearity: 0.25,
    });

    setTimeout(() => {
      const marker = markerMapRef.current.get(alert.id);
      if (marker) {
        marker.openPopup();
      }
    }, 1300);

    // If on mobile, scroll map container into view
    if (window.innerWidth < 1024 && mapContainerRef.current) {
      mapContainerRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  // Recenter map view to active scope
  const handleRecenterMap = () => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    if (selectedArea.lat != null && selectedArea.lng != null) {
      const targetZoom =
        selectedArea.level === 'country' || selectedArea.name === 'All India'
          ? 5
          : selectedArea.level === 'state'
          ? 7
          : 10;
      map.setView([selectedArea.lat, selectedArea.lng], targetZoom, { animate: true });
    } else {
      map.setView([22.5937, 78.9629], 5, { animate: true });
    }
  };

  const toggleExpand = (alertId) => {
    setExpandedAlertId(expandedAlertId === alertId ? null : alertId);
  };

  const isAllIndia = selectedArea.level === 'country' || selectedArea.name === 'All India';

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">

      {/* TOP COMMAND HEADER */}
      <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200/90 shadow-2xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">

          {/* Left: Home Navigation & Platform Title */}
          <div className="flex items-center gap-3 sm:gap-4 min-w-0">
            <button
              onClick={() => onNavigate('landing')}
              className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs px-3.5 py-2 rounded-xl border border-slate-200 transition-colors cursor-pointer shrink-0"
              title="Return to DISHA Command Dashboard"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">Back to Home</span>
            </button>

            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-9 h-9 rounded-xl bg-orange-600 flex items-center justify-center text-white shadow-xs shrink-0">
                <Bell className="w-5 h-5 animate-pulse" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h1 className="text-base sm:text-lg font-black text-slate-900 tracking-tight truncate">
                    DISHA Alert Command Center
                  </h1>
                  <span className="hidden md:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                    LIVE TELEMETRY
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 font-medium truncate">
                  Targeted disaster hazard monitoring & safety advisories across India
                </p>
              </div>
            </div>
          </div>

          {/* Right: Sync Status & View Mode Controls */}
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <div className="hidden xl:flex items-center gap-1.5 text-[11px] text-slate-400 font-mono">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>Synced {lastSyncTime}</span>
            </div>

            {/* View Mode Toggle (Split / Feed / Map) */}
            <div className="hidden sm:flex items-center bg-slate-100 p-0.5 rounded-xl border border-slate-200">
              <button
                onClick={() => setViewMode('split')}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  viewMode === 'split'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
                title="Split View (Feed + Map side by side)"
              >
                <Columns className="w-3.5 h-3.5" />
                <span className="hidden md:inline">Split</span>
              </button>
              <button
                onClick={() => setViewMode('feed')}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  viewMode === 'feed'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
                title="Feed Only (Full width alert list)"
              >
                <List className="w-3.5 h-3.5" />
                <span className="hidden md:inline">Feed</span>
              </button>
              <button
                onClick={() => setViewMode('map')}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  viewMode === 'map'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
                title="Map Focus (Expansive tactical map)"
              >
                <MapIcon className="w-3.5 h-3.5" />
                <span className="hidden md:inline">Map</span>
              </button>
            </div>

            {/* Refresh Button */}
            <button
              onClick={() => loadAlerts()}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-600 hover:bg-orange-700 text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer disabled:opacity-50"
              title="Refresh Alert Stream"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>

        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-5 space-y-5 flex-1">

        {/* 1. TELEMETRY KPI RIBBON */}
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {/* Card 1: Active In-Scope Alerts */}
          <div className="bg-white rounded-2xl p-4 border border-slate-200/90 shadow-2xs flex items-center justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-wider text-slate-400">Total In Scope</p>
              <h3 className="text-2xl font-black text-slate-900 mt-0.5">
                {loading ? '—' : processedVerifiedAlerts.length}
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5 font-medium truncate">
                {selectedArea?.name || 'All India'}
              </p>
            </div>
            <div className="w-11 h-11 rounded-2xl bg-orange-50 border border-orange-200 flex items-center justify-center text-orange-600 shrink-0">
              <ShieldAlert className="w-6 h-6" />
            </div>
          </div>

          {/* Card 2: High Threat Emergencies */}
          <div className="bg-white rounded-2xl p-4 border border-slate-200/90 shadow-2xs flex items-center justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-wider text-slate-400">High / Severe Threats</p>
              <h3 className="text-2xl font-black text-red-600 mt-0.5">
                {loading ? '—' : criticalCount}
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5 font-medium">Critical advisories active</p>
            </div>
            <div className="w-11 h-11 rounded-2xl bg-red-50 border border-red-200 flex items-center justify-center text-red-600 shrink-0">
              <AlertTriangle className="w-6 h-6" />
            </div>
          </div>

          {/* Card 3: Geographically Mapped */}
          <div className="bg-white rounded-2xl p-4 border border-slate-200/90 shadow-2xs flex items-center justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-wider text-slate-400">Mappable Alerts</p>
              <h3 className="text-2xl font-black text-emerald-600 mt-0.5">
                {loading ? '—' : verifiedAlerts.length}
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5 font-medium">Validated GPS coordinates</p>
            </div>
            <div className="w-11 h-11 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shrink-0">
              <ShieldCheck className="w-6 h-6" />
            </div>
          </div>

          {/* Card 4: Location Unverified News */}
          <div
            onClick={() => setActiveTab('unresolved')}
            className="bg-white hover:bg-amber-50/40 rounded-2xl p-4 border border-slate-200/90 hover:border-amber-300 shadow-2xs flex items-center justify-between cursor-pointer transition-all"
            title="Click to view preserved articles with unresolved locations"
          >
            <div>
              <p className="text-[11px] font-black uppercase tracking-wider text-slate-400">Unverified News</p>
              <h3 className="text-2xl font-black text-amber-600 mt-0.5">
                {loading ? '—' : unresolvedNews.length}
              </h3>
              <p className="text-[11px] text-amber-700 mt-0.5 font-medium">Preserved in DB • Non-mapped</p>
            </div>
            <div className="w-11 h-11 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0">
              <FileText className="w-6 h-6" />
            </div>
          </div>
        </section>

        {/* 2. GEOGRAPHIC TARGETING & FILTER CONTROL PANEL */}
        <section className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs p-4 sm:p-5 space-y-4">

          {/* Row 1: Geographic Hierarchy Selection */}
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 pb-3 border-b border-slate-100">

            {/* Active Area Badge */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-orange-100 text-orange-600 flex items-center justify-center shrink-0">
                <MapPin className="w-4 h-4" />
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-medium text-slate-400">Geographic Area:</span>
                  <span className="text-sm font-black text-slate-900">{selectedArea?.name || 'All India'}</span>
                  <span
                    className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                      isAllIndia
                        ? 'bg-blue-100 text-blue-800 border border-blue-200'
                        : selectedArea.level === 'state'
                        ? 'bg-amber-100 text-amber-800 border border-amber-200'
                        : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    }`}
                  >
                    {isAllIndia ? 'Nationwide (All India)' : selectedArea.level === 'state' ? 'State Scope' : 'District / City Scope'}
                  </span>
                  {selectedArea?.isGps && (
                    <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                      GPS Mode
                    </span>
                  )}
                </div>
                {locationError && (
                  <p className="text-[11px] text-amber-700 font-medium mt-0.5">{locationError}</p>
                )}
              </div>
            </div>

            {/* Quick Area Switches + CitySelector Dropdown */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => selectQuickArea('country', 'All India')}
                className={`px-3 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 border shadow-2xs ${
                  isAllIndia
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200'
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                <span>All India</span>
              </button>

              <button
                onClick={requestGeolocation}
                className="px-3 py-2 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 shadow-2xs"
                title="Detect your device coordinates"
              >
                <Compass className="w-3.5 h-3.5 text-orange-600" />
                <span>My GPS</span>
              </button>

              {/* Searchable CitySelector Component */}
              <div className="w-full sm:w-64 lg:w-72">
                <CitySelector
                  value={selectedArea}
                  onSelectCity={handleSelectArea}
                  placeholder="Select State, District, City..."
                />
              </div>
            </div>

          </div>

          {/* Row 2: Tactical Filters (Time Range, Severity, Search, Radius) */}
          <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 pt-1">

            {/* Time Range Selector */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-1 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-orange-500" />
                <span>Range:</span>
              </span>
              {[
                { label: '24 Hours', val: '24h' },
                { label: '7 Days', val: '7d' },
                { label: '15 Days', val: '15d' },
                { label: '30 Days', val: '30d' },
                { label: 'All History', val: 'all' },
              ].map((r) => (
                <button
                  key={r.val}
                  onClick={() => setSelectedTimeRange(r.val)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    selectedTimeRange === r.val
                      ? 'bg-slate-900 text-white shadow-2xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>

            {/* Severity Filter */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-1 flex items-center gap-1">
                <Filter className="w-3.5 h-3.5 text-orange-500" />
                <span>Severity:</span>
              </span>
              {['All', 'Critical', 'Severe', 'Moderate'].map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSelectedSeverity(sev)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    selectedSeverity === sev
                      ? 'bg-slate-900 text-white shadow-2xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>

          </div>

          {/* Row 3: Live Search Keyword & Radius */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2 border-t border-slate-100">
            {/* Live Search Input */}
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search alerts by headline, keyword, or district..."
                className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-9 pr-8 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5 rounded cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Radius Filter (when GPS or local district is active) */}
            {selectedArea?.lat != null && !isAllIndia && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-1 flex items-center gap-1">
                  <Sliders className="w-3.5 h-3.5 text-orange-500" />
                  <span>Radius:</span>
                </span>
                {[
                  { label: '50 km', val: 50 },
                  { label: '150 km', val: 150 },
                  { label: '300 km', val: 300 },
                  { label: 'Entire Scope', val: 0 },
                ].map((rad) => (
                  <button
                    key={rad.val}
                    onClick={() => setMaxRadiusKm(rad.val)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      maxRadiusKm === rad.val
                        ? 'bg-orange-600 text-white shadow-2xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {rad.label}
                  </button>
                ))}
              </div>
            )}
          </div>

        </section>

        {/* 3. CORE SITUATION WORKSPACE: SPLIT / FEED / MAP */}
        <div
          className={`grid gap-5 ${
            viewMode === 'map'
              ? 'grid-cols-1'
              : viewMode === 'feed'
              ? 'grid-cols-1'
              : 'grid-cols-1 lg:grid-cols-12'
          }`}
        >

          {/* LEFT / PRIMARY COLUMN: ALERT STREAM FEED */}
          {viewMode !== 'map' && (
            <div
              className={`space-y-4 ${
                viewMode === 'split' ? 'lg:col-span-7 xl:col-span-7' : 'w-full'
              }`}
            >

              {/* Feed Navigation Tabs: Verified Alerts vs Unresolved News */}
              <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setActiveTab('verified')}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-black transition-all cursor-pointer ${
                      activeTab === 'verified'
                        ? 'bg-slate-900 text-white shadow-2xs'
                        : 'bg-white hover:bg-slate-100 text-slate-600 border border-slate-200'
                    }`}
                  >
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Verified Incident Alerts</span>
                    <span className="px-1.5 py-0.2 rounded-full bg-white/20 text-[10px]">
                      {processedVerifiedAlerts.length}
                    </span>
                  </button>

                  <button
                    onClick={() => setActiveTab('unresolved')}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-black transition-all cursor-pointer ${
                      activeTab === 'unresolved'
                        ? 'bg-amber-600 text-white shadow-2xs'
                        : 'bg-white hover:bg-amber-50 text-slate-600 border border-slate-200'
                    }`}
                  >
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    <span>Location Unverified</span>
                    <span className="px-1.5 py-0.2 rounded-full bg-black/10 text-[10px]">
                      {processedUnresolvedNews.length}
                    </span>
                  </button>
                </div>

                <div className="text-[11px] font-medium text-slate-400 hidden sm:block">
                  {activeTab === 'verified'
                    ? `Showing ${processedVerifiedAlerts.length} verified threats`
                    : `Showing ${processedUnresolvedNews.length} unmapped reports`}
                </div>
              </div>

              {/* TAB 1: GEOGRAPHICALLY VERIFIED ALERTS STREAM */}
              {activeTab === 'verified' && (
                <div className="space-y-3.5">
                  {/* Loading Skeletons */}
                  {loading && (
                    <div className="space-y-3">
                      {[1, 2, 3].map((n) => (
                        <div
                          key={n}
                          className="bg-white rounded-2xl p-5 border border-slate-200 shadow-2xs animate-pulse space-y-3"
                        >
                          <div className="flex gap-2">
                            <div className="h-5 w-24 bg-slate-200 rounded-full" />
                            <div className="h-5 w-20 bg-slate-200 rounded-full" />
                          </div>
                          <div className="h-6 w-3/4 bg-slate-200 rounded-lg" />
                          <div className="h-4 w-1/2 bg-slate-100 rounded-lg" />
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Empty State */}
                  {!loading && processedVerifiedAlerts.length === 0 && (
                    <div className="bg-white rounded-2xl p-8 border border-slate-200 text-center space-y-3 shadow-2xs">
                      <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 mx-auto">
                        <ShieldCheck className="w-7 h-7" />
                      </div>
                      <h3 className="text-base font-bold text-slate-800">
                        No Geographically Verified Threat Alerts
                      </h3>
                      <p className="text-xs text-slate-500 max-w-md mx-auto">
                        There are currently no active disaster alerts plotted within{' '}
                        <strong>{selectedArea?.name || 'All India'}</strong> matching your chosen time and severity filters.
                      </p>
                      {!isAllIndia && (
                        <button
                          onClick={() => selectQuickArea('country', 'All India')}
                          className="mt-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer inline-flex items-center gap-1.5"
                        >
                          <Globe className="w-3.5 h-3.5" />
                          <span>View All India Incidents</span>
                        </button>
                      )}
                    </div>
                  )}

                  {/* Verified Threat Cards List */}
                  {!loading &&
                    processedVerifiedAlerts.map((alert) => {
                      const config = getCategoryConfig(alert.category);
                      const sevConfig = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.Moderate;
                      const isExpanded = expandedAlertId === alert.id;
                      const istTimeString = formatDateTimeIST(alert);
                      const isCritical = alert.severity === 'Critical';
                      const isSevere = alert.severity === 'Severe';

                      return (
                        <div
                          key={alert.id}
                          className={`bg-white rounded-2xl border transition-all duration-200 shadow-2xs hover:shadow-xs overflow-hidden ${
                            isCritical
                              ? 'border-l-4 border-l-red-600 border-slate-200'
                              : isSevere
                              ? 'border-l-4 border-l-orange-500 border-slate-200'
                              : 'border-l-4 border-l-blue-500 border-slate-200'
                          }`}
                        >
                          <div className="p-4 sm:p-5 space-y-3">

                            {/* Card Header: Badges & Time */}
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold border ${config.badge}`}>
                                  <span>{config.icon}</span>
                                  <span>{config.label}</span>
                                </span>

                                <span className={`inline-flex items-center px-2 py-0.5 rounded-full font-extrabold text-[10px] uppercase tracking-wider ${sevConfig.badge}`}>
                                  {alert.severity || 'Moderate'}
                                </span>

                                {alert.distanceKm != null && (
                                  <span
                                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-bold text-[11px] ${
                                      alert.distanceKm <= 50
                                        ? 'bg-red-500 text-white animate-pulse'
                                        : alert.distanceKm <= 150
                                        ? 'bg-orange-500 text-white'
                                        : 'bg-slate-100 text-slate-700 border border-slate-200'
                                    }`}
                                  >
                                    <Navigation className="w-3 h-3 shrink-0" />
                                    <span>{alert.distanceKm} km away</span>
                                  </span>
                                )}
                              </div>

                              <div className="flex items-center gap-1 text-[11px] text-slate-400 font-medium">
                                <Clock className="w-3.5 h-3.5 text-slate-400" />
                                <span>{istTimeString}</span>
                              </div>
                            </div>

                            {/* Headline */}
                            <h3 className="text-sm sm:text-base font-bold text-slate-900 leading-snug">
                              {alert.title}
                            </h3>

                            {/* Location & Provenance Metadata */}
                            <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-100 text-xs">
                              <div className="flex flex-wrap items-center gap-2 text-slate-500 font-medium">
                                <span className="flex items-center gap-1 text-slate-700 font-bold">
                                  <MapPin className="w-3.5 h-3.5 text-orange-600 shrink-0" />
                                  <span>{alert.location || 'India'}{alert.state ? `, ${alert.state}` : ''}</span>
                                </span>
                                {alert.latitude != null && alert.longitude != null && (
                                  <span className="font-mono text-[10px] bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                                    {alert.latitude.toFixed(2)}°N, {alert.longitude.toFixed(2)}°E
                                  </span>
                                )}
                                <span>•</span>
                                <span className="text-slate-400">
                                  Source: <strong className="text-slate-700">{alert.source_label || alert.source}</strong>
                                </span>
                              </div>

                              {/* Card Action Controls */}
                              <div className="flex items-center gap-2 shrink-0">
                                <button
                                  onClick={() => handleFocusAlertOnMap(alert)}
                                  className="px-2.5 py-1 bg-slate-100 hover:bg-orange-50 hover:text-orange-600 text-slate-700 rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center gap-1"
                                  title="Pan map to this alert location"
                                >
                                  <Crosshair className="w-3.5 h-3.5 text-orange-600" />
                                  <span>Locate</span>
                                </button>

                                <button
                                  onClick={() => toggleExpand(alert.id)}
                                  className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center gap-1"
                                >
                                  <span>{isExpanded ? 'Hide' : 'Details'}</span>
                                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                </button>
                              </div>
                            </div>

                            {/* Expanded Details & DOs/DON'Ts Action Plan */}
                            {isExpanded && (
                              <div className="pt-3 border-t border-slate-100 space-y-3.5 bg-slate-50/70 -mx-4 sm:-mx-5 -mb-4 sm:-mb-5 p-4 sm:p-5">
                                {alert.description && (
                                  <div className="space-y-1.5">
                                    <div className="flex items-center justify-between text-xs">
                                      <h4 className="font-bold uppercase tracking-wider text-slate-400">
                                        Situation Assessment
                                      </h4>
                                      {alert.source_url && (
                                        <a
                                          href={alert.source_url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="text-orange-600 hover:text-orange-700 font-bold inline-flex items-center gap-1 hover:underline cursor-pointer"
                                        >
                                          <span>Read Original Source</span>
                                          <ExternalLink className="w-3 h-3" />
                                        </a>
                                      )}
                                    </div>
                                    <p className="text-xs text-slate-700 leading-relaxed bg-white p-3 rounded-xl border border-slate-200 break-words">
                                      {alert.description}
                                    </p>
                                  </div>
                                )}

                                {/* Official Disaster Advisory: DOs and DON'Ts */}
                                {config && (config.dos?.length > 0 || config.donts?.length > 0) && (
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                                    {config.dos?.length > 0 && (
                                      <div className="bg-emerald-50/80 border border-emerald-200 rounded-xl p-3.5 space-y-1.5">
                                        <h5 className="text-xs font-black text-emerald-900 uppercase tracking-wider flex items-center gap-1.5">
                                          <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                                          <span>Recommended Action (DOs)</span>
                                        </h5>
                                        <ul className="text-xs text-emerald-800 space-y-1 pl-4 list-disc">
                                          {config.dos.map((item, i) => (
                                            <li key={i}>{item}</li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}

                                    {config.donts?.length > 0 && (
                                      <div className="bg-rose-50/80 border border-rose-200 rounded-xl p-3.5 space-y-1.5">
                                        <h5 className="text-xs font-black text-rose-900 uppercase tracking-wider flex items-center gap-1.5">
                                          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                                          <span>High-Risk Pitfalls (DON'Ts)</span>
                                        </h5>
                                        <ul className="text-xs text-rose-800 space-y-1 pl-4 list-disc">
                                          {config.donts.map((item, i) => (
                                            <li key={i}>{item}</li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}

                          </div>
                        </div>
                      );
                    })}
                </div>
              )}

              {/* TAB 2: LOCATION UNVERIFIED NEWS FEED */}
              {activeTab === 'unresolved' && (
                <div className="space-y-3.5">
                  <div className="p-4 bg-amber-50 rounded-2xl border border-amber-200 flex items-start gap-3">
                    <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                    <div className="space-y-1 text-xs text-amber-900">
                      <h4 className="font-bold">Preserved Non-Mappable Intelligence</h4>
                      <p className="text-amber-800/90 leading-relaxed">
                        These news articles were verified as disaster incidents by AI classification, but lack confirmed coordinates in their source metadata. In accordance with DISHA data integrity standards, they are preserved in MongoDB and accessible here, but strictly excluded from map placement to avoid misleading false locations.
                      </p>
                    </div>
                  </div>

                  {processedUnresolvedNews.length === 0 ? (
                    <div className="bg-white rounded-2xl p-8 border border-slate-200 text-center space-y-2 shadow-2xs">
                      <p className="text-xs text-slate-500">No unverified news reports match current criteria.</p>
                    </div>
                  ) : (
                    <div className="space-y-2.5">
                      {processedUnresolvedNews.map((news) => (
                        <div
                          key={news.id}
                          className="p-4 bg-white rounded-2xl border border-slate-200 hover:border-amber-300 transition-colors shadow-2xs space-y-2"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                              {news.category || 'Disaster Incident'}
                            </span>
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                              Location Unverified
                            </span>
                          </div>

                          <h4 className="text-xs sm:text-sm font-bold text-slate-900 leading-snug">
                            {news.title}
                          </h4>

                          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-100 text-[11px] text-slate-500">
                            <div>
                              <span>Raw Location Text: <strong className="text-slate-700">{news.location || 'Unknown'}</strong></span>
                              <span className="mx-2">•</span>
                              <span>Source: <strong className="text-slate-700">{news.source_label || news.source}</strong></span>
                            </div>

                            {news.source_url && (
                              <a
                                href={news.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs font-bold text-orange-600 hover:underline flex items-center gap-1"
                              >
                                <span>Article Link</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

            </div>
          )}

          {/* RIGHT / SECONDARY COLUMN: TACTICAL INCIDENT MAP */}
          {viewMode !== 'feed' && (
            <div
              className={`${
                viewMode === 'split' ? 'lg:col-span-5 xl:col-span-5' : 'w-full'
              }`}
            >
              <div
                className={`bg-white rounded-2xl border border-slate-200/90 shadow-2xs overflow-hidden flex flex-col ${
                  isMapFullscreen
                    ? 'fixed inset-4 z-50 shadow-2xl'
                    : viewMode === 'map'
                    ? 'h-[750px]'
                    : 'lg:sticky lg:top-20 h-[520px] lg:h-[640px]'
                }`}
              >

                {/* Map Control Toolbar */}
                <div className="px-4 py-2.5 bg-slate-900 text-white flex items-center justify-between gap-2 shrink-0">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                    <h3 className="text-xs font-black uppercase tracking-wider text-slate-200 truncate">
                      {selectedArea?.name || 'All India'} Tactical Map
                    </h3>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={handleRecenterMap}
                      className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center gap-1"
                      title="Recenter Map View"
                    >
                      <Crosshair className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline text-[10px]">Reset</span>
                    </button>

                    <button
                      onClick={() => setIsMapFullscreen(!isMapFullscreen)}
                      className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition-colors cursor-pointer"
                      title={isMapFullscreen ? 'Exit Fullscreen' : 'Expand Fullscreen'}
                    >
                      {isMapFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {/* Leaflet Map Canvas */}
                <div className="relative flex-1 w-full bg-slate-100">
                  <div ref={mapContainerRef} className="w-full h-full" style={{ zIndex: 1 }} />

                  {/* Floating Map Marker Counter */}
                  <div className="absolute top-3 left-3 z-10 bg-slate-900/90 backdrop-blur-xs text-white px-2.5 py-1 rounded-xl text-[11px] font-bold border border-white/10 shadow-md flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-orange-500" />
                    <span>{processedVerifiedAlerts.length} Verified Incidents Plotted</span>
                  </div>

                  {/* Floating Map Legend */}
                  <div className="absolute bottom-3 left-3 z-10 bg-white/95 backdrop-blur-xs text-slate-700 px-3 py-2 rounded-xl text-[10px] font-bold border border-slate-200 shadow-md space-y-1">
                    <span className="text-[9px] uppercase tracking-wider text-slate-400 block font-black">
                      Threat Legend
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <span className="w-2.5 h-2.5 rounded-full bg-red-600" /> Critical
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2.5 h-2.5 rounded-full bg-orange-500" /> Severe
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> Moderate
                      </span>
                    </div>
                  </div>

                  {/* Empty State Overlay */}
                  {!loading && processedVerifiedAlerts.length === 0 && (
                    <div className="absolute inset-0 bg-white/85 backdrop-blur-xs flex flex-col items-center justify-center p-6 text-center z-10">
                      <ShieldCheck className="w-10 h-10 text-emerald-600 mb-2" />
                      <h4 className="text-sm font-bold text-slate-900">No Incidents Plotted</h4>
                      <p className="text-xs text-slate-500 max-w-xs mt-1">
                        No verified disaster coordinates recorded for <strong>{selectedArea?.name}</strong>.
                      </p>
                      {!isAllIndia && (
                        <button
                          onClick={() => selectQuickArea('country', 'All India')}
                          className="mt-3 px-3 py-1.5 bg-orange-600 hover:bg-orange-700 text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer"
                        >
                          View All India Incidents
                        </button>
                      )}
                    </div>
                  )}
                </div>

              </div>
            </div>
          )}

        </div>

      </main>

    </div>
  );
};
