import React, { useState, useEffect, useMemo } from 'react';
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
} from 'lucide-react';
import { fetchEvents } from '../services/api';
import { EVENT_CONFIG, getCategoryConfig, SEVERITY_CONFIG } from '../config/eventConfig';
import { formatDateTimeIST } from '../utils/dateTime';
import { normalizeEvent } from '../utils/eventNormalizer';
import { CitySelector } from '../components/common/CitySelector';

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

const DEFAULT_CITY = { name: 'Delhi NCR, Delhi', lat: 28.6139, lng: 77.2090, isGps: false };

export const AlertsPage = ({ onNavigate }) => {
  // User Location State
  const [userLocation, setUserLocation] = useState(DEFAULT_CITY);
  const [locationStatus, setLocationStatus] = useState('prompt'); // 'prompt', 'locating', 'granted', 'denied', 'manual'
  const [locationError, setLocationError] = useState(null);

  // Filter & Radius Settings
  const [maxRadiusKm, setMaxRadiusKm] = useState(300); // Default 300 km
  const [selectedSeverity, setSelectedSeverity] = useState('All');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [expandedAlertId, setExpandedAlertId] = useState(null);

  // Events
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  // 1. Request Browser Geolocation
  const requestGeolocation = () => {
    if (!navigator.geolocation) {
      setLocationStatus('denied');
      setLocationError('Geolocation is not supported by your browser.');
      setUserLocation(DEFAULT_CITY);
      return;
    }

    setLocationStatus('locating');
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setUserLocation({
          lat,
          lng,
          name: `${lat.toFixed(2)}°N, ${lng.toFixed(2)}°E (Your GPS Location)`,
          isGps: true,
        });
        setLocationStatus('granted');
      },
      (err) => {
        console.warn('[AlertsPage] Geolocation permission denied or unavailable:', err.message);
        setLocationStatus('denied');
        setLocationError('Location permission denied. Select your city or region below.');
        setUserLocation(DEFAULT_CITY);
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
    );
  };

  useEffect(() => {
    requestGeolocation();
  }, []);

  // 2. Fetch Active Incidents & Alerts
  const loadAlerts = async () => {
    setLoading(true);
    try {
      const data = await fetchEvents({ range: '30d' });
      if (data && Array.isArray(data.events)) {
        // Normalize each event and deduplicate by unique id/key
        const seen = new Set();
        const deduped = [];
        for (const rawEv of data.events) {
          const ev = normalizeEvent(rawEv);
          if (!ev) continue;
          const key = ev.id || `${ev.latitude}_${ev.longitude}_${ev.title}`;
          if (!seen.has(key)) {
            seen.add(key);
            deduped.push(ev);
          }
        }
        setEvents(deduped);
      }
    } catch (err) {
      console.error('[AlertsPage] Error loading alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  // Handle City Selection from Searchable CitySelector
  const handleSelectCity = (city) => {
    setUserLocation({
      lat: city.lat,
      lng: city.lng,
      name: city.name,
      isGps: false,
    });
    setLocationStatus('manual');
    if (city.unresolved) {
      setLocationError(`Coordinates for "${city.name}" not found in offline index. Showing all regional alerts.`);
    } else {
      setLocationError(null);
    }
  };

  // Compute distances & filter alerts
  const processedAlerts = useMemo(() => {
    return events
      .map((ev) => {
        let distanceKm = null;
        if (userLocation && userLocation.lat != null && ev.latitude != null) {
          distanceKm = calculateHaversineDistanceKm(
            userLocation.lat,
            userLocation.lng,
            ev.latitude,
            ev.longitude
          );
        }
        return {
          ...ev,
          distanceKm,
        };
      })
      .filter((ev) => {
        // Severity filter
        if (selectedSeverity !== 'All' && ev.severity !== selectedSeverity) return false;
        // Category filter
        if (selectedCategory !== 'All' && ev.category !== selectedCategory) return false;
        // Radius filter (if user location is available and not "All India")
        if (maxRadiusKm !== 0 && ev.distanceKm != null) {
          return ev.distanceKm <= maxRadiusKm;
        }
        return true;
      })
      .sort((a, b) => {
        // Proximity first, then by timestamp descending
        if (a.distanceKm != null && b.distanceKm != null) {
          return a.distanceKm - b.distanceKm;
        }
        return (b.timestamp || 0) - (a.timestamp || 0);
      });
  }, [events, userLocation, maxRadiusKm, selectedSeverity, selectedCategory]);

  const toggleExpand = (alertId) => {
    setExpandedAlertId(expandedAlertId === alertId ? null : alertId);
  };

  return (
    <div className="min-h-screen bg-[#f5f2ea] text-slate-900 flex flex-col p-4 sm:p-6 lg:p-8 font-sans">
      <div className="max-w-5xl mx-auto w-full space-y-6">
        
        {/* Top Navigation Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3 sm:gap-4">
            <button
              id="back-to-home-btn"
              onClick={() => onNavigate('landing')}
              className="flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm px-4 py-2.5 rounded-xl shadow-xs border border-slate-200 transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Home</span>
            </button>

            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-600 shadow-xs">
                <Bell className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                  Proximity Alert Network
                </h1>
                <p className="text-xs text-slate-500 font-medium">
                  Real-time early warning and situational safety advisories based on your location
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadAlerts}
              disabled={loading}
              className="flex items-center gap-2 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-orange-600' : ''}`} />
              <span>Refresh Alerts</span>
            </button>
          </div>
        </div>

        {/* Location & Radius Control Panel */}
        <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/90 shadow-xs space-y-4">
          
          {/* Location Status Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center gap-2.5">
              <MapPin className="w-4 h-4 text-orange-600 shrink-0" />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-800">
                    Active Center: {userLocation?.name || 'Locating...'}
                  </span>
                  {userLocation?.isGps && (
                    <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                      GPS Active
                    </span>
                  )}
                </div>
                {locationError && (
                  <p className="text-[11px] text-amber-700 font-medium">{locationError}</p>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={requestGeolocation}
                className="px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-xl text-xs font-bold transition-colors cursor-pointer flex items-center gap-1.5 shadow-xs shrink-0"
              >
                <Compass className="w-3.5 h-3.5" />
                <span>Use My GPS</span>
              </button>

              {/* Searchable / Typeable City Selector */}
              <div className="w-64">
                <CitySelector
                  value={userLocation}
                  onSelectCity={handleSelectCity}
                  placeholder="Search / Type city..."
                />
              </div>
            </div>
          </div>

          {/* Radius & Severity Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
            
            {/* Radius Selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider mr-1 flex items-center gap-1">
                <Sliders className="w-3.5 h-3.5 text-orange-500" />
                <span>Alert Radius:</span>
              </span>
              {[
                { label: '50 km', val: 50 },
                { label: '150 km', val: 150 },
                { label: '300 km', val: 300 },
                { label: '500 km', val: 500 },
                { label: 'All India', val: 0 },
              ].map((r) => (
                <button
                  key={r.val}
                  onClick={() => setMaxRadiusKm(r.val)}
                  className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    maxRadiusKm === r.val
                      ? 'bg-orange-600 text-white shadow-xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>

            {/* Severity Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider mr-1">
                Severity:
              </span>
              {['All', 'Critical', 'Severe', 'Moderate'].map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSelectedSeverity(sev)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    selectedSeverity === sev
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>

          </div>

        </div>

        {/* Loading State */}
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map((n) => (
              <div key={n} className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs animate-pulse space-y-3">
                <div className="flex gap-2">
                  <div className="h-5 w-24 bg-slate-200 rounded-full" />
                  <div className="h-5 w-20 bg-slate-200 rounded-full" />
                </div>
                <div className="h-6 w-1/2 bg-slate-200 rounded-lg" />
                <div className="h-4 w-3/4 bg-slate-100 rounded-lg" />
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && processedAlerts.length === 0 && (
          <div className="bg-white rounded-3xl p-12 border border-slate-200/80 shadow-xs text-center space-y-4 min-h-[280px] flex flex-col items-center justify-center">
            <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
              <ShieldCheck className="w-7 h-7" />
            </div>
            <div className="space-y-1 max-w-md">
              <h3 className="text-lg font-bold text-slate-900">No Active Alerts Nearby</h3>
              <p className="text-sm text-slate-500 leading-relaxed">
                There are currently no recorded hazard threats within <strong>{maxRadiusKm === 0 ? 'All India' : `${maxRadiusKm} km`}</strong> of {userLocation?.name || 'your location'}.
              </p>
            </div>
            {maxRadiusKm !== 0 && (
              <button
                onClick={() => setMaxRadiusKm(0)}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white text-xs font-bold rounded-xl transition-colors cursor-pointer"
              >
                Expand View to All India Warnings
              </button>
            )}
          </div>
        )}

        {/* Alerts Feed List */}
        {!loading && processedAlerts.length > 0 && (
          <div className="space-y-3.5">
            <div className="flex items-center justify-between text-xs font-bold text-slate-500 px-1">
              <span>ACTIVE THREATS MATCHING CRITERIA ({processedAlerts.length})</span>
              <span>SORTED BY PROXIMITY</span>
            </div>

            {processedAlerts.map((alert) => {
              const config = getCategoryConfig(alert.category);
              const sevConfig = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.Moderate;
              const isExpanded = expandedAlertId === alert.id;
              const istTimeString = formatDateTimeIST(alert);

              return (
                <div
                  key={alert.id}
                  className="bg-white rounded-2xl border border-slate-200/90 hover:border-orange-400 transition-all duration-200 shadow-xs overflow-hidden"
                >
                  {/* Alert Header Summary */}
                  <div
                    onClick={() => toggleExpand(alert.id)}
                    className="p-5 sm:p-6 cursor-pointer flex flex-col sm:flex-row items-start justify-between gap-4 hover:bg-slate-50/60 transition-colors"
                  >
                    <div className="flex-1 space-y-2 min-w-0">
                      
                      {/* Top Badges */}
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        {/* Hazard Category Badge */}
                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-bold border ${config.badge}`}>
                          <span>{config.icon}</span>
                          <span>{config.label}</span>
                        </span>

                        {/* Severity Badge */}
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-bold text-[11px] uppercase tracking-wider ${sevConfig.badge}`}>
                          {alert.severity || 'Moderate'}
                        </span>

                        {/* Distance Badge */}
                        {alert.distanceKm != null && (
                          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-bold text-xs ${
                            alert.distanceKm <= 50
                              ? 'bg-red-500 text-white animate-pulse'
                              : alert.distanceKm <= 150
                              ? 'bg-orange-500 text-white'
                              : 'bg-slate-100 text-slate-800 border border-slate-200'
                          }`}>
                            <Navigation className="w-3 h-3 shrink-0" />
                            <span>{alert.distanceKm} km away</span>
                          </span>
                        )}

                        {/* IST Time */}
                        <span className="inline-flex items-center gap-1 text-slate-500 font-medium text-xs ml-auto">
                          <Clock className="w-3.5 h-3.5 text-orange-500" />
                          <span>{istTimeString}</span>
                        </span>
                      </div>

                      {/* Title */}
                      <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                        {alert.title}
                      </h3>

                      {/* Location & Source */}
                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 font-medium">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5 text-orange-500 shrink-0" />
                          <span>{alert.location || 'India'}{alert.state ? `, ${alert.state}` : ''}</span>
                        </span>
                        <span>•</span>
                        <span>Source: <strong className="text-slate-700">{alert.source_label || alert.source}</strong></span>
                      </div>

                    </div>

                    {/* Expand/Collapse Chevron */}
                    <div className="flex items-center gap-2 text-xs font-bold text-orange-600 shrink-0 self-end sm:self-center">
                      <span>{isExpanded ? 'Hide Advisory' : 'Safety Advisory'}</span>
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </div>

                  </div>

                  {/* Expanded Safety Advisory Section */}
                  {isExpanded && (
                    <div className="px-5 sm:px-6 pb-6 pt-2 border-t border-slate-100 bg-slate-50/50 space-y-4 animate-in fade-in duration-200">
                      
                      {/* Description */}
                      {alert.description && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <h4 className="font-bold uppercase tracking-wider text-slate-400">
                              Situation Briefing
                            </h4>
                            {alert.source_url && (
                              <a
                                href={alert.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-orange-600 hover:text-orange-700 font-bold inline-flex items-center gap-1 hover:underline cursor-pointer"
                              >
                                <span>Read Source</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            )}
                          </div>
                          <p className="text-xs sm:text-sm text-slate-700 leading-relaxed bg-white p-3.5 rounded-xl border border-slate-200/80 break-words">
                            {alert.description}
                          </p>
                        </div>
                      )}

                      {/* Event-Specific DOs and DON'Ts */}
                      {config && (config.dos?.length > 0 || config.donts?.length > 0) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {config.dos?.length > 0 && (
                            <div className="bg-emerald-50/80 border border-emerald-200 rounded-xl p-4 space-y-2">
                              <h5 className="text-xs font-bold text-emerald-900 uppercase tracking-wider flex items-center gap-1.5">
                                <CheckCircle className="w-4 h-4 text-emerald-600" />
                                <span>Actionable Guidance (DOs)</span>
                              </h5>
                              <ul className="text-xs text-emerald-800 space-y-1.5 pl-4 list-disc">
                                {config.dos.map((item, i) => (
                                  <li key={i}>{item}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {config.donts?.length > 0 && (
                            <div className="bg-rose-50/80 border border-rose-200 rounded-xl p-4 space-y-2">
                              <h5 className="text-xs font-bold text-rose-900 uppercase tracking-wider flex items-center gap-1.5">
                                <AlertTriangle className="w-4 h-4 text-rose-600" />
                                <span>High-Risk Actions (DON'Ts)</span>
                              </h5>
                              <ul className="text-xs text-rose-800 space-y-1.5 pl-4 list-disc">
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
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
};
