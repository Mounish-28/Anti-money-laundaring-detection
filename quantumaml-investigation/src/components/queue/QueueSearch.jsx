import React from 'react';
import { Search, X } from 'lucide-react';
import { useInvestigation } from '../../context/InvestigationContext';

export function QueueSearch() {
  const { filters, updateFilters } = useInvestigation();
  const searchVal = filters?.search || '';

  return (
    <div className="relative flex items-center w-full">
      <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 pointer-events-none" />
      <input
        type="text"
        placeholder="Filter by Case, Suspect, or Typology..."
        value={searchVal}
        onChange={(e) => updateFilters('search', e.target.value)}
        className="w-full pl-8 pr-7 py-1.5 rounded-lg bg-surface-950/80 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 font-mono focus:outline-none focus:border-amber-500/50 transition-colors"
      />
      {searchVal && (
        <button
          onClick={() => updateFilters('search', '')}
          title="Clear search"
          className="absolute right-2 p-0.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}

export default QueueSearch;
