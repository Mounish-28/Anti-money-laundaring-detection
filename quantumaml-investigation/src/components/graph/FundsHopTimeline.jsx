import React, { useState } from 'react';
import {
  Clock,
  Zap,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  AlertTriangle,
} from 'lucide-react';

export function FundsHopTimeline({ timeline = [], summary = {} }) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (!timeline || timeline.length === 0) {
    return null;
  }

  return (
    <div className="border-t border-slate-800/80 bg-surface-950/95 backdrop-blur-md select-none shrink-0 z-20">
      {/* Drawer Header Toggle Bar */}
      <div
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-slate-900/40 transition-colors border-b border-slate-900"
      >
        <div className="flex items-center gap-2 text-xs font-mono">
          <div className="p-1 rounded bg-amber-500/10 text-amber-400">
            <Zap className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
          </div>
          <span className="font-bold text-slate-200 uppercase tracking-wide">
            FUNDS HOP VELOCITY TIMELINE
          </span>
          <span className="text-slate-500 text-[11px] hidden sm:inline">
            ({timeline.length} Monitored Propagation Steps)
          </span>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          {summary?.anomalousHopCount > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-800/60 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 text-rose-400" />
              {summary.anomalousHopCount} RAPID TRANSITS (&lt; 120s)
            </span>
          )}

          <div className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200">
            <span>{isCollapsed ? 'Expand' : 'Collapse'}</span>
            {isCollapsed ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </div>
        </div>
      </div>

      {/* Horizontal Sequence of Hops */}
      {!isCollapsed && (
        <div className="p-3 overflow-x-auto flex items-center gap-3 no-scrollbar max-w-full">
          {timeline.map((hop, idx) => {
            const isRapid = hop.latency < 120;

            return (
              <React.Fragment key={idx}>
                {/* Hop Card */}
                <div
                  className={`min-w-[210px] p-2.5 rounded-xl border text-xs font-mono transition-all shrink-0 ${
                    isRapid
                      ? 'bg-rose-950/20 border-rose-500/40 shadow-[0_0_12px_-3px_rgba(244,63,94,0.2)]'
                      : 'bg-surface-900/60 border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-bold text-slate-400">
                      HOP #{hop.hopIndex || idx + 1}
                    </span>
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-800 text-cyan-300 border border-slate-700">
                      {hop.rail || 'UPI'}
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-200 font-semibold truncate mb-1">
                    {hop.from} &rarr; {hop.to}
                  </div>

                  <div className="flex items-center justify-between text-[10px]">
                    <span className="font-bold text-slate-300">
                      {hop.amount}
                    </span>

                    <span
                      className={`flex items-center gap-0.5 font-bold ${
                        isRapid ? 'text-rose-400 animate-pulse' : 'text-slate-400'
                      }`}
                    >
                      <Clock className="w-3 h-3" />
                      <span>{hop.latency}s delay</span>
                    </span>
                  </div>

                  {isRapid && (
                    <div className="mt-1 pt-1 border-t border-rose-900/40 text-[9px] text-rose-300 font-semibold flex items-center gap-1">
                      <Zap className="w-2.5 h-2.5" />
                      <span>⚡ RAPID HOPPING DETECTED</span>
                    </div>
                  )}
                </div>

                {/* Arrow between hops */}
                {idx < timeline.length - 1 && (
                  <ArrowRight className="w-4 h-4 text-slate-600 shrink-0" />
                )}
              </React.Fragment>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default FundsHopTimeline;
