import React, { useState, useMemo } from 'react';
import {
  ANALYSIS_CATEGORIES,
  ANALYSIS_GRAPHS,
} from '../../../data/analysisRegistry';
import { AnalyticsCard } from './AnalyticsCard';
import {
  Activity,
  MapPin,
  Clock,
  Cpu,
  Search,
  Grid,
  CheckCircle2,
  SlidersHorizontal,
  ChevronRight,
  Layers,
} from 'lucide-react';

export const CategoryGraphsView = ({ chartData = {}, defaultCategory = 'all' }) => {
  const [activeCategory, setActiveCategory] = useState(defaultCategory);
  const [searchQuery, setSearchQuery] = useState('');

  // Category Icon Lookup
  const getCategoryIcon = (id) => {
    switch (id) {
      case 'disaster_overview':
        return Activity;
      case 'geographic_intelligence':
        return MapPin;
      case 'temporal_trends':
        return Clock;
      case 'ai_response_intelligence':
        return Cpu;
      default:
        return Layers;
    }
  };

  // Filter graphs based on active category tab & search query
  const filteredGraphs = useMemo(() => {
    return ANALYSIS_GRAPHS.filter((g) => {
      const matchesCategory = activeCategory === 'all' || g.category === activeCategory;
      const matchesSearch =
        !searchQuery.trim() ||
        g.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        g.subtitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
        g.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        g.dataSource.toLowerCase().includes(searchQuery.toLowerCase());

      return matchesCategory && matchesSearch;
    });
  }, [activeCategory, searchQuery]);

  return (
    <section id="graphs-analytics-section" className="w-full space-y-6">
      {/* Category Navigation Bar & Search Header */}
      <div className="bg-white dark:bg-[#101318] rounded-3xl p-5 sm:p-6 border border-slate-200/90 dark:border-white/10 shadow-lg space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-orange-500 animate-ping" />
              <h2 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight font-sans">
                Deep-Dive Graph Analytics Workspace
              </h2>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Exactly 40 specialized analytical graphs categorized across 4 disaster intelligence disciplines (10 graphs each).
            </p>
          </div>

          {/* Quick Search */}
          <div className="relative max-w-xs w-full">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search 40 graphs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl pl-10 pr-4 py-2 text-xs font-medium text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600"
              >
                ×
              </button>
            )}
          </div>
        </div>

        {/* Category Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none border-t border-slate-100 dark:border-white/10 pt-4">
          <button
            onClick={() => setActiveCategory('all')}
            className={`px-4 py-2.5 rounded-2xl text-xs font-bold transition-all duration-200 cursor-pointer shrink-0 flex items-center gap-2 ${
              activeCategory === 'all'
                ? 'bg-[#101318] dark:bg-white text-white dark:text-slate-900 shadow-md'
                : 'bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-400 hover:bg-slate-200/80 dark:hover:bg-white/10'
            }`}
          >
            <Grid className="w-3.5 h-3.5" />
            <span>All 40 Graphs</span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${
              activeCategory === 'all' ? 'bg-orange-500 text-white' : 'bg-slate-200 dark:bg-white/10 text-slate-500'
            }`}>
              40
            </span>
          </button>

          {ANALYSIS_CATEGORIES.map((cat) => {
            const Icon = getCategoryIcon(cat.id);
            const isActive = activeCategory === cat.id;

            return (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id)}
                className={`px-4 py-2.5 rounded-2xl text-xs font-bold transition-all duration-200 cursor-pointer shrink-0 flex items-center gap-2 ${
                  isActive
                    ? 'bg-[#101318] dark:bg-white text-white dark:text-slate-900 shadow-md'
                    : 'bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-400 hover:bg-slate-200/80 dark:hover:bg-white/10'
                }`}
              >
                <Icon className="w-3.5 h-3.5 text-orange-500" />
                <span>{cat.label}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                  isActive ? 'bg-orange-500 text-white' : 'bg-slate-200 dark:bg-white/10 text-slate-500'
                }`}>
                  10
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Active Category Description Banner (if single category selected) */}
      {activeCategory !== 'all' && (
        <div className="bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/10 rounded-2xl p-4 flex items-center justify-between gap-4">
          <div>
            <div className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider font-sans">
              {ANALYSIS_CATEGORIES.find((c) => c.id === activeCategory)?.label} — Category Focus
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {ANALYSIS_CATEGORIES.find((c) => c.id === activeCategory)?.description}
            </p>
          </div>
          <span className="text-xs font-mono font-bold text-orange-600 dark:text-orange-400 bg-orange-500/10 px-3 py-1 rounded-xl shrink-0">
            10 of 10 Loaded
          </span>
        </div>
      )}

      {/* 40 Graphs Responsive Grid */}
      {filteredGraphs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-6">
          {filteredGraphs.map((graph) => (
            <AnalyticsCard
              key={graph.id}
              graph={graph}
              chartData={chartData}
            />
          ))}
        </div>
      ) : (
        <div className="bg-white dark:bg-[#101318] rounded-3xl p-12 text-center border border-slate-200 dark:border-white/10 shadow-md">
          <p className="text-sm font-semibold text-slate-600 dark:text-slate-400">
            No graphs match the search term "{searchQuery}".
          </p>
          <button
            onClick={() => setSearchQuery('')}
            className="mt-3 text-xs font-bold text-orange-600 hover:underline cursor-pointer"
          >
            Clear search query
          </button>
        </div>
      )}
    </section>
  );
};
