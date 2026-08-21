/**
 * DISHA Platform - Comprehensive Full Situational Brief Modal
 * Disaster Intelligence and Situational Hazard Awareness Platform
 * 
 * Production-Grade 3-Tier Layout:
 * ├── Fixed Header (Never scrolls, close button always accessible)
 * ├── Scrollable Content (Single primary scroll area with flex-1 min-h-0 overflow-y-auto)
 * └── Fixed Footer (Never scrolls, actions & reference data always accessible)
 * 
 * Preserves all 11 structured situation briefing sections:
 * 1. Situation Overview
 * 2. Situation Description & Intelligence
 * 3. Event Details & Telemetry
 * 4. Location Information
 * 5. Location Context & Navigation Directions
 * 6. Response / Rescue Radius
 * 7. Nearby Emergency Resources
 * 8. Impact Assessment & Urgency
 * 9. Official Recommended Actions & Safety Guidance (DOs & DON'Ts)
 * 10. Source Evidence & Authority Links
 * 11. Disclaimer & Surveillance Notice
 */

import React, { useEffect, useRef } from 'react';
import {
  X,
  Clock,
  MapPin,
  Compass,
  Navigation,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Radio,
  Hospital,
  Shield,
  Flame,
  Info,
  CheckCircle,
  Activity,
  Layers,
} from 'lucide-react';
import { getCategoryConfig, SEVERITY_CONFIG } from '../../../config/eventConfig';
import { normalizeEvent } from '../../../utils/eventNormalizer';

export const IncidentDetailModal = ({ incident: rawIncident, onClose, onFindNearbyServices }) => {
  const contentRef = useRef(null);
  const closeButtonRef = useRef(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Robust Body Scroll Lock with Scrollbar Shift Prevention & Guaranteed Cleanup
  useEffect(() => {
    const originalOverflow = document.body.style.overflow;
    const originalPaddingRight = document.body.style.paddingRight;
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;

    document.body.style.overflow = 'hidden';
    if (scrollbarWidth > 0) {
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    }

    // Automatically focus the scrollable content area so keyboard scrolling works immediately
    if (contentRef.current) {
      contentRef.current.focus();
    }

    return () => {
      document.body.style.overflow = originalOverflow || '';
      document.body.style.paddingRight = originalPaddingRight || '';
    };
  }, []);

  if (!rawIncident) return null;

  // Normalize event data into consistent, safe structure
  const incident = normalizeEvent(rawIncident);
  if (!incident) return null;

  const config = getCategoryConfig(incident.category || incident.raw_category);
  const sevConfig = SEVERITY_CONFIG[incident.severity] || SEVERITY_CONFIG.Moderate;

  // Forward scroll wheel from anywhere on modal dialog to content area
  const handleDialogWheel = (e) => {
    if (contentRef.current && !contentRef.current.contains(e.target)) {
      contentRef.current.scrollTop += e.deltaY;
    }
  };

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-2 sm:p-4 md:p-6 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="incident-brief-title"
      aria-describedby="incident-brief-desc"
    >
      {/* Modal Main Window Card */}
      <div
        className="relative bg-white rounded-2xl sm:rounded-3xl shadow-2xl w-full max-w-5xl h-[92vh] sm:h-[88vh] flex flex-col border border-slate-200 overflow-hidden font-sans animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
        onWheel={handleDialogWheel}
      >
        {/* =========================================================================
            1. FIXED HEADER (Locked at top, Never Scrolls Away, Close Button Always Visible)
           ========================================================================= */}
        <header className="bg-[#101318] text-white p-4 sm:p-5 flex items-start justify-between relative overflow-hidden border-b border-slate-800 shrink-0 z-20">
          <div className="absolute right-0 top-0 w-64 h-64 bg-orange-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="flex items-start gap-3 sm:gap-4 z-10 min-w-0 pr-2 flex-1">
            <div className={`w-11 h-11 sm:w-12 sm:h-12 rounded-2xl ${config.bg || 'bg-orange-500'} flex items-center justify-center shadow-lg shrink-0 mt-0.5`}>
              <span className="text-xl sm:text-2xl">{config.icon}</span>
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-1.5">
                <span className="text-[10px] sm:text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-white/10 text-orange-400 flex items-center gap-1 border border-white/10">
                  <span>{config.icon}</span>
                  <span>{config.label}</span>
                </span>
                <span className={`text-[10px] sm:text-xs font-bold px-2.5 py-0.5 rounded-full ${sevConfig.badge}`}>
                  {incident.severity} Severity
                </span>
                <span className="text-[10px] sm:text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Verified Incident</span>
                </span>
                <span className="text-[10px] text-slate-400 font-mono hidden md:inline">
                  Ref: {incident.id || 'DISHA-INTEL'}
                </span>
              </div>
              <h2 id="incident-brief-title" className="text-base sm:text-xl font-bold text-white leading-snug break-words">
                {incident.title}
              </h2>
            </div>
          </div>

          <button
            ref={closeButtonRef}
            id="close-incident-modal-btn"
            onClick={onClose}
            aria-label="Close Full Situation Brief"
            className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-white/10 transition-colors z-10 cursor-pointer shrink-0 ml-2"
          >
            <X className="w-5 h-5 sm:w-6 sm:h-6" />
          </button>
        </header>

        {/* =========================================================================
            2. SCROLLABLE CONTENT (Single Primary Scroll Container, flex-1 min-h-0)
           ========================================================================= */}
        <main
          ref={contentRef}
          tabIndex={0}
          className="p-4 sm:p-6 md:p-8 flex-1 min-h-0 overflow-y-auto space-y-6 text-slate-700 bg-white overscroll-contain focus:outline-none"
        >

          {/* Section 1: Situation Overview & Key Metrics */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 p-4 bg-slate-50 rounded-2xl border border-slate-200">
            {/* Location */}
            <div className="flex items-start gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-xl bg-orange-100 border border-orange-200 flex items-center justify-center text-orange-600 shrink-0 mt-0.5">
                <MapPin className="w-4 h-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[10.5px] font-bold text-slate-400 uppercase tracking-wider">Affected Area</p>
                <p className="text-xs sm:text-sm font-bold text-slate-900 leading-snug break-words">
                  {incident.location || 'India'}
                  {incident.state && incident.location && !incident.location.toLowerCase().includes(incident.state.toLowerCase()) ? `, ${incident.state}` : ''}
                </p>
              </div>
            </div>

            {/* Reported Time (IST) */}
            <div className="flex items-start gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-xl bg-blue-100 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 mt-0.5">
                <Clock className="w-4 h-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[10.5px] font-bold text-slate-400 uppercase tracking-wider">Reported (IST)</p>
                <p className="text-xs sm:text-sm font-bold text-slate-900 leading-snug break-words">
                  {incident.formatted_time_ist}
                </p>
              </div>
            </div>

            {/* Coordinates */}
            <div className="flex items-start gap-2.5 min-w-0 pt-2 sm:pt-0 sm:border-t-0 border-t border-slate-200/60">
              <div className="w-8 h-8 rounded-xl bg-emerald-100 border border-emerald-200 flex items-center justify-center text-emerald-600 shrink-0 mt-0.5">
                <Compass className="w-4 h-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[10.5px] font-bold text-slate-400 uppercase tracking-wider">Coordinates</p>
                <p className="text-xs sm:text-sm font-mono font-bold text-slate-800 break-words">
                  {incident.coordinates_formatted}
                </p>
              </div>
            </div>

            {/* Reporting Authority */}
            <div className="flex items-start gap-2.5 min-w-0 pt-2 sm:pt-0 sm:border-t-0 border-t border-slate-200/60">
              <div className="w-8 h-8 rounded-xl bg-purple-100 border border-purple-200 flex items-center justify-center text-purple-600 shrink-0 mt-0.5">
                <Radio className="w-4 h-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[10.5px] font-bold text-slate-400 uppercase tracking-wider">Source Agency</p>
                <p className="text-xs sm:text-sm font-bold text-slate-800 break-words">
                  {incident.source_label}
                </p>
              </div>
            </div>
          </section>

          {/* Section 2: Situation Description & Intelligence */}
          <section className="space-y-2">
            <h3 className="text-xs uppercase font-bold text-slate-500 tracking-wider flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-orange-600" />
              <span>Situation Description & Intelligence</span>
            </h3>
            <div
              id="incident-brief-desc"
              className="bg-orange-50/50 p-4 sm:p-5 rounded-2xl border border-orange-100 text-xs sm:text-sm leading-relaxed text-slate-800 font-normal"
            >
              {incident.description ? (
                <p className="whitespace-pre-line break-words">
                  {incident.description}
                </p>
              ) : (
                <p className="text-slate-500 italic">
                  Verified real-time disaster situation report recorded by DISHA automated surveillance network.
                </p>
              )}
            </div>
          </section>

          {/* Section 3 & 4: Event Details & Location Metadata Grid */}
          <section className="space-y-2">
            <h3 className="text-xs uppercase font-bold text-slate-500 tracking-wider flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-orange-600" />
              <span>Event Details & Geographic Telemetry</span>
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 p-3.5 bg-slate-50 rounded-2xl border border-slate-200 text-xs">
              <div className="space-y-0.5">
                <span className="text-[10px] uppercase font-bold text-slate-400">DISHA Ref</span>
                <p className="font-mono font-bold text-slate-800 truncate">{incident.id || 'N/A'}</p>
              </div>
              <div className="space-y-0.5">
                <span className="text-[10px] uppercase font-bold text-slate-400">Hazard Code</span>
                <p className="font-mono font-bold text-slate-800 truncate">{config.id || 'hazard'}</p>
              </div>
              <div className="space-y-0.5">
                <span className="text-[10px] uppercase font-bold text-slate-400">Severity Tier</span>
                <p className="font-bold text-slate-800 truncate">{incident.severity}</p>
              </div>
              <div className="space-y-0.5">
                <span className="text-[10px] uppercase font-bold text-slate-400">State / Region</span>
                <p className="font-bold text-slate-800 truncate">{incident.state || incident.location || 'India'}</p>
              </div>
              <div className="space-y-0.5">
                <span className="text-[10px] uppercase font-bold text-slate-400">Coordinates</span>
                <p className="font-mono font-bold text-slate-800 truncate">{incident.coordinates_formatted}</p>
              </div>
              <div className="space-y-0.5">
                <span className="text-[10px] uppercase font-bold text-slate-400">Timezone</span>
                <p className="font-mono font-bold text-slate-800 truncate">IST (UTC+05:30)</p>
              </div>
            </div>
          </section>

          {/* Section 5 & 6 & 7: Emergency Response & Rescue Radius Actions */}
          <section className="p-4 sm:p-5 bg-slate-900 text-white rounded-2xl border border-slate-800 space-y-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Hospital className="w-5 h-5 text-cyan-400" />
                <h4 className="text-sm font-bold uppercase tracking-wider text-cyan-300">
                  Emergency Response & Nearby Resource Discovery
                </h4>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-cyan-500/20 text-cyan-300 rounded-full border border-cyan-500/30">
                  Surveillance Radius: 5 km • 15 km • 25 km
                </span>
              </div>
            </div>

            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Explore nearby medical trauma hospitals, police command posts, and fire rescue units indexed within the operational response radius of this incident.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <div className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/20 text-cyan-300 flex items-center justify-center font-bold text-xs">
                  🏥
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] font-bold text-white">Trauma Hospitals</p>
                  <p className="text-[10px] text-slate-400">Emergency & Ambulance</p>
                </div>
              </div>

              <div className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-300 flex items-center justify-center font-bold text-xs">
                  🚔
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] font-bold text-white">Police Stations</p>
                  <p className="text-[10px] text-slate-400">Law & Evacuation Control</p>
                </div>
              </div>

              <div className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-300 flex items-center justify-center font-bold text-xs">
                  🚒
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] font-bold text-white">Fire & Rescue</p>
                  <p className="text-[10px] text-slate-400">Hazmat & First-Response</p>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2.5 pt-1">
              {onFindNearbyServices && incident.has_coordinates && (
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onFindNearbyServices(incident);
                  }}
                  className="flex-1 min-w-[220px] bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white font-bold text-xs py-2.5 px-4 rounded-xl transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Navigation className="w-4 h-4" />
                  <span>Discover Nearby Facilities on Live Map →</span>
                </button>
              )}

              {incident.has_coordinates && (
                <a
                  href={`https://www.google.com/maps/dir/?api=1&destination=${incident.latitude},${incident.longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 min-w-[200px] bg-white/10 hover:bg-white/20 text-white font-bold text-xs py-2.5 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 border border-white/15 cursor-pointer text-center"
                >
                  <ExternalLink className="w-4 h-4 text-orange-400" />
                  <span>Open Directions in Google Maps ↗</span>
                </a>
              )}
            </div>
          </section>

          {/* Section 8 & 9: Official Disaster Safety Guidance (DOs and DON'Ts) */}
          {config && ((config.dos && config.dos.length > 0) || (config.donts && config.donts.length > 0)) && (
            <section className="space-y-3">
              <h3 className="text-xs uppercase font-bold text-slate-500 tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Official Safety Advisory & Impact Protocol for {config.label}</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {/* DOs Card */}
                {config.dos && config.dos.length > 0 && (
                  <div className="p-4 bg-emerald-50/70 rounded-2xl border border-emerald-200/80 space-y-2">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-1.5">
                      <CheckCircle className="w-4 h-4 text-emerald-600" />
                      <span>Recommended Actions (DOs)</span>
                    </h4>
                    <ul className="space-y-2 text-xs text-slate-700 leading-relaxed">
                      {config.dos.map((item, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-emerald-600 font-bold mt-0.5 shrink-0">✓</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* DON'Ts Card */}
                {config.donts && config.donts.length > 0 && (
                  <div className="p-4 bg-rose-50/70 rounded-2xl border border-rose-200/80 space-y-2">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-rose-900 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-rose-600" />
                      <span>Critical Precautions (DON'Ts)</span>
                    </h4>
                    <ul className="space-y-2 text-xs text-slate-700 leading-relaxed">
                      {config.donts.map((item, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-rose-600 font-bold mt-0.5 shrink-0">✕</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Section 10: Verified Source Authority & Evidence Link */}
          {incident.source_url && (
            <section className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-slate-50 rounded-2xl border border-slate-200 text-xs">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" />
                <div className="text-slate-600 min-w-0">
                  <span className="font-semibold text-slate-500">Source Evidence: </span>
                  <span className="font-bold text-slate-800">{incident.source_label}</span>
                </div>
              </div>
              <a
                href={incident.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-white hover:bg-orange-50 text-orange-600 hover:text-orange-700 font-bold text-xs rounded-xl border border-orange-200 shadow-sm transition-colors cursor-pointer shrink-0"
              >
                <span>Read Full Reporting Source</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </section>
          )}

          {/* Section 11: Official Disclaimer & Telemetry Notice */}
          <footer className="p-3 bg-slate-50/80 rounded-xl border border-slate-100 text-[11px] text-slate-400 space-y-1">
            <p className="flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span>DISHA Real-Time Hazard Surveillance Notice: Data aggregated from official reporting authorities and calibrated via automated ingestion pipelines.</span>
            </p>
          </footer>

        </main>

        {/* =========================================================================
            3. FIXED FOOTER (Locked at bottom, Never Scrolls Away, Always Accessible)
           ========================================================================= */}
        <footer className="p-3.5 sm:p-4 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3 shrink-0 z-20">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="hidden sm:inline">DISHA Situation Intelligence:</span>
            <code className="font-mono text-slate-700 font-bold">{incident.id || 'LIVE-ALERT'}</code>
          </div>

          <div className="flex items-center gap-2">
            {incident.has_coordinates && (
              <a
                href={`https://www.google.com/maps/dir/?api=1&destination=${incident.latitude},${incident.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3.5 py-2 bg-white hover:bg-slate-100 text-slate-700 font-semibold text-xs rounded-xl border border-slate-200 transition-colors hidden sm:inline-flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                <Navigation className="w-3.5 h-3.5 text-orange-600" />
                <span>Directions ↗</span>
              </a>
            )}
            <button
              id="close-incident-bottom-btn"
              onClick={onClose}
              className="px-5 sm:px-6 bg-[#101318] hover:bg-slate-800 text-white font-bold text-xs py-2 rounded-xl transition-colors cursor-pointer shadow-sm"
            >
              Close Full Brief
            </button>
          </div>
        </footer>

      </div>
    </div>
  );
};
