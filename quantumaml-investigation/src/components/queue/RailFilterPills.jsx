import React from 'react';
import { useInvestigation } from '../../context/InvestigationContext';

const RAILS = ['ALL', 'UPI', 'IMPS', 'BTC'];
const RISK_TIERS = ['ALL', 'CRITICAL', 'HIGH'];

export function RailFilterPills() {
  const { filters, updateFilters } = useInvestigation();
  const activeRail = filters?.rail || 'ALL';
  const activeRisk = filters?.riskTier || 'ALL';

  return (
    <div className="space-y-1.5 pt-0.5">
      {/* Rail Filter Row */}
      <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
        <span className="text-[10px] font-mono text-slate-500 uppercase mr-1 shrink-0">
          Rail:
        </span>
        {RAILS.map((rail) => {
          const isActive = activeRail === rail;
          return (
            <button
              key={rail}
              onClick={() => updateFilters('rail', rail)}
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider transition-all border ${
                isActive
                  ? 'bg-cyan-950/80 text-cyan-300 border-cyan-500/50 shadow-[0_0_10px_-2px_rgba(6,182,212,0.35)]'
                  : 'bg-surface-950/70 text-slate-400 hover:text-slate-200 border-slate-800'
              }`}
            >
              {rail}
            </button>
          );
        })}
      </div>

      {/* Risk Tier Toggle Row */}
      <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
        <span className="text-[10px] font-mono text-slate-500 uppercase mr-1 shrink-0">
          Risk:
        </span>
        {RISK_TIERS.map((tier) => {
          const isActive = activeRisk === tier;
          return (
            <button
              key={tier}
              onClick={() => updateFilters('riskTier', tier)}
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider transition-all border ${
                isActive
                  ? tier === 'CRITICAL'
                    ? 'bg-rose-950/80 text-rose-300 border-rose-500/60 shadow-[0_0_10px_-2px_rgba(244,63,94,0.4)]'
                    : tier === 'HIGH'
                    ? 'bg-amber-950/80 text-amber-300 border-amber-500/60 shadow-[0_0_10px_-2px_rgba(245,158,11,0.35)]'
                    : 'bg-slate-800 text-slate-200 border-slate-600'
                  : 'bg-surface-950/70 text-slate-400 hover:text-slate-200 border-slate-800'
              }`}
            >
              {tier}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default RailFilterPills;
