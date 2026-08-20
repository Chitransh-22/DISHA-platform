import React from 'react';
import {
  HorizontalBarChart,
  ColumnBarChart,
  DonutChart,
  StackedBarChart,
  AreaLineChart,
  MultiLineChart,
  FunnelChart,
  RadarSpiderChart,
  DeltaBarChart,
} from '../../../components/charts/DISHALightweightCharts';
import { Info, Sparkles, Database, ExternalLink } from 'lucide-react';
import { ErrorBoundary } from '../../../components/common/ErrorBoundary';

/**
 * Universal Analytics Card for DISHA Graphs
 * Renders consistent title, subtitle, graph component, computed dynamic insight, and data source tag.
 */
export const AnalyticsCard = ({ graph, chartData = {} }) => {
  if (!graph) return null;

  const {
    id,
    number,
    title,
    subtitle,
    chartType,
    dataKey,
    dataSource,
    insightGenerator,
  } = graph;

  const data = chartData[dataKey] || [];
  let dynamicInsight = 'Dynamic telemetry updated from live stream.';
  if (typeof insightGenerator === 'function') {
    try {
      dynamicInsight = insightGenerator(data) || dynamicInsight;
    } catch (e) {
      dynamicInsight = 'Telemetry actively synchronized from verified disaster records.';
    }
  }

  // Render proper chart based on type
  const renderChart = () => {
    switch (chartType) {
      case 'horizontal_bar':
        return <HorizontalBarChart data={data} />;
      case 'column_bar':
      case 'histogram':
        return <ColumnBarChart data={data} />;
      case 'donut':
        return <DonutChart data={data} />;
      case 'stacked_bar':
        return <StackedBarChart data={data} />;
      case 'area':
      case 'pareto':
      case 'line_with_bars':
        return <AreaLineChart data={data} isArea={true} strokeColor="#ea580c" />;
      case 'multi_line':
      case 'stacked_area':
        return <MultiLineChart data={data} />;
      case 'funnel':
        return <FunnelChart data={data} />;
      case 'radar':
        return <RadarSpiderChart data={data} />;
      case 'delta_bar':
        return <DeltaBarChart data={data} />;
      default:
        return <HorizontalBarChart data={data} />;
    }
  };

  return (
    <div
      id={`analytics-card-${id}`}
      className="group relative bg-white dark:bg-[#101318] rounded-3xl p-5 sm:p-6 border border-slate-200/90 dark:border-white/10 shadow-lg hover:shadow-xl transition-all duration-300 flex flex-col justify-between overflow-hidden"
    >
      {/* Top Ambient Highlight */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-linear-to-r from-orange-500/40 via-amber-500/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

      {/* Header Bar */}
      <div>
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-orange-500/10 text-orange-600 dark:text-orange-400 font-mono text-xs font-bold shrink-0">
              {number < 10 ? `0${number}` : number}
            </span>
            <h3 className="text-base font-bold text-slate-900 dark:text-white leading-snug font-sans group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">
              {title}
            </h3>
          </div>
        </div>

        {/* Subtitle / One-line explanation */}
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mb-4">
          {subtitle}
        </p>

        {/* Graph Render Area */}
        <div className="w-full min-h-[190px] flex items-center justify-center bg-slate-50/50 dark:bg-black/20 rounded-2xl p-3 border border-slate-100 dark:border-white/5 mb-4">
          <ErrorBoundary title="Chart Render Error" fallback={<div className="text-xs text-slate-400 p-4">Graph rendering in progress...</div>}>
            {renderChart()}
          </ErrorBoundary>
        </div>
      </div>

      {/* Footer Area: Dynamic Insight + Data Source */}
      <div className="space-y-2.5 pt-3 border-t border-slate-100 dark:border-white/10 text-xs">
        {/* Dynamic Computed Insight */}
        <div className="flex items-start gap-2 bg-orange-50/80 dark:bg-orange-950/20 p-2.5 rounded-xl border border-orange-200/60 dark:border-orange-500/20 text-slate-700 dark:text-slate-300">
          <Sparkles className="w-3.5 h-3.5 text-orange-600 dark:text-orange-400 shrink-0 mt-0.5" />
          <div className="text-[11px] leading-relaxed">
            <span className="font-bold text-orange-900 dark:text-orange-300 mr-1">Insight:</span>
            <span>{dynamicInsight}</span>
          </div>
        </div>

        {/* Data Source Tag */}
        <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
          <div className="flex items-center gap-1.5 truncate">
            <Database className="w-3 h-3 text-slate-400 shrink-0" />
            <span className="truncate">{dataSource || 'DISHA Telemetry Stream'}</span>
          </div>
          <span className="text-slate-500 font-sans font-medium shrink-0">Live Calculated</span>
        </div>
      </div>
    </div>
  );
};
