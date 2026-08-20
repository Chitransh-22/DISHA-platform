import React, { useState } from 'react';
import {
  Radio,
  Filter,
  Award,
  Cpu,
  MapPin,
  Clock,
  ShieldAlert,
  ChevronRight,
  Sparkles,
} from 'lucide-react';

export const AnalysisMethodology = () => {
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    {
      number: '01',
      title: 'Signal Collection',
      subtitle: 'Multi-Source Feeds & Sensor APIs',
      icon: Radio,
      color: 'text-orange-500',
      bgColor: 'bg-orange-500/10',
      description:
        'DISHA continuously collects disaster telemetry from official government feeds including National Center for Seismology (NCS RISEQ), NDMA SACHET Common Alerting Protocol (CAP), IMD meteorological bulletins, and pan-India digital news sources.',
      details: [
        'Automated REST scraping of NCS 30-day rolling seismic events',
        'XML/RSS parsing of NDMA SACHET emergency broadcast alerts',
        'Continuous ingestion of digital news headlines across India',
      ],
    },
    {
      number: '02',
      title: 'Heuristic & Local Filtering',
      subtitle: 'Noise Elimination & Geotag Verification',
      icon: Filter,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
      description:
        'Raw incoming articles are immediately screened using regex-based local filters to weed out non-disaster sports/political metaphors, academic papers, and foreign-exclusive incidents before expensive AI processing.',
      details: [
        'Filters metaphorical usages (e.g. "landslide victory", "election heatwave")',
        'Enforces Indian geographic boundary validation',
        'Eliminates duplicate article URLs and hashes',
      ],
    },
    {
      number: '03',
      title: 'Quality & Evidence Scoring',
      subtitle: 'Deterministic Multi-Factor Scorer',
      icon: Award,
      color: 'text-amber-500',
      bgColor: 'bg-amber-500/10',
      description:
        'Candidate articles are evaluated by DISHA\'s quality scorer, calculating priority weights based on source reliability tiers (PTI, ANI, NDTV, Hindu), physical impact evidence (casualties, evacuations), and publication recency.',
      details: [
        'Source reliability weight ranging from Tier 1 (Gov/Sensors) to Tier 4 (Regional)',
        'Physical damage detection: casualties, road blockades, relief camp activations',
        'Strict score thresholding (Score >= 5.0) to prioritize AI verification queue',
      ],
    },
    {
      number: '04',
      title: 'Gemini AI Disaster Verification',
      subtitle: 'High-Precision Ground-Truth Classification',
      icon: Cpu,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
      description:
        'High-scoring candidates are submitted to Google Gemini models (Gemini 3.7 / 3.5 Flash) with strict quota controllers. The AI performs schema-enforced verification, categorizing disaster type, severity level (Critical, High, Moderate, Low), and exact incident date.',
      details: [
        'Distinguishes current emergencies from historical retrospective articles',
        'Assigns statistical confidence scores and structured ground-truth evidence bullets',
        'Standardized 4-tier severity rating based on casualties and destruction',
      ],
    },
    {
      number: '05',
      title: 'Geospatial Normalization',
      subtitle: 'Coordinate Geocoding & Regional Clustering',
      icon: MapPin,
      color: 'text-emerald-500',
      bgColor: 'bg-emerald-500/10',
      description:
        'Every verified event is geocoded to its respective Indian State, District, and geographic coordinate. Correlated incidents are spatially clustered using density algorithms to identify active disaster corridors.',
      details: [
        'State and district polygon normalization',
        'Geospatial clustering to isolate multi-district river basin floods',
        'Population density overlay for estimated human exposure calculations',
      ],
    },
    {
      number: '06',
      title: 'Temporal & Rolling Trend Engine',
      subtitle: 'Chronological Time Series Aggregation',
      icon: Clock,
      color: 'text-indigo-500',
      bgColor: 'bg-indigo-500/10',
      description:
        'Incidents are indexed along chronological timelines to generate rolling 30-day moving averages, diurnal 24-hour cycle distributions, and day-over-day signal velocity indicators.',
      details: [
        'Tracks incident acceleration and rapid surge alerts',
        'Diurnal time-of-day mapping (Night, Morning, Afternoon, Evening)',
        'Automatic 30-day rolling data retention and expiration',
      ],
    },
    {
      number: '07',
      title: 'Actionable Early Warning',
      subtitle: 'Situational Command & Response Mobilization',
      icon: ShieldAlert,
      color: 'text-rose-500',
      bgColor: 'bg-rose-500/10',
      description:
        'The processed disaster intelligence powers interactive GIS maps, executive analytics dashboards, state emergency response alerts, and public safety helplines for faster rescue coordination.',
      details: [
        'Real-time emergency telemetry for NDRF, SDRF, and district command cells',
        'Interactive OpenStreetMap GIS visualization with pulsating threat pins',
        'Exportable analytical reports and multi-dimensional graph workspaces',
      ],
    },
  ];

  return (
    <section className="w-full bg-white dark:bg-[#101318] rounded-3xl p-6 sm:p-8 border border-slate-200/90 dark:border-white/10 shadow-lg mb-8 transition-all duration-300">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
        <div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20 mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            Verification Architecture
          </span>
          <h2 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight font-sans">
            How DISHA Analyzes Disasters
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-2xl mt-1">
            An end-to-end overview of how raw disaster signals are filtered, verified by AI, geocoded, and transformed into actionable emergency intelligence.
          </p>
        </div>

        <div className="flex items-center gap-1 bg-slate-100 dark:bg-white/5 p-1 rounded-2xl border border-slate-200 dark:border-white/10 text-xs font-semibold overflow-x-auto">
          {steps.map((s, idx) => (
            <button
              key={s.number}
              onClick={() => setActiveStep(idx)}
              className={`px-3 py-1.5 rounded-xl transition-all cursor-pointer whitespace-nowrap ${
                activeStep === idx
                  ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-md'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {s.number}
            </button>
          ))}
        </div>
      </div>

      {/* Active Step Feature Box */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center p-6 rounded-3xl bg-slate-50 dark:bg-black/30 border border-slate-200/80 dark:border-white/5">
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-4xl font-black text-orange-600 dark:text-orange-400 font-mono">
              {steps[activeStep].number}
            </span>
            <div className={`w-12 h-12 rounded-2xl ${steps[activeStep].bgColor} flex items-center justify-center ${steps[activeStep].color}`}>
              {React.createElement(steps[activeStep].icon, { className: 'w-6 h-6' })}
            </div>
          </div>

          <div>
            <h3 className="text-xl font-bold text-slate-900 dark:text-white font-sans">
              {steps[activeStep].title}
            </h3>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              {steps[activeStep].subtitle}
            </div>
          </div>
        </div>

        <div className="lg:col-span-8 space-y-3">
          <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-normal">
            {steps[activeStep].description}
          </p>

          <div className="space-y-1.5 pt-2 border-t border-slate-200 dark:border-white/10">
            {steps[activeStep].details.map((bullet, bIdx) => (
              <div key={bIdx} className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                <ChevronRight className="w-3.5 h-3.5 text-orange-500 shrink-0" />
                <span>{bullet}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
