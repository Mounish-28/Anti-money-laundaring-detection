import React, { useState, useEffect, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
} from '@tanstack/react-table';
import { Clock, AlertTriangle, RefreshCcw } from 'lucide-react';
import { useInvestigation } from '../../context/InvestigationContext';
import { RiskBadge } from '../common/RiskBadge';
import { Loader } from '../common/Loader';

// Dynamic SLA Countdown Timer component with 1s precision
function SlaCountdown({ deadline }) {
  const [timeLeft, setTimeLeft] = useState(() => calculateTimeLeft(deadline));

  function calculateTimeLeft(target) {
    const diff = new Date(target).getTime() - Date.now();
    if (diff <= 0) {
      return { expired: true, text: 'EXPIRED', isCritical: true };
    }
    const totalSecs = Math.floor(diff / 1000);
    const hours = Math.floor(totalSecs / 3600);
    const mins = Math.floor((totalSecs % 3600) / 60);
    const secs = totalSecs % 60;
    const isCritical = diff < 30 * 60 * 1000; // < 30 mins

    let text = '';
    if (hours > 0) {
      text = `${hours}h ${mins}m`;
    } else {
      text = `${mins}m ${secs < 10 ? '0' : ''}${secs}s`;
    }

    return { expired: false, text, isCritical };
  }

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft(deadline));
    }, 1000);
    return () => clearInterval(timer);
  }, [deadline]);

  if (timeLeft.isCritical) {
    return (
      <span className="flex items-center gap-1 font-mono text-[10px] font-bold text-rose-400 animate-pulse">
        <Clock className="w-3 h-3 text-rose-400" />
        <span>SLA: {timeLeft.text}</span>
      </span>
    );
  }

  return (
    <span className="flex items-center gap-1 font-mono text-[10px] font-semibold text-amber-400">
      <Clock className="w-3 h-3 text-amber-400/80" />
      <span>SLA: {timeLeft.text}</span>
    </span>
  );
}

// Format currency amounts appropriately
function formatAmount(amount, currency = 'INR', rail = 'UPI') {
  if (currency === 'BTC' || rail === 'BTC') {
    return `${Number(amount).toFixed(4)} BTC`;
  }
  return `₹${Number(amount).toLocaleString('en-IN', {
    maximumFractionDigits: 0,
  })}`;
}

export function CaseTriageTable() {
  const {
    cases,
    activeCaseId,
    selectCase,
    filters,
    resetFilters,
    isLoadingCases,
  } = useInvestigation();

  const [sorting, setSorting] = useState([{ id: 'riskScore', desc: true }]);

  // Filter dataset by search, rail, and riskTier
  const filteredData = useMemo(() => {
    if (!Array.isArray(cases)) return [];
    return cases.filter((item) => {
      // 1. Search Query filter (matches id, suspectEntity, typology)
      if (filters.search && filters.search.trim()) {
        const query = filters.search.trim().toLowerCase();
        const matchesId = String(item.id || '').toLowerCase().includes(query);
        const matchesSuspect = String(item.suspectEntity || '').toLowerCase().includes(query);
        const matchesTypology = String(item.typology || '').toLowerCase().includes(query);
        if (!matchesId && !matchesSuspect && !matchesTypology) {
          return false;
        }
      }

      // 2. Rail filter
      if (filters.rail && filters.rail !== 'ALL') {
        if (item.rail !== filters.rail) {
          return false;
        }
      }

      // 3. Risk Tier filter
      if (filters.riskTier && filters.riskTier !== 'ALL') {
        if (String(item.riskTier).toUpperCase() !== String(filters.riskTier).toUpperCase()) {
          return false;
        }
      }

      return true;
    });
  }, [cases, filters.search, filters.rail, filters.riskTier]);

  // TanStack Table Column Definitions
  const columns = useMemo(
    () => [
      {
        accessorKey: 'id',
        header: 'Case ID',
      },
      {
        accessorKey: 'rail',
        header: 'Rail',
      },
      {
        accessorKey: 'riskScore',
        header: 'Risk',
      },
      {
        accessorKey: 'amount',
        header: 'Amount',
      },
      {
        accessorKey: 'typology',
        header: 'Typology',
      },
      {
        accessorKey: 'slaDeadline',
        header: 'SLA',
      },
    ],
    []
  );

  const table = useReactTable({
    data: filteredData,
    columns,
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  if (isLoadingCases) {
    return <Loader label="Loading triage feed..." className="h-64" />;
  }

  if (filteredData.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-center space-y-3 h-64 text-slate-400">
        <div className="p-3 rounded-full bg-slate-900 border border-slate-800 text-slate-500">
          <AlertTriangle className="w-5 h-5 text-amber-500/70" />
        </div>
        <div>
          <p className="text-xs font-mono font-bold text-slate-300">
            No Matching Cases Found
          </p>
          <p className="text-[11px] font-mono text-slate-500 mt-0.5">
            Try adjusting your search criteria or rail/risk filters.
          </p>
        </div>
        <button
          onClick={resetFilters}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-cyan-400 border border-slate-800 text-xs font-mono font-semibold transition-colors"
        >
          <RefreshCcw className="w-3 h-3" />
          <span>Reset All Filters</span>
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col divide-y divide-slate-800/60 select-none">
      {table.getRowModel().rows.map((row) => {
        const item = row.original;
        const isSelected = item.id === activeCaseId;

        return (
          <div
            key={item.id}
            onClick={() => selectCase(item)}
            className={`p-3 transition-all cursor-pointer border-l-2 text-left space-y-1.5 group ${
              isSelected
                ? 'bg-surface-850/90 border-rose-500 shadow-md shadow-rose-950/20'
                : 'bg-surface-950/40 hover:bg-surface-900/60 border-transparent hover:border-slate-700'
            }`}
          >
            {/* Primary Row Line: Case ID + Rail Tag + Risk Badge */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs font-mono font-bold tracking-tight ${
                    isSelected ? 'text-rose-300' : 'text-slate-100 group-hover:text-cyan-300'
                  }`}
                >
                  {item.id}
                </span>

                <span
                  className={`px-1.5 py-0.2 rounded text-[10px] font-mono font-bold ${
                    item.rail === 'BTC'
                      ? 'bg-amber-500/10 text-amber-300 border border-amber-500/30'
                      : item.rail === 'IMPS'
                      ? 'bg-purple-500/10 text-purple-300 border border-purple-500/30'
                      : 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/30'
                  }`}
                >
                  {item.rail}
                </span>
              </div>

              <RiskBadge tier={item.riskTier} score={item.riskScore} />
            </div>

            {/* Secondary Row Line: Typology description + Formatted Amount */}
            <div className="flex items-center justify-between text-xs gap-2">
              <span
                className="font-medium text-slate-300 truncate text-[11px] max-w-[190px]"
                title={item.typology}
              >
                {item.typology}
              </span>
              <span className="font-mono font-bold text-slate-100 text-[11px] shrink-0">
                {formatAmount(item.amount, item.currency, item.rail)}
              </span>
            </div>

            {/* Tertiary Row Line: Suspect Entity snippet + Dynamic SLA Countdown Timer */}
            <div className="flex items-center justify-between text-[10px] font-mono pt-0.5">
              <span
                className="text-slate-500 truncate max-w-[160px] group-hover:text-slate-400 transition-colors"
                title={item.suspectEntity}
              >
                {item.suspectEntity}
              </span>
              <SlaCountdown deadline={item.slaDeadline} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default CaseTriageTable;
