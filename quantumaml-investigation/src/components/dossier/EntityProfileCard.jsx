import React from 'react';
import {
  UserCheck,
  ShieldAlert,
  Bitcoin,
  Building,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Fingerprint,
} from 'lucide-react';
import { useInvestigation } from '../../context/InvestigationContext';

export function EntityProfileCard() {
  const { activeCase, selectedNodeData, setSelectedNodeId, setSelectedNodeData } = useInvestigation();

  if (!activeCase) {
    return (
      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono text-slate-500">
        No active case selected
      </div>
    );
  }

  const isCrypto = activeCase.currency === 'BTC' || activeCase.rail === 'BTC';

  // Format monetary volume
  const formattedVolume = isCrypto
    ? `${activeCase.amount} BTC`
    : `₹${Number(activeCase.amount || 0).toLocaleString('en-IN')}`;

  // Mode 1: Selected Graph Node Inspection
  if (selectedNodeData) {
    const isNodeCritical = selectedNodeData.riskTier === 'CRITICAL';
    const isNodeHigh = selectedNodeData.riskTier === 'HIGH';

    return (
      <div className="p-3.5 rounded-xl bg-slate-900/90 border border-cyan-500/40 text-xs font-mono space-y-3 shadow-lg relative overflow-hidden animate-fade-in">
        <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl pointer-events-none" />

        {/* Node Inspection Header with Reset Button */}
        <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
          <div className="flex items-center gap-1.5 text-cyan-400 font-bold">
            <Fingerprint className="w-4 h-4 text-cyan-400" />
            <span className="uppercase text-[11px] tracking-wider">Node Topology Inspection</span>
          </div>
          <button
            onClick={() => {
              setSelectedNodeId(null);
              setSelectedNodeData(null);
            }}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-slate-300 font-medium transition-colors"
            title="Return to primary suspect profile"
          >
            <RotateCcw className="w-2.5 h-2.5 text-cyan-400" />
            <span>Reset Target</span>
          </button>
        </div>

        {/* Node Identity & Risk Tier */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Entity Identity</span>
            <span
              className={`px-1.5 py-0.2 rounded text-[10px] font-bold border ${
                isNodeCritical
                  ? 'bg-rose-950/80 text-rose-300 border-rose-800/60'
                  : isNodeHigh
                  ? 'bg-amber-950/80 text-amber-300 border-amber-800/60'
                  : 'bg-cyan-950/80 text-cyan-300 border-cyan-800/60'
              }`}
            >
              {selectedNodeData.riskTier || 'MEDIUM'}
            </span>
          </div>
          <div className="text-[12px] font-bold text-white break-all bg-slate-950/80 p-2 rounded-lg border border-slate-800/80">
            {selectedNodeData.label || selectedNodeData.id}
          </div>
        </div>

        {/* Node Attributes Grid */}
        <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
          <div className="p-2 rounded bg-slate-950/60 border border-slate-800/60">
            <span className="text-slate-500 text-[10px] block">Role / Topology</span>
            <strong className="text-cyan-300">{selectedNodeData.type || 'INTERMEDIARY'}</strong>
          </div>
          <div className="p-2 rounded bg-slate-950/60 border border-slate-800/60">
            <span className="text-slate-500 text-[10px] block">Graph Degree</span>
            <strong className="text-amber-300">{selectedNodeData.degree ?? 3} Connections</strong>
          </div>
          <div className="p-2 rounded bg-slate-950/60 border border-slate-800/60 col-span-2">
            <span className="text-slate-500 text-[10px] block">Observed Balance Flow</span>
            <strong className="text-emerald-400 text-xs">
              {selectedNodeData.balance || formattedVolume}
            </strong>
          </div>
        </div>
      </div>
    );
  }

  // Mode 2: Primary Subject Entity Profile (from activeCase)
  const suspectEntity = activeCase.suspectEntity || 'Unknown Suspect';
  const panMatch = suspectEntity.match(/PAN:\s*([A-Z0-9]+)/i);
  const detectedPan = panMatch ? panMatch[1] : null;

  return (
    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono space-y-3 shadow-md relative overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <div className="flex items-center gap-2 text-cyan-400 font-bold">
          <UserCheck className="w-3.5 h-3.5 text-cyan-400" />
          <span className="uppercase text-[11px] tracking-wider">Primary Subject Profile</span>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950/70 text-rose-300 border border-rose-800/50">
          {activeCase.riskTier || 'CRITICAL'}
        </span>
      </div>

      {/* Target Identity */}
      <div className="space-y-1">
        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Subject Identity / Counterparty</span>
        <div className="text-[11px] font-semibold text-white break-all bg-slate-950/80 p-2 rounded-lg border border-slate-800/80">
          {suspectEntity}
        </div>
      </div>

      {/* KYC / Compliance Identifier Badges */}
      <div className="flex flex-wrap gap-1.5 pt-0.5">
        {detectedPan ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 text-[10px] font-semibold">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            PAN: {detectedPan}
          </span>
        ) : isCrypto ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800/60 text-[10px] font-semibold">
            <Bitcoin className="w-3 h-3 text-purple-400" />
            Unhosted VDA Cluster
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800/60 text-[10px] font-semibold">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            Unlinked PAN (Structuring Evasion)
          </span>
        )}

        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px]">
          {isCrypto ? <Bitcoin className="w-3 h-3 text-amber-400" /> : <Building className="w-3 h-3 text-cyan-400" />}
          Rail: {activeCase.rail || 'UPI'}
        </span>
      </div>

      {/* Financial Exposure Metrics */}
      <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
        <div className="p-2 rounded bg-slate-950/60 border border-slate-800/60">
          <span className="text-slate-500 text-[10px] block">Aggregated Exposure</span>
          <strong className="text-emerald-400 text-xs">{formattedVolume}</strong>
        </div>
        <div className="p-2 rounded bg-slate-950/60 border border-slate-800/60">
          <span className="text-slate-500 text-[10px] block">Cluster Topography</span>
          <strong className="text-amber-300 text-xs">
            {activeCase.clusterSize || 6} Nodes · {activeCase.hopCount || 4} Hops
          </strong>
        </div>
      </div>

      {/* KYC Risk Status Footer */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400">
        <span className="flex items-center gap-1">
          <ShieldAlert className="w-3 h-3 text-rose-400" />
          KYC Compliance:
        </span>
        <strong className="text-rose-400 uppercase font-semibold">
          {isCrypto ? 'High-Entropy Darknet Wasabi' : 'Flagged Mule Shell Entity'}
        </strong>
      </div>
    </div>
  );
}

export default EntityProfileCard;
