import React from 'react';
import { Filter, RotateCcw, Calendar, AlertTriangle, MapPin, Activity, Database } from 'lucide-react';

export const AnalysisFilters = ({
  filters = {},
  onFilterChange,
  onResetFilters,
  matchingCount = 0,
  totalCount = 0,
}) => {
  const isFiltered =
    (filters?.timeWindow && filters.timeWindow !== 'all') ||
    (filters?.disasterType && filters.disasterType !== 'all') ||
    (filters?.state && filters.state !== 'all') ||
    (filters?.severity && filters.severity !== 'all') ||
    (filters?.dataSource && filters.dataSource !== 'all');

  const indianStates = [
    'Assam',
    'Uttarakhand',
    'West Bengal',
    'Maharashtra',
    'Odisha',
    'Kerala',
    'Jammu & Kashmir',
    'Gujarat',
    'Andhra Pradesh',
    'Rajasthan',
    'Punjab',
    'Karnataka',
    'Himachal Pradesh',
    'Sikkim',
    'Bihar',
    'Andaman and Nicobar',
  ];

  return (
    <div className="w-full bg-white dark:bg-[#101318] rounded-3xl p-4 sm:p-5 border border-slate-200/90 dark:border-white/10 shadow-lg mb-6 transition-all duration-300">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-orange-500/10 text-orange-600 dark:text-orange-400 flex items-center justify-center">
            <Filter className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white font-sans">
              Global Analysis Filters
            </h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Synchronizes KPIs, all 40 graphs, and analytical insights across the platform
            </p>
          </div>
        </div>

        {/* Status Count & Reset */}
        <div className="flex items-center gap-3">
          <div className="text-xs font-medium px-3 py-1 rounded-full bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-700 dark:text-slate-300 font-mono">
            Showing <span className="font-bold text-orange-600 dark:text-orange-400">{matchingCount}</span> of {totalCount} events
          </div>

          {isFiltered && (
            <button
              onClick={onResetFilters}
              className="flex items-center gap-1.5 text-xs font-semibold text-rose-600 dark:text-rose-400 hover:underline cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset Filters</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter Select Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 pt-3">
        {/* 1. Time Window */}
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
            <Calendar className="w-3 h-3 text-slate-400" />
            <span>Time Window</span>
          </label>
          <select
            value={filters.timeWindow}
            onChange={(e) => onFilterChange('timeWindow', e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-orange-500 cursor-pointer"
          >
            <option value="all">All Available Records</option>
            <option value="24h">Past 24 Hours</option>
            <option value="7d">Past 7 Days</option>
            <option value="30d">Rolling 30 Days</option>
          </select>
        </div>

        {/* 2. Hazard Type */}
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
            <Activity className="w-3 h-3 text-slate-400" />
            <span>Disaster Type</span>
          </label>
          <select
            value={filters.disasterType}
            onChange={(e) => onFilterChange('disasterType', e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-orange-500 cursor-pointer"
          >
            <option value="all">All Hazard Categories</option>
            <option value="Flood">Floods & Inundation</option>
            <option value="Earthquake">Earthquakes & Tremors</option>
            <option value="Cyclone">Cyclones & Storms</option>
            <option value="Landslide">Landslides & Rockfalls</option>
            <option value="Fire">Wildfires & Industrial Fires</option>
            <option value="Other">Severe Weather & Other</option>
          </select>
        </div>

        {/* 3. State / Jurisdiction */}
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
            <MapPin className="w-3 h-3 text-slate-400" />
            <span>State / UT</span>
          </label>
          <select
            value={filters.state}
            onChange={(e) => onFilterChange('state', e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-orange-500 cursor-pointer"
          >
            <option value="all">All States & Territories</option>
            {indianStates.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>
        </div>

        {/* 4. Severity Level */}
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-slate-400" />
            <span>Severity Tier</span>
          </label>
          <select
            value={filters.severity}
            onChange={(e) => onFilterChange('severity', e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-orange-500 cursor-pointer"
          >
            <option value="all">All Severity Levels</option>
            <option value="critical">Critical (Level 4)</option>
            <option value="severe">Severe / High (Level 3)</option>
            <option value="moderate">Moderate / Medium (Level 2)</option>
            <option value="low">Low / Minor (Level 1)</option>
          </select>
        </div>

        {/* 5. Data Source */}
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
            <Database className="w-3 h-3 text-slate-400" />
            <span>Data Stream</span>
          </label>
          <select
            value={filters.dataSource}
            onChange={(e) => onFilterChange('dataSource', e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-orange-500 cursor-pointer"
          >
            <option value="all">All Integrated Feeds</option>
            <option value="sachet">NDMA SACHET CAP Alerts</option>
            <option value="ncs">NCS RISEQ Seismology</option>
            <option value="news">Verified Multi-Source News</option>
          </select>
        </div>
      </div>
    </div>
  );
};
