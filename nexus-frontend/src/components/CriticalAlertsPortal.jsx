import React, { useState, useMemo } from 'react';
import {
  ShieldAlert,
  Flame,
  CreditCard,
  Bitcoin,
  Search,
  ArrowRight,
  FileWarning,
  Copy,
  CheckCircle2,
  Layers,
  Zap,
  Eye,
  X,
} from 'lucide-react';
import { cn } from '../utils/cn';

export function CriticalAlertsPortal({
  transactions = [],
  openSarModal,
  onOpenSarModal,
  activeFiatAlert,
  activeCryptoAlert,
  onDismissFiatAlert,
  onDismissCryptoAlert,
}) {
  // 'BANKING' | 'CRYPTO' | 'DUAL'
  const [activeDashboard, setActiveDashboard] = useState('DUAL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTypology, setSelectedTypology] = useState('ALL');
  const [selectedAlertForInspection, setSelectedAlertForInspection] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  const handleOpenSar = (sarId, fallbackTxId) => {
    const openFn = openSarModal || onOpenSarModal;
    if (openFn) {
      openFn(sarId || fallbackTxId);
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard?.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Extract all critical alerts from session transactions
  const allCriticalAlerts = useMemo(() => {
    return transactions.filter((tx) => {
      const isCritical =
        Boolean(tx.sar_id) ||
        tx.risk_tier === 'CRITICAL_SAR' ||
        tx.risk_tier === 'CRITICAL' ||
        tx.risk_tier === 'HIGH' ||
        tx.risk_tier === 'HIGH_RISK' ||
        Number(tx.risk_score) >= 0.80 ||
        (Array.isArray(tx.flags) &&
          tx.flags.some((f) =>
            [
              'PAN_STRUCTURING_EVASION',
              'HAWALA_WIRE',
              'MULE_BURST',
              'AUTO_FLAG_SAR',
              'CRITICAL_SAR',
              'ANOMALY',
              'WHALE_TRANSFER',
            ].includes(String(f).toUpperCase())
          ));
      return isCritical;
    });
  }, [transactions]);

  // Separate Banking vs Crypto Critical Alerts
  const bankingCriticalAlerts = useMemo(() => {
    return allCriticalAlerts.filter((tx) => {
      const isCrypto =
        tx.engine === 'CRYPTO_FORENSICS' || tx.rail === 'BTC' || tx.currency === 'BTC';
      return !isCrypto;
    });
  }, [allCriticalAlerts]);

  const cryptoCriticalAlerts = useMemo(() => {
    return allCriticalAlerts.filter((tx) => {
      const isCrypto =
        tx.engine === 'CRYPTO_FORENSICS' || tx.rail === 'BTC' || tx.currency === 'BTC';
      return isCrypto;
    });
  }, [allCriticalAlerts]);

  // Banking Metrics
  const bankingMetrics = useMemo(() => {
    let totalExposureInr = 0;
    let structuringCount = 0;
    let hawalaCount = 0;
    let muleCount = 0;

    for (const tx of bankingCriticalAlerts) {
      totalExposureInr += Number(tx.amount || 0);
      const flags = (tx.flags || []).map((f) => String(f).toUpperCase());
      if (flags.includes('PAN_STRUCTURING_EVASION') || String(tx.account_to || '').includes('aggregator')) {
        structuringCount++;
      } else if (flags.includes('HAWALA_WIRE') || tx.payment_format === 'RTGS' || tx.rail === 'RTGS') {
        hawalaCount++;
      } else {
        muleCount++;
      }
    }

    return {
      count: bankingCriticalAlerts.length,
      exposureInr: totalExposureInr,
      structuringCount,
      hawalaCount,
      muleCount,
    };
  }, [bankingCriticalAlerts]);

  // Crypto Metrics
  const cryptoMetrics = useMemo(() => {
    let totalExposureBtc = 0;
    let mixerCount = 0;
    let whaleCount = 0;
    let peelingCount = 0;

    for (const tx of cryptoCriticalAlerts) {
      const btc = Number(tx.amount || tx.btc_value || 0);
      totalExposureBtc += btc;
      const flags = (tx.flags || []).map((f) => String(f).toUpperCase());

      if (flags.includes('WHALE_TRANSFER') || btc >= 10.0) {
        whaleCount++;
      } else if (tx.in_count > 6 || tx.out_count > 10 || String(tx.from_entity || '').includes('mixer')) {
        mixerCount++;
      } else {
        peelingCount++;
      }
    }

    return {
      count: cryptoCriticalAlerts.length,
      exposureBtc: totalExposureBtc,
      mixerCount,
      whaleCount,
      peelingCount,
    };
  }, [cryptoCriticalAlerts]);

  // Filtered lists based on search & typology
  const filteredBankingAlerts = useMemo(() => {
    return bankingCriticalAlerts.filter((tx) => {
      const matchesSearch =
        !searchQuery ||
        String(tx.transaction_id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        String(tx.from_entity || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        String(tx.to_entity || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        String(tx.sar_id || '').toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      if (selectedTypology === 'STRUCTURING') {
        return (
          (tx.flags || []).includes('PAN_STRUCTURING_EVASION') ||
          String(tx.account_to || '').includes('aggregator')
        );
      }
      if (selectedTypology === 'HAWALA') {
        return (
          (tx.flags || []).includes('HAWALA_WIRE') ||
          tx.payment_format === 'RTGS' ||
          tx.rail === 'RTGS'
        );
      }
      if (selectedTypology === 'MULE') {
        return (
          (tx.flags || []).includes('MULE_BURST') ||
          tx.payment_format === 'IMPS' ||
          tx.rail === 'IMPS'
        );
      }
      return true;
    });
  }, [bankingCriticalAlerts, searchQuery, selectedTypology]);

  const filteredCryptoAlerts = useMemo(() => {
    return cryptoCriticalAlerts.filter((tx) => {
      const matchesSearch =
        !searchQuery ||
        String(tx.transaction_id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        String(tx.from_entity || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        String(tx.to_entity || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        String(tx.sar_id || '').toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      const btc = Number(tx.amount || tx.btc_value || 0);
      if (selectedTypology === 'WHALE') {
        return (tx.flags || []).includes('WHALE_TRANSFER') || btc >= 10.0;
      }
      if (selectedTypology === 'MIXER') {
        return (
          tx.in_count > 6 ||
          tx.out_count > 10 ||
          String(tx.from_entity || '').includes('mixer')
        );
      }
      if (selectedTypology === 'PEELING') {
        return btc < 10.0 && tx.in_count <= 4;
      }
      return true;
    });
  }, [cryptoCriticalAlerts, searchQuery, selectedTypology]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Real-time Incoming Critical Incident Banners */}
      {(activeFiatAlert || activeCryptoAlert) && (
        <div className="space-y-3">
          {activeFiatAlert && (
            <div className="relative overflow-hidden rounded-2xl border-2 border-rose-500 bg-gradient-to-r from-rose-950/90 via-obsidian-950 to-cyan-950/80 p-4 shadow-glow-rose animate-fade-in">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="p-2.5 rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/50 shrink-0">
                    <CreditCard className="w-5 h-5 text-cyan-400" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center flex-wrap gap-2">
                      <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-rose-600 text-slate-50">
                        🇮🇳 ACTIVE CRITICAL BANKING INCIDENT
                      </span>
                      <span className="text-xs font-mono font-bold text-cyan-300">
                        UTR: {activeFiatAlert.transaction_id}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        Rail: {activeFiatAlert.rail}
                      </span>
                    </div>
                    <p className="text-xs text-slate-200 font-mono">
                      Domestic transfer of <strong className="text-rose-300">₹{Number(activeFiatAlert.amount || 0).toLocaleString('en-IN')}</strong> triggered statutory threshold evasion or hawala topology.
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                  <button
                    onClick={() => {
                      const fn = openSarModal || onOpenSarModal;
                      if (fn) fn(activeFiatAlert.sar_id || activeFiatAlert.transaction_id);
                    }}
                    className="px-3 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-slate-950 text-xs font-mono font-bold transition-all shadow-md"
                  >
                    Open FIU Dossier
                  </button>
                  {onDismissFiatAlert && (
                    <button
                      onClick={onDismissFiatAlert}
                      className="p-2 rounded-xl border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                      title="Dismiss Alert"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeCryptoAlert && (
            <div className="relative overflow-hidden rounded-2xl border-2 border-amber-500 bg-gradient-to-r from-amber-950/90 via-obsidian-950 to-purple-950/80 p-4 shadow-glow-amber animate-fade-in">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/50 shrink-0">
                    <Bitcoin className="w-5 h-5 text-amber-400" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center flex-wrap gap-2">
                      <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-amber-500 text-slate-950">
                        ⚡ ACTIVE ON-CHAIN VDA INCIDENT
                      </span>
                      <span className="text-xs font-mono font-bold text-amber-300">
                        TX: {String(activeCryptoAlert.transaction_id || '').slice(0, 16)}...
                      </span>
                    </div>
                    <p className="text-xs text-slate-200 font-mono">
                      On-chain transaction of <strong className="text-amber-300">{Number(activeCryptoAlert.amount || 0).toFixed(4)} BTC</strong> flagged for Darknet Mixer / Whale anomaly.
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                  <button
                    onClick={() => {
                      const fn = openSarModal || onOpenSarModal;
                      if (fn) fn(activeCryptoAlert.sar_id || activeCryptoAlert.transaction_id);
                    }}
                    className="px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-mono font-bold transition-all shadow-md"
                  >
                    Open Crypto Dossier
                  </button>
                  {onDismissCryptoAlert && (
                    <button
                      onClick={onDismissCryptoAlert}
                      className="p-2 rounded-xl border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                      title="Dismiss Alert"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------------------ */}
      {/* 1. Header & Dual Dashboard Mode Selector */}
      {/* ------------------------------------------------------------------------ */}
      <div className="p-6 rounded-2xl glass-card border border-slate-800/90 bg-gradient-to-r from-obsidian-950 via-slate-950 to-obsidian-950 shadow-2xl relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-gradient-to-tr from-rose-600 to-amber-600 text-slate-50 shadow-glow-rose">
                <Flame className="w-6 h-6 animate-pulse" />
              </div>
              <div>
                <h1 className="text-xl lg:text-2xl font-black font-mono tracking-wider text-slate-100 uppercase flex items-center gap-2">
                  CRITICAL THREAT COMMAND CENTER
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-950 text-rose-300 border border-rose-500/40 font-bold">
                    ACTIVE SURVEILLANCE
                  </span>
                </h1>
                <p className="text-xs font-mono text-slate-400">
                  Dedicated dual-engine regulatory dashboards separating FIU-IND statutory banking from On-Chain VDA Forensics.
                </p>
              </div>
            </div>
          </div>

          {/* Switcher Tabs */}
          <div className="flex items-center p-1 rounded-xl bg-obsidian-900/90 border border-slate-800 shadow-inner flex-wrap gap-1">
            <button
              onClick={() => setActiveDashboard('DUAL')}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-bold transition-all',
                activeDashboard === 'DUAL'
                  ? 'bg-gradient-to-r from-rose-600 via-purple-600 to-cyan-600 text-slate-50 shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              )}
            >
              <Layers className="w-4 h-4" />
              <span>Dual Command Center</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-900/80 text-slate-300">
                {allCriticalAlerts.length}
              </span>
            </button>

            <button
              onClick={() => setActiveDashboard('BANKING')}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-bold transition-all',
                activeDashboard === 'BANKING'
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-500/50 shadow-glow-cyan'
                  : 'text-slate-400 hover:text-cyan-300 hover:bg-slate-800/50'
              )}
            >
              <CreditCard className="w-4 h-4 text-cyan-400" />
              <span>Indian Banking Hub</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-cyan-900 text-cyan-200">
                {bankingCriticalAlerts.length}
              </span>
            </button>

            <button
              onClick={() => setActiveDashboard('CRYPTO')}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-bold transition-all',
                activeDashboard === 'CRYPTO'
                  ? 'bg-amber-950 text-amber-300 border border-amber-500/50 shadow-glow-amber'
                  : 'text-slate-400 hover:text-amber-300 hover:bg-slate-800/50'
              )}
            >
              <Bitcoin className="w-4 h-4 text-amber-400" />
              <span>Crypto Forensics Hub</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-900 text-amber-200">
                {cryptoCriticalAlerts.length}
              </span>
            </button>
          </div>
        </div>

        {/* Global Filter Bar */}
        <div className="mt-6 pt-4 border-t border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search by UTR, Tx Hash, VPA, Wallet Address, or SAR ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-obsidian-900/80 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-mono text-slate-500">TYPOLOGY FILTER:</span>
            <button
              onClick={() => setSelectedTypology('ALL')}
              className={cn(
                'px-2.5 py-1 rounded-lg text-[11px] font-mono transition-all',
                selectedTypology === 'ALL'
                  ? 'bg-slate-700 text-slate-100 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              )}
            >
              All Typologies
            </button>
            {activeDashboard !== 'CRYPTO' && (
              <>
                <button
                  onClick={() => setSelectedTypology('STRUCTURING')}
                  className={cn(
                    'px-2.5 py-1 rounded-lg text-[11px] font-mono transition-all',
                    selectedTypology === 'STRUCTURING'
                      ? 'bg-cyan-900 text-cyan-300 font-bold border border-cyan-700'
                      : 'text-slate-400 hover:text-cyan-300 hover:bg-slate-800'
                  )}
                >
                  PAN Structuring
                </button>
                <button
                  onClick={() => setSelectedTypology('HAWALA')}
                  className={cn(
                    'px-2.5 py-1 rounded-lg text-[11px] font-mono transition-all',
                    selectedTypology === 'HAWALA'
                      ? 'bg-rose-900 text-rose-300 font-bold border border-rose-700'
                      : 'text-slate-400 hover:text-rose-300 hover:bg-slate-800'
                  )}
                >
                  Hawala RTGS
                </button>
                <button
                  onClick={() => setSelectedTypology('MULE')}
                  className={cn(
                    'px-2.5 py-1 rounded-lg text-[11px] font-mono transition-all',
                    selectedTypology === 'MULE'
                      ? 'bg-purple-900 text-purple-300 font-bold border border-purple-700'
                      : 'text-slate-400 hover:text-purple-300 hover:bg-slate-800'
                  )}
                >
                  Mule Velocity
                </button>
              </>
            )}
            {activeDashboard !== 'BANKING' && (
              <>
                <button
                  onClick={() => setSelectedTypology('MIXER')}
                  className={cn(
                    'px-2.5 py-1 rounded-lg text-[11px] font-mono transition-all',
                    selectedTypology === 'MIXER'
                      ? 'bg-amber-900 text-amber-300 font-bold border border-amber-700'
                      : 'text-slate-400 hover:text-amber-300 hover:bg-slate-800'
                  )}
                >
                  Darknet Mixer
                </button>
                <button
                  onClick={() => setSelectedTypology('WHALE')}
                  className={cn(
                    'px-2.5 py-1 rounded-lg text-[11px] font-mono transition-all',
                    selectedTypology === 'WHALE'
                      ? 'bg-orange-900 text-orange-300 font-bold border border-orange-700'
                      : 'text-slate-400 hover:text-orange-300 hover:bg-slate-800'
                  )}
                >
                  Whale Transfer
                </button>
                <button
                  onClick={() => setSelectedTypology('PEELING')}
                  className={cn(
                    'px-2.5 py-1 rounded-lg text-[11px] font-mono transition-all',
                    selectedTypology === 'PEELING'
                      ? 'bg-indigo-900 text-indigo-300 font-bold border border-indigo-700'
                      : 'text-slate-400 hover:text-indigo-300 hover:bg-slate-800'
                  )}
                >
                  Peeling Chain
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------------ */}
      {/* 2. Dashboards Layout: Dual Side-by-Side or Individual Focus */}
      {/* ------------------------------------------------------------------------ */}
      <div
        className={cn(
          'grid gap-6',
          activeDashboard === 'DUAL' ? 'grid-cols-1 xl:grid-cols-2' : 'grid-cols-1'
        )}
      >
        {/* ==================================================================== */}
        {/* DASHBOARD 1: INDIAN BANKING CRITICAL THREATS                         */}
        {/* ==================================================================== */}
        {(activeDashboard === 'DUAL' || activeDashboard === 'BANKING') && (
          <div className="space-y-6">
            {/* Dashboard Header & KPI Bar */}
            <div className="p-5 rounded-2xl glass-card border border-rose-500/30 bg-obsidian-950/90 shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="text-xl">🇮🇳</span>
                  <div>
                    <h2 className="text-base font-black font-mono text-cyan-300 tracking-wide uppercase">
                      INDIAN BANKING CRITICAL DASHBOARD
                    </h2>
                    <span className="text-[10px] font-mono text-slate-400">
                      PMLA 2002 § 12 Compliance & FIU-IND Form STR Telemetry
                    </span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-500/40 text-xs font-mono font-bold">
                  {bankingCriticalAlerts.length} THREATS
                </span>
              </div>

              {/* KPI Cards Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-obsidian-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 block mb-1">TOTAL EXPOSURE</span>
                  <div className="text-sm lg:text-base font-black font-mono text-rose-400 truncate">
                    ₹{bankingMetrics.exposureInr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-obsidian-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 block mb-1">PAN STRUCTURING</span>
                  <div className="text-sm lg:text-base font-black font-mono text-cyan-400">
                    {bankingMetrics.structuringCount} <span className="text-[10px] font-normal text-slate-500">&lt;₹50k</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-obsidian-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 block mb-1">HAWALA WIRES</span>
                  <div className="text-sm lg:text-base font-black font-mono text-amber-400">
                    {bankingMetrics.hawalaCount} <span className="text-[10px] font-normal text-slate-500">RTGS</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-obsidian-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 block mb-1">MULE DRAINING</span>
                  <div className="text-sm lg:text-base font-black font-mono text-purple-400">
                    {bankingMetrics.muleCount} <span className="text-[10px] font-normal text-slate-500">IMPS</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Banking Alert Feed */}
            <div className="rounded-2xl glass-card border border-slate-800 bg-obsidian-950/90 overflow-hidden shadow-xl">
              <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between bg-obsidian-900/70">
                <span className="text-xs font-mono font-bold text-slate-300 flex items-center gap-2">
                  <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                  <span>Verified Banking Critical Alerts ({filteredBankingAlerts.length})</span>
                </span>
                <span className="text-[10px] font-mono text-slate-500">
                  Auto-Dispatched STR Queue
                </span>
              </div>

              <div className="divide-y divide-slate-800/60 max-h-[600px] overflow-y-auto custom-scrollbar">
                {filteredBankingAlerts.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 font-mono text-xs">
                    No active banking critical threats matching current filters.
                  </div>
                ) : (
                  filteredBankingAlerts.map((tx) => {
                    const amountInr = Number(tx.amount || 0);
                    const flags = tx.flags || [];
                    const isStructuring =
                      flags.includes('PAN_STRUCTURING_EVASION') ||
                      String(tx.account_to || '').includes('aggregator');
                    const isHawala =
                      flags.includes('HAWALA_WIRE') ||
                      tx.payment_format === 'RTGS' ||
                      tx.rail === 'RTGS';

                    return (
                      <div
                        key={tx.transaction_id || tx.alertId}
                        className="p-4 hover:bg-slate-900/50 transition-all space-y-2.5 group border-l-2 border-transparent hover:border-cyan-400"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-[10px] font-bold border border-slate-700">
                              {tx.payment_format || tx.rail || 'UPI'}
                            </span>
                            <span
                              className={cn(
                                'text-[10px] font-mono font-bold px-2 py-0.5 rounded border',
                                isStructuring
                                  ? 'bg-cyan-950 text-cyan-300 border-cyan-800'
                                  : isHawala
                                  ? 'bg-rose-950 text-rose-300 border-rose-800'
                                  : 'bg-purple-950 text-purple-300 border-purple-800'
                              )}
                            >
                              {isStructuring
                                ? 'PAN STRUCTURING EVASION'
                                : isHawala
                                ? 'HIGH-VALUE HAWALA RTGS'
                                : 'VELOCITY MULE DRAINING'}
                            </span>
                            <span className="text-[10px] font-mono text-slate-500">
                              {tx.timestamp ? new Date(tx.timestamp).toLocaleTimeString() : 'LIVE'}
                            </span>
                          </div>

                          <div className="text-right">
                            <span className="text-sm font-mono font-black text-rose-400">
                              ₹{amountInr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            </span>
                          </div>
                        </div>

                        {/* Remitter -> Beneficiary Details */}
                        <div className="flex items-center justify-between gap-2 text-xs font-mono text-slate-300 pt-1">
                          <div className="flex items-center gap-2 truncate max-w-[70%]">
                            <span className="truncate text-slate-200" title={tx.from_entity}>
                              {tx.from_entity || tx.account_from || 'Remitter VPA'}
                            </span>
                            <ArrowRight className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                            <span className="truncate text-slate-200" title={tx.to_entity}>
                              {tx.to_entity || tx.account_to || 'Beneficiary VPA'}
                            </span>
                          </div>

                          <span className="text-[11px] font-mono text-cyan-400 shrink-0">
                            p={Number(tx.risk_score || 0.98).toFixed(3)}
                          </span>
                        </div>

                        {/* Action buttons & UTR Bar */}
                        <div className="flex items-center justify-between pt-1 text-[11px] font-mono text-slate-400">
                          <div className="flex items-center gap-2">
                            <span>UTR: <strong className="text-slate-300">{tx.transaction_id}</strong></span>
                            <button
                              onClick={() => copyToClipboard(tx.transaction_id, tx.transaction_id)}
                              className="text-slate-500 hover:text-slate-300 transition-colors"
                              title="Copy UTR Number"
                            >
                              {copiedId === tx.transaction_id ? (
                                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => setSelectedAlertForInspection(tx)}
                              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold transition-all flex items-center gap-1"
                            >
                              <Eye className="w-3 h-3 text-cyan-400" />
                              <span>Inspect</span>
                            </button>
                            <button
                              onClick={() => handleOpenSar(tx.sar_id, tx.transaction_id)}
                              className="px-3 py-1 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 text-[10px] font-bold transition-all shadow-glow-cyan flex items-center gap-1"
                            >
                              <FileWarning className="w-3 h-3 text-slate-950" />
                              <span>FIU-IND STR</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        )}

        {/* ==================================================================== */}
        {/* DASHBOARD 2: CRYPTO FORENSICS CRITICAL THREATS                       */}
        {/* ==================================================================== */}
        {(activeDashboard === 'DUAL' || activeDashboard === 'CRYPTO') && (
          <div className="space-y-6">
            {/* Dashboard Header & KPI Bar */}
            <div className="p-5 rounded-2xl glass-card border border-amber-500/30 bg-obsidian-950/90 shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="text-xl">⚡</span>
                  <div>
                    <h2 className="text-base font-black font-mono text-amber-300 tracking-wide uppercase">
                      CRYPTO FORENSICS CRITICAL DASHBOARD
                    </h2>
                    <span className="text-[10px] font-mono text-slate-400">
                      Bitcoin Mempool & Elliptic Graph Topology Forensics
                    </span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-amber-950 text-amber-400 border border-amber-500/40 text-xs font-mono font-bold">
                  {cryptoCriticalAlerts.length} THREATS
                </span>
              </div>

              {/* KPI Cards Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-obsidian-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 block mb-1">TOTAL BTC EXPOSURE</span>
                  <div className="text-sm lg:text-base font-black font-mono text-amber-400 truncate">
                    {cryptoMetrics.exposureBtc.toFixed(4)} BTC
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-obsidian-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 block mb-1">DARKNET MIXERS</span>
                  <div className="text-sm lg:text-base font-black font-mono text-purple-400">
                    {cryptoMetrics.mixerCount} <span className="text-[10px] font-normal text-slate-500">CoinJoin</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-obsidian-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 block mb-1">WHALE TRANSFERS</span>
                  <div className="text-sm lg:text-base font-black font-mono text-rose-400">
                    {cryptoMetrics.whaleCount} <span className="text-[10px] font-normal text-slate-500">&gt;10 BTC</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-obsidian-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 block mb-1">PEELING CHAINS</span>
                  <div className="text-sm lg:text-base font-black font-mono text-orange-400">
                    {cryptoMetrics.peelingCount} <span className="text-[10px] font-normal text-slate-500">Split UTXO</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Crypto Alert Feed */}
            <div className="rounded-2xl glass-card border border-slate-800 bg-obsidian-950/90 overflow-hidden shadow-xl">
              <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between bg-obsidian-900/70">
                <span className="text-xs font-mono font-bold text-slate-300 flex items-center gap-2">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  <span>On-Chain VDA Critical Alerts ({filteredCryptoAlerts.length})</span>
                </span>
                <span className="text-[10px] font-mono text-slate-500">
                  High-Entropy Graph Nodes
                </span>
              </div>

              <div className="divide-y divide-slate-800/60 max-h-[600px] overflow-y-auto custom-scrollbar">
                {filteredCryptoAlerts.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 font-mono text-xs">
                    No active crypto critical threats matching current filters.
                  </div>
                ) : (
                  filteredCryptoAlerts.map((tx) => {
                    const btcVal = Number(tx.amount || tx.btc_value || 0);
                    const flags = tx.flags || [];
                    const isWhale = flags.includes('WHALE_TRANSFER') || btcVal >= 10.0;
                    const isMixer =
                      tx.in_count > 6 ||
                      tx.out_count > 10 ||
                      String(tx.from_entity || '').includes('mixer');

                    return (
                      <div
                        key={tx.transaction_id || tx.alertId}
                        className="p-4 hover:bg-slate-900/50 transition-all space-y-2.5 group border-l-2 border-transparent hover:border-amber-400"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-amber-300 font-mono text-[10px] font-bold border border-slate-700">
                              BTC MEMPOOL
                            </span>
                            <span
                              className={cn(
                                'text-[10px] font-mono font-bold px-2 py-0.5 rounded border',
                                isMixer
                                  ? 'bg-purple-950 text-purple-300 border-purple-800'
                                  : isWhale
                                  ? 'bg-rose-950 text-rose-300 border-rose-800'
                                  : 'bg-orange-950 text-orange-300 border-orange-800'
                              )}
                            >
                              {isMixer
                                ? 'DARKNET COINJOIN MIXER'
                                : isWhale
                                ? 'WHALE OUTLIER TRANSFER'
                                : 'PEELING CHAIN RAPID HOP'}
                            </span>
                            <span className="text-[10px] font-mono text-slate-500">
                              {tx.timestamp ? new Date(tx.timestamp).toLocaleTimeString() : 'LIVE'}
                            </span>
                          </div>

                          <div className="text-right">
                            <span className="text-sm font-mono font-black text-amber-400">
                              {btcVal.toFixed(4)} BTC
                            </span>
                          </div>
                        </div>

                        {/* In/Out count & Addresses */}
                        <div className="flex items-center justify-between gap-2 text-xs font-mono text-slate-300 pt-1">
                          <div className="flex items-center gap-2 truncate max-w-[70%]">
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono shrink-0">
                              {tx.in_count || 1} in &rarr; {tx.out_count || 2} out
                            </span>
                            <span className="truncate text-slate-300" title={tx.from_entity}>
                              {String(tx.from_entity || '').slice(0, 16)}...
                            </span>
                            <ArrowRight className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                            <span className="truncate text-slate-300" title={tx.to_entity}>
                              {String(tx.to_entity || '').slice(0, 16)}...
                            </span>
                          </div>

                          <span className="text-[11px] font-mono text-amber-400 shrink-0">
                            p={Number(tx.risk_score || 0.99).toFixed(3)}
                          </span>
                        </div>

                        {/* Action buttons & Tx Hash Bar */}
                        <div className="flex items-center justify-between pt-1 text-[11px] font-mono text-slate-400">
                          <div className="flex items-center gap-2">
                            <span>Hash: <strong className="text-slate-300">{String(tx.transaction_id || '').slice(0, 12)}...</strong></span>
                            <button
                              onClick={() => copyToClipboard(tx.transaction_id, tx.transaction_id)}
                              className="text-slate-500 hover:text-slate-300 transition-colors"
                              title="Copy Bitcoin Tx Hash"
                            >
                              {copiedId === tx.transaction_id ? (
                                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => setSelectedAlertForInspection(tx)}
                              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold transition-all flex items-center gap-1"
                            >
                              <Eye className="w-3 h-3 text-amber-400" />
                              <span>Inspect</span>
                            </button>
                            <button
                              onClick={() => handleOpenSar(tx.sar_id, tx.transaction_id)}
                              className="px-3 py-1 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-[10px] font-bold transition-all shadow-glow-amber flex items-center gap-1"
                            >
                              <FileWarning className="w-3 h-3 text-slate-950" />
                              <span>Crypto SAR</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------------------ */}
      {/* 3. Deep Forensic Alert Inspector Drawer / Modal                         */}
      {/* ------------------------------------------------------------------------ */}
      {selectedAlertForInspection && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian-950/80 backdrop-blur-md animate-fade-in">
          <div className="w-full max-w-2xl bg-obsidian-900 border border-slate-800 rounded-2xl shadow-2xl p-6 space-y-5 text-xs font-mono relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setSelectedAlertForInspection(null)}
              className="absolute top-5 right-5 p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/40">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-black text-slate-100 uppercase">
                  FORENSIC THREAT TELEMETRY INSPECTOR
                </h3>
                <span className="text-slate-400 text-[11px]">
                  Target Identifier: {selectedAlertForInspection.transaction_id}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2">
              <div className="p-3 rounded-xl bg-obsidian-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 text-[10px] block">ENGINE CLASSIFIER</span>
                <span className="text-cyan-300 font-bold">
                  {selectedAlertForInspection.engine || (selectedAlertForInspection.rail === 'BTC' ? 'CRYPTO_FORENSICS' : 'FIAT_BANKING')}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-obsidian-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 text-[10px] block">RISK CLASSIFICATION</span>
                <span className="text-rose-400 font-black">
                  {selectedAlertForInspection.risk_tier || 'CRITICAL_SAR'} (Score: {Number(selectedAlertForInspection.risk_score || 0.98).toFixed(3)})
                </span>
              </div>
              <div className="p-3 rounded-xl bg-obsidian-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 text-[10px] block">EXPOSURE VOLUME</span>
                <span className="text-slate-100 font-bold">
                  {selectedAlertForInspection.currency === 'BTC' || selectedAlertForInspection.rail === 'BTC'
                    ? `${Number(selectedAlertForInspection.amount || selectedAlertForInspection.btc_value || 0).toFixed(4)} BTC`
                    : `₹${Number(selectedAlertForInspection.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-obsidian-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 text-[10px] block">SETTLEMENT RAIL</span>
                <span className="text-amber-400 font-bold">
                  {selectedAlertForInspection.payment_format || selectedAlertForInspection.rail || 'INR'}
                </span>
              </div>
            </div>

            {/* Entities */}
            <div className="p-3.5 rounded-xl bg-obsidian-950 border border-slate-800 space-y-2">
              <span className="text-slate-500 text-[10px] block">COUNTERPARTY TRACE</span>
              <div className="flex items-center justify-between text-slate-200">
                <span className="text-slate-400">Remitter / Input:</span>
                <strong className="text-cyan-300">{selectedAlertForInspection.from_entity || selectedAlertForInspection.account_from}</strong>
              </div>
              <div className="flex items-center justify-between text-slate-200">
                <span className="text-slate-400">Beneficiary / Output:</span>
                <strong className="text-rose-300">{selectedAlertForInspection.to_entity || selectedAlertForInspection.account_to}</strong>
              </div>
            </div>

            {/* Raw JSON viewer */}
            <div className="space-y-1.5">
              <span className="text-slate-400 text-[11px] block">RAW FORENSIC TELEMETRY RECORD:</span>
              <pre className="p-3 rounded-xl bg-obsidian-950 border border-slate-800 text-[10px] text-slate-300 overflow-x-auto max-h-40">
                {JSON.stringify(selectedAlertForInspection, null, 2)}
              </pre>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                onClick={() => setSelectedAlertForInspection(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold transition-all"
              >
                Close Inspector
              </button>
              <button
                onClick={() => {
                  const sarId = selectedAlertForInspection.sar_id;
                  const txId = selectedAlertForInspection.transaction_id;
                  setSelectedAlertForInspection(null);
                  handleOpenSar(sarId, txId);
                }}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-slate-50 font-bold transition-all shadow-glow-rose flex items-center gap-1.5"
              >
                <FileWarning className="w-3.5 h-3.5" />
                <span>Open SAR Dossier</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
