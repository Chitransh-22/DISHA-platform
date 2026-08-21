import React, { useState, useEffect, useMemo } from 'react';
import {
  ArrowLeft,
  MapPin,
  Compass,
  Navigation,
  RefreshCw,
  Sliders,
  ShieldCheck,
  AlertTriangle,
  Clock,
  ExternalLink,
  ChevronRight,
  Filter,
  Search,
} from 'lucide-react';
import { fetchEvents } from '../services/api';
import { EVENT_CONFIG, getCategoryConfig, SEVERITY_CONFIG } from '../config/eventConfig';

function calculateHaversineDistanceKm(lat1, lon1, lat2, lon2) {
  if (lat1 == null || lon1 == null || lat2 == null || lon2 == null) return null;
  const R = 6371;
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

const FALLBACK_CITIES = [
  { name: 'Delhi NCR', lat: 28.6139, lng: 77.2090 },
  { name: 'Mumbai, Maharashtra', lat: 19.0760, lng: 72.8777 },
  { name: 'Kolkata, West Bengal', lat: 22.5726, lng: 88.3639 },
  { name: 'Chennai, Tamil Nadu', lat: 13.0827, lng: 80.2707 },
  { name: 'Bengaluru, Karnataka', lat: 12.9716, lng: 77.5946 },
  { name: 'Guwahati, Assam', lat: 26.1445, lng: 91.7362 },
  { name: 'Dehradun, Uttarakhand', lat: 30.3165, lng: 78.0322 },
  { name: 'Shimla, Himachal Pradesh', lat: 31.1048, lng: 77.1734 },
  { name: 'Bhubaneswar, Odisha', lat: 20.2961, lng: 85.8245 },
  { name: 'Kochi, Kerala', lat: 9.9312, lng: 76.2673 },
];

export const NearbyIncidentsPage = ({ onNavigate }) => {
  const [userLocation, setUserLocation] = useState(null);
  const [locationStatus, setLocationStatus] = useState('prompt');
  const [locationError, setLocationError] = useState(null);

  const [maxRadiusKm, setMaxRadiusKm] = useState(150);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  const requestGeolocation = () => {
    if (!navigator.geolocation) {
      setLocationStatus('denied');
      setLocationError('Geolocation not supported.');
      setUserLocation(FALLBACK_CITIES[0]);
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
          name: `${lat.toFixed(2)}°N, ${lng.toFixed(2)}°E (Your GPS Coordinates)`,
          isGps: true,
        });
        setLocationStatus('granted');
      },
      (err) => {
        console.warn('[NearbyIncidentsPage] GPS error:', err.message);
        setLocationStatus('denied');
        setLocationError('GPS permission not provided. Selected Delhi NCR by default.');
        setUserLocation(FALLBACK_CITIES[0]);
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
    );
  };

  useEffect(() => {
    requestGeolocation();
  }, []);

  const loadEvents = async () => {
    setLoading(true);
    try {
      const data = await fetchEvents({ range: '30d' });
      if (data && Array.isArray(data.events)) {
        setEvents(data.events);
      }
    } catch (err) {
      console.error('[NearbyIncidentsPage] Error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const handleSelectCity = (city) => {
    setUserLocation({
      lat: city.lat,
      lng: city.lng,
      name: city.name,
      isGps: false,
    });
    setLocationStatus('manual');
    setLocationError(null);
  };

  const nearbyList = useMemo(() => {
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
        return { ...ev, distanceKm };
      })
      .filter((ev) => {
        if (selectedCategory !== 'All' && ev.category !== selectedCategory) return false;
        if (maxRadiusKm !== 0 && ev.distanceKm != null) {
          if (ev.distanceKm > maxRadiusKm) return false;
        }
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase().trim();
          const match =
            (ev.title && ev.title.toLowerCase().includes(q)) ||
            (ev.location && ev.location.toLowerCase().includes(q)) ||
            (ev.state && ev.state.toLowerCase().includes(q)) ||
            (ev.category && ev.category.toLowerCase().includes(q));
          if (!match) return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (a.distanceKm != null && b.distanceKm != null) {
          return a.distanceKm - b.distanceKm;
        }
        return (b.timestamp || 0) - (a.timestamp || 0);
      });
  }, [events, userLocation, maxRadiusKm, selectedCategory, searchQuery]);

  return (
    <div className="min-h-screen bg-[#f5f2ea] text-slate-900 flex flex-col p-4 sm:p-6 lg:p-8 font-sans">
      <div className="max-w-5xl mx-auto w-full space-y-6">
        
        {/* Top Navigation Bar */}
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
              <div className="w-10 h-10 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-600 shadow-xs">
                <MapPin className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                  Nearby Incidents Radar
                </h1>
                <p className="text-xs text-slate-500 font-medium">
                  Real-time geographic proximity calculation to active disaster events
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={loadEvents}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-orange-600' : ''}`} />
            <span>Refresh Incidents</span>
          </button>
        </div>

        {/* Location & Controls Bar */}
        <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/90 shadow-xs space-y-4">
          
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center gap-2.5">
              <Compass className="w-4 h-4 text-orange-600 shrink-0" />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-800">
                    Radar Center: {userLocation?.name || 'Locating...'}
                  </span>
                  {userLocation?.isGps && (
                    <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                      GPS Live
                    </span>
                  )}
                </div>
                {locationError && (
                  <p className="text-[11px] text-amber-700 font-medium">{locationError}</p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={requestGeolocation}
                className="px-3 py-1.5 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <Compass className="w-3.5 h-3.5" />
                <span>Use Current GPS</span>
              </button>

              <select
                onChange={(e) => {
                  const c = FALLBACK_CITIES.find((city) => city.name === e.target.value);
                  if (c) handleSelectCity(c);
                }}
                value={userLocation?.isGps ? '' : userLocation?.name || ''}
                className="bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-orange-500/30 cursor-pointer"
              >
                <option value="" disabled>
                  Select City Focus
                </option>
                {FALLBACK_CITIES.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Radius & Filters */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider mr-1 flex items-center gap-1">
                <Sliders className="w-3.5 h-3.5 text-orange-500" />
                <span>Search Radius:</span>
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

            <div className="relative flex-1 min-w-[200px] max-w-xs">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter by keyword / location..."
                className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8.5 pr-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
              />
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
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && nearbyList.length === 0 && (
          <div className="bg-white rounded-3xl p-12 border border-slate-200/80 shadow-xs text-center space-y-4 min-h-[280px] flex flex-col items-center justify-center">
            <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
              <ShieldCheck className="w-7 h-7" />
            </div>
            <div className="space-y-1 max-w-md">
              <h3 className="text-lg font-bold text-slate-900">No Incidents Within {maxRadiusKm === 0 ? 'All India' : `${maxRadiusKm} km`}</h3>
              <p className="text-sm text-slate-500 leading-relaxed">
                No active threats recorded near your active radar coordinates.
              </p>
            </div>
            {maxRadiusKm !== 0 && (
              <button
                onClick={() => setMaxRadiusKm(0)}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white text-xs font-bold rounded-xl transition-colors cursor-pointer"
              >
                Expand Radar to All India
              </button>
            )}
          </div>
        )}

        {/* Incidents List */}
        {!loading && nearbyList.length > 0 && (
          <div className="space-y-3.5">
            <div className="flex items-center justify-between text-xs font-bold text-slate-500 px-1">
              <span>ACTIVE INCIDENTS IN RADAR RANGE ({nearbyList.length})</span>
              <span>CLOSEST FIRST</span>
            </div>

            {nearbyList.map((incident) => {
              const config = getCategoryConfig(incident.category);
              const sevConfig = SEVERITY_CONFIG[incident.severity] || SEVERITY_CONFIG.Moderate;

              return (
                <div
                  key={incident.id}
                  className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200/90 shadow-xs hover:shadow-md transition-all duration-200 flex flex-col sm:flex-row items-start justify-between gap-4"
                >
                  <div className="flex-1 space-y-2 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-bold border ${config.badge}`}>
                        <span>{config.icon}</span>
                        <span>{config.label}</span>
                      </span>

                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-bold text-[11px] uppercase tracking-wider ${sevConfig.badge}`}>
                        {incident.severity || 'Moderate'}
                      </span>

                      {incident.distanceKm != null && (
                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-bold text-xs ${
                          incident.distanceKm <= 50
                            ? 'bg-red-500 text-white animate-pulse'
                            : incident.distanceKm <= 150
                            ? 'bg-orange-500 text-white'
                            : 'bg-slate-100 text-slate-800 border border-slate-200'
                        }`}>
                          <Navigation className="w-3 h-3 shrink-0" />
                          <span>{incident.distanceKm} km from you</span>
                        </span>
                      )}

                      <span className="inline-flex items-center gap-1 text-slate-400 font-mono text-[11px] ml-auto">
                        <Clock className="w-3 h-3" />
                        <span>{incident.date} {incident.time ? `• ${incident.time}` : ''}</span>
                      </span>
                    </div>

                    <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                      {incident.title}
                    </h3>

                    {incident.description && (
                      <p className="text-xs sm:text-sm text-slate-600 leading-relaxed line-clamp-2">
                        {incident.description}
                      </p>
                    )}

                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 pt-1">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-orange-500 shrink-0" />
                        <span>{incident.location || 'India'}{incident.state ? `, ${incident.state}` : ''}</span>
                      </span>
                      <span>•</span>
                      <span>Source: <strong className="text-slate-700">{incident.source_label || incident.source}</strong></span>
                    </div>
                  </div>

                  {/* Direction Link */}
                  {incident.latitude != null && incident.longitude != null && (
                    <a
                      href={`https://www.google.com/maps/dir/?api=1&destination=${incident.latitude},${incident.longitude}`}
                      target="_blank"
                      rel="noreferrer"
                      className="px-4 py-2 bg-slate-900 hover:bg-orange-600 text-white text-xs font-bold rounded-xl transition-colors shrink-0 flex items-center gap-1.5 shadow-xs cursor-pointer"
                    >
                      <Navigation className="w-3.5 h-3.5" />
                      <span>Directions ↗</span>
                    </a>
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
