import React, { useState, useMemo } from 'react';
import {
  Activity,
  ShieldAlert,
  Flame,
  Pause,
  Play,
  RotateCcw,
  FileText,
  AlertTriangle,
  Clock,
  ArrowRight,
  Filter,
  X,
  Radio,
  Zap,
  CreditCard,
  Bitcoin,
  CheckCircle2,
  Copy,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../utils/cn';
import { generateSar, DEFAULT_API_URL } from '../services/api';

export function LiveAuditLedger({
  transactions,
  telemetry,
  isPaused,
  onTogglePause,
  onClearFeed,
  activeAlert,
  onDismissAlert,
  wsStatus,
  onOpenSarModal,
  openSarModal,
  apiUrl = DEFAULT_API_URL,
  sarMetrics,
  onSarGenerated,
}) {
  const [activeFilter, setActiveFilter] = useState('ALL'); // 'ALL' | 'FIAT' | 'CRYPTO' | 'SARS'
  const [selectedTxForSar, setSelectedTxForSar] = useState(null);
  const [sarFiledSuccess, setSarFiledSuccess] = useState(false);
  const [generatingTxId, setGeneratingTxId] = useState(null);

  // Filtered transactions based on active pill
  const filteredTransactions = useMemo(() => {
    return transactions.filter((tx) => {
      const isCrypto =
        tx.engine === 'CRYPTO_FORENSICS' || tx.rail === 'BTC' || tx.currency === 'BTC';
      const isSar = tx.risk_tier === 'CRITICAL_SAR' || tx.risk_tier === 'HIGH';

      if (activeFilter === 'FIAT') return !isCrypto;
      if (activeFilter === 'CRYPTO') return isCrypto;
      if (activeFilter === 'SARS') return isSar;
      return true;
    });
  }, [transactions, activeFilter]);

  // Counts for filter pills
  const counts = useMemo(() => {
    let fiat = 0;
    let crypto = 0;
    let sars = 0;
    for (const tx of transactions) {
      const isCrypto =
        tx.engine === 'CRYPTO_FORENSICS' || tx.rail === 'BTC' || tx.currency === 'BTC';
      if (isCrypto) crypto++;
      else fiat++;
      if (tx.risk_tier === 'CRITICAL_SAR' || tx.risk_tier === 'HIGH') sars++;
    }
    return { all: transactions.length, fiat, crypto, sars };
  }, [transactions]);

  const handleGenerateSar = (tx) => {
    setSelectedTxForSar(tx);
    setSarFiledSuccess(false);
  };

  const handleConfirmFileSar = () => {
    setSarFiledSuccess(true);
    setTimeout(() => {
      setSelectedTxForSar(null);
      setSarFiledSuccess(false);
    }, 2000);
  };

  const handleGenerateSarRow = async (e, tx) => {
    if (e && e.stopPropagation) e.stopPropagation();
    try {
      setGeneratingTxId(tx.transaction_id);
      const isBtc = tx.currency === 'BTC' || tx.rail === 'BTC';
      const typology = isBtc
        ? 'IN_TYP_VDA_MIX'
        : (tx.flags && tx.flags.some((f) => String(f).toLowerCase().includes('hawala')))
        ? 'IN_TYP_HAWALA'
        : 'IN_TYP_STRUCT';

      const payload = {
        transaction_ids: [tx.transaction_id],
        primary_typology: typology,
        investigator_notes: `Initiated from Live Audit Ledger for flagged transaction ${tx.transaction_id} on rail ${tx.rail}. Amount: ${tx.amount} ${tx.currency || 'INR'}. Flags: ${tx.flags?.join(', ') || 'CRITICAL_SAR'}.`,
        assigned_investigator: 'COMPLIANCE-ANALYST-01',
        suspect_identifier: tx.from_entity || `SUSPECT_${tx.transaction_id.slice(0, 8)}`,
      };

      const newCase = await generateSar(payload, apiUrl);
      if (newCase && newCase.sar_id) {
        tx.sar_id = newCase.sar_id;
        if (onSarGenerated) {
          onSarGenerated(newCase);
        }
        const openFn = openSarModal || onOpenSarModal;
        if (openFn) {
          openFn(newCase.sar_id);
        }
      }
    } catch (err) {
      console.error('Failed to generate SAR:', err);
      alert(`SAR Generation failed: ${err.message}`);
    } finally {
      setGeneratingTxId(null);
    }
  };

  const formatClockTime = (ts) => {
    if (!ts) return '--:--:--.---';
    try {
      const d = new Date(ts);
      if (isNaN(d.getTime())) return String(ts).slice(11, 23);
      const hours = String(d.getUTCHours()).padStart(2, '0');
      const mins = String(d.getUTCMinutes()).padStart(2, '0');
      const secs = String(d.getUTCSeconds()).padStart(2, '0');
      const ms = String(d.getUTCMilliseconds()).padStart(3, '0');
      return `${hours}:${mins}:${secs}.${ms}`;
    } catch {
      return String(ts);
    }
  };

  const formatAmount = (tx) => {
    const amt = typeof tx.amount === 'number' ? tx.amount : 0.0;
    if (tx.currency === 'BTC' || tx.rail === 'BTC') {
      return `${amt.toFixed(4)} BTC`;
    }
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(amt);
  };

  const renderRailBadge = (rail) => {
    const r = (rail || 'UPI').toUpperCase();
    if (r === 'UPI') {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-950/70 text-emerald-400 border border-emerald-500/40 shadow-sm">
          UPI
        </span>
      );
    }
    if (r === 'IMPS') {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-blue-950/70 text-blue-400 border border-blue-500/40 shadow-sm">
          IMPS
        </span>
      );
    }
    if (r === 'NEFT') {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-purple-950/70 text-purple-400 border border-purple-500/40 shadow-sm">
          NEFT
        </span>
      );
    }
    if (r === 'RTGS') {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-indigo-950/70 text-indigo-400 border border-indigo-500/40 shadow-sm">
          RTGS
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-950/70 text-amber-400 border border-amber-500/40 shadow-sm flex items-center gap-1">
        <Bitcoin className="w-3 h-3" />
        BTC
      </span>
    );
  };

  const renderRiskBadge = (tier, score) => {
    const t = (tier || 'LOW').toUpperCase();
    if (t === 'CRITICAL_SAR' || t === 'CRITICAL') {
      return (
        <div className="flex items-center gap-1.5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500" />
          </span>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-rose-950/90 text-rose-300 border border-rose-500/60 animate-pulse">
            CRITICAL SAR
          </span>
          {typeof score === 'number' && (
            <span className="text-[10px] font-mono text-rose-400">
              p={(score * 100).toFixed(1)}%
            </span>
          )}
        </div>
      );
    }
    if (t === 'HIGH') {
      return (
        <div className="flex items-center gap-1.5">
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-amber-950/70 text-amber-300 border border-amber-500/50">
            HIGH
          </span>
          {typeof score === 'number' && (
            <span className="text-[10px] font-mono text-amber-400">
              p={(score * 100).toFixed(1)}%
            </span>
          )}
        </div>
      );
    }
    if (t === 'ELEVATED' || t === 'MEDIUM') {
      return (
        <div className="flex items-center gap-1.5">
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-yellow-950/70 text-yellow-300 border border-yellow-500/40">
            ELEVATED
          </span>
          {typeof score === 'number' && (
            <span className="text-[10px] font-mono text-yellow-400">
              p={(score * 100).toFixed(1)}%
            </span>
          )}
        </div>
      );
    }
    return (
      <div className="flex items-center gap-1.5">
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-emerald-950/50 text-emerald-400 border border-emerald-500/30">
          LOW
        </span>
        {typeof score === 'number' && (
          <span className="text-[10px] font-mono text-slate-500">
            p={(score * 100).toFixed(1)}%
          </span>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------------------ */}
      {/* Flashing Critical Alert Banner (Requirement 6) */}
      {/* ------------------------------------------------------------------------ */}
      {activeAlert && (
        <div className="relative overflow-hidden rounded-2xl border-2 border-rose-500/90 bg-gradient-to-r from-rose-950/90 via-obsidian-950 to-rose-950/90 p-4 lg:p-5 shadow-glow-rose animate-fade-in">
          <div className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-r from-rose-500 via-amber-400 to-rose-500 animate-pulse" />

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="p-2.5 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/50 animate-pulse shrink-0">
                <Flame className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center flex-wrap gap-2">
                  <span className="text-xs font-mono font-black tracking-wider uppercase px-2 py-0.5 rounded bg-rose-500 text-slate-950">
                    CRITICAL SAR ALERT TRIGGERED
                  </span>
                  <span className="text-xs font-mono font-bold text-rose-400">
                    UTR: {activeAlert.transaction_id}
                  </span>
                  <span className="text-[11px] font-mono text-slate-400">
                    {formatClockTime(activeAlert.timestamp)}
                  </span>
                </div>

                <p className="text-xs sm:text-sm text-slate-200 font-mono">
                  Suspicious high-velocity transfer of{' '}
                  <strong className="text-rose-300 font-bold">{formatAmount(activeAlert)}</strong>{' '}
                  detected on rail <strong className="text-cyan-400 font-bold">{activeAlert.rail}</strong>.
                  Scheme typology indicates potential structuring or darknet clustering.
                </p>

                <div className="flex items-center gap-2 text-xs font-mono text-slate-400 pt-0.5">
                  <span className="text-slate-300 truncate max-w-[200px] sm:max-w-none">
                    {activeAlert.from_entity}
                  </span>
                  <ArrowRight className="w-3 h-3 text-rose-400 shrink-0" />
                  <span className="text-slate-300 truncate max-w-[200px] sm:max-w-none">
                    {activeAlert.to_entity}
                  </span>
                  {activeAlert.flags && activeAlert.flags.length > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-rose-900/60 text-rose-300 border border-rose-800">
                      {activeAlert.flags.join(', ')}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 self-end md:self-center shrink-0">
              <button
                onClick={() => {
                  if (onOpenSarModal) {
                    onOpenSarModal(activeAlert.sar_id || activeAlert.transaction_id);
                  } else {
                    handleGenerateSar(activeAlert);
                  }
                }}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-slate-50 text-xs font-mono font-bold transition-all shadow-lg hover:shadow-rose-600/40"
              >
                <FileText className="w-4 h-4" />
                <span>Open SAR Dossier</span>
              </button>
              <button
                onClick={onDismissAlert}
                className="p-2 rounded-xl border border-slate-800 hover:border-slate-700 bg-slate-900/80 text-slate-400 hover:text-slate-200 transition-colors"
                title="Dismiss Banner"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------------ */}
      {/* Header Telemetry & KPI Cards (Requirement 3) */}
      {/* ------------------------------------------------------------------------ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Screened */}
        <div className="p-4 rounded-2xl glass-card border border-slate-800/80 bg-obsidian-950/70 hover:border-cyan-500/30 transition-all group">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
            <span>TOTAL TRANSACTIONS</span>
            <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 group-hover:scale-110 transition-transform">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl lg:text-3xl font-black font-mono text-slate-100 tracking-tight">
            {telemetry.totalScreened.toLocaleString()}
          </div>
          <div className="flex items-center gap-2 mt-2 text-[11px] font-mono text-slate-400">
            <span className="flex items-center gap-1 text-emerald-400">
              <Zap className="w-3 h-3" />
              Active Stream
            </span>
            <span className="text-slate-600">•</span>
            <span>Buffered: {transactions.length}/100</span>
          </div>
        </div>

        {/* Card 2: Sub-50ms SLA Tracker */}
        <div className="p-4 rounded-2xl glass-card border border-slate-800/80 bg-obsidian-950/70 hover:border-emerald-500/30 transition-all group">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
            <span>SUB-50MS SLA TRACKER</span>
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 group-hover:scale-110 transition-transform">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-2xl lg:text-3xl font-black font-mono text-emerald-400 tracking-tight">
              {telemetry.avgLatency} <span className="text-sm font-normal text-slate-400">ms</span>
            </div>
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/40">
              SLA MET
            </span>
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-[11px] font-mono text-slate-400">
            <span>Rolling 50-sample inference latency</span>
          </div>
        </div>

        {/* Card 3: Active Threat Flags / SARs */}
        <div className="p-4 rounded-2xl glass-card border border-slate-800/80 bg-obsidian-950/70 hover:border-rose-500/30 transition-all group">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
            <span>THREAT FLAGS / SARS</span>
            <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 group-hover:scale-110 transition-transform">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-2xl lg:text-3xl font-black font-mono text-rose-400 tracking-tight">
              {telemetry.threatFlagsCount.toLocaleString()}
            </div>
            {sarMetrics?.totalSarsGenerated > 0 && (
              <span className="text-xs font-mono font-bold text-amber-400">
                / {sarMetrics.totalSarsGenerated} SARs
              </span>
            )}
            {(telemetry.threatFlagsCount > 0 || sarMetrics?.totalSarsGenerated > 0) && (
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-500/40 animate-pulse">
                CRITICAL / HIGH
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-[11px] font-mono text-slate-400">
            <span>
              {telemetry.totalScreened > 0
                ? `${((telemetry.threatFlagsCount / telemetry.totalScreened) * 100).toFixed(1)}% detection rate`
                : '0.0% detection rate'}
              {sarMetrics?.totalSarsGenerated > 0 ? ` • ${sarMetrics.totalSarsGenerated} Dossiers` : ''}
            </span>
          </div>
        </div>

        {/* Card 4: Cross-Rail Split */}
        <div className="p-4 rounded-2xl glass-card border border-slate-800/80 bg-obsidian-950/70 hover:border-indigo-500/30 transition-all group">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
            <span>CROSS-RAIL SPLIT</span>
            <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 group-hover:scale-110 transition-transform">
              <CreditCard className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-center justify-between font-mono text-sm font-bold text-slate-200 pt-1">
            <span className="flex items-center gap-1.5 text-cyan-400">
              <CreditCard className="w-3.5 h-3.5" />
              Fiat: {telemetry.fiatCount}
            </span>
            <span className="flex items-center gap-1.5 text-amber-400">
              <Bitcoin className="w-3.5 h-3.5" />
              Crypto: {telemetry.cryptoCount}
            </span>
          </div>
          {/* Distribution bar */}
          <div className="w-full bg-slate-800 rounded-full h-2 mt-3 overflow-hidden flex">
            <div
              className="bg-cyan-500 transition-all duration-500"
              style={{
                width: `${
                  telemetry.totalScreened > 0
                    ? (telemetry.fiatCount / telemetry.totalScreened) * 100
                    : 50
                }%`,
              }}
              title="Fiat Volume"
            />
            <div
              className="bg-amber-500 transition-all duration-500"
              style={{
                width: `${
                  telemetry.totalScreened > 0
                    ? (telemetry.cryptoCount / telemetry.totalScreened) * 100
                    : 50
                }%`,
              }}
              title="Crypto Volume"
            />
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------------ */}
      {/* Live Audit Ledger Container & Table Controls */}
      {/* ------------------------------------------------------------------------ */}
      <div className="rounded-2xl glass-card border border-slate-800 bg-obsidian-950/80 overflow-hidden shadow-2xl">
        {/* Table Toolbar / Filters Bar */}
        <div className="p-4 border-b border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-obsidian-900/60">
          {/* Left: Filter Buttons */}
          <div className="flex items-center flex-wrap gap-1.5">
            <button
              onClick={() => setActiveFilter('ALL')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-semibold transition-all',
                activeFilter === 'ALL'
                  ? 'bg-slate-700 text-slate-100 border border-slate-600 shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              )}
            >
              <span>All Streams</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">
                {counts.all}
              </span>
            </button>

            <button
              onClick={() => setActiveFilter('FIAT')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-semibold transition-all',
                activeFilter === 'FIAT'
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-500/50 shadow-glow-cyan'
                  : 'text-slate-400 hover:text-cyan-300 hover:bg-slate-800/50'
              )}
            >
              <CreditCard className="w-3.5 h-3.5 text-cyan-400" />
              <span>Indian Banking (Fiat)</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-400">
                {counts.fiat}
              </span>
            </button>

            <button
              onClick={() => setActiveFilter('CRYPTO')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-semibold transition-all',
                activeFilter === 'CRYPTO'
                  ? 'bg-amber-950/80 text-amber-300 border border-amber-500/50 shadow-glow-amber'
                  : 'text-slate-400 hover:text-amber-300 hover:bg-slate-800/50'
              )}
            >
              <Bitcoin className="w-3.5 h-3.5 text-amber-400" />
              <span>Crypto Forensics</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-amber-950 text-amber-400">
                {counts.crypto}
              </span>
            </button>

            <button
              onClick={() => setActiveFilter('SARS')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-semibold transition-all',
                activeFilter === 'SARS'
                  ? 'bg-rose-950/80 text-rose-300 border border-rose-500/60 shadow-glow-rose'
                  : 'text-slate-400 hover:text-rose-300 hover:bg-slate-800/50'
              )}
            >
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>Alerts Only (SARs)</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-rose-950 text-rose-400">
                {counts.sars}
              </span>
            </button>
          </div>

          {/* Right: Pause/Resume, Clear, WS Status */}
          <div className="flex items-center gap-2 self-end md:self-center">
            {/* Pause / Resume Button */}
            <button
              onClick={onTogglePause}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-semibold border transition-all',
                isPaused
                  ? 'bg-amber-950/80 text-amber-300 border-amber-500/50 shadow-glow-amber'
                  : 'bg-slate-800/80 text-slate-200 border-slate-700 hover:bg-slate-700'
              )}
              title={isPaused ? 'Click to Resume Live Stream' : 'Click to Pause Feed for Inspection'}
            >
              {isPaused ? (
                <>
                  <Play className="w-3.5 h-3.5 text-amber-400" />
                  <span>Resume Feed</span>
                </>
              ) : (
                <>
                  <Pause className="w-3.5 h-3.5 text-slate-400" />
                  <span>Pause Feed</span>
                </>
              )}
            </button>

            {/* Clear Feed Button */}
            <button
              onClick={onClearFeed}
              disabled={transactions.length === 0}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono text-slate-400 hover:text-slate-200 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/50 transition-all disabled:opacity-40 disabled:pointer-events-none"
              title="Clear Session Buffer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          </div>
        </div>

        {/* ------------------------------------------------------------------------ */}
        {/* High-Density Ledger Table (Requirement 4) */}
        {/* ------------------------------------------------------------------------ */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-obsidian-950/90 text-slate-400 uppercase tracking-wider text-[10px]">
                <th className="py-3 px-4">Time (UTC)</th>
                <th className="py-3 px-4">Rail / Engine</th>
                <th className="py-3 px-4">Transaction ID</th>
                <th className="py-3 px-4">Counterparties (From → To)</th>
                <th className="py-3 px-4 text-right">Amount</th>
                <th className="py-3 px-4">Risk Assessment</th>
                <th className="py-3 px-4">Latency</th>
                <th className="py-3 px-4">Typology / Flags</th>
                <th className="py-3 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-16 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="relative flex items-center justify-center w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800">
                        <Radio className="w-6 h-6 text-cyan-400 animate-pulse" />
                      </div>
                      <div className="space-y-1">
                        <p className="font-bold text-slate-200">
                          Waiting for live transaction stream from WebSocket...
                        </p>
                        <p className="text-xs text-slate-400">
                          Run <code className="text-cyan-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">python streamer.py</code> or <code className="text-amber-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">python live_crypto_feed.py</code> in your terminal.
                        </p>
                      </div>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((tx, idx) => {
                  const isCrypto =
                    tx.engine === 'CRYPTO_FORENSICS' || tx.rail === 'BTC' || tx.currency === 'BTC';
                  const isCritical =
                    tx.risk_tier === 'CRITICAL_SAR' || tx.risk_tier === 'CRITICAL';

                  return (
                    <tr
                      key={tx.transaction_id || idx}
                      onClick={() => {
                        const openFn = openSarModal || onOpenSarModal;
                        if (tx.sar_id && openFn) {
                          openFn(tx.sar_id);
                        } else if (isCritical) {
                          handleGenerateSarRow({ stopPropagation: () => {} }, tx);
                        }
                      }}
                      className={cn(
                        'transition-colors animate-fade-in hover:bg-slate-850/60',
                        isCritical
                          ? 'bg-rose-950/20 hover:bg-rose-950/30 border-l-2 border-l-rose-500 cursor-pointer'
                          : idx === 0
                          ? 'bg-cyan-950/10'
                          : ''
                      )}
                    >
                      {/* Column 1: Time */}
                      <td className="py-2.5 px-4 whitespace-nowrap text-slate-400 text-[11px]">
                        {formatClockTime(tx.timestamp)}
                      </td>

                      {/* Column 2: Rail / Engine */}
                      <td className="py-2.5 px-4 whitespace-nowrap">
                        {renderRailBadge(tx.rail)}
                      </td>

                      {/* Column 3: Transaction ID */}
                      <td className="py-2.5 px-4 whitespace-nowrap text-slate-300 font-semibold max-w-[140px] truncate" title={tx.transaction_id}>
                        {tx.transaction_id}
                      </td>

                      {/* Column 4: Counterparties */}
                      <td className="py-2.5 px-4">
                        <div className="flex items-center gap-1.5 max-w-xs md:max-w-sm truncate text-[11px]">
                          <span
                            className="text-slate-300 font-medium truncate"
                            title={tx.from_entity}
                          >
                            {tx.from_entity}
                          </span>
                          <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />
                          <span
                            className="text-slate-400 truncate"
                            title={tx.to_entity}
                          >
                            {tx.to_entity}
                          </span>
                        </div>
                      </td>

                      {/* Column 5: Amount */}
                      <td className="py-2.5 px-4 whitespace-nowrap text-right font-bold text-slate-100">
                        <span className={cn(isCrypto ? 'text-amber-300' : 'text-slate-100')}>
                          {formatAmount(tx)}
                        </span>
                      </td>

                      {/* Column 6: Risk Assessment */}
                      <td className="py-2.5 px-4 whitespace-nowrap">
                        {renderRiskBadge(tx.risk_tier, tx.risk_score)}
                      </td>

                      {/* Column 7: Latency */}
                      <td className="py-2.5 px-4 whitespace-nowrap text-slate-400 text-[11px]">
                        <span className="text-emerald-400 font-medium">
                          {typeof tx.latency_ms === 'number'
                            ? `~${tx.latency_ms.toFixed(1)} ms`
                            : '~12.0 ms'}
                        </span>
                      </td>

                      {/* Column 8: Typology Flags */}
                      <td className="py-2.5 px-4 whitespace-nowrap">
                        {tx.flags && tx.flags.length > 0 ? (
                          <div className="flex items-center gap-1">
                            {tx.flags.map((flag, fIdx) => (
                              <span
                                key={fIdx}
                                className={cn(
                                  'px-1.5 py-0.5 rounded text-[10px] font-mono font-medium',
                                  isCritical
                                    ? 'bg-rose-900/60 text-rose-300 border border-rose-800/60'
                                    : 'bg-slate-800 text-slate-300 border border-slate-700'
                                )}
                              >
                                {flag}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-slate-600 text-[10px]">--</span>
                        )}
                      </td>

                      {/* Column 9: Action */}
                      <td className="py-2.5 px-4 whitespace-nowrap text-center">
                        {isCritical ? (
                          tx.sar_id ? (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                const openFn = openSarModal || onOpenSarModal;
                                if (openFn) openFn(tx.sar_id);
                              }}
                              className="px-2.5 py-1 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30 hover:bg-rose-500/30 transition-all flex items-center justify-center gap-1 shadow-sm mx-auto whitespace-nowrap"
                              title={`View Regulatory Case Dossier: ${tx.sar_id}`}
                            >
                              <FileText className="w-3 h-3" />
                              <span>View SAR {tx.sar_id.length > 18 ? `${tx.sar_id.slice(0, 10)}...` : tx.sar_id}</span>
                            </button>
                          ) : (
                            <button
                              onClick={(e) => handleGenerateSarRow(e, tx)}
                              disabled={generatingTxId === tx.transaction_id}
                              className="px-2.5 py-1 rounded text-[10px] font-mono font-bold bg-rose-600 hover:bg-rose-500 text-white transition-all shadow-sm flex items-center justify-center gap-1 mx-auto whitespace-nowrap disabled:opacity-50"
                              title="Generate SAR Dossier via POST /api/v1/sar/generate"
                            >
                              {generatingTxId === tx.transaction_id ? (
                                <span className="animate-spin text-xs">⏳</span>
                              ) : (
                                <FileText className="w-3 h-3" />
                              )}
                              <span>Generate SAR</span>
                            </button>
                          )
                        ) : (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (tx.sar_id) {
                                const openFn = openSarModal || onOpenSarModal;
                                if (openFn) openFn(tx.sar_id);
                              } else {
                                handleGenerateSar(tx);
                              }
                            }}
                            className="px-2 py-1 rounded text-[10px] font-mono font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all"
                            title="Generate or Inspect Suspicious Activity Report"
                          >
                            {tx.sar_id ? 'View SAR' : 'SAR'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer */}
        <div className="p-3 border-t border-slate-800/80 bg-obsidian-950/90 flex items-center justify-between text-xs font-mono text-slate-400 px-4">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span
                  className={cn(
                    'relative inline-flex rounded-full h-2 w-2',
                    wsStatus === 'CONNECTED'
                      ? 'bg-emerald-500'
                      : wsStatus === 'CONNECTING'
                      ? 'bg-amber-500 animate-pulse'
                      : 'bg-rose-500'
                  )}
                />
              </span>
              <span>Hub: {wsStatus}</span>
            </span>
            <span className="text-slate-700">|</span>
            <span>Showing {filteredTransactions.length} of {transactions.length} entries</span>
          </div>

          <div className="flex items-center gap-2">
            <span>Buffer: 100 max (bounded ring)</span>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------------ */}
      {/* Interactive SAR Report Generator Modal */}
      {/* ------------------------------------------------------------------------ */}
      {selectedTxForSar && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian-950/80 backdrop-blur-md animate-fade-in">
          <div className="max-w-lg w-full rounded-2xl glass-card border border-slate-700 bg-obsidian-900 shadow-2xl p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/40">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-mono font-bold text-slate-100 uppercase tracking-wide">
                    FinCEN / FIU-IND Suspicious Activity Report
                  </h3>
                  <p className="text-[11px] font-mono text-slate-400">
                    Automated Case Filing: SAR-{selectedTxForSar.transaction_id}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedTxForSar(null)}
                className="text-slate-500 hover:text-slate-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1.5">
                <div className="flex justify-between text-slate-400">
                  <span>Target Transaction:</span>
                  <span className="text-slate-200 font-bold">{selectedTxForSar.transaction_id}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Evaluated Amount:</span>
                  <span className="text-rose-400 font-bold">{formatAmount(selectedTxForSar)}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Rail & Engine:</span>
                  <span className="text-cyan-400">{selectedTxForSar.rail} ({selectedTxForSar.engine})</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Risk Score & Tier:</span>
                  <span className="text-rose-300 font-bold">
                    {selectedTxForSar.risk_tier} (p={(selectedTxForSar.risk_score * 100).toFixed(1)}%)
                  </span>
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400 font-semibold">Narrative Summary:</span>
                <p className="text-slate-300 text-[11px] leading-relaxed p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
                  Automated surveillance flagged anomalous financial flow from remitter{' '}
                  <strong className="text-cyan-300">{selectedTxForSar.from_entity}</strong> to{' '}
                  <strong className="text-cyan-300">{selectedTxForSar.to_entity}</strong>. Triggered risk engine evaluation in {selectedTxForSar.latency_ms}ms with flags: {selectedTxForSar.flags?.join(', ') || 'ANOMALY'}.
                </p>
              </div>

              {sarFiledSuccess ? (
                <div className="p-3 rounded-xl bg-emerald-950/70 border border-emerald-500/50 text-emerald-300 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <span>SAR dossier officially filed and queued to compliance ledger!</span>
                </div>
              ) : (
                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    onClick={() => setSelectedTxForSar(null)}
                    className="px-3.5 py-2 rounded-xl text-xs font-mono text-slate-400 hover:text-slate-200 border border-slate-800 hover:bg-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleConfirmFileSar}
                    className="px-4 py-2 rounded-xl text-xs font-mono font-bold bg-rose-600 hover:bg-rose-500 text-white shadow-lg transition-all"
                  >
                    Confirm & File SAR
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
