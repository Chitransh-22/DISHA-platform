import React, { useState, useEffect, useMemo } from 'react';
import {
  ArrowLeft,
  Newspaper,
  Clock,
  MapPin,
  ExternalLink,
  ChevronRight,
  Filter,
  Search,
  RefreshCw,
  Building2,
  Calendar,
  AlertTriangle,
  Flame,
  ShieldCheck,
} from 'lucide-react';
import { fetchRecentNews, fetchNewsSources } from '../services/api';
import { EVENT_CONFIG, getCategoryConfig, SEVERITY_CONFIG } from '../config/eventConfig';
import { formatDateTimeIST } from '../utils/dateTime';
import { sanitizeNewsDescription } from '../utils/htmlSanitizer';

export const RecentNewsPage = ({ onNavigate, onSelectNews }) => {
  const [timeRange, setTimeRange] = useState('24h');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedSource, setSelectedSource] = useState('All');
  const [sourcesList, setSourcesList] = useState(['All']);
  const [searchQuery, setSearchQuery] = useState('');
  const [newsList, setNewsList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [totalCount, setTotalCount] = useState(0);

  // 1. Fetch available news sources from backend on mount
  useEffect(() => {
    const loadSources = async () => {
      try {
        const res = await fetchNewsSources();
        if (res && Array.isArray(res.sources)) {
          setSourcesList(['All', ...res.sources]);
        }
      } catch (err) {
        console.error('[RecentNewsPage] Error fetching news sources:', err);
      }
    };
    loadSources();
  }, []);

  // 2. Fetch recent news with active filters
  const loadNews = async (range = timeRange, cat = selectedCategory, src = selectedSource) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRecentNews({
        range,
        category: cat !== 'All' ? cat : undefined,
        source: src !== 'All' ? src : undefined,
        limit: 50,
      });
      if (data && Array.isArray(data.news)) {
        // Sanitize every article summary and description
        const sanitized = data.news.map((item) => ({
          ...item,
          title: sanitizeNewsDescription(item.title),
          summary: sanitizeNewsDescription(item.summary || item.description || ''),
          description: sanitizeNewsDescription(item.description || item.summary || ''),
        }));
        setNewsList(sanitized);
        setTotalCount(data.total || sanitized.length);
      } else {
        setNewsList([]);
        setTotalCount(0);
      }
    } catch (err) {
      console.error('[RecentNewsPage] Error fetching news:', err);
      setError('Unable to load disaster news articles. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNews(timeRange, selectedCategory, selectedSource);
  }, [timeRange, selectedCategory, selectedSource]);

  const handleTimeRangeChange = (newRange) => {
    if (newRange === timeRange) return;
    setTimeRange(newRange);
  };

  const handleCategoryChange = (cat) => {
    if (cat === selectedCategory) return;
    setSelectedCategory(cat);
  };

  const handleSourceChange = (src) => {
    if (src === selectedSource) return;
    setSelectedSource(src);
  };

  const handleOpenDetail = (article) => {
    if (onSelectNews) {
      onSelectNews(article);
    }
    if (onNavigate) {
      onNavigate('news-detail', { newsId: article.id || article.article_id || article.event_id, article });
    }
  };

  // Filter list by keyword search in client memory
  const filteredArticles = useMemo(() => {
    if (!searchQuery.trim()) return newsList;
    const q = searchQuery.toLowerCase().trim();
    return newsList.filter(
      (item) =>
        (item.title && item.title.toLowerCase().includes(q)) ||
        (item.summary && item.summary.toLowerCase().includes(q)) ||
        (item.location && item.location.toLowerCase().includes(q)) ||
        (item.source && item.source.toLowerCase().includes(q)) ||
        (item.state && item.state.toLowerCase().includes(q)) ||
        (item.category && item.category.toLowerCase().includes(q))
    );
  }, [newsList, searchQuery]);

  const categoriesList = ['All', 'Flood', 'Heavy Rain', 'Landslide', 'Earthquake', 'Fire', 'Cyclone', 'Other'];

  return (
    <div className="min-h-screen bg-[#f5f2ea] text-slate-900 flex flex-col p-4 sm:p-6 lg:p-8 font-sans">
      <div className="max-w-6xl mx-auto w-full space-y-6">
        
        {/* Top Header Bar */}
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
                <Newspaper className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                  Recent Disaster News
                </h1>
                <p className="text-xs text-slate-500 font-medium">
                  Verified disaster intelligence briefings aggregated across national media & government wires
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={() => loadNews(timeRange, selectedCategory, selectedSource)}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-orange-600' : ''}`} />
            <span>Refresh Feed</span>
          </button>
        </div>

        {/* Filter Controls Panel */}
        <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/90 shadow-xs space-y-4">
          
          <div className="flex flex-wrap items-center justify-between gap-3">
            
            {/* 1. Time Window Pills */}
            <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl">
              {[
                { label: '24 Hours', value: '24h' },
                { label: '7 Days', value: '7d' },
                { label: '15 Days', value: '15d' },
                { label: '30 Days', value: '30d' },
              ].map((pill) => (
                <button
                  key={pill.value}
                  onClick={() => handleTimeRangeChange(pill.value)}
                  disabled={loading}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer disabled:opacity-50 ${
                    timeRange === pill.value
                      ? 'bg-orange-600 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-white/80'
                  }`}
                >
                  {pill.label}
                </button>
              ))}
            </div>

            {/* 2. Source Filter Dropdown */}
            <div className="flex items-center gap-2 bg-slate-100/80 px-3 py-1.5 rounded-xl border border-slate-200">
              <Building2 className="w-4 h-4 text-orange-600 shrink-0" />
              <label htmlFor="source-filter-select" className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                Source:
              </label>
              <select
                id="source-filter-select"
                value={selectedSource}
                onChange={(e) => handleSourceChange(e.target.value)}
                disabled={loading}
                className="bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-orange-500/30 cursor-pointer max-w-[200px] truncate"
              >
                {sourcesList.map((src) => (
                  <option key={src} value={src}>
                    {src === 'All' ? 'All Verified Sources' : src}
                  </option>
                ))}
              </select>
            </div>

            {/* 3. Keyword Search */}
            <div className="relative flex-1 min-w-[240px]">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search headlines, locations, sources..."
                className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-9.5 pr-4 py-2 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500/30 focus:border-orange-500 transition-all"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400 hover:text-slate-600"
                >
                  Clear
                </button>
              )}
            </div>

          </div>

          {/* 4. Category Filter Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-1 scrollbar-none border-t border-slate-100">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-1 shrink-0">
              Hazard:
            </span>
            {categoriesList.map((cat) => {
              const active = selectedCategory === cat;
              const config = getCategoryConfig(cat);
              return (
                <button
                  key={cat}
                  onClick={() => handleCategoryChange(cat)}
                  disabled={loading}
                  className={`px-3 py-1 rounded-full text-xs font-bold transition-all shrink-0 cursor-pointer flex items-center gap-1 disabled:opacity-50 ${
                    active
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200/80'
                  }`}
                >
                  {cat !== 'All' && <span>{config.icon}</span>}
                  <span>{cat}</span>
                </button>
              );
            })}
          </div>

        </div>

        {/* Loading State */}
        {loading && (
          <div className="space-y-4">
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs animate-pulse flex gap-5">
                <div className="flex-1 space-y-3">
                  <div className="flex gap-2">
                    <div className="h-5 w-24 bg-slate-200 rounded-full" />
                    <div className="h-5 w-20 bg-slate-200 rounded-full" />
                  </div>
                  <div className="h-6 w-3/4 bg-slate-200 rounded-lg" />
                  <div className="h-4 w-full bg-slate-100 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-8 text-center space-y-3">
            <AlertTriangle className="w-8 h-8 text-red-500 mx-auto" />
            <h3 className="text-base font-bold text-red-900">Failed to Load News Feed</h3>
            <p className="text-sm text-red-700 max-w-md mx-auto">{error}</p>
            <button
              onClick={() => loadNews(timeRange, selectedCategory, selectedSource)}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-xl transition-colors cursor-pointer"
            >
              Retry Feed
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && filteredArticles.length === 0 && (
          <div className="bg-white rounded-3xl p-12 border border-slate-200/80 shadow-xs text-center space-y-4 min-h-[300px] flex flex-col items-center justify-center">
            <div className="w-14 h-14 rounded-2xl bg-orange-50 border border-orange-200 flex items-center justify-center text-orange-600">
              <Newspaper className="w-7 h-7" />
            </div>
            <div className="space-y-1 max-w-md">
              <h3 className="text-lg font-bold text-slate-900">No News Found</h3>
              <p className="text-sm text-slate-500 leading-relaxed">
                No disaster news items match the selected time window (
                <strong>{timeRange === '24h' ? '24 Hours' : timeRange === '7d' ? '7 Days' : timeRange === '15d' ? '15 Days' : '30 Days'}</strong>
                ), source (<strong>{selectedSource}</strong>), and category.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 pt-2">
              <button
                onClick={() => { setSelectedSource('All'); handleTimeRangeChange('7d'); }}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white text-xs font-bold rounded-xl transition-colors cursor-pointer"
              >
                Expand to 7 Days & All Sources
              </button>
              <button
                onClick={() => { setSelectedSource('All'); handleTimeRangeChange('30d'); }}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition-colors cursor-pointer"
              >
                View 30 Days
              </button>
            </div>
          </div>
        )}

        {/* News List */}
        {!loading && !error && filteredArticles.length > 0 && (
          <div className="space-y-4">
            {filteredArticles.map((article, idx) => {
              const config = getCategoryConfig(article.category);
              const sevConfig = SEVERITY_CONFIG[article.severity] || SEVERITY_CONFIG.Moderate;
              const istTimeString = formatDateTimeIST(article);

              return (
                <div
                  key={article.id || article.db_id || idx}
                  onClick={() => handleOpenDetail(article)}
                  className="group bg-white rounded-2xl p-5 sm:p-6 border border-slate-200/90 shadow-xs hover:shadow-md hover:border-orange-500/40 transition-all duration-200 cursor-pointer flex flex-col sm:flex-row items-start justify-between gap-5"
                >
                  <div className="flex-1 space-y-2.5 min-w-0">
                    
                    {/* Badges & Meta Row */}
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      {/* Category Badge */}
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-bold border ${config.badge}`}>
                        <span>{config.icon}</span>
                        <span>{config.label}</span>
                      </span>

                      {/* Severity Badge */}
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-bold text-[11px] uppercase tracking-wider ${sevConfig.badge}`}>
                        {article.severity || 'Moderate'}
                      </span>

                      {/* Location Tag */}
                      {article.location && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 font-semibold border border-slate-200/80">
                          <MapPin className="w-3 h-3 text-orange-500 shrink-0" />
                          <span className="truncate max-w-[200px]">{article.location}</span>
                        </span>
                      )}

                      {/* IST Date & Time */}
                      <span className="inline-flex items-center gap-1 text-slate-500 font-medium ml-auto sm:ml-0 text-xs">
                        <Clock className="w-3.5 h-3.5 text-orange-500" />
                        <span>{istTimeString}</span>
                      </span>
                    </div>

                    {/* Headline */}
                    <h2 className="text-base sm:text-lg font-bold text-slate-900 group-hover:text-orange-600 transition-colors leading-snug">
                      {article.title}
                    </h2>

                    {/* Cleaned Summary snippet (No HTML tags) */}
                    {article.summary && (
                      <p className="text-xs sm:text-sm text-slate-600 leading-relaxed line-clamp-2">
                        {article.summary}
                      </p>
                    )}

                    {/* Source & Action Row */}
                    <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-xs">
                      <div className="flex items-center gap-1.5 text-slate-500 font-medium truncate max-w-sm">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                        <span>Source: <strong className="text-slate-800">{article.source || 'Verified Disaster Feed'}</strong></span>
                      </div>

                      <span className="inline-flex items-center gap-1 font-bold text-orange-600 group-hover:translate-x-0.5 transition-transform shrink-0">
                        <span>Read Full Report</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </span>
                    </div>

                  </div>

                </div>
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
};
