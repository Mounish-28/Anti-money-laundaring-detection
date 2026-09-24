import React, { useMemo } from 'react';
import { Layers, Network, FileText } from 'lucide-react';
import { useInvestigation } from '../../context/InvestigationContext';
import { CaseTriageTable } from '../queue/CaseTriageTable';
import { QueueSearch } from '../queue/QueueSearch';
import { RailFilterPills } from '../queue/RailFilterPills';
import { EntityLinkGraph } from '../graph/EntityLinkGraph';
import { ExplainabilityDeck } from '../dossier/ExplainabilityDeck';
import { EntityProfileCard } from '../dossier/EntityProfileCard';
import { SarNarrativeEditor } from '../dossier/SarNarrativeEditor';
import { SarExportActions } from '../dossier/SarExportActions';

export function WorkbenchLayout() {
  const { cases, activeCase, activeCaseId, filters } = useInvestigation();

  // Compute matching open case count based on active filters
  const matchingCount = useMemo(() => {
    if (!Array.isArray(cases)) return 0;
    return cases.filter((item) => {
      if (filters.search && filters.search.trim()) {
        const query = filters.search.trim().toLowerCase();
        const matchesId = String(item.id || '').toLowerCase().includes(query);
        const matchesSuspect = String(item.suspectEntity || '').toLowerCase().includes(query);
        const matchesTypology = String(item.typology || '').toLowerCase().includes(query);
        if (!matchesId && !matchesSuspect && !matchesTypology) return false;
      }
      if (filters.rail && filters.rail !== 'ALL' && item.rail !== filters.rail) return false;
      if (
        filters.riskTier &&
        filters.riskTier !== 'ALL' &&
        String(item.riskTier).toUpperCase() !== String(filters.riskTier).toUpperCase()
      ) {
        return false;
      }
      return true;
    }).length;
  }, [cases, filters.search, filters.rail, filters.riskTier]);

  const formattedVolume = useMemo(() => {
    if (!activeCase) return '₹0';
    if (activeCase.currency === 'BTC' || activeCase.rail === 'BTC') {
      return `${activeCase.amount} BTC`;
    }
    return `₹${Number(activeCase.amount || 0).toLocaleString('en-IN')}`;
  }, [activeCase]);

  return (
    <div className="h-[calc(100vh-49px)] flex flex-col lg:flex-row overflow-hidden bg-surface-950 text-slate-100">
      {/* ======================================================== */}
      {/* PANE 1: Left Pane (25% / min-w-[320px]): CASE QUEUE      */}
      {/* ======================================================== */}
      <section
        aria-label="Case Queue"
        className="w-full lg:w-1/4 lg:min-w-[320px] lg:max-w-[400px] border-b lg:border-b-0 lg:border-r border-slate-800/80 flex flex-col bg-surface-900/40 shrink-0 overflow-hidden"
      >
        {/* Pane 1 Header with dynamic count */}
        <div className="p-3 border-b border-slate-800/80 flex items-center justify-between bg-surface-950/60 shrink-0 select-none">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Layers className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <h2 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase">
              ACTIVE QUEUE ({matchingCount})
            </h2>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
            {cases.length} TOTAL
          </span>
        </div>

        {/* Filter Controls */}
        <div className="p-2.5 border-b border-slate-800/60 space-y-2 shrink-0 bg-surface-950/30">
          <QueueSearch />
          <RailFilterPills />
        </div>

        {/* Case Triage List (Scrollable) */}
        <div className="flex-1 overflow-y-auto">
          <CaseTriageTable />
        </div>
      </section>

      {/* ======================================================== */}
      {/* PANE 2: Center Pane (50% / flex-1): ENTITY LINK GRAPH    */}
      {/* ======================================================== */}
      <section
        aria-label="Forensic Entity Link Graph"
        className="flex-1 flex flex-col bg-surface-950 overflow-hidden relative"
      >
        {/* Pane 2 Sub-Header with telemetry metrics */}
        <div className="p-2.5 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-2 bg-surface-950/80 backdrop-blur-sm shrink-0 z-10 select-none">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Network className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase">
                FORENSIC ENTITY LINK GRAPH
              </h2>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800/40">
                CASE #{activeCaseId}
              </span>
            </div>
          </div>

          {/* Sub-Header Metrics: Nodes, Hops, Volume */}
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
              NODES: <strong className="text-cyan-300">{activeCase?.clusterSize || 6}</strong>
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
              HOPS: <strong className="text-amber-300">{activeCase?.hopCount || 4}</strong>
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
              VOLUME: <strong className="text-emerald-400">{formattedVolume}</strong>
            </span>
          </div>
        </div>

        {/* Center Interactive Graph Canvas & Integrated Controls/Timeline */}
        <div className="flex-1 flex flex-col relative overflow-hidden">
          <EntityLinkGraph />
        </div>
      </section>

      {/* ======================================================== */}
      {/* PANE 3: Right Pane (25% / min-w-[340px]): SAR DOSSIER    */}
      {/* ======================================================== */}
      <section
        aria-label="Explainability & SAR Dossier"
        className="w-full lg:w-1/4 lg:min-w-[340px] lg:max-w-[420px] border-t lg:border-t-0 lg:border-l border-slate-800/80 flex flex-col bg-surface-900/40 shrink-0 overflow-hidden"
      >
        {/* Pane 3 Header */}
        <div className="p-3 border-b border-slate-800/80 flex items-center justify-between bg-surface-950/60 shrink-0 select-none">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <FileText className="w-3.5 h-3.5 text-rose-400" />
            </div>
            <h2 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase">
              EXPLAINABILITY & SAR DOSSIER
            </h2>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800/40">
            PMLA 2002
          </span>
        </div>

        {/* Dossier Content Stack */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <ExplainabilityDeck />
          <EntityProfileCard />
          <SarNarrativeEditor key={activeCase?.id || 'none'} />
          <SarExportActions />
        </div>
      </section>
    </div>
  );
}

export default WorkbenchLayout;
