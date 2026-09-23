import React from 'react';

export function Loader({ label = 'Loading forensic telemetry...', className = '' }) {
  return (
    <div className={`flex flex-col items-center justify-center p-6 space-y-3 ${className}`}>
      <div className="relative flex items-center justify-center">
        <div className="w-10 h-10 rounded-full border-2 border-slate-800 border-t-amber-400 border-r-cyan-400 animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80 animate-ping" />
        </div>
      </div>
      {label && (
        <span className="text-xs font-mono text-slate-400 animate-pulse tracking-wide">
          {label}
        </span>
      )}
    </div>
  );
}

export function SkeletonRow({ count = 3, className = '' }) {
  return (
    <div className={`space-y-2 animate-pulse ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-9 rounded-lg bg-slate-900/80 border border-slate-800/60"
        />
      ))}
    </div>
  );
}

export default Loader;
