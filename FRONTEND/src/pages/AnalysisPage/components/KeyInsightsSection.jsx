import React from 'react';
import { Lightbulb, AlertTriangle, CheckCircle2, TrendingUp, Sparkles } from 'lucide-react';

export const KeyInsightsSection = ({ keyFindings = [] }) => {
  if (!keyFindings || keyFindings.length === 0) return null;

  return (
    <section className="w-full bg-white dark:bg-[#101318] rounded-3xl p-6 sm:p-8 border border-slate-200/90 dark:border-white/10 shadow-lg mb-8 transition-all duration-300">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-2xl bg-orange-500/10 text-orange-600 dark:text-orange-400 flex items-center justify-center">
          <Lightbulb className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight font-sans">
            Key Analytical Findings
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Real-time deductive conclusions computed dynamically from the active filtered disaster dataset.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {keyFindings.map((finding) => (
          <div
            key={finding.id}
            className="p-5 rounded-2xl bg-slate-50 dark:bg-black/30 border border-slate-200/80 dark:border-white/5 flex flex-col justify-between space-y-3 hover:border-orange-500/30 transition-colors"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20">
                  {finding.badge}
                </span>
                <span className={`w-2 h-2 rounded-full ${
                  finding.severity === 'critical' ? 'bg-red-500' :
                  finding.severity === 'high' ? 'bg-orange-500' : 'bg-blue-500'
                }`} />
              </div>

              <h3 className="text-sm font-bold text-slate-900 dark:text-white leading-snug font-sans">
                {finding.title}
              </h3>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              {finding.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
};
