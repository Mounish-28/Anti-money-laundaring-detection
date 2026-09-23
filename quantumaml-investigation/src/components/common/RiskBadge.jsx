import React from 'react';

const TIER_STYLES = {
  CRITICAL: 'bg-rose-500/15 text-rose-300 border-rose-500/40 shadow-[0_0_12px_-2px_rgba(244,63,94,0.3)]',
  CRITICAL_SAR: 'bg-rose-500/15 text-rose-300 border-rose-500/40 shadow-[0_0_12px_-2px_rgba(244,63,94,0.3)]',
  HIGH: 'bg-amber-500/15 text-amber-300 border-amber-500/40 shadow-[0_0_12px_-2px_rgba(245,158,11,0.25)]',
  ELEVATED: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  MED: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40',
  MEDIUM: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40',
  LOW: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
};

export function RiskBadge({ tier = 'LOW', score = null, className = '' }) {
  const normalizedTier = String(tier || 'LOW').toUpperCase();
  const style = TIER_STYLES[normalizedTier] || TIER_STYLES.LOW;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold tracking-wider border uppercase ${style} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
      <span>{normalizedTier}</span>
      {score !== null && (
        <span className="opacity-80 font-normal">
          ({typeof score === 'number' ? (score > 1 ? (score / 100).toFixed(2) : score.toFixed(2)) : score})
        </span>
      )}
    </span>
  );
}

export default RiskBadge;
