import React from 'react';
import { ShieldAlert, Lock } from 'lucide-react';
import { useInvestigation } from '../../context/InvestigationContext';

export function Header() {
  const { activeCaseId, activeCase, backendStatus, backendHealthy, checkHealthStatus } = useInvestigation();
  const caseTitle = activeCase?.typology || activeCase?.title || 'UPI Smurfing Cluster';

  const isConnected = backendHealthy || backendStatus === 'CONNECTED';

  return (
    <header className="h-[49px] border-b border-slate-800/80 bg-surface-950/95 backdrop-blur-md px-4 lg:px-6 flex items-center justify-between z-50 select-none">
      {/* Left: Brand & Status Icon */}
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono font-black text-xs sm:text-sm tracking-wider bg-gradient-to-r from-slate-100 via-amber-200 to-rose-300 bg-clip-text text-transparent">
            QUANTUM AML // FORENSIC INVESTIGATION ENCLAVE
          </span>
          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-semibold bg-slate-900 text-amber-400 border border-amber-500/20 hidden md:inline-block">
            v2.4-ISOLATED
          </span>
        </div>
      </div>

      {/* Center: Active Case Badge */}
      <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/90 border border-amber-500/30 font-mono text-xs shadow-[0_0_15px_-3px_rgba(245,158,11,0.2)]">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
        <span className="text-slate-400">Case #{activeCaseId}</span>
        <span className="text-amber-300 font-semibold">[{caseTitle}]</span>
      </div>

      {/* Right: Backend Status & Operator Tag */}
      <div className="flex items-center gap-3 font-mono text-xs">
        {/* Backend Status Badge with Real-Time State */}
        <button
          onClick={() => checkHealthStatus?.()}
          title="Click to manually refresh backend connection"
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] transition-all cursor-pointer ${
            isConnected
              ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300 hover:bg-emerald-950/80 shadow-[0_0_10px_-2px_rgba(16,185,129,0.3)]'
              : 'bg-amber-950/60 border-amber-500/40 text-amber-300 hover:bg-amber-950/80 shadow-[0_0_10px_-2px_rgba(245,158,11,0.3)]'
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${
              isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
            }`}
          />
          <span className="font-bold">
            {isConnected ? 'API: ONLINE :8000' : 'API: OFFLINE (FALLBACK MODE)'}
          </span>
        </button>

        {/* Operator Credentials */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/30 text-[11px] font-bold">
          <Lock className="w-3 h-3 text-amber-400" />
          <span>OFFICER: OP-441</span>
          <span className="text-amber-400/60 hidden xl:inline">[TIER-3 FORENSIC ACCESS]</span>
        </div>
      </div>
    </header>
  );
}

export default Header;
