import React, { useState, useEffect, useMemo } from 'react';
import { Navbar } from '../LandingPage/components/Navbar';
import { Footer } from '../LandingPage/components/Footer';
import { AnalysisHero } from './components/AnalysisHero';
import { AnalysisFilters } from './components/AnalysisFilters';
import { AnalysisKPIGrid } from './components/AnalysisKPIGrid';
import { AnalysisMethodology } from './components/AnalysisMethodology';
import { KeyInsightsSection } from './components/KeyInsightsSection';
import { CategoryGraphsView } from './components/CategoryGraphsView';
import {
  fetchRawAnalysisData,
  filterIncidents,
  computeAnalysisAnalytics,
} from '../../services/analysisDataService';
import {
  ANALYSIS_CATEGORIES,
  ANALYSIS_GRAPHS,
} from '../../data/analysisRegistry';
import { AnalyticsCard } from './components/AnalyticsCard';
import {
  ArrowRight,
  BarChart3,
  Layers,
  Sparkles,
  Activity,
  MapPin,
  Clock,
  Cpu,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';

export const AnalysisPage = ({ currentPage = 'analysis', onNavigate }) => {
  const [loading, setLoading] = useState(true);
  const [rawData, setRawData] = useState({ rawIncidents: [], dbStats: {}, isLiveBackend: false, lastSyncTime: '' });
  const [error, setError] = useState(null);
  const [showFullWorkspace, setShowFullWorkspace] = useState(false);

  // Global Filter State
  const [filters, setFilters] = useState({
    timeWindow: 'all',
    disasterType: 'all',
    state: 'all',
    severity: 'all',
    dataSource: 'all',
  });

  // Load raw data on mount
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRawAnalysisData();
      if (data) {
        setRawData(data);
      }
    } catch (err) {
      console.error('[AnalysisPage] Data loading failure:', err);
      setError('Unable to load latest disaster intelligence feed. Please retry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleResetFilters = () => {
    setFilters({
      timeWindow: 'all',
      disasterType: 'all',
      state: 'all',
      severity: 'all',
      dataSource: 'all',
    });
  };

  // Filter incidents based on active global filters
  const filteredIncidents = useMemo(() => {
    return filterIncidents(rawData.rawIncidents, filters);
  }, [rawData.rawIncidents, filters]);

  // Compute all analytics, KPIs, insights, and 40 graph datasets
  const analytics = useMemo(() => {
    return computeAnalysisAnalytics(filteredIncidents, rawData.rawIncidents, rawData.dbStats);
  }, [filteredIncidents, rawData.rawIncidents, rawData.dbStats]);

  // Highlight preview graphs for main dashboard (1 selected per category)
  const previewGraphs = useMemo(() => {
    return [
      ANALYSIS_GRAPHS[0],  // Graph 1: Events by Disaster Type (Overview)
      ANALYSIS_GRAPHS[10], // Graph 11: Events by State (Geographic)
      ANALYSIS_GRAPHS[20], // Graph 21: Daily Timeline (Temporal)
      ANALYSIS_GRAPHS[32], // Graph 33: 5-Stage Pipeline Funnel (AI/Data)
    ];
  }, []);

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col selection:bg-orange-500 selection:text-white relative overflow-x-clip font-sans">
      {/* Subtle Ambient Grid & Glow Texture */}
      <div className="fixed inset-0 bg-grid-slate pointer-events-none opacity-40 z-0" />
      <div className="fixed top-20 left-1/2 -translate-x-1/2 w-275 h-112.5 bg-linear-to-b from-orange-500/10 via-amber-500/5 to-transparent blur-3xl pointer-events-none z-0" />

      {/* Main Navbar */}
      <Navbar currentPage={currentPage} onNavigate={onNavigate} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pt-24 pb-16 relative z-10 space-y-8">
        
        {/* SECTION 1: HERO HEADER */}
        <AnalysisHero
          lastSyncTime={rawData.lastSyncTime}
          onRefresh={loadData}
          loading={loading}
          isLive={rawData.isLiveBackend}
          totalEvents={analytics.kpis.totalEvents}
        />

        {/* Error Notification with Retry */}
        {error && (
          <div className="bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-400 p-4 rounded-2xl flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs font-semibold">
              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={loadData}
              className="text-xs font-bold px-3 py-1 rounded-xl bg-rose-500 text-white hover:bg-rose-600 transition-colors cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* GLOBAL ANALYSIS FILTERS */}
        <AnalysisFilters
          filters={filters}
          onFilterChange={handleFilterChange}
          onResetFilters={handleResetFilters}
          matchingCount={filteredIncidents.length}
          totalCount={rawData.rawIncidents.length}
        />

        {/* SECTION 2: EXECUTIVE KPI SUMMARY */}
        <AnalysisKPIGrid kpis={analytics.kpis} />

        {/* SECTION 12: KEY ANALYTICAL FINDINGS */}
        <KeyInsightsSection keyFindings={analytics.keyFindings} />

        {/* SECTION 3: HOW DISHA ANALYZES DISASTERS */}
        <AnalysisMethodology />

        {/* SECTION 4: 40-GRAPH WORKSPACE CTA & CATEGORY SHOWCASE */}
        <section className="w-full bg-[#101318] text-white rounded-3xl p-6 sm:p-10 border border-white/10 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-linear-to-bl from-orange-500/20 via-amber-500/10 to-transparent rounded-full blur-3xl pointer-events-none" />

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10 mb-8">
            <div className="space-y-2 max-w-2xl">
              <div className="flex items-center gap-2 text-xs font-bold text-orange-400 uppercase tracking-wider">
                <BarChart3 className="w-4 h-4 text-orange-500" />
                <span>Deep-Dive Analytics Infrastructure</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-white font-sans tracking-tight">
                Explore Exactly 40 Disaster Intelligence Graphs
              </h2>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                Comprehensive data-driven visualizations across 4 specialized categories (10 graphs per discipline), derived from live telemetry and verified historical baselines.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                id="explore-40-graphs-cta-btn"
                onClick={() => {
                  setShowFullWorkspace(true);
                  const el = document.getElementById('deep-dive-workspace-anchor');
                  if (el) el.scrollIntoView({ behavior: 'smooth' });
                }}
                className="group flex items-center gap-3 bg-linear-to-r from-[#f26522] to-[#ea580c] hover:from-[#ea580c] hover:to-[#c2410c] text-white font-bold text-sm px-6 py-3.5 rounded-full transition-all duration-300 shadow-xl shadow-orange-950/50 hover:shadow-orange-500/30 hover:-translate-y-0.5 cursor-pointer border border-orange-400/30"
              >
                <span>{showFullWorkspace ? 'Viewing 40 Graphs Below ↓' : 'Explore 40 Analytics Graphs →'}</span>
                <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
              </button>

              <button
                onClick={() => onNavigate('graphs')}
                className="bg-white/10 hover:bg-white/15 text-white font-semibold text-sm px-5 py-3.5 rounded-full transition-colors cursor-pointer border border-white/10"
              >
                Open Fullscreen Workspace
              </button>
            </div>
          </div>

          {/* 4 Category Summary Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-white/10">
            {ANALYSIS_CATEGORIES.map((cat, cIdx) => (
              <div
                key={cat.id}
                onClick={() => {
                  setShowFullWorkspace(true);
                  const el = document.getElementById('deep-dive-workspace-anchor');
                  if (el) el.scrollIntoView({ behavior: 'smooth' });
                }}
                className="p-4 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 transition-all cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30">
                    Category {cIdx + 1}
                  </span>
                  <span className="text-xs font-bold text-slate-400 font-mono">10 Graphs</span>
                </div>
                <h4 className="text-sm font-bold text-white group-hover:text-orange-400 transition-colors font-sans">
                  {cat.label}
                </h4>
                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                  {cat.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* DASHBOARD PREVIEW GRAPHS OR FULL 40-GRAPH WORKSPACE */}
        <div id="deep-dive-workspace-anchor" className="space-y-6">
          {showFullWorkspace ? (
            <CategoryGraphsView
              chartData={analytics.chartData}
              defaultCategory="all"
            />
          ) : (
            <section className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white font-sans">
                    Executive Analytics Highlights
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Key representative indicators from each of the 4 disaster intelligence disciplines.
                  </p>
                </div>
                <button
                  id="expand-all-40-graphs-btn"
                  onClick={() => setShowFullWorkspace(true)}
                  className="text-xs font-bold text-orange-600 dark:text-orange-400 hover:underline cursor-pointer flex items-center gap-1"
                >
                  <span>Expand all 40 graphs</span>
                  <span>→</span>
                </button>
              </div>

              {/* 4 Preview Analytics Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {previewGraphs.map((graph) => (
                  <AnalyticsCard
                    key={graph.id}
                    graph={graph}
                    chartData={analytics.chartData}
                  />
                ))}
              </div>
            </section>
          )}
        </div>

      </main>

      {/* Footer */}
      <Footer onNavigate={onNavigate} />
    </div>
  );
};
