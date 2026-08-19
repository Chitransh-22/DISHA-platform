import React from 'react';
import { DISASTER_TYPES_CONFIG } from '../../../data/disasterData';
import { X, ShieldAlert, Phone, Users, Clock, MapPin, Radio } from 'lucide-react';

export const IncidentDetailModal = ({ incident, onClose }) => {
  if (!incident) return null;

  const config = DISASTER_TYPES_CONFIG[incident.type] || DISASTER_TYPES_CONFIG.Other;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="bg-white rounded-2xl sm:rounded-3xl shadow-2xl max-w-lg w-full overflow-hidden border border-slate-200 flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="bg-[#111827] text-white p-5 sm:p-6 flex items-start justify-between relative overflow-hidden">
          <div className="absolute right-0 top-0 w-32 h-32 bg-orange-500/10 rounded-full blur-2xl pointer-events-none" />
          
          <div className="flex items-center gap-3.5 z-10">
            <div className={`w-10 h-10 rounded-xl ${config.bg} flex items-center justify-center shadow-lg`}>
              <ShieldAlert className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-white/10 text-orange-400">
                  {incident.type}
                </span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                  incident.severity === 'Critical' ? 'bg-red-500/20 text-red-400 border border-red-500/40' :
                  incident.severity === 'Severe' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40' :
                  'bg-yellow-500/20 text-yellow-300 border border-yellow-500/40'
                }`}>
                  {incident.severity} Severity
                </span>
              </div>
              <h3 className="text-lg sm:text-xl font-bold mt-1 text-white">
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
          
          {/* Location & Status Bar */}
          <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200/80">
            <div className="flex items-start gap-2">
              <MapPin className="w-4 h-4 text-orange-600 mt-0.5 shrink-0" />
              <div>
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Location</p>
                <p className="text-xs sm:text-sm font-bold text-slate-900">{incident.location}, {incident.state}</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Clock className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
              <div>
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Reported</p>
                <p className="text-xs sm:text-sm font-bold text-slate-900">{incident.timeAgo}</p>
              </div>
            </div>
          </div>

          {/* Description */}
          <div>
            <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider mb-1.5">Situation Brief</h4>
            <p className="text-sm leading-relaxed text-slate-600 bg-orange-50/50 p-3.5 rounded-xl border border-orange-100">
              {incident.description}
            </p>
          </div>

          {/* Affected Population */}
          <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200/80">
            <Users className="w-5 h-5 text-slate-600 shrink-0" />
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Impacted Population</p>
              <p className="text-xs sm:text-sm font-bold text-slate-800">{incident.affectedPopulation}</p>
            </div>
          </div>

          {/* Response Units Deployed */}
          {incident.responseUnits && incident.responseUnits.length > 0 && (
            <div>
              <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider mb-1.5 flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-emerald-600" />
                <span>Active Response Units</span>
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {incident.responseUnits.map((unit, idx) => (
                  <span
                    key={idx}
                    className="text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-1 rounded-lg"
                  >
                    ✓ {unit}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Emergency Helpline */}
          <div className="bg-red-50 border border-red-200 rounded-xl p-3.5 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Phone className="w-4 h-4 text-red-600" />
              <div>
                <p className="text-[11px] font-semibold text-red-700 uppercase">Emergency Helpline</p>
                <p className="text-xs sm:text-sm font-bold text-red-950 font-mono">{incident.helpline || '1070 / 112'}</p>
              </div>
            </div>
            <a
              href={`tel:${(incident.helpline || '1070').split('/')[0].trim()}`}
              className="bg-red-600 hover:bg-red-700 text-white font-bold text-xs px-3 py-1.5 rounded-lg shadow-sm"
            >
              Call Helpline
            </a>
          </div>

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
