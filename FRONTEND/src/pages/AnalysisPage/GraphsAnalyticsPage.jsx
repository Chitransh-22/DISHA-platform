import React, { useState, useEffect, useMemo } from 'react';
import { Navbar } from '../LandingPage/components/Navbar';
import { Footer } from '../LandingPage/components/Footer';
import { AnalysisFilters } from './components/AnalysisFilters';
import { CategoryGraphsView } from './components/CategoryGraphsView';
import {
  fetchRawAnalysisData,
  filterIncidents,
  computeAnalysisAnalytics,
} from '../../services/analysisDataService';
import { ArrowLeft, BarChart3, Database, RefreshCw } from 'lucide-react';

export const GraphsAnalyticsPage = ({ onNavigate }) => {
  const [loading, setLoading] = useState(true);
  const [rawData, setRawData] = useState({ rawIncidents: [], dbStats: {}, isLiveBackend: false, lastSyncTime: '' });

  // Global Filter State
  const [filters, setFilters] = useState({
    timeWindow: 'all',
    disasterType: 'all',
    state: 'all',
    severity: 'all',
    dataSource: 'all',
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchRawAnalysisData();
      if (data) {
        setRawData(data);
      }
    } catch (err) {
      console.error('[GraphsAnalyticsPage] Data load err:', err);
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

  // Filter incidents based on global filters
  const filteredIncidents = useMemo(() => {
    return filterIncidents(rawData.rawIncidents, filters);
  }, [rawData.rawIncidents, filters]);

  // Compute analytics
  const analytics = useMemo(() => {
    return computeAnalysisAnalytics(filteredIncidents, rawData.rawIncidents, rawData.dbStats);
  }, [filteredIncidents, rawData.rawIncidents, rawData.dbStats]);

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col selection:bg-orange-500 selection:text-white relative overflow-hidden font-sans">
      {/* Subtle Background Pattern */}
      <div className="fixed inset-0 bg-grid-slate pointer-events-none opacity-40 z-0" />
      <div className="fixed top-20 right-10 w-96 h-96 bg-orange-500/5 rounded-full blur-3xl pointer-events-none z-0" />

      {/* Top Navbar */}
      <Navbar currentPage="analysis" onNavigate={onNavigate} />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pt-24 pb-16 relative z-10 space-y-6">
        
        {/* Navigation & Header Breadcrumb */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-[#101318] p-5 rounded-3xl border border-slate-200/90 dark:border-white/10 shadow-md">
          <div className="flex items-center gap-3">
            <button
              id="back-to-analysis-overview-btn"
              onClick={() => onNavigate('analysis')}
              className="flex items-center gap-2 bg-slate-100 dark:bg-white/10 hover:bg-slate-200 dark:hover:bg-white/20 text-slate-800 dark:text-white text-xs font-bold px-3.5 py-2 rounded-xl transition-all cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Analysis Overview</span>
            </button>

            <div className="h-5 w-px bg-slate-200 dark:bg-white/10" />

            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-orange-500" />
              <h1 className="text-base sm:text-lg font-black text-slate-900 dark:text-white font-sans tracking-tight">
                Disaster Intelligence — 40 Graph Analytics Workspace
              </h1>
            </div>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-300 hover:text-orange-500 transition-colors cursor-pointer self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-orange-500' : ''}`} />
            <span>Sync Live Telemetry</span>
          </button>
        </div>

        {/* Global Filters */}
        <AnalysisFilters
          filters={filters}
          onFilterChange={handleFilterChange}
          onResetFilters={handleResetFilters}
          matchingCount={filteredIncidents.length}
          totalCount={rawData.rawIncidents.length}
        />

        {/* 40 Graphs Categorized Analytics View */}
        <CategoryGraphsView
          chartData={analytics.chartData}
          defaultCategory="all"
        />

      </main>

      {/* Footer */}
      <Footer onNavigate={onNavigate} />
    </div>
  );
};
