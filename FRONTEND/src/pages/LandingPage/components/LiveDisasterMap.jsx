import React, { useState, useEffect, useRef, useMemo } from 'react';
import L from 'leaflet';
import {
  MapPin,
  Clock,
  Plus,
  Minus,
  Maximize2,
  Compass,
  Layers,
  Filter,
  RefreshCw,
  Search,
  Shield,
  Phone,
  Navigation,
  X,
  ChevronRight,
  AlertTriangle,
  HeartPulse,
  Flame,
  Radio,
  Check,
  TrendingDown,
} from 'lucide-react';
import { fetchEvents, fetchNearbyEmergencyServices } from '../../../services/api';
import { IncidentDetailModal } from './IncidentDetailModal';

// Presentation configuration for hazard threat categories
const CATEGORY_STYLES = {
  Earthquake: { color: '#ef4444', bg: 'bg-red-500', border: 'border-red-500', icon: '⚡', lightBg: 'bg-red-50 text-red-700 border-red-200' },
  Flood: { color: '#f97316', bg: 'bg-orange-500', border: 'border-orange-500', icon: '🌊', lightBg: 'bg-orange-50 text-orange-700 border-orange-200' },
  'Heavy Rain': { color: '#3b82f6', bg: 'bg-blue-500', border: 'border-blue-500', icon: '🌧️', lightBg: 'bg-blue-50 text-blue-700 border-blue-200' },
  Landslide: { color: '#a855f7', bg: 'bg-purple-500', border: 'border-purple-500', icon: '⛰️', lightBg: 'bg-purple-50 text-purple-700 border-purple-200' },
  Lightning: { color: '#eab308', bg: 'bg-yellow-500', border: 'border-yellow-500', icon: '⚡', lightBg: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  Cyclone: { color: '#10b981', bg: 'bg-emerald-500', border: 'border-emerald-500', icon: '🌀', lightBg: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  Fire: { color: '#f59e0b', bg: 'bg-amber-500', border: 'border-amber-500', icon: '🔥', lightBg: 'bg-amber-50 text-amber-700 border-amber-200' },
  Cloudburst: { color: '#06b6d4', bg: 'bg-cyan-500', border: 'border-cyan-500', icon: '⛈️', lightBg: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
  'Building Collapse': { color: '#e11d48', bg: 'bg-rose-600', border: 'border-rose-600', icon: '🏚️', lightBg: 'bg-rose-50 text-rose-700 border-rose-200' },
  'Industrial Accident': { color: '#d97706', bg: 'bg-amber-600', border: 'border-amber-600', icon: '⚠️', lightBg: 'bg-amber-50 text-amber-700 border-amber-200' },
  Explosion: { color: '#dc2626', bg: 'bg-red-600', border: 'border-red-600', icon: '💥', lightBg: 'bg-red-50 text-red-700 border-red-200' },
  Other: { color: '#64748b', bg: 'bg-slate-500', border: 'border-slate-500', icon: '⚠️', lightBg: 'bg-slate-50 text-slate-700 border-slate-200' },
};

export const LiveDisasterMap = () => {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const eventMarkersLayerRef = useRef(null);
  const emergencyMarkersLayerRef = useRef(null);
  const radiusCircleRef = useRef(null);

  // Events State
  const [events, setEvents] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(true);
  const [eventsError, setEventsError] = useState(null);
  const [sourceCounts, setSourceCounts] = useState({ total: 0, earthquakes: 0, sachet: 0, news: 0 });

  // Filters State
  const [activeSource, setActiveSource] = useState('all'); // 'all', 'ncs', 'sachet', 'news'
  const [selectedCategories, setSelectedCategories] = useState(['All']); // Multi-select array
  const [selectedSeverity, setSelectedSeverity] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Event & Nearby Services State
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [nearbyServicesData, setNearbyServicesData] = useState(null);
  const [loadingNearbyServices, setLoadingNearbyServices] = useState(false);
  const [nearbyServicesError, setNearbyServicesError] = useState(null);
  const [serviceFilterCategory, setServiceFilterCategory] = useState('all');
  const [selectedRadiusM, setSelectedRadiusM] = useState(5000);

  // Modal State for full situation briefing
  const [modalIncident, setModalIncident] = useState(null);

  // Map Telemetry State
  const [currentZoom, setCurrentZoom] = useState(5);
  const [cursorCoords, setCursorCoords] = useState({ lat: 22.35, lng: 78.66 });
  const [lastSyncTime, setLastSyncTime] = useState(
    new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
  );

  // 1. Fetch 100% real database events from backend
  const loadEventsData = async () => {
    setLoadingEvents(true);
    setEventsError(null);
    try {
      const data = await fetchEvents();
      if (data && Array.isArray(data.events)) {
        // Filter strictly to events with valid numeric coordinates
        const validEvents = data.events.filter(
          (ev) =>
            ev &&
            typeof ev.latitude === 'number' &&
            typeof ev.longitude === 'number' &&
            !isNaN(ev.latitude) &&
            !isNaN(ev.longitude) &&
            ev.latitude >= -90 &&
            ev.latitude <= 90 &&
            ev.longitude >= -180 &&
            ev.longitude <= 180
        );

        setEvents(validEvents);

        if (data.source_counts) {
          setSourceCounts(data.source_counts);
        } else {
          setSourceCounts({
            total: validEvents.length,
            earthquakes: validEvents.filter((e) => e.source === 'NCS_RISEQ' || e.source_group === 'ncs').length,
            sachet: validEvents.filter((e) => e.source === 'NDMA_SACHET' || e.source_group === 'sachet').length,
            news: validEvents.filter((e) => e.source === 'GNEWS' || e.source_group === 'news').length,
          });
        }

        setLastSyncTime(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }));
      } else {
        setEvents([]);
      }
    } catch (err) {
      console.error('[LiveDisasterMap] Failed to load events:', err);
      setEventsError('Unable to load events. Please check connection and try again.');
    } finally {
      setLoadingEvents(false);
    }
  };

  useEffect(() => {
    loadEventsData();
  }, []);

  // Compute category counts for sorting in descending order
  const categoryCounts = useMemo(() => {
    const counts = {};
    events.forEach((ev) => {
      const cat = ev.category || 'Other';
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return counts;
  }, [events]);

  // Categories sorted in STRICT DESCENDING ORDER by event count
  const sortedCategories = useMemo(() => {
    return Object.keys(categoryCounts).sort((a, b) => {
      const countDiff = (categoryCounts[b] || 0) - (categoryCounts[a] || 0);
      if (countDiff !== 0) return countDiff;
      return a.localeCompare(b);
    });
  }, [categoryCounts]);

  // Multiple Select Category Toggle Handler
  const handleToggleCategory = (cat) => {
    if (cat === 'All') {
      setSelectedCategories(['All']);
      return;
    }

    setSelectedCategories((prev) => {
      if (prev.includes('All')) {
        return [cat];
      }

      if (prev.includes(cat)) {
        const next = prev.filter((c) => c !== cat);
        return next.length === 0 ? ['All'] : next;
      } else {
        const next = [...prev, cat];
        if (sortedCategories.length > 0 && next.length === sortedCategories.length) {
          return ['All'];
        }
        return next;
      }
    });
  };

  // Select All Categories
  const handleSelectAllCategories = () => {
    setSelectedCategories(['All']);
  };

  // 2. Filter Events Client-Side
  const filteredEvents = useMemo(() => {
    const isAllCats = selectedCategories.includes('All') || selectedCategories.length === 0;

    return events.filter((ev) => {
      // 1. Source Group Filter (NCS, SACHET, News)
      if (activeSource !== 'all') {
        const src = (ev.source_group || ev.source || '').toLowerCase();
        if (activeSource === 'ncs' && !src.includes('ncs') && !src.includes('riseq')) return false;
        if (activeSource === 'sachet' && !src.includes('sachet') && !src.includes('ndma')) return false;
        if (activeSource === 'news' && !src.includes('gnews') && !src.includes('news')) return false;
      }

      // 2. Multiple Category Filter
      if (!isAllCats) {
        const evCat = ev.category || 'Other';
        const evRaw = ev.raw_category || '';
        const match = selectedCategories.some(
          (c) => c.toLowerCase() === evCat.toLowerCase() || c.toLowerCase() === evRaw.toLowerCase()
        );
        if (!match) return false;
      }

      // 3. Severity Filter
      if (selectedSeverity !== 'All') {
        if (ev.severity?.toLowerCase() !== selectedSeverity.toLowerCase()) {
          return false;
        }
      }

      // 4. Search Query Filter (Title, Location, State, District)
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const titleMatch = ev.title?.toLowerCase().includes(query);
        const locMatch = ev.location?.toLowerCase().includes(query);
        const stateMatch = ev.state?.toLowerCase().includes(query);
        const distMatch = ev.district?.toLowerCase().includes(query);
        const descMatch = ev.description?.toLowerCase().includes(query);
        if (!titleMatch && !locMatch && !stateMatch && !distMatch && !descMatch) {
          return false;
        }
      }

      return true;
    });
  }, [events, activeSource, selectedCategories, selectedSeverity, searchQuery]);

  // 3. Initialize Leaflet Map
  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container) return;

    if (mapInstanceRef.current) {
      try {
        mapInstanceRef.current.remove();
      } catch (e) {
        console.warn(e);
      }
      mapInstanceRef.current = null;
    }

    if (container._leaflet_id) {
      try {
        delete container._leaflet_id;
      } catch (e) {
        container._leaflet_id = undefined;
      }
    }

    try {
      const map = L.map(container, {
        center: [22.3511, 78.6677],
        zoom: 5,
        minZoom: 4,
        maxZoom: 16,
        zoomControl: false,
        attributionControl: true,
        scrollWheelZoom: false,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors | DISHA Platform',
        subdomains: ['a', 'b', 'c'],
        maxZoom: 19,
      }).addTo(map);

      // Create dedicated LayerGroups
      const eventMarkersLayer = L.layerGroup().addTo(map);
      const emergencyMarkersLayer = L.layerGroup().addTo(map);

      eventMarkersLayerRef.current = eventMarkersLayer;
      emergencyMarkersLayerRef.current = emergencyMarkersLayer;

      map.on('zoomend', () => {
        try {
          setCurrentZoom(map.getZoom());
        } catch (e) {}
      });

      map.on('mousemove', (e) => {
        try {
          if (e && e.latlng) {
            setCursorCoords({
              lat: +e.latlng.lat.toFixed(2),
              lng: +e.latlng.lng.toFixed(2),
            });
          }
        } catch (e) {}
      });

      mapInstanceRef.current = map;
    } catch (err) {
      console.error('[LiveDisasterMap] Leaflet initialization error:', err);
    }

    return () => {
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
        } catch (e) {}
        mapInstanceRef.current = null;
      }
      if (container && container._leaflet_id) {
        try {
          delete container._leaflet_id;
        } catch (e) {
          container._leaflet_id = undefined;
        }
      }
    };
  }, []);

  // 4. Handle Event Selection & Fetch Nearby Emergency Services
  const handleSelectEvent = async (event, radiusM = 5000) => {
    if (!event || typeof event.latitude !== 'number' || typeof event.longitude !== 'number') return;

    setSelectedEvent(event);
    setSelectedRadiusM(radiusM);
    setLoadingNearbyServices(true);
    setNearbyServicesError(null);
    setServiceFilterCategory('all');

    // Pan map smoothly to the selected event
    if (mapInstanceRef.current) {
      mapInstanceRef.current.flyTo([event.latitude, event.longitude], 11, {
        duration: 0.8,
        easeLinearity: 0.25,
      });
    }

    try {
      const servicesPayload = await fetchNearbyEmergencyServices(event.latitude, event.longitude, radiusM);
      setNearbyServicesData(servicesPayload);
    } catch (err) {
      console.error('[LiveDisasterMap] Error fetching nearby emergency services:', err);
      setNearbyServicesError('Unable to load nearby emergency services.');
      setNearbyServicesData(null);
    } finally {
      setLoadingNearbyServices(false);
    }
  };

  // Deselect event and reset map view
  const handleDeselectEvent = () => {
    setSelectedEvent(null);
    setNearbyServicesData(null);
    setNearbyServicesError(null);
    setLoadingNearbyServices(false);

    if (mapInstanceRef.current && radiusCircleRef.current) {
      mapInstanceRef.current.removeLayer(radiusCircleRef.current);
      radiusCircleRef.current = null;
    }
    if (emergencyMarkersLayerRef.current) {
      emergencyMarkersLayerRef.current.clearLayers();
    }
  };

  // Change search radius for selected event
  const handleRadiusChange = (newRadiusM) => {
    if (selectedEvent) {
      handleSelectEvent(selectedEvent, newRadiusM);
    }
  };

  // 5. Render Event Markers on Map
  useEffect(() => {
    if (!mapInstanceRef.current || !eventMarkersLayerRef.current) return;

    try {
      const layer = eventMarkersLayerRef.current;
      layer.clearLayers();

      filteredEvents.forEach((ev) => {
        const isSelected = selectedEvent && selectedEvent.id === ev.id;
        const style = CATEGORY_STYLES[ev.category] || CATEGORY_STYLES.Other;
        const iconSymbol = style.icon || '⚠️';

        // Marker HTML with distinct styling for selected vs normal state
        const markerHtml = `
          <div class="custom-disaster-pin relative flex items-center justify-center cursor-pointer transition-transform duration-150 ${
            isSelected ? 'scale-125 z-40' : 'hover:scale-115'
          }" style="width: 42px; height: 42px;">
            ${
              isSelected
                ? `<span class="animate-ping-slow absolute inline-flex h-11 w-11 rounded-full" style="background-color: #0284c7; opacity: 0.85;"></span>
                   <span class="absolute inline-flex h-10 w-10 rounded-full border-2 border-cyan-400" style="background-color: ${style.color}44;"></span>`
                : `<span class="animate-pulse-ring absolute inline-flex h-9 w-9 rounded-full" style="background-color: ${style.color}; opacity: 0.35;"></span>`
            }
            <div class="relative w-8 h-8 rounded-full shadow-xl flex items-center justify-center text-white border-2 ${
              isSelected ? 'border-cyan-300 ring-4 ring-cyan-500/50' : 'border-white'
            }" style="background-color: ${style.color};">
              <span style="font-size: 13px;">${iconSymbol}</span>
            </div>
            ${
              isSelected
                ? `<div class="absolute -bottom-5 whitespace-nowrap bg-slate-900/90 text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow border border-cyan-400">SELECTED INCIDENT</div>`
                : ''
            }
          </div>
        `;

        const customIcon = L.divIcon({
          className: 'custom-leaflet-marker',
          html: markerHtml,
          iconSize: [42, 42],
          iconAnchor: [21, 21],
          popupAnchor: [0, -22],
        });

        const marker = L.marker([ev.latitude, ev.longitude], { icon: customIcon });

        // Popup Container
        const popupContent = document.createElement('div');
        popupContent.className = 'p-3.5 space-y-2.5 text-slate-100 max-w-[280px] font-sans';
        popupContent.innerHTML = `
          <div class="flex items-center justify-between gap-2 border-b border-white/10 pb-2">
            <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full" style="background-color: ${style.color}33; color: ${style.color}; border: 1px solid ${style.color}66;">
              ${ev.category || 'Disaster'}
            </span>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${
              ev.severity === 'Critical'
                ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                : ev.severity === 'Severe'
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40'
                : 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/40'
            }">
              ${ev.severity || 'Moderate'}
            </span>
          </div>
          <div>
            <h4 class="text-sm font-bold text-white leading-snug">${ev.title || 'Incident'}</h4>
            <p class="text-[11px] text-slate-400 mt-0.5">📍 ${ev.location || ''}${ev.state ? ` (${ev.state})` : ''}</p>
            <p class="text-[10px] text-slate-500 mt-0.5">🕒 ${ev.date} • ${ev.time}</p>
            <span class="inline-block mt-1 text-[9.5px] font-bold text-cyan-300 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800/50">
              Source: ${ev.source_label || ev.source}
            </span>
          </div>
          <p class="text-xs text-slate-300 line-clamp-2 leading-relaxed bg-white/5 p-2 rounded-lg border border-white/10">
            ${ev.description || 'Disaster incident monitoring.'}
          </p>
          <div class="flex flex-col gap-1.5 mt-2">
            <button id="find-nearby-btn-${ev.id.replace(/[^a-zA-Z0-9]/g, '_')}" class="w-full bg-linear-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold text-xs py-2 rounded-xl transition-all duration-150 shadow-md cursor-pointer flex items-center justify-center gap-1.5">
              <span>Find Nearby Emergency Services</span>
              <span>→</span>
            </button>
            <button id="briefing-btn-${ev.id.replace(/[^a-zA-Z0-9]/g, '_')}" class="w-full bg-white/10 hover:bg-white/20 text-slate-200 font-semibold text-[11px] py-1.5 rounded-lg transition-colors cursor-pointer text-center">
              View Situation Brief
            </button>
          </div>
        `;

        const sanitizedId = ev.id.replace(/[^a-zA-Z0-9]/g, '_');
        const findNearbyBtn = popupContent.querySelector(`#find-nearby-btn-${sanitizedId}`);
        if (findNearbyBtn) {
          findNearbyBtn.addEventListener('click', () => {
            handleSelectEvent(ev, selectedRadiusM);
            marker.closePopup();
          });
        }

        const briefingBtn = popupContent.querySelector(`#briefing-btn-${sanitizedId}`);
        if (briefingBtn) {
          briefingBtn.addEventListener('click', () => {
            setModalIncident(ev);
          });
        }

        marker.on('click', () => {
          handleSelectEvent(ev, selectedRadiusM);
        });

        marker.bindPopup(popupContent);
        marker.addTo(layer);
      });
    } catch (err) {
      console.error('[LiveDisasterMap] Error rendering event markers:', err);
    }
  }, [filteredEvents, selectedEvent, selectedRadiusM]);

  // 6. Render Nearby Emergency Service Markers & Radius Circle on Map
  useEffect(() => {
    if (!mapInstanceRef.current || !emergencyMarkersLayerRef.current) return;

    const layer = emergencyMarkersLayerRef.current;
    layer.clearLayers();

    if (radiusCircleRef.current) {
      mapInstanceRef.current.removeLayer(radiusCircleRef.current);
      radiusCircleRef.current = null;
    }

    if (!selectedEvent || !nearbyServicesData || !nearbyServicesData.services) {
      return;
    }

    const { services, search_radius_km } = nearbyServicesData;
    const originLat = selectedEvent.latitude;
    const originLng = selectedEvent.longitude;

    // Draw radius boundary circle around the selected incident
    const radiusMeters = (search_radius_km || selectedRadiusM / 1000.0) * 1000.0;
    const circle = L.circle([originLat, originLng], {
      radius: radiusMeters,
      color: '#0284c7',
      weight: 1.5,
      opacity: 0.8,
      fillColor: '#0284c7',
      fillOpacity: 0.06,
      dashArray: '5, 5',
    }).addTo(mapInstanceRef.current);
    radiusCircleRef.current = circle;

    // Aggregate and filter services to plot on map
    const serviceItems = [];
    if (services.medical && (serviceFilterCategory === 'all' || serviceFilterCategory === 'medical')) {
      serviceItems.push(...services.medical);
    }
    if (services.police && (serviceFilterCategory === 'all' || serviceFilterCategory === 'police')) {
      serviceItems.push(...services.police);
    }
    if (services.fire && (serviceFilterCategory === 'all' || serviceFilterCategory === 'fire')) {
      serviceItems.push(...services.fire);
    }

    const mapMarkersForBounds = [L.marker([originLat, originLng])];

    serviceItems.forEach((svc) => {
      if (typeof svc.latitude !== 'number' || typeof svc.longitude !== 'number') return;

      let pinColor = '#0284c7'; // Medical (Cyan)
      let pinIcon = '🏥';
      let pinBadgeBg = 'bg-cyan-600';

      if (svc.category === 'police') {
        pinColor = '#4f46e5'; // Police (Indigo)
        pinIcon = '🚔';
        pinBadgeBg = 'bg-indigo-600';
      } else if (svc.category === 'fire') {
        pinColor = '#d97706'; // Fire (Amber)
        pinIcon = '🚒';
        pinBadgeBg = 'bg-amber-600';
      }

      // Visually distinctive emergency facility marker
      const markerHtml = `
        <div class="custom-emergency-pin relative flex flex-col items-center justify-center cursor-pointer group" style="width: 34px; height: 34px;">
          <div class="w-7 h-7 rounded-lg shadow-lg flex items-center justify-center text-white border-2 border-white transition-transform duration-150 group-hover:scale-125" style="background-color: ${pinColor};">
            <span style="font-size: 13px;">${pinIcon}</span>
          </div>
          <div class="absolute -bottom-3.5 bg-slate-900/90 text-white text-[8.5px] font-mono font-bold px-1 rounded shadow-xs border border-white/20 whitespace-nowrap">
            ${svc.distance_formatted || `${svc.distance_km} km`}
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'custom-emergency-marker',
        html: markerHtml,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
        popupAnchor: [0, -18],
      });

      const marker = L.marker([svc.latitude, svc.longitude], { icon: customIcon });
      mapMarkersForBounds.push(marker);

      // Interactive Service Popup
      const popupContent = document.createElement('div');
      popupContent.className = 'p-3.5 space-y-2 text-slate-100 max-w-[280px] font-sans';
      popupContent.innerHTML = `
        <div class="flex items-center justify-between gap-2 border-b border-white/10 pb-1.5">
          <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full text-white ${pinBadgeBg}">
            ${svc.category_label || svc.category || 'Emergency Unit'}
          </span>
          <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
            ${svc.distance_formatted || `${svc.distance_km} km`}
          </span>
        </div>
        <div>
          <h4 class="text-sm font-bold text-white leading-snug">${svc.name || 'Emergency Facility'}</h4>
          <p class="text-[11px] text-slate-400 mt-0.5">${svc.address || 'Address registered on OpenStreetMap'}</p>
          <p class="text-[10px] text-cyan-300 mt-0.5 font-mono">⚡ Est. Response Transit: ${svc.estimated_time_formatted || '~5 min'}</p>
        </div>
        <div class="flex items-center gap-2 pt-1 border-t border-white/10">
          ${
            svc.phone
              ? `<a href="tel:${svc.phone.replace(/[^0-9+]/g, '')}" class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs py-1.5 rounded-lg transition-colors text-center flex items-center justify-center gap-1">
                  <span>📞 Call</span>
                </a>`
              : ''
          }
          <a href="${svc.directions_url || `https://www.google.com/maps/dir/?api=1&origin=${originLat},${originLng}&destination=${svc.latitude},${svc.longitude}`}" target="_blank" rel="noreferrer" class="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-1.5 px-2.5 rounded-lg transition-colors text-center flex items-center justify-center gap-1">
            <span>🧭 Directions</span>
          </a>
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.addTo(layer);
    });

    // Auto-fit map bounds to encompass incident and all discovered services
    if (mapMarkersForBounds.length > 1) {
      const group = L.featureGroup(mapMarkersForBounds);
      mapInstanceRef.current.flyToBounds(group.getBounds().pad(0.2), {
        duration: 0.9,
        easeLinearity: 0.25,
        maxZoom: 14,
      });
    }
  }, [selectedEvent, nearbyServicesData, serviceFilterCategory, selectedRadiusM]);

  // Zoom controls
  const handleZoomIn = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.zoomIn();
  };

  const handleZoomOut = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.zoomOut();
  };

  const handleRecenter = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.flyTo([22.3511, 78.6677], 5, { duration: 1.2 });
    }
  };

  // Filtered list of emergency services for the side panel
  const panelServiceList = useMemo(() => {
    if (!nearbyServicesData || !nearbyServicesData.services) return [];
    const { services } = nearbyServicesData;
    let list = [];
    if (serviceFilterCategory === 'all') {
      list = [...(services.medical || []), ...(services.police || []), ...(services.fire || [])];
    } else if (serviceFilterCategory === 'medical') {
      list = [...(services.medical || [])];
    } else if (serviceFilterCategory === 'police') {
      list = [...(services.police || [])];
    } else if (serviceFilterCategory === 'fire') {
      list = [...(services.fire || [])];
    }
    return list.sort((a, b) => (a.distance_km || 0) - (b.distance_km || 0));
  }, [nearbyServicesData, serviceFilterCategory]);

  return (
    <section id="disaster-map-section" className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-10 relative z-10">
      
      {/* Main Map Container Card */}
      <div className="bg-white rounded-3xl shadow-xl shadow-slate-200/60 border border-slate-200/90 overflow-hidden flex flex-col transition-all duration-300">
        
        {/* Command Header Bar */}
        <div className="px-5 sm:px-8 py-4 sm:py-5 border-b border-slate-100 flex flex-wrap items-center justify-between gap-4 bg-white z-20 relative">
          
          {/* Left Title: Pin + "Live Event & Emergency Services Map" */}
          <div className="flex items-center gap-3 sm:gap-3.5">
            <div className="w-10 h-10 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-600 shadow-xs">
              <MapPin className="w-5 h-5 fill-orange-500/20 text-orange-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight font-sans">
                  DISHA Event & Emergency Services Map
                </h2>
                <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-orange-500/10 text-orange-600 border border-orange-500/20">
                  GIS Rescue Intelligence
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                {events.length} Real-Time Events Ingested from NCS, NDMA & News • Select an incident to map first-responders
              </p>
            </div>
          </div>

          {/* Right Controls: Refresh + Status Indicator */}
          <div className="flex items-center gap-3">
            <button
              onClick={loadEventsData}
              disabled={loadingEvents}
              className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200/80 text-slate-600 hover:text-slate-900 transition-colors cursor-pointer disabled:opacity-50"
              title="Sync Latest Sensor Data from Render Backend"
              aria-label="Sync Latest Sensor Data"
            >
              <RefreshCw className={`w-4 h-4 ${loadingEvents ? 'animate-spin text-orange-600' : ''}`} />
            </button>

            <div className="flex items-center gap-3 bg-slate-50 border border-slate-200/80 px-3.5 py-2 rounded-2xl shadow-2xs">
              <Clock className="w-4 h-4 text-slate-400 shrink-0" />
              <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2">
                <span className="text-[10px] sm:text-xs text-slate-400 font-semibold uppercase tracking-wider">Backend Sync</span>
                <span className="text-xs sm:text-sm font-bold text-slate-800 font-sans">{lastSyncTime}</span>
              </div>

              <div className="flex items-center gap-1.5 pl-2 border-l border-slate-200">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                </span>
                <span className="text-[11px] font-bold text-emerald-600 hidden md:inline">CONNECTED</span>
              </div>
            </div>
          </div>

        </div>

        {/* 1. Source Feed Selector Tabs (All Feeds, NCS Earthquakes, NDMA SACHET Alerts, Disaster News) */}
        <div className="px-5 sm:px-8 py-2.5 bg-slate-100/75 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 z-20">
          <div className="flex items-center gap-2 overflow-x-auto scrollbar-none py-0.5">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider shrink-0 flex items-center gap-1">
              <Radio className="w-3.5 h-3.5 text-orange-500" />
              <span>Data Source:</span>
            </span>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setActiveSource('all')}
                className={`px-3 py-1 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeSource === 'all'
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-white text-slate-600 hover:bg-slate-200/80 border border-slate-200'
                }`}
              >
                <span>All Sources</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${activeSource === 'all' ? 'bg-orange-500 text-white' : 'bg-slate-100 text-slate-600'}`}>
                  {sourceCounts.total || events.length}
                </span>
              </button>

              <button
                onClick={() => setActiveSource('ncs')}
                className={`px-3 py-1 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeSource === 'ncs'
                    ? 'bg-red-700 text-white shadow-xs'
                    : 'bg-white text-slate-600 hover:bg-slate-200/80 border border-slate-200'
                }`}
              >
                <span>⚡ NCS Earthquakes</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${activeSource === 'ncs' ? 'bg-red-900 text-white' : 'bg-slate-100 text-slate-600'}`}>
                  {sourceCounts.earthquakes}
                </span>
              </button>

              <button
                onClick={() => setActiveSource('sachet')}
                className={`px-3 py-1 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeSource === 'sachet'
                    ? 'bg-purple-700 text-white shadow-xs'
                    : 'bg-white text-slate-600 hover:bg-slate-200/80 border border-slate-200'
                }`}
              >
                <span>🏛️ NDMA SACHET Feed</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${activeSource === 'sachet' ? 'bg-purple-900 text-white' : 'bg-slate-100 text-slate-600'}`}>
                  {sourceCounts.sachet}
                </span>
              </button>

              <button
                onClick={() => setActiveSource('news')}
                className={`px-3 py-1 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeSource === 'news'
                    ? 'bg-blue-700 text-white shadow-xs'
                    : 'bg-white text-slate-600 hover:bg-slate-200/80 border border-slate-200'
                }`}
              >
                <span>📰 Disaster News</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${activeSource === 'news' ? 'bg-blue-900 text-white' : 'bg-slate-100 text-slate-600'}`}>
                  {sourceCounts.news}
                </span>
              </button>
            </div>
          </div>

          <span className="text-[11px] font-semibold text-slate-500 hidden sm:inline">
            Showing <strong className="text-slate-800">{filteredEvents.length}</strong> matching markers
          </span>
        </div>

        {/* 2. Multiple-Select Threat Category Bar (SORTED DESCENDING BY EVENT COUNT) */}
        <div className="px-5 sm:px-8 py-3 bg-slate-50 border-b border-slate-200/80 flex flex-wrap items-center justify-between gap-3 z-20">
          
          {/* Multiple Select Category Pills */}
          <div className="flex items-center gap-2 overflow-x-auto scrollbar-none py-1 flex-1 min-w-0">
            <div className="flex items-center gap-1 text-xs font-bold text-slate-600 uppercase tracking-wider mr-1 shrink-0">
              <Filter className="w-3.5 h-3.5 text-slate-500" />
              <span>Categories:</span>
            </div>

            {/* "All" Toggle Pill */}
            <button
              onClick={() => handleToggleCategory('All')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer shrink-0 flex items-center gap-1.5 ${
                selectedCategories.includes('All')
                  ? 'bg-slate-900 text-white shadow-md ring-2 ring-slate-700'
                  : 'bg-white text-slate-600 hover:bg-slate-200/80 border border-slate-200/90'
              }`}
            >
              <span>All</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                  selectedCategories.includes('All') ? 'bg-orange-500 text-white' : 'bg-slate-100 text-slate-500'
                }`}
              >
                {events.length}
              </span>
            </button>

            {/* Individual Multi-Select Category Pills (Rendered in Descending Order of Event Count) */}
            {sortedCategories.map((cat) => {
              const isSelected = selectedCategories.includes(cat) || selectedCategories.includes('All');
              const isExplicitlySelected = selectedCategories.includes(cat);
              const count = categoryCounts[cat] || 0;
              const style = CATEGORY_STYLES[cat] || CATEGORY_STYLES.Other;

              return (
                <button
                  key={cat}
                  onClick={() => handleToggleCategory(cat)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer shrink-0 flex items-center gap-1.5 ${
                    isExplicitlySelected
                      ? 'bg-slate-900 text-white shadow-md ring-2 ring-orange-500/80'
                      : isSelected && selectedCategories.includes('All')
                      ? 'bg-white text-slate-800 border-2 border-slate-300 hover:border-slate-400'
                      : 'bg-white/60 text-slate-400 border border-slate-200 hover:text-slate-700 hover:bg-white'
                  }`}
                  title={`Click to toggle ${cat} (${count} events)`}
                >
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: style.color }} />
                  <span>{cat}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                      isExplicitlySelected
                        ? 'bg-orange-500 text-white'
                        : isSelected
                        ? 'bg-slate-100 text-slate-700 font-semibold'
                        : 'bg-slate-100 text-slate-400'
                    }`}
                  >
                    {count}
                  </span>
                  {isExplicitlySelected && <Check className="w-3 h-3 text-orange-400 ml-0.5" />}
                </button>
              );
            })}

            {/* Select All / Reset Actions if partially selected */}
            {!selectedCategories.includes('All') && (
              <button
                onClick={handleSelectAllCategories}
                className="text-[11px] font-bold text-orange-600 hover:text-orange-700 underline px-2 py-1 shrink-0 cursor-pointer"
              >
                Reset All
              </button>
            )}
          </div>

          {/* Secondary Filters: Severity & Search */}
          <div className="flex items-center gap-2.5 w-full sm:w-auto shrink-0">
            {/* Severity Filter Dropdown */}
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="bg-white border border-slate-200/90 text-slate-700 text-xs font-semibold rounded-xl px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-orange-500/20 cursor-pointer"
            >
              <option value="All">All Severities</option>
              <option value="Critical">Critical</option>
              <option value="Severe">Severe</option>
              <option value="Moderate">Moderate</option>
              <option value="Low">Low</option>
            </select>

            {/* Keyword Search Input */}
            <div className="relative flex-1 sm:w-44">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                placeholder="Search state/city..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white border border-slate-200/90 text-slate-700 text-xs rounded-xl pl-8 pr-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-orange-500/20 placeholder:text-slate-400"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

        </div>

        {/* Map Viewport Area & Integrated Nearby Emergency Services Panel */}
        <div className="relative w-full h-[540px] sm:h-[620px] lg:h-[680px] bg-slate-100 overflow-hidden flex flex-col md:flex-row">
          
          {/* Center Leaflet Map Viewport */}
          <div className="relative flex-1 w-full h-full min-w-0">
            
            {/* Leaflet DOM Root */}
            <div ref={mapContainerRef} className="w-full h-full z-10" />

            {/* Loading Events Banner Overlay */}
            {loadingEvents && (
              <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 bg-slate-900/90 backdrop-blur-md text-white text-xs font-semibold px-4 py-2 rounded-full border border-white/10 shadow-xl flex items-center gap-2 pointer-events-none animate-in fade-in">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-orange-400" />
                <span>Loading real hazard events from database...</span>
              </div>
            )}

            {/* Events Error Notice */}
            {eventsError && !loadingEvents && (
              <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 bg-red-950/90 backdrop-blur-md text-red-200 text-xs font-semibold px-4 py-2 rounded-full border border-red-500/30 shadow-xl flex items-center gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                <span>{eventsError}</span>
                <button
                  onClick={loadEventsData}
                  className="underline font-bold hover:text-white cursor-pointer ml-1"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Empty Events Filter Notice */}
            {!loadingEvents && filteredEvents.length === 0 && !eventsError && (
              <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 bg-slate-900/90 backdrop-blur-md text-slate-300 text-xs font-medium px-4 py-2 rounded-full border border-white/10 shadow-xl pointer-events-none">
                No events available matching your selected filters.
              </div>
            )}

            {/* Floating Zoom HUD (Top Left) */}
            <div className="absolute top-4 left-4 z-30 flex flex-col gap-1 bg-white/95 backdrop-blur-xl rounded-2xl shadow-xl border border-slate-200/90 p-1.5">
              <button
                id="map-zoom-in-btn"
                onClick={handleZoomIn}
                className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center rounded-xl bg-slate-50 hover:bg-orange-500 hover:text-white text-slate-700 font-bold transition-all duration-150 shadow-xs cursor-pointer active:scale-95"
                title="Zoom In"
                aria-label="Zoom In"
              >
                <Plus className="w-4 h-4" />
              </button>
              <div className="text-[10px] font-mono font-bold text-slate-600 text-center py-0.5 select-none">
                {currentZoom}x
              </div>
              <button
                id="map-zoom-out-btn"
                onClick={handleZoomOut}
                className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center rounded-xl bg-slate-50 hover:bg-orange-500 hover:text-white text-slate-700 font-bold transition-all duration-150 shadow-xs cursor-pointer active:scale-95"
                title="Zoom Out"
                aria-label="Zoom Out"
              >
                <Minus className="w-4 h-4" />
              </button>
              <button
                id="map-recenter-btn"
                onClick={handleRecenter}
                className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center rounded-xl bg-slate-50 hover:bg-orange-500 hover:text-white text-slate-700 transition-all duration-150 shadow-xs cursor-pointer active:scale-95 mt-0.5"
                title="Reset to All India View"
                aria-label="Recenter Map"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Coordinates HUD (Top Right) */}
            <div className="hidden sm:flex absolute top-4 right-4 z-30 items-center gap-2 bg-[#0b0f17]/90 backdrop-blur-xl text-white px-3.5 py-1.5 rounded-xl border border-white/15 text-[11px] font-mono shadow-xl pointer-events-none">
              <Compass className="w-3.5 h-3.5 text-orange-400 animate-spin [animation-duration:12s]" />
              <span className="text-slate-300">
                LAT: {cursorCoords.lat}°N | LNG: {cursorCoords.lng}°E
              </span>
            </div>

            {/* Interaction Hint (Bottom Left) */}
            {!selectedEvent && (
              <div className="absolute bottom-4 left-4 z-30 bg-[#0b0f17]/85 backdrop-blur-md text-white text-[11px] font-medium px-3.5 py-1.5 rounded-full border border-white/10 shadow-lg pointer-events-none flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                <span>Click any incident marker to discover surrounding emergency services</span>
              </div>
            )}

            {/* Active Selected Incident Notification Bar */}
            {selectedEvent && (
              <div className="absolute bottom-4 left-4 z-30 bg-[#0b0f17]/90 backdrop-blur-md text-white text-xs px-4 py-2 rounded-2xl border border-cyan-500/40 shadow-xl flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                  <span className="font-bold text-cyan-300">Focused Incident:</span>
                  <span className="font-semibold text-white truncate max-w-[200px] sm:max-w-xs">{selectedEvent.title}</span>
                </div>
                <button
                  onClick={handleDeselectEvent}
                  className="bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase transition-colors cursor-pointer"
                >
                  Clear Selection
                </button>
              </div>
            )}

          </div>

          {/* DOCKED NEARBY EMERGENCY SERVICES PANEL (Opens when an incident is selected) */}
          {selectedEvent && (
            <div className="w-full md:w-[380px] lg:w-[420px] h-[340px] md:h-full bg-slate-900 text-slate-100 border-t md:border-t-0 md:border-l border-slate-700 flex flex-col z-30 shadow-2xl animate-in slide-in-from-right duration-200">
              
              {/* Panel Header */}
              <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-start justify-between gap-3 shrink-0">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                      Rescue Network
                    </span>
                    <span className="text-[10px] font-semibold text-slate-400">
                      {nearbyServicesData?.zone_label || `${selectedRadiusM / 1000} km Local Area`}
                    </span>
                  </div>
                  <h3 className="text-sm sm:text-base font-bold text-white mt-1 leading-snug">
                    {selectedEvent.title}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-orange-400 shrink-0" />
                    <span>{selectedEvent.location || selectedEvent.state || 'Incident Coordinate Area'}</span>
                  </p>
                  <span className="inline-block mt-1 text-[9.5px] font-bold text-cyan-300 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800/50">
                    Source: {selectedEvent.source_label || selectedEvent.source}
                  </span>
                </div>

                <button
                  onClick={handleDeselectEvent}
                  className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer shrink-0"
                  title="Close Rescue Panel"
                  aria-label="Close"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Radius Selector Bar */}
              <div className="px-4 py-2.5 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between gap-2 shrink-0">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Search Radius:</span>
                <div className="flex items-center gap-1.5">
                  {[5000, 15000, 25000].map((radiusM) => {
                    const radiusKm = radiusM / 1000;
                    const isActive = selectedRadiusM === radiusM;
                    return (
                      <button
                        key={radiusM}
                        onClick={() => handleRadiusChange(radiusM)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
                          isActive
                            ? 'bg-cyan-600 text-white shadow-xs'
                            : 'bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700'
                        }`}
                      >
                        {radiusKm} km
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Service Categories Filter Tabs & Counts */}
              <div className="px-4 py-2 bg-slate-900 border-b border-slate-800 flex items-center gap-1.5 shrink-0 overflow-x-auto scrollbar-none">
                <button
                  onClick={() => setServiceFilterCategory('all')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center gap-1 shrink-0 ${
                    serviceFilterCategory === 'all'
                      ? 'bg-slate-700 text-white'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  <span>All</span>
                  <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 rounded-full">
                    {nearbyServicesData?.counts?.total || 0}
                  </span>
                </button>

                <button
                  onClick={() => setServiceFilterCategory('medical')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center gap-1 shrink-0 ${
                    serviceFilterCategory === 'medical'
                      ? 'bg-cyan-900/60 text-cyan-200 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  <span>🏥 Medical</span>
                  <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 rounded-full">
                    {nearbyServicesData?.counts?.medical || 0}
                  </span>
                </button>

                <button
                  onClick={() => setServiceFilterCategory('police')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center gap-1 shrink-0 ${
                    serviceFilterCategory === 'police'
                      ? 'bg-indigo-900/60 text-indigo-200 border border-indigo-500/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  <span>🚔 Police</span>
                  <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 rounded-full">
                    {nearbyServicesData?.counts?.police || 0}
                  </span>
                </button>

                <button
                  onClick={() => setServiceFilterCategory('fire')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center gap-1 shrink-0 ${
                    serviceFilterCategory === 'fire'
                      ? 'bg-amber-900/60 text-amber-200 border border-amber-500/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  <span>🚒 Fire</span>
                  <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 rounded-full">
                    {nearbyServicesData?.counts?.fire || 0}
                  </span>
                </button>
              </div>

              {/* Scrollable Facility Cards List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {/* Loading State for Nearby Services */}
                {loadingNearbyServices && (
                  <div className="flex flex-col items-center justify-center py-12 text-center text-slate-400 space-y-3">
                    <RefreshCw className="w-7 h-7 animate-spin text-cyan-400" />
                    <div>
                      <p className="text-sm font-bold text-white">Finding nearby emergency services...</p>
                      <p className="text-xs text-slate-500 mt-1">Querying hospital, police, and fire rescue index</p>
                    </div>
                  </div>
                )}

                {/* Error State for Nearby Services */}
                {nearbyServicesError && !loadingNearbyServices && (
                  <div className="bg-red-950/40 border border-red-500/40 rounded-xl p-4 text-center space-y-2">
                    <AlertTriangle className="w-6 h-6 text-red-400 mx-auto" />
                    <p className="text-xs font-bold text-red-300">{nearbyServicesError}</p>
                    <button
                      onClick={() => handleSelectEvent(selectedEvent, selectedRadiusM)}
                      className="text-xs font-semibold bg-red-900/60 hover:bg-red-800 text-white px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
                    >
                      Retry Lookup
                    </button>
                  </div>
                )}

                {/* Empty State for Nearby Services */}
                {!loadingNearbyServices && !nearbyServicesError && panelServiceList.length === 0 && (
                  <div className="text-center py-12 text-slate-400 space-y-2">
                    <Shield className="w-8 h-8 text-slate-600 mx-auto" />
                    <p className="text-sm font-semibold text-slate-300">No emergency services found nearby</p>
                    <p className="text-xs text-slate-500">
                      Try expanding the search radius to 15 km or 25 km above.
                    </p>
                  </div>
                )}

                {/* Render Discovered Facilities */}
                {!loadingNearbyServices &&
                  !nearbyServicesError &&
                  panelServiceList.map((svc) => {
                    let badgeBg = 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
                    let categoryIcon = <HeartPulse className="w-3.5 h-3.5 text-cyan-400" />;

                    if (svc.category === 'police') {
                      badgeBg = 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
                      categoryIcon = <Shield className="w-3.5 h-3.5 text-indigo-400" />;
                    } else if (svc.category === 'fire') {
                      badgeBg = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
                      categoryIcon = <Flame className="w-3.5 h-3.5 text-amber-400" />;
                    }

                    return (
                      <div
                        key={svc.id}
                        className="bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 hover:border-cyan-500/40 rounded-xl p-3.5 transition-all duration-150 space-y-2.5 shadow-sm"
                      >
                        {/* Title & Distance Bar */}
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-1.5 mb-1">
                              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border flex items-center gap-1 ${badgeBg}`}>
                                {categoryIcon}
                                <span>{svc.category_label || svc.category}</span>
                              </span>
                            </div>
                            <h4 className="text-sm font-bold text-white leading-snug">{svc.name}</h4>
                          </div>

                          <div className="text-right shrink-0">
                            <span className="text-xs font-mono font-bold text-cyan-300 block">
                              {svc.distance_formatted || `${svc.distance_km} km`}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              {svc.estimated_time_formatted || '~4 min'}
                            </span>
                          </div>
                        </div>

                        {/* Address */}
                        {svc.address && (
                          <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                            📍 {svc.address}
                          </p>
                        )}

                        {/* Action Buttons: Directions & Phone */}
                        <div className="flex items-center gap-2 pt-1">
                          {svc.phone && (
                            <a
                              href={`tel:${svc.phone.replace(/[^0-9+]/g, '')}`}
                              className="flex-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 font-bold text-xs py-1.5 px-2.5 rounded-lg transition-colors flex items-center justify-center gap-1.5"
                            >
                              <Phone className="w-3.5 h-3.5" />
                              <span>{svc.phone}</span>
                            </a>
                          )}

                          <a
                            href={
                              svc.directions_url ||
                              `https://www.google.com/maps/dir/?api=1&origin=${selectedEvent.latitude},${selectedEvent.longitude}&destination=${svc.latitude},${svc.longitude}`
                            }
                            target="_blank"
                            rel="noreferrer"
                            className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-1.5 px-2.5 rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-sm"
                          >
                            <Navigation className="w-3.5 h-3.5" />
                            <span>Get Directions</span>
                          </a>
                        </div>
                      </div>
                    );
                  })}
              </div>

              {/* Panel Footer */}
              <div className="p-3 bg-slate-950 border-t border-slate-800 flex items-center justify-between gap-2 shrink-0">
                <button
                  onClick={() => setModalIncident(selectedEvent)}
                  className="text-xs font-bold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors cursor-pointer"
                >
                  <span>Full Incident Briefing</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={handleDeselectEvent}
                  className="text-xs font-semibold text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  Close Panel
                </button>
              </div>

            </div>
          )}

        </div>

        {/* FULLY UPDATED COMPREHENSIVE MAP LEGEND BAR (DYNAMICALLY SORTED DESCENDING BY EVENT COUNT) */}
        <div className="px-4 sm:px-8 py-4 bg-slate-50 border-t border-slate-200/80 flex flex-col gap-3 text-xs">
          
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-slate-700 font-bold uppercase text-[11px] tracking-wider">
              <Layers className="w-4 h-4 text-orange-500" />
              <span>Map Legend & Visual Indicators</span>
            </div>
            <div className="flex items-center gap-1 text-[11px] text-slate-500 font-medium">
              <TrendingDown className="w-3 h-3 text-orange-500" />
              <span>Sorted in descending order by live frequency</span>
            </div>
          </div>

          {/* Hazard Threat Markers Grid (Sorted Descending by Real Count) */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-1 border-t border-slate-200/60">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 shrink-0">
              Hazard Types:
            </span>

            <div className="flex flex-wrap items-center gap-x-3.5 gap-y-2">
              {sortedCategories.map((cat) => {
                const count = categoryCounts[cat] || 0;
                const style = CATEGORY_STYLES[cat] || CATEGORY_STYLES.Other;
                const isSelected = selectedCategories.includes(cat) || selectedCategories.includes('All');

                return (
                  <button
                    key={cat}
                    onClick={() => handleToggleCategory(cat)}
                    className={`flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                      isSelected
                        ? 'text-slate-800 hover:bg-slate-200/60'
                        : 'text-slate-400 opacity-60 hover:opacity-100 hover:bg-slate-100'
                    }`}
                    title={`Click to filter ${cat}`}
                  >
                    <span
                      className="w-2.5 h-2.5 rounded-full shadow-2xs shrink-0"
                      style={{ backgroundColor: style.color }}
                    />
                    <span>{cat}</span>
                    <span className="text-[10px] font-mono text-slate-500 bg-slate-200/80 px-1 py-0.2 rounded font-bold">
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Emergency First-Responder Facilities Grid */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-2 border-t border-slate-200/60">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 shrink-0">
              Emergency Facilities:
            </span>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <div className="flex items-center gap-1.5 text-slate-800 font-bold bg-cyan-50 text-cyan-900 border border-cyan-200 px-2.5 py-1 rounded-lg">
                <span className="text-sm">🏥</span>
                <span>Hospital / Medical Unit (Cyan Pin)</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-800 font-bold bg-indigo-50 text-indigo-900 border border-indigo-200 px-2.5 py-1 rounded-lg">
                <span className="text-sm">🚔</span>
                <span>Police Station / Outpost (Indigo Pin)</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-800 font-bold bg-amber-50 text-amber-900 border border-amber-200 px-2.5 py-1 rounded-lg">
                <span className="text-sm">🚒</span>
                <span>Fire & Rescue Station (Amber Pin)</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-600 font-medium italic text-[11px]">
                <span className="w-3 h-3 rounded-full border border-dashed border-cyan-500" />
                <span>Dashed Circle = Search Radius (5 / 15 / 25 km)</span>
              </div>
            </div>
          </div>

        </div>

      </div>

      {/* Situation Briefing Modal */}
      <IncidentDetailModal
        incident={modalIncident}
        onClose={() => setModalIncident(null)}
        onFindNearbyServices={(inc) => {
          setModalIncident(null);
          handleSelectEvent(inc, selectedRadiusM);
        }}
      />

    </section>
  );
};
