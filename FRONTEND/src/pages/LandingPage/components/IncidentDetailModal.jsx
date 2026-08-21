import React from 'react';
import { X, ShieldAlert, Users, Clock, MapPin, Radio, Navigation, CheckCircle } from 'lucide-react';
import { getCategoryConfig, SEVERITY_CONFIG } from '../../../config/eventConfig';
import { formatDateTimeIST } from '../../../utils/dateTime';

export const IncidentDetailModal = ({ incident, onClose, onFindNearbyServices }) => {
  if (!incident) return null;

  const config = getCategoryConfig(incident.category || incident.type || incident.disaster_type);
  const sevConfig = SEVERITY_CONFIG[incident.severity] || SEVERITY_CONFIG.Moderate;
  const istTimeString = formatDateTimeIST(incident);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl sm:rounded-3xl shadow-2xl max-w-lg w-full overflow-hidden border border-slate-200 flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="bg-[#111827] text-white p-5 sm:p-6 flex items-start justify-between relative overflow-hidden">
          <div className="absolute right-0 top-0 w-32 h-32 bg-orange-500/10 rounded-full blur-2xl pointer-events-none" />

          <div className="flex items-center gap-3.5 z-10">
            <div className={`w-10 h-10 rounded-xl ${config.bg || 'bg-orange-500'} flex items-center justify-center shadow-lg`}>
              <ShieldAlert className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-white/10 text-orange-400 flex items-center gap-1">
                  <span>{config.icon}</span>
                  <span>{config.label}</span>
                </span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${sevConfig.badge}`}>
                  {incident.severity || 'Moderate'} Severity
                </span>
              </div>
              <h3 className="text-lg sm:text-xl font-bold mt-1 text-white leading-snug">
                {incident.title}
              </h3>
            </div>
          </div>

          <button
            id="close-incident-modal-btn"
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-full hover:bg-white/10 transition-colors z-10 cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body Content */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-4 text-slate-700">
          
          {/* Location & Reported Time Bar */}
          <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200/80">
            <div className="flex items-start gap-2">
              <MapPin className="w-4 h-4 text-orange-600 mt-0.5 shrink-0" />
              <div>
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Location</p>
                <p className="text-xs sm:text-sm font-bold text-slate-900">
                  {incident.location || incident.district || 'India'}
                  {incident.state ? `, ${incident.state}` : ''}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Clock className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
              <div>
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Reported Time</p>
                <p className="text-xs sm:text-sm font-bold text-slate-900">{istTimeString}</p>
              </div>
            </div>
          </div>

          {/* Situation Briefing */}
          <div>
            <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider mb-1.5">Situation Brief</h4>
            <p className="text-sm leading-relaxed text-slate-700 bg-orange-50/40 p-3.5 rounded-xl border border-orange-100/80">
              {incident.description || 'Verified real-time disaster situation report.'}
            </p>
          </div>

          {/* Source Authority Badge */}
          {incident.source_label && (
            <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-200 text-xs">
              <span className="text-slate-500 font-semibold">Reporting Source:</span>
              <span className="font-bold text-slate-800">{incident.source_label}</span>
            </div>
          )}

          {/* Action: Discover Nearby Emergency Services */}
          {onFindNearbyServices && (
            <button
              onClick={() => onFindNearbyServices(incident)}
              className="w-full bg-linear-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold text-sm py-3 px-4 rounded-xl transition-all duration-150 shadow-md flex items-center justify-center gap-2 cursor-pointer"
            >
              <Navigation className="w-4 h-4" />
              <span>Discover Nearby Emergency Facilities</span>
              <span>→</span>
            </button>
          )}

          {/* Directions Button */}
          {incident.latitude != null && incident.longitude != null && (
            <a
              href={`https://www.google.com/maps/dir/?api=1&destination=${incident.latitude},${incident.longitude}`}
              target="_blank"
              rel="noreferrer"
              className="w-full bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs py-2.5 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 cursor-pointer"
            >
              <Navigation className="w-3.5 h-3.5 text-orange-600" />
              <span>Get Directions on Google Maps ↗</span>
            </a>
          )}

        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-end gap-3">
          <button
            id="close-incident-bottom-btn"
            onClick={onClose}
            className="w-full bg-[#111827] hover:bg-slate-800 text-white font-semibold text-sm py-2.5 rounded-xl transition-colors cursor-pointer"
          >
            Close Briefing
          </button>
        </div>
      </div>
    </div>
  );
};
