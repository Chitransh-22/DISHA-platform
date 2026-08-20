import React, { useState } from 'react';

/**
 * Universal Tooltip Component
 */
const Tooltip = ({ x, y, title, subtitle, items = [] }) => {
  return (
    <div
      className="absolute pointer-events-none z-50 bg-[#0b0f17]/95 text-white px-3 py-2 rounded-xl shadow-2xl border border-white/20 text-xs backdrop-blur-md transition-all duration-75 transform -translate-x-1/2 -translate-y-full mb-2"
      style={{ left: `${x}px`, top: `${y}px` }}
    >
      {title && <div className="font-bold text-slate-100 text-xs">{title}</div>}
      {subtitle && <div className="text-[11px] text-slate-400 mt-0.5">{subtitle}</div>}
      {items.length > 0 && (
        <div className="mt-1.5 space-y-1 pt-1 border-t border-white/10">
          {items.map((it, idx) => (
            <div key={idx} className="flex items-center justify-between gap-3 text-[11px]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: it.color || '#f97316' }} />
                <span className="text-slate-300">{it.label}</span>
              </div>
              <span className="font-mono font-bold text-white">{it.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * 1. Horizontal Bar Chart
 */
export const HorizontalBarChart = ({ data = [], maxVal = null, showPercentage = true }) => {
  const [hovered, setHovered] = useState(null);

  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-48 text-xs text-slate-400">No chart data available</div>;
  }

  const calculatedMax = maxVal || Math.max(...data.map((d) => d.value || 0), 1);

  return (
    <div className="w-full space-y-3 py-2">
      {data.map((item, idx) => {
        const val = item.value || 0;
        const widthPct = Math.min(100, Math.max(4, (val / calculatedMax) * 100));
        const color = item.color || '#ea580c';
        const isHovered = hovered === idx;

        return (
          <div
            key={idx}
            className="group cursor-pointer"
            onMouseEnter={() => setHovered(idx)}
            onMouseLeave={() => setHovered(null)}
          >
            <div className="flex items-center justify-between text-xs mb-1">
              <div className="flex items-center gap-2 max-w-[70%] truncate">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
                <span className="font-semibold text-slate-700 dark:text-slate-200 truncate group-hover:text-orange-600 transition-colors">
                  {item.label}
                </span>
              </div>
              <div className="flex items-center gap-1.5 font-mono text-xs shrink-0">
                <span className="font-bold text-slate-900 dark:text-white">{item.formattedValue || val.toLocaleString('en-IN')}</span>
                {showPercentage && item.percentage !== undefined && (
                  <span className="text-[10px] text-slate-400 font-normal">({item.percentage}%)</span>
                )}
              </div>
            </div>
            <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-3 overflow-hidden p-0.5 border border-slate-200/60 dark:border-white/5">
              <div
                className={`h-full rounded-full transition-all duration-500 ease-out ${isHovered ? 'brightness-110 shadow-md' : ''}`}
                style={{
                  width: `${widthPct}%`,
                  backgroundColor: color,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

/**
 * 2. Column / Vertical Bar Chart
 */
export const ColumnBarChart = ({ data = [], height = 180 }) => {
  const [tooltip, setTooltip] = useState(null);

  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-48 text-xs text-slate-400">No chart data available</div>;
  }

  const maxVal = Math.max(...data.map((d) => d.value || 0), 1);

  return (
    <div className="relative w-full" style={{ height: `${height}px` }}>
      {tooltip && <Tooltip {...tooltip} />}
      <div className="flex items-end justify-between gap-2 h-[calc(100%-28px)] w-full pt-4 px-2">
        {data.map((item, idx) => {
          const val = item.value || 0;
          const heightPct = Math.min(100, Math.max(6, (val / maxVal) * 100));
          const color = item.color || '#ea580c';

          return (
            <div
              key={idx}
              className="flex-1 flex flex-col items-center h-full justify-end group cursor-pointer"
              onMouseEnter={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                setTooltip({
                  x: rect.left + rect.width / 2,
                  y: rect.top,
                  title: item.label,
                  items: [{ label: 'Count', value: val.toLocaleString('en-IN'), color }],
                });
              }}
              onMouseLeave={() => setTooltip(null)}
            >
              <div className="text-[10px] font-mono font-bold text-slate-600 dark:text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity mb-1">
                {val}
              </div>
              <div
                className="w-full max-w-[36px] rounded-t-lg transition-all duration-300 group-hover:brightness-110 group-hover:scale-y-105 origin-bottom shadow-xs"
                style={{
                  height: `${heightPct}%`,
                  backgroundColor: color,
                }}
              />
            </div>
          );
        })}
      </div>
      {/* X-Axis Labels */}
      <div className="flex justify-between items-center px-2 pt-2 border-t border-slate-200 dark:border-slate-800 text-[10px] font-medium text-slate-500 truncate">
        {data.map((item, idx) => (
          <div key={idx} className="flex-1 text-center truncate px-0.5" title={item.label}>
            {item.label}
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * 3. Donut / Pie Chart
 */
export const DonutChart = ({ data = [], size = 180, strokeWidth = 26, centerText = null }) => {
  const [hovered, setHovered] = useState(null);

  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-48 text-xs text-slate-400">No chart data available</div>;
  }

  const total = data.reduce((acc, item) => acc + (item.value || 0), 0) || 1;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let accumulated = 0;
  const slices = data.map((item, idx) => {
    const val = item.value || 0;
    const fraction = val / total;
    const strokeDasharray = `${fraction * circumference} ${circumference}`;
    const strokeDashoffset = -(accumulated * circumference);
    accumulated += fraction;

    return {
      ...item,
      strokeDasharray,
      strokeDashoffset,
      percentage: Math.round(fraction * 100),
      color: item.color || '#ea580c',
    };
  });

  return (
    <div className="flex flex-col sm:flex-row items-center justify-center gap-6 py-2">
      {/* SVG Ring */}
      <div className="relative flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke="currentColor"
            className="text-slate-100 dark:text-slate-800"
            strokeWidth={strokeWidth}
          />
          {slices.map((slice, idx) => (
            <circle
              key={idx}
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="transparent"
              stroke={slice.color}
              strokeWidth={hovered === idx ? strokeWidth + 4 : strokeWidth}
              strokeDasharray={slice.strokeDasharray}
              strokeDashoffset={slice.strokeDashoffset}
              strokeLinecap="round"
              className="transition-all duration-300 cursor-pointer"
              onMouseEnter={() => setHovered(idx)}
              onMouseLeave={() => setHovered(null)}
            />
          ))}
        </svg>
        {/* Center Label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
          <span className="text-xl font-black text-slate-900 dark:text-white font-sans">
            {hovered !== null ? slices[hovered].value : centerText || total}
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
            {hovered !== null ? slices[hovered].label : 'Total'}
          </span>
        </div>
      </div>

      {/* Legend List */}
      <div className="flex-1 space-y-2 max-w-xs w-full">
        {slices.map((slice, idx) => (
          <div
            key={idx}
            className={`flex items-center justify-between p-1.5 rounded-xl text-xs transition-colors cursor-pointer ${
              hovered === idx ? 'bg-slate-100 dark:bg-white/10 font-bold' : 'hover:bg-slate-50 dark:hover:bg-white/5'
            }`}
            onMouseEnter={() => setHovered(idx)}
            onMouseLeave={() => setHovered(null)}
          >
            <div className="flex items-center gap-2 truncate">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: slice.color }} />
              <span className="text-slate-700 dark:text-slate-300 truncate">{slice.label}</span>
            </div>
            <div className="flex items-center gap-2 font-mono shrink-0">
              <span className="font-bold text-slate-900 dark:text-white">{slice.value}</span>
              <span className="text-[10px] text-slate-400">({slice.percentage}%)</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * 4. Stacked Bar Chart
 */
export const StackedBarChart = ({ data = [], height = 200 }) => {
  const [tooltip, setTooltip] = useState(null);

  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-48 text-xs text-slate-400">No chart data available</div>;
  }

  const keys = ['Critical', 'High', 'Moderate', 'Low', 'Critical_Severe', 'Moderate_Low'].filter((k) =>
    data.some((d) => d[k] !== undefined)
  );

  const colors = {
    Critical: '#dc2626',
    High: '#ea580c',
    Moderate: '#f59e0b',
    Low: '#10b981',
    Critical_Severe: '#ea580c',
    Moderate_Low: '#3b82f6',
  };

  const maxTotal = Math.max(
    ...data.map((d) => {
      let sum = 0;
      keys.forEach((k) => {
        sum += d[k] || 0;
      });
      return sum || d.total || 1;
    }),
    1
  );

  return (
    <div className="w-full space-y-4">
      {tooltip && <Tooltip {...tooltip} />}
      <div className="space-y-2.5">
        {data.map((item, idx) => {
          let sum = 0;
          keys.forEach((k) => {
            sum += item[k] || 0;
          });
          const total = sum || item.total || 1;

          return (
            <div key={idx} className="space-y-1">
              <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-200">
                <span className="truncate">{item.category}</span>
                <span className="font-mono text-slate-500">{total} events</span>
              </div>
              <div
                className="w-full h-4 bg-slate-100 dark:bg-slate-800 rounded-full flex overflow-hidden cursor-pointer p-0.5 border border-slate-200 dark:border-white/5"
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  setTooltip({
                    x: rect.left + rect.width / 2,
                    y: rect.top,
                    title: item.category,
                    items: keys.map((k) => ({
                      label: k.replace('_', ' / '),
                      value: item[k] || 0,
                      color: colors[k],
                    })),
                  });
                }}
                onMouseLeave={() => setTooltip(null)}
              >
                {keys.map((k) => {
                  const val = item[k] || 0;
                  const pct = (val / total) * 100;
                  if (pct <= 0) return null;
                  return (
                    <div
                      key={k}
                      style={{ width: `${pct}%`, backgroundColor: colors[k] }}
                      className="h-full first:rounded-l-full last:rounded-r-full transition-all hover:brightness-110"
                      title={`${k}: ${val}`}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-slate-200 dark:border-slate-800 text-[11px]">
        {keys.map((k) => (
          <div key={k} className="flex items-center gap-1.5 font-medium text-slate-600 dark:text-slate-400">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: colors[k] }} />
            <span>{k.replace('_', ' / ')}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * 5. Line & Area Chart (Smooth Curves)
 */
export const AreaLineChart = ({ data = [], height = 180, isArea = true, strokeColor = '#ea580c' }) => {
  const [hoveredIdx, setHoveredIdx] = useState(null);

  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-48 text-xs text-slate-400">No chart data available</div>;
  }

  const width = 500;
  const padding = 20;
  const innerWidth = width - padding * 2;
  const innerHeight = height - padding * 2;

  const maxVal = Math.max(...data.map((d) => d.value || d.movingAvg || d.count || 0), 1);
  const minVal = 0;

  const points = data.map((item, idx) => {
    const val = item.value !== undefined ? item.value : item.movingAvg !== undefined ? item.movingAvg : item.count || 0;
    const x = padding + (idx / Math.max(data.length - 1, 1)) * innerWidth;
    const y = padding + innerHeight - ((val - minVal) / (maxVal - minVal)) * innerHeight;
    return { x, y, val, label: item.date || item.day || item.label || `P${idx + 1}` };
  });

  // Construct SVG Path
  const linePath = points.reduce((acc, pt, idx) => {
    if (idx === 0) return `M ${pt.x} ${pt.y}`;
    const prev = points[idx - 1];
    const cx = (prev.x + pt.x) / 2;
    return `${acc} C ${cx} ${prev.y}, ${cx} ${pt.y}, ${pt.x} ${pt.y}`;
  }, '');

  const areaPath = `${linePath} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`;

  return (
    <div className="relative w-full" style={{ height: `${height}px` }}>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible">
        <defs>
          <linearGradient id={`areaGrad-${strokeColor}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.35" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => (
          <line
            key={i}
            x1={padding}
            y1={padding + innerHeight * ratio}
            x2={width - padding}
            y2={padding + innerHeight * ratio}
            stroke="currentColor"
            className="text-slate-200 dark:text-slate-800"
            strokeDasharray="4 4"
          />
        ))}

        {/* Area Fill */}
        {isArea && <path d={areaPath} fill={`url(#areaGrad-${strokeColor})`} />}

        {/* Smooth Line */}
        <path d={linePath} fill="none" stroke={strokeColor} strokeWidth="3" strokeLinecap="round" />

        {/* Point Markers */}
        {points.map((pt, idx) => (
          <circle
            key={idx}
            cx={pt.x}
            cy={pt.y}
            r={hoveredIdx === idx ? 6 : 4}
            fill={hoveredIdx === idx ? '#fff' : strokeColor}
            stroke={strokeColor}
            strokeWidth="2"
            className="transition-all cursor-pointer"
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
          />
        ))}
      </svg>

      {/* Interactive Tooltip Overlay */}
      {hoveredIdx !== null && (
        <div
          className="absolute pointer-events-none bg-[#0b0f17] text-white px-2.5 py-1 rounded-lg text-xs font-mono font-bold shadow-xl border border-white/20 -translate-x-1/2 -translate-y-full"
          style={{
            left: `${(points[hoveredIdx].x / width) * 100}%`,
            top: `${(points[hoveredIdx].y / height) * 100}%`,
          }}
        >
          {points[hoveredIdx].label}: {points[hoveredIdx].val}
        </div>
      )}
    </div>
  );
};

/**
 * 6. Multi-Line Chart (e.g. Critical vs Severe vs Moderate over time)
 */
export const MultiLineChart = ({ data = [], height = 200 }) => {
  const [hoveredIdx, setHoveredIdx] = useState(null);

  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-48 text-xs text-slate-400">No chart data available</div>;
  }

  const width = 500;
  const padding = 24;
  const innerWidth = width - padding * 2;
  const innerHeight = height - padding * 2;

  const series = [
    { key: 'Critical', label: 'Critical', color: '#dc2626' },
    { key: 'Severe', label: 'Severe', color: '#ea580c' },
    { key: 'Moderate', label: 'Moderate', color: '#f59e0b' },
  ].filter((s) => data.some((d) => d[s.key] !== undefined));

  let maxVal = 1;
  data.forEach((d) => {
    series.forEach((s) => {
      if (d[s.key] > maxVal) maxVal = d[s.key];
    });
  });

  return (
    <div className="w-full space-y-2">
      <div className="relative w-full" style={{ height: `${height}px` }}>
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible">
          {/* Grid lines */}
          {[0, 0.33, 0.66, 1].map((ratio, i) => (
            <line
              key={i}
              x1={padding}
              y1={padding + innerHeight * ratio}
              x2={width - padding}
              y2={padding + innerHeight * ratio}
              stroke="currentColor"
              className="text-slate-200 dark:text-slate-800"
              strokeDasharray="4 4"
            />
          ))}

          {series.map((s) => {
            const pts = data.map((d, idx) => {
              const val = d[s.key] || 0;
              const x = padding + (idx / Math.max(data.length - 1, 1)) * innerWidth;
              const y = padding + innerHeight - (val / maxVal) * innerHeight;
              return { x, y, val };
            });

            const pathStr = pts.reduce((acc, pt, idx) => {
              if (idx === 0) return `M ${pt.x} ${pt.y}`;
              const prev = pts[idx - 1];
              const cx = (prev.x + pt.x) / 2;
              return `${acc} C ${cx} ${prev.y}, ${cx} ${pt.y}, ${pt.x} ${pt.y}`;
            }, '');

            return (
              <g key={s.key}>
                <path d={pathStr} fill="none" stroke={s.color} strokeWidth="2.5" strokeLinecap="round" />
                {pts.map((p, i) => (
                  <circle
                    key={i}
                    cx={p.x}
                    cy={p.y}
                    r={hoveredIdx === i ? 5 : 3.5}
                    fill="#fff"
                    stroke={s.color}
                    strokeWidth="2"
                    className="cursor-pointer"
                    onMouseEnter={() => setHoveredIdx(i)}
                    onMouseLeave={() => setHoveredIdx(null)}
                  />
                ))}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend & X Axis */}
      <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          {series.map((s) => (
            <div key={s.key} className="flex items-center gap-1.5 text-[11px] font-medium text-slate-600 dark:text-slate-400">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: s.color }} />
              <span>{s.label}</span>
            </div>
          ))}
        </div>
        <div className="flex gap-4 text-[10px] font-mono text-slate-400">
          {data.map((d, i) => (
            <span key={i}>{d.period || `W${i + 1}`}</span>
          ))}
        </div>
      </div>
    </div>
  );
};

/**
 * 7. Funnel / Step Pipeline Chart
 */
export const FunnelChart = ({ data = [] }) => {
  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-48 text-xs text-slate-400">No chart data available</div>;
  }

  const maxVal = data[0]?.count || 100;

  return (
    <div className="w-full space-y-2.5 py-2">
      {data.map((step, idx) => {
        const pct = Math.min(100, Math.max(12, (step.count / maxVal) * 100));
        const color = step.color || '#3b82f6';

        return (
          <div key={idx} className="group">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="font-bold text-slate-800 dark:text-slate-200 group-hover:text-orange-500 transition-colors">
                {step.stage}
              </span>
              <div className="flex items-center gap-2 font-mono">
                <span className="font-bold text-slate-900 dark:text-white">{step.count.toLocaleString('en-IN')}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-white/10 text-slate-500 dark:text-slate-300">
                  {step.percentage}%
                </span>
              </div>
            </div>
            <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-xl h-5 overflow-hidden p-0.5 border border-slate-200/80 dark:border-white/5">
              <div
                className="h-full rounded-lg transition-all duration-700 ease-out shadow-xs flex items-center justify-end px-2 text-[10px] font-bold text-white"
                style={{
                  width: `${pct}%`,
                  backgroundColor: color,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

/**
 * 8. Radar / Component Weight Spider Chart
 */
export const RadarSpiderChart = ({ data = [], size = 220 }) => {
  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-48 text-xs text-slate-400">No chart data available</div>;
  }

  const center = size / 2;
  const radius = size * 0.38;
  const totalSides = data.length;

  const getCoordinates = (index, value, maxVal = 5.0) => {
    const angle = (Math.PI * 2 * index) / totalSides - Math.PI / 2;
    const r = (value / maxVal) * radius;
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    };
  };

  const polygonPoints = data.map((d, i) => getCoordinates(i, d.weight || 3, d.maxWeight || 5.0));
  const polygonPath = polygonPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';

  return (
    <div className="flex flex-col items-center justify-center py-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="overflow-visible">
          {/* Background web rings */}
          {[0.25, 0.5, 0.75, 1].map((scale, i) => {
            const ringPoints = data.map((_, idx) => getCoordinates(idx, 5.0 * scale, 5.0));
            const ringPath = ringPoints.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';
            return (
              <path
                key={i}
                d={ringPath}
                fill="none"
                stroke="currentColor"
                className="text-slate-200 dark:text-slate-800"
                strokeWidth="1"
              />
            );
          })}

          {/* Spokes */}
          {data.map((_, i) => {
            const end = getCoordinates(i, 5.0, 5.0);
            return (
              <line
                key={i}
                x1={center}
                y1={center}
                x2={end.x}
                y2={end.y}
                stroke="currentColor"
                className="text-slate-200 dark:text-slate-800"
                strokeWidth="1"
              />
            );
          })}

          {/* Filled radar area */}
          <path d={polygonPath} fill="#ea580c" fillOpacity="0.3" stroke="#ea580c" strokeWidth="2.5" />

          {/* Points */}
          {polygonPoints.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r="4" fill="#fff" stroke="#ea580c" strokeWidth="2" />
          ))}
        </svg>
      </div>

      {/* Feature Labels */}
      <div className="grid grid-cols-2 gap-2 mt-2 w-full text-[11px]">
        {data.map((item, idx) => (
          <div key={idx} className="flex items-center justify-between p-1.5 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/60 dark:border-white/5">
            <span className="text-slate-600 dark:text-slate-300 truncate">{item.feature}</span>
            <span className="font-mono font-bold text-orange-600 dark:text-orange-400">+{item.weight}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * 9. Delta / Velocity Bar Chart (Positives vs Negatives)
 */
export const DeltaBarChart = ({ data = [], height = 180 }) => {
  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-48 text-xs text-slate-400">No chart data available</div>;
  }

  const maxAbs = Math.max(...data.map((d) => Math.abs(d.delta || 0)), 1);

  return (
    <div className="w-full" style={{ height: `${height}px` }}>
      <div className="flex items-center justify-between gap-2 h-[calc(100%-28px)] relative px-2">
        {/* Center Zero Axis */}
        <div className="absolute top-1/2 left-0 right-0 h-px bg-slate-300 dark:bg-slate-700 z-10" />

        {data.map((item, idx) => {
          const delta = item.delta || 0;
          const isPositive = delta >= 0;
          const heightPct = Math.min(48, Math.max(8, (Math.abs(delta) / maxAbs) * 48));

          return (
            <div key={idx} className="flex-1 flex flex-col items-center h-full justify-center group cursor-pointer">
              <div className="h-1/2 flex items-end w-full justify-center">
                {isPositive && (
                  <div
                    className="w-full max-w-[28px] bg-emerald-500 rounded-t-md transition-all group-hover:brightness-110 shadow-xs"
                    style={{ height: `${heightPct * 2}%` }}
                    title={`+${delta}%`}
                  />
                )}
              </div>
              <div className="h-1/2 flex items-start w-full justify-center">
                {!isPositive && (
                  <div
                    className="w-full max-w-[28px] bg-rose-500 rounded-b-md transition-all group-hover:brightness-110 shadow-xs"
                    style={{ height: `${heightPct * 2}%` }}
                    title={`${delta}%`}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Day Labels */}
      <div className="flex justify-between items-center px-2 pt-2 border-t border-slate-200 dark:border-slate-800 text-[10px] font-mono text-slate-500">
        {data.map((item, idx) => (
          <div key={idx} className="flex-1 text-center truncate">
            {item.day}
          </div>
        ))}
      </div>
    </div>
  );
};
