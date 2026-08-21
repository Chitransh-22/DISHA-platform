import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Newspaper,
  Clock,
  MapPin,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Flame,
  Radio,
  FileText,
  Compass,
  Phone,
  CheckCircle,
  Share2,
} from 'lucide-react';
import { fetchNewsDetail } from '../services/api';
import { EVENT_CONFIG, getCategoryConfig, SEVERITY_CONFIG } from '../config/eventConfig';

export const NewsDetailPage = ({ newsId, initialArticle, onNavigate }) => {
  const [article, setArticle] = useState(initialArticle || null);
  const [loading, setLoading] = useState(!initialArticle && Boolean(newsId));
  const [error, setError] = useState(null);

  useEffect(() => {
    if (newsId && (!article || (article.id !== newsId && article.article_id !== newsId && article.event_id !== newsId))) {
      const loadDetail = async () => {
        setLoading(true);
        setError(null);
        try {
          const res = await fetchNewsDetail(newsId);
          if (res && res.news) {
            setArticle(res.news);
          } else {
            setError('Article details could not be found.');
          }
        } catch (err) {
          console.error('[NewsDetailPage] Error loading news detail:', err);
          setError('Unable to load this news article. It may have expired or the ID is invalid.');
        } finally {
          setLoading(false);
        }
      };
      loadDetail();
    }
  }, [newsId]);

  const config = article ? getCategoryConfig(article.category) : EVENT_CONFIG.Other;
  const sevConfig = article ? (SEVERITY_CONFIG[article.severity] || SEVERITY_CONFIG.Moderate) : SEVERITY_CONFIG.Moderate;

  const corroboratingSources = article?.corroboration?.sources || [];
  const confidenceScore = article?.metadata?.confidence ?? article?.classification?.confidence;

  return (
    <div className="min-h-screen bg-[#f5f2ea] text-slate-900 flex flex-col p-4 sm:p-6 lg:p-8 font-sans">
      <div className="max-w-4xl mx-auto w-full space-y-6">
        
        {/* Top Header Navigation */}
        <div className="flex items-center justify-between gap-4">
          <button
            id="back-to-news-btn"
            onClick={() => onNavigate('news')}
            className="flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm px-4 py-2.5 rounded-xl shadow-xs border border-slate-200 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Recent News</span>
          </button>

          <button
            onClick={() => onNavigate('landing')}
            className="text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors cursor-pointer"
          >
            Go to Home
          </button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-3xl p-8 sm:p-12 border border-slate-200/90 shadow-sm animate-pulse space-y-6">
            <div className="flex gap-2">
              <div className="h-6 w-24 bg-slate-200 rounded-full" />
              <div className="h-6 w-20 bg-slate-200 rounded-full" />
            </div>
            <div className="h-8 w-3/4 bg-slate-200 rounded-xl" />
            <div className="h-4 w-1/2 bg-slate-100 rounded-lg" />
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-slate-100">
              {[1, 2, 3, 4].map((n) => (
                <div key={n} className="h-14 bg-slate-100 rounded-xl" />
              ))}
            </div>
            <div className="space-y-2 pt-4">
              <div className="h-4 w-full bg-slate-100 rounded-lg" />
              <div className="h-4 w-full bg-slate-100 rounded-lg" />
              <div className="h-4 w-2/3 bg-slate-100 rounded-lg" />
            </div>
          </div>
        )}

        {/* Error / Not Found State */}
        {!loading && (error || !article) && (
          <div className="bg-white rounded-3xl p-12 border border-slate-200/80 shadow-sm text-center space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-red-50 border border-red-200 flex items-center justify-center text-red-600 mx-auto">
              <AlertTriangle className="w-7 h-7" />
            </div>
            <div className="space-y-1 max-w-md mx-auto">
              <h2 className="text-xl font-bold text-slate-900">Article Not Found</h2>
              <p className="text-sm text-slate-500 leading-relaxed">
                {error || 'The requested disaster news briefing could not be loaded.'}
              </p>
            </div>
            <button
              onClick={() => onNavigate('news')}
              className="px-5 py-2.5 bg-orange-600 hover:bg-orange-700 text-white font-bold text-sm rounded-xl transition-colors cursor-pointer inline-flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Return to Recent News</span>
            </button>
          </div>
        )}

        {/* Full Article Content */}
        {!loading && article && (
          <article className="bg-white rounded-3xl p-6 sm:p-10 border border-slate-200/90 shadow-sm space-y-6">
            
            {/* Header Badges & Meta */}
            <div className="flex flex-wrap items-center gap-2.5 pb-2">
              {/* Category */}
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-bold text-xs border ${config.badge}`}>
                <span>{config.icon}</span>
                <span>{config.label}</span>
              </span>

              {/* Severity */}
              <span className={`inline-flex items-center px-3 py-1 rounded-full font-bold text-xs uppercase tracking-wider ${sevConfig.badge}`}>
                {article.severity || 'Moderate'} Severity
              </span>

              {/* Status */}
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 font-bold text-xs border border-emerald-200">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                <span>{article.status || 'Verified Intelligence'}</span>
              </span>

              {/* AI Confidence */}
              {confidenceScore != null && (
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-blue-50 text-blue-700 font-bold text-xs border border-blue-200">
                  <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                  <span>{Math.round(confidenceScore * 100)}% Match Confidence</span>
                </span>
              )}
            </div>

            {/* Main Headline */}
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight leading-snug">
              {article.title}
            </h1>

            {/* Time & Author / Agency row */}
            <div className="flex flex-wrap items-center justify-between gap-4 py-3 border-y border-slate-100 text-xs sm:text-sm text-slate-500">
              <div className="flex items-center gap-2 font-mono">
                <Clock className="w-4 h-4 text-orange-500" />
                <span>Published: <strong className="text-slate-800">{article.date}</strong> {article.time && <span>at {article.time}</span>}</span>
              </div>

              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Source: <strong className="text-slate-800">{article.source || 'Verified Disaster Feed'}</strong></span>
              </div>
            </div>

            {/* Hero Image if present */}
            {article.image && (
              <div className="w-full max-h-[380px] rounded-2xl overflow-hidden bg-slate-100 border border-slate-200">
                <img
                  src={article.image}
                  alt={article.title}
                  className="w-full h-full object-cover"
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
              </div>
            )}

            {/* Key Field Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 bg-slate-50 p-4 sm:p-5 rounded-2xl border border-slate-200/80">
              
              <div className="space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Affected Location</span>
                <div className="flex items-center gap-1 text-slate-800 font-bold text-sm">
                  <MapPin className="w-3.5 h-3.5 text-orange-500 shrink-0" />
                  <span className="truncate">{article.location || 'India'}</span>
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Hazard Type</span>
                <div className="text-slate-800 font-bold text-sm flex items-center gap-1">
                  <span>{config.icon}</span>
                  <span>{config.label}</span>
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Coordinates</span>
                <div className="text-slate-800 font-mono font-bold text-xs">
                  {article.latitude != null && article.longitude != null
                    ? `${article.latitude.toFixed(4)}° N, ${article.longitude.toFixed(4)}° E`
                    : 'Geocoded Regional Area'}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Primary Source</span>
                <div className="text-slate-800 font-bold text-sm truncate">
                  {article.source || 'News Wire'}
                </div>
              </div>

            </div>

            {/* Full Briefing / Content (HTML-Sanitized) */}
            <div className="space-y-4 pt-2">
              <h3 className="text-lg font-black text-slate-900 tracking-tight flex items-center gap-2">
                <FileText className="w-5 h-5 text-orange-600" />
                <span>Situation Report & Details</span>
              </h3>

              <div className="text-slate-700 leading-relaxed text-sm sm:text-base space-y-3 font-normal">
                {article.full_content || article.full_description || article.description || article.summary ? (
                  <p className="whitespace-pre-line">
                    {article.full_content || article.full_description || article.description || article.summary}
                  </p>
                ) : (
                  <p className="text-slate-400 italic">
                    Detailed situation briefing generated via automated disaster intelligence.
                  </p>
                )}
              </div>
            </div>

            {/* Corroborating Sources / Evidence */}
            {corroboratingSources.length > 0 && (
              <div className="space-y-2.5 pt-4 border-t border-slate-100">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Corroborating Intelligence Sources ({corroboratingSources.length})
                </h4>
                <div className="flex flex-wrap gap-2">
                  {corroboratingSources.map((src, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold border border-slate-200/80"
                    >
                      {src}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Official DOs and DON'Ts based on Disaster Category */}
            {config && (config.dos?.length > 0 || config.donts?.length > 0) && (
              <div className="space-y-3 pt-4 border-t border-slate-100">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>Official Safety Advisory for {config.label}</span>
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {config.dos?.length > 0 && (
                    <div className="bg-emerald-50/70 border border-emerald-200 rounded-2xl p-4 space-y-2">
                      <h5 className="text-xs font-bold text-emerald-900 uppercase tracking-wider flex items-center gap-1">
                        <span>✓</span> Recommended Actions (DOs)
                      </h5>
                      <ul className="text-xs text-emerald-800 space-y-1.5 pl-4 list-disc">
                        {config.dos.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {config.donts?.length > 0 && (
                    <div className="bg-rose-50/70 border border-rose-200 rounded-2xl p-4 space-y-2">
                      <h5 className="text-xs font-bold text-rose-900 uppercase tracking-wider flex items-center gap-1">
                        <span>✗</span> Hazards to Avoid (DON'Ts)
                      </h5>
                      <ul className="text-xs text-rose-800 space-y-1.5 pl-4 list-disc">
                        {config.donts.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* External Source Action Button & Helpline Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-6 border-t border-slate-100">
              
              {article.source_url ? (
                <a
                  href={article.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-orange-600 hover:bg-orange-700 text-white text-xs sm:text-sm font-bold rounded-xl transition-all shadow-sm hover:shadow-orange-950/20 cursor-pointer"
                >
                  <span>View Original Source Article</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
              ) : (
                <div className="text-xs text-slate-400">
                  Direct official bulletin ingest
                </div>
              )}

              <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-600">
                <Phone className="w-3.5 h-3.5 text-red-500" />
                <span>National Emergency Helpline: <strong className="text-slate-900">112 / 1070</strong></span>
              </div>

            </div>

          </article>
        )}

      </div>
    </div>
  );
};
