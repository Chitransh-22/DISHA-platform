import React from 'react';
import { Activity, Clock, RefreshCw, Radio, Layers, CheckCircle2 } from 'lucide-react';

export const AnalysisHero = ({
  lastSyncTime,
  onRefresh,
  loading = false,
  isLive = false,
  totalEvents = 0,
}) => {
  return (
    <section className="w-full relative overflow-hidden pt-6 pb-4">
      {/* Background ambient accent */}
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-orange-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 bg-[#101318] text-white rounded-3xl p-6 sm:p-8 border border-white/10 shadow-2xl relative z-10 overflow-hidden">
        {/* Ambient Top Glow */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-linear-to-r from-orange-500 via-amber-500 to-transparent" />
        <div className="absolute -bottom-10 right-0 w-80 h-32 bg-orange-600/10 blur-2xl pointer-events-none" />

        {/* Left: Operational Title & Description */}
        <div className="space-y-3 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-orange-500/20 text-orange-400 border border-orange-500/30">
              <Radio className="w-3.5 h-3.5 animate-pulse text-orange-400" />
              Operational Intelligence
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-white/5 text-slate-300 border border-white/10">
              <Layers className="w-3.5 h-3.5 text-slate-400" />
              Pan-India Disaster Coverage
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-white tracking-tight font-sans leading-tight">
            Disaster Intelligence <span className="text-[#f26522]">Analysis</span>
          </h1>

          <p className="text-sm sm:text-base text-slate-300 leading-relaxed font-normal">
            Transforming multi-source disaster signals from NCS RISEQ Seismology, NDMA SACHET CAP Alerts, and verified news feeds into actionable emergency intelligence.
          </p>
        </div>

        {/* Right: Telemetry Status Controls */}
        <div className="flex flex-wrap items-center lg:flex-col lg:items-end gap-3 shrink-0">
          <div className="flex items-center gap-3 bg-white/5 border border-white/10 px-4 py-2.5 rounded-2xl backdrop-blur-md">
            <Clock className="w-4 h-4 text-orange-400 shrink-0" />
            <div className="text-left">
              <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Last Telemetry Sync</div>
              <div className="text-xs sm:text-sm font-bold text-white font-mono">{lastSyncTime || 'Live Stream'} IST</div>
            </div>
            
            <div className="flex items-center gap-1.5 pl-3 border-l border-white/10">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
              </span>
              <span className="text-[11px] font-bold text-emerald-400">{isLive ? 'BACKEND LIVE' : 'SYNCED'}</span>
            </div>
          </div>

          {/* Sync Button */}
          <button
            id="analysis-refresh-btn"
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-2 bg-linear-to-r from-[#f26522] to-[#ea580c] hover:from-[#ea580c] hover:to-[#c2410c] text-white text-xs font-bold px-4 py-2.5 rounded-2xl transition-all duration-200 shadow-lg shadow-orange-950/40 cursor-pointer disabled:opacity-50 active:scale-95 border border-orange-400/30"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Recalculating...' : 'Refresh Analytics'}</span>
          </button>
        </div>
      </div>
    </section>
  );
};
