import React, { useState, useEffect } from 'react';
import {
  CreditCard,
  Bitcoin,
  Layers,
  Activity,
  ShieldAlert,
  Flame,
  X,
  Lock,
  Radio,
  FileWarning,
} from 'lucide-react';
import { Header } from './components/Header';
import { TransactionTriage } from './components/TransactionTriage';
import { CryptoTriage } from './components/CryptoTriage';
import { BatchPortal } from './components/BatchPortal';
import { ObservabilityPortal } from './components/ObservabilityPortal';
import { LiveAuditLedger } from './components/LiveAuditLedger';
import { SARCaseManager } from './components/SARCaseManager';
import { SARInvestigationModal } from './components/SARInvestigationModal';
import { useLiveFeed } from './hooks/useLiveFeed';
import { DEFAULT_API_URL } from './services/api';
import { cn } from './utils/cn';

const INITIAL_HISTORY = [
  {
    entity_id: 'tx_baseline_payroll_01',
    dataset: 'IBM Transactions',
    risk_score: 0.0412,
    risk_tier: 'LOW',
    is_anomaly: false,
    recommended_action: 'AUTO_CLEARED',
    latency_ms: 12.4,
    timestamp: '2026-09-05T18:00:00.000Z',
    inputSummary: 'ACH $3,250.00 (PAYROLL_CORP_881 → EMP_SAVINGS_104)',
  },
  {
    entity_id: 'tx_baseline_smurf_02',
    dataset: 'IBM Transactions',
    risk_score: 0.8845,
    risk_tier: 'ELEVATED',
    is_anomaly: false,
    recommended_action: 'MANUAL_REVIEW',
    latency_ms: 15.1,
    timestamp: '2026-09-05T18:30:00.000Z',
    inputSummary: 'Cash $9,850.00 (SMURF_LAYER_09 → AGGREGATOR_77)',
  },
  {
    entity_id: 'tx_baseline_wire_03',
    dataset: 'IBM Transactions',
    risk_score: 0.9924,
    risk_tier: 'CRITICAL_SAR',
    is_anomaly: true,
    recommended_action: 'AUTO_FLAG_SAR',
    latency_ms: 18.2,
    timestamp: '2026-09-05T19:15:00.000Z',
    inputSummary: 'Wire $485,000.00 (SHELL_CYPRUS_401 → ESCROW_NY_990)',
  },
  {
    entity_id: 'btc_node_darknet_04',
    dataset: 'Elliptic Bitcoin',
    risk_score: 0.9610,
    risk_tier: 'HIGH',
    is_anomaly: true,
    recommended_action: 'ENHANCED_DUE_DILIGENCE',
    latency_ms: 14.8,
    timestamp: '2026-09-05T20:00:00.000Z',
    inputSummary: 'Node btc_darknet_491820 (t=34, 165 feats)',
  },
];

export default function App() {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [activeTab, setActiveTab] = useState('live');
  const [history, setHistory] = useState(INITIAL_HISTORY);

  // Alert toast state for immediate critical notifications
  const [activeToast, setActiveToast] = useState(null);

  // SAR Investigation Modal & Separate Alert Banner states
  const [isSarModalOpen, setIsSarModalOpen] = useState(false);
  const [selectedSarId, setSelectedSarId] = useState(null);
  const [activeFiatAlertBanner, setActiveFiatAlertBanner] = useState(null);
  const [activeCryptoAlertBanner, setActiveCryptoAlertBanner] = useState(null);
  const [sarMetrics, setSarMetrics] = useState({
    totalSarsGenerated: 0,
    pendingReviewCount: 0,
  });

  // Initialize live WebSocket stream hook
  const liveFeed = useLiveFeed(apiUrl);

  // Modal helper handlers
  const openSarModal = (sarId) => {
    setSelectedSarId(sarId);
    setIsSarModalOpen(true);
  };

  const closeSarModal = () => {
    setSelectedSarId(null);
    setIsSarModalOpen(false);
  };

  const handleSarStatusUpdated = (sarId, newStatus) => {
    // Update local metrics and transaction statuses
    setSarMetrics((prev) => ({
      ...prev,
      pendingReviewCount:
        newStatus === 'FILED_WITH_FIU' || newStatus === 'DISMISSED'
          ? Math.max(0, prev.pendingReviewCount - 1)
          : prev.pendingReviewCount,
    }));

    // Update transactions in liveFeed if they reference this sar_id
    if (liveFeed.updateTransactionStatus) {
      liveFeed.updateTransactionStatus(sarId, newStatus);
    }

    // Dismiss active banners if matching this resolved case
    if (
      activeFiatAlertBanner?.sar_id === sarId &&
      (newStatus === 'FILED_WITH_FIU' || newStatus === 'DISMISSED')
    ) {
      setActiveFiatAlertBanner(null);
    }
    if (
      activeCryptoAlertBanner?.sar_id === sarId &&
      (newStatus === 'FILED_WITH_FIU' || newStatus === 'DISMISSED')
    ) {
      setActiveCryptoAlertBanner(null);
    }

    setActiveToast({
      id: Date.now(),
      tier: 'STATUS_UPDATE',
      entity_id: sarId,
      score: 1.0,
      action: `Case remediation state transitioned to ${newStatus}`,
    });
  };

  // Real-Time Event Listener for incoming SAR_DISPATCHED WebSocket alerts
  useEffect(() => {
    if (liveFeed.lastSarDispatched) {
      const data = liveFeed.lastSarDispatched;
      const isCrypto =
        data.engine === 'CRYPTO_FORENSICS' ||
        data.rail === 'BTC' ||
        data.currency === 'BTC' ||
        Boolean(data.exposure_btc);

      // Increment SAR metrics in KPI header
      setSarMetrics((prev) => ({
        totalSarsGenerated: prev.totalSarsGenerated + 1,
        pendingReviewCount: prev.pendingReviewCount + 1,
      }));

      const bannerData = {
        sar_id: data.sar_id,
        transaction_id: data.triggering_tx_id || data.sar_id,
        typology: data.typology || (isCrypto ? 'On-Chain VDA Anomaly' : 'Automated PMLA Ring Dispatched'),
        amount: isCrypto ? data.exposure_btc : (data.exposure_inr || 0),
        exposure_inr: data.exposure_inr || 0,
        exposure_btc: data.exposure_btc || 0,
        currency: isCrypto ? 'BTC' : 'INR',
        rail: data.rail || (isCrypto ? 'BTC' : 'UPI'),
        suspect: data.suspect || (isCrypto ? 'Unhosted Wallet Target' : 'Automated Surveillance Target'),
        timestamp: data.timestamp || data.receivedAt || new Date().toISOString(),
      };

      if (isCrypto) {
        setActiveCryptoBanner(bannerData);
      } else {
        setActiveFiatBanner(bannerData);
      }

      // Retroactively link triggering transaction in circular ledger
      if (liveFeed.updateTransactionSar) {
        liveFeed.updateTransactionSar(
          data.sar_id,
          data.triggering_tx_id || data.suspect
        );
      }
    }
  }, [liveFeed.lastSarDispatched]);

  // Separate Critical Alert Banner hook for Indian Banking events
  useEffect(() => {
    if (
      liveFeed.activeFiatAlert &&
      (liveFeed.activeFiatAlert.risk_tier === 'CRITICAL_SAR' ||
        liveFeed.activeFiatAlert.risk_tier === 'CRITICAL')
    ) {
      const alert = liveFeed.activeFiatAlert;
      const flags = alert.flags || [];
      const typStr =
        flags.length > 0 ? flags.join(', ') : 'High-Risk Banking Laundering Signature';

      setActiveFiatAlertBanner((prev) => {
        if (prev?.sar_id && prev.sar_id.startsWith('SAR-IND')) return prev;
        return {
          sar_id: alert.sar_id || `SAR-${alert.transaction_id}`,
          transaction_id: alert.transaction_id,
          rail: alert.rail || 'UPI',
          typology: typStr,
          amount: alert.amount || 0,
          exposure_inr: alert.amount || 0,
          currency: 'INR',
          from_entity: alert.from_entity,
          to_entity: alert.to_entity,
          suspect: alert.from_entity || 'Unknown Remitter',
          timestamp: alert.timestamp || new Date().toISOString(),
        };
      });
    }
  }, [liveFeed.activeFiatAlert]);

  // Separate Critical Alert Banner hook for Crypto Forensics events
  useEffect(() => {
    if (
      liveFeed.activeCryptoAlert &&
      (liveFeed.activeCryptoAlert.risk_tier === 'CRITICAL_SAR' ||
        liveFeed.activeCryptoAlert.risk_tier === 'CRITICAL')
    ) {
      const alert = liveFeed.activeCryptoAlert;
      const flags = alert.flags || [];
      const typStr =
        flags.length > 0 ? flags.join(', ') : 'High-Entropy Darknet / Whale Signature';

      setActiveCryptoAlertBanner((prev) => {
        if (prev?.sar_id && prev.sar_id.startsWith('SAR-IND')) return prev;
        return {
          sar_id: alert.sar_id || `SAR-${alert.transaction_id}`,
          transaction_id: alert.transaction_id,
          rail: alert.rail || 'BTC',
          typology: typStr,
          amount: alert.amount || 0,
          exposure_btc: alert.amount || 0,
          currency: 'BTC',
          from_entity: alert.from_entity,
          to_entity: alert.to_entity,
          suspect: alert.from_entity || 'bc1q_unresolved',
          timestamp: alert.timestamp || new Date().toISOString(),
        };
      });
    }
  }, [liveFeed.activeCryptoAlert]);

  // Appends newly scored entity to session history ledger and triggers toast if critical
  const handleScored = (result) => {
    setHistory((prev) => [result, ...prev]);

    if (result.risk_tier === 'CRITICAL_SAR' || result.is_anomaly) {
      setActiveToast({
        id: Date.now(),
        tier: result.risk_tier,
        entity_id: result.entity_id,
        score: result.risk_score,
        action: result.recommended_action,
      });

      const isCrypto =
        result.dataset?.toLowerCase().includes('elliptic') ||
        result.dataset?.toLowerCase().includes('crypto') ||
        result.currency === 'BTC' ||
        result.rail === 'BTC';

      const bannerData = {
        sar_id: result.sar_id || result.entity_id,
        transaction_id: result.transaction_id || result.entity_id,
        typology: result.recommended_action || 'Critical Anomaly Detected',
        amount: result.amount || 0,
        exposure_inr: !isCrypto ? (result.amount || 0) : 0,
        exposure_btc: isCrypto ? (result.amount || 0) : 0,
        currency: isCrypto ? 'BTC' : 'INR',
        rail: result.payment_format || result.rail || (isCrypto ? 'BTC' : 'UPI'),
        suspect: result.account_from || result.from_address || result.entity_id,
        timestamp: result.timestamp || new Date().toISOString(),
      };

      if (result.risk_tier === 'CRITICAL_SAR') {
        if (isCrypto) {
          setActiveCryptoAlertBanner(bannerData);
        } else {
          setActiveFiatAlertBanner(bannerData);
        }
      }

      // Auto-dismiss toast after 6 seconds
      setTimeout(() => {
        setActiveToast((current) =>
          current?.entity_id === result.entity_id ? null : current
        );
      }, 6000);
    }
  };

  const handleAddBatchToLedger = (batchItems) => {
    setHistory((prev) => [...batchItems, ...prev]);
    setActiveTab('observability');
  };

  const handleClearHistory = () => {
    if (
      window.confirm('Clear all session case records from the current audit ledger?')
    ) {
      setHistory([]);
    }
  };

  const tabs = [
    {
      id: 'live',
      label: 'Live Surveillance Ledger',
      sublabel: 'WebSocket Dual-Stream',
      icon: Radio,
      color: 'text-rose-400',
      badge:
        liveFeed.transactions.length > 0
          ? liveFeed.transactions.length
          : undefined,
      isLive: true,
    },
    {
      id: 'transactions',
      label: 'Banking Transactions',
      sublabel: 'IBM CatBoost',
      icon: CreditCard,
      color: 'text-cyan-400',
    },
    {
      id: 'crypto',
      label: 'Crypto Graph Nodes',
      sublabel: 'Elliptic XGBoost',
      icon: Bitcoin,
      color: 'text-orange-400',
    },
    {
      id: 'batch',
      label: 'Batch Ingestion Portal',
      sublabel: 'Vectorized Processing',
      icon: Layers,
      color: 'text-indigo-400',
    },
    {
      id: 'sar',
      label: 'SAR Case Management',
      sublabel: 'PMLA Compliance & FIU',
      icon: FileWarning,
      color: 'text-amber-400',
      badge:
        sarMetrics.totalSarsGenerated > 0
          ? sarMetrics.totalSarsGenerated
          : liveFeed.dispatchedSarCount > 0
          ? liveFeed.dispatchedSarCount
          : undefined,
    },
    {
      id: 'observability',
      label: 'SRE Observability & Ledger',
      sublabel: 'Telemetry & Audit Logs',
      icon: Activity,
      color: 'text-emerald-400',
      badge: history.length,
    },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-obsidian-900 text-slate-100 font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Module 1: Persistent Glassmorphic Header & System Telemetry */}
      <Header
        apiUrl={apiUrl}
        onApiUrlChange={setApiUrl}
        wsStatus={liveFeed.connectionStatus}
        threatCount={liveFeed.telemetry.threatFlagsCount}
        sarMetrics={sarMetrics}
      />

      {/* Navigation Sub-Header Bar */}
      <nav
        aria-label="Main Navigation"
        className="border-b border-slate-800/80 bg-obsidian-950/60 backdrop-blur-md px-4 lg:px-8 py-2 sticky top-[65px] z-40"
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between overflow-x-auto no-scrollbar gap-2">
          <div className="flex items-center gap-1 sm:gap-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-2.5 px-3.5 py-2 rounded-xl text-xs font-mono font-semibold transition-all whitespace-nowrap',
                    isActive
                      ? tab.isLive
                        ? 'bg-rose-950/50 text-rose-200 border border-rose-500/50 shadow-glow-rose'
                        : 'bg-slate-800 text-slate-100 border border-cyan-500/40 shadow-glow-cyan'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                  )}
                >
                  <div className="relative flex items-center">
                    <Icon
                      className={cn(
                        'w-4 h-4',
                        isActive ? tab.color : 'text-slate-400'
                      )}
                    />
                    {tab.isLive && liveFeed.connectionStatus === 'CONNECTED' && (
                      <span className="absolute -top-1 -right-1 flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500" />
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col text-left">
                    <span>{tab.label}</span>
                    <span className="text-[10px] text-slate-400 font-normal hidden sm:inline">
                      {tab.sublabel}
                    </span>
                  </div>
                  {tab.badge !== undefined && (
                    <span
                      className={cn(
                        'px-1.5 py-0.2 rounded-full text-[10px] font-mono',
                        isActive
                          ? tab.isLive
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                          : 'bg-slate-800 text-slate-400'
                      )}
                    >
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="hidden lg:flex items-center gap-2 text-xs font-mono text-slate-400">
            <Lock className="w-3.5 h-3.5 text-cyan-400" />
            <span>FinCEN 314(a) Compliant Session</span>
          </div>
        </div>
      </nav>

      {/* 1. Indian Banking Critical Compliance Alert Banner */}
      {activeFiatAlertBanner && (
        <div className="border-b border-rose-500/50 bg-gradient-to-r from-obsidian-950 via-rose-950/80 to-obsidian-950 text-rose-100 backdrop-blur-md px-4 lg:px-8 py-3 sticky top-[113px] z-30 shadow-2xl shadow-rose-950/70 animate-fade-in">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-3.5">
              <div className="relative flex items-center justify-center p-2 rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shrink-0">
                <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-cyan-400 opacity-75" />
                <span className="relative text-base">🇮🇳</span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center flex-wrap gap-2 text-xs font-mono">
                <span className="font-black text-cyan-300 tracking-wider uppercase flex items-center gap-1.5">
                  INDIAN BANKING // FIU-IND PMLA CRITICAL ALERT
                </span>
                <span className="text-slate-500 hidden sm:inline">—</span>
                <span className="px-2 py-0.5 rounded bg-rose-900/60 text-rose-200 border border-rose-700/60 font-semibold">
                  {activeFiatAlertBanner.typology}
                </span>
                <span className="text-slate-300">
                  UTR: <strong className="text-cyan-300 font-bold">{activeFiatAlertBanner.transaction_id || activeFiatAlertBanner.sar_id}</strong>
                </span>
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700 font-bold">
                  {activeFiatAlertBanner.rail || 'UPI'}
                </span>
                <span className="text-rose-400 font-bold">
                  Exposure: ₹{Number(activeFiatAlertBanner.exposure_inr || activeFiatAlertBanner.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
                {activeFiatAlertBanner.suspect && (
                  <span className="text-slate-400 hidden xl:inline">
                    Suspect: <strong className="text-slate-200">{activeFiatAlertBanner.suspect}</strong>
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 self-end md:self-center shrink-0">
              <button
                onClick={() => openSarModal(activeFiatAlertBanner.sar_id)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-slate-950 text-xs font-mono font-bold transition-all shadow-glow-cyan hover:scale-[1.02]"
              >
                <FileWarning className="w-3.5 h-3.5 text-slate-950" />
                <span>Investigate FIU-IND STR</span>
              </button>
              <button
                onClick={() => setActiveFiatAlertBanner(null)}
                className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                title="Dismiss Indian Banking Alert"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Crypto Forensics Critical On-Chain Alert Banner */}
      {activeCryptoAlertBanner && (
        <div className={cn(
          "border-b border-amber-500/50 bg-gradient-to-r from-obsidian-950 via-amber-950/80 to-obsidian-950 text-amber-100 backdrop-blur-md px-4 lg:px-8 py-3 z-30 shadow-2xl shadow-amber-950/70 animate-fade-in",
          activeFiatAlertBanner ? "relative" : "sticky top-[113px]"
        )}>
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-3.5">
              <div className="relative flex items-center justify-center p-2 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/40 shrink-0">
                <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-amber-400 opacity-75" />
                <span className="relative text-base">⚡</span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center flex-wrap gap-2 text-xs font-mono">
                <span className="font-black text-amber-300 tracking-wider uppercase flex items-center gap-1.5">
                  CRYPTO FORENSICS // ON-CHAIN VDA ANOMALY ALERT
                </span>
                <span className="text-slate-500 hidden sm:inline">—</span>
                <span className="px-2 py-0.5 rounded bg-amber-900/60 text-amber-200 border border-amber-700/60 font-semibold">
                  {activeCryptoAlertBanner.typology}
                </span>
                <span className="text-slate-300">
                  Tx Hash: <strong className="text-amber-300 font-bold">{String(activeCryptoAlertBanner.transaction_id || '').slice(0, 14)}...</strong>
                </span>
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-amber-300 border border-slate-700 font-bold">
                  BTC MEMPOOL
                </span>
                <span className="text-amber-400 font-bold">
                  Exposure: {Number(activeCryptoAlertBanner.exposure_btc || activeCryptoAlertBanner.amount || 0).toFixed(4)} BTC
                </span>
                {activeCryptoAlertBanner.suspect && (
                  <span className="text-slate-400 hidden xl:inline">
                    Target: <strong className="text-slate-200">{String(activeCryptoAlertBanner.suspect).slice(0, 20)}...</strong>
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 self-end md:self-center shrink-0">
              <button
                onClick={() => openSarModal(activeCryptoAlertBanner.sar_id)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-mono font-bold transition-all shadow-glow-amber hover:scale-[1.02]"
              >
                <FileWarning className="w-3.5 h-3.5 text-slate-950" />
                <span>Investigate Crypto SAR</span>
              </button>
              <button
                onClick={() => setActiveCryptoAlertBanner(null)}
                className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                title="Dismiss Crypto Forensics Alert"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Workspace Container */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-4 lg:p-8 space-y-6">
        {activeTab === 'live' && (
          <LiveAuditLedger
            transactions={liveFeed.transactions}
            telemetry={liveFeed.telemetry}
            isPaused={liveFeed.isPaused}
            onTogglePause={liveFeed.togglePause}
            onClearFeed={liveFeed.clearFeed}
            activeAlert={liveFeed.activeAlert}
            activeFiatAlert={liveFeed.activeFiatAlert}
            activeCryptoAlert={liveFeed.activeCryptoAlert}
            onDismissAlert={liveFeed.dismissAlert}
            onDismissFiatAlert={liveFeed.dismissFiatAlert}
            onDismissCryptoAlert={liveFeed.dismissCryptoAlert}
            wsStatus={liveFeed.connectionStatus}
            onOpenSarModal={openSarModal}
            openSarModal={openSarModal}
            apiUrl={apiUrl}
            sarMetrics={sarMetrics}
            onSarGenerated={(newCase) => {
              setSarMetrics((prev) => ({
                totalSarsGenerated: prev.totalSarsGenerated + 1,
                pendingReviewCount: prev.pendingReviewCount + 1,
              }));
              setActiveToast({
                id: Date.now(),
                tier: 'CRITICAL_SAR',
                entity_id: newCase.sar_id,
                score: 1.0,
                action: `SAR Dossier ${newCase.sar_id} initialized`,
              });
            }}
          />
        )}
        {activeTab === 'transactions' && (
          <TransactionTriage apiUrl={apiUrl} onScored={handleScored} />
        )}
        {activeTab === 'crypto' && (
          <CryptoTriage apiUrl={apiUrl} onScored={handleScored} />
        )}
        {activeTab === 'batch' && (
          <BatchPortal
            apiUrl={apiUrl}
            onAddBatchToLedger={handleAddBatchToLedger}
          />
        )}
        {activeTab === 'sar' && (
          <SARCaseManager apiUrl={apiUrl} onOpenSarModal={openSarModal} />
        )}
        {activeTab === 'observability' && (
          <ObservabilityPortal
            apiUrl={apiUrl}
            history={history}
            onClearHistory={handleClearHistory}
          />
        )}
      </main>

      {/* Root Mounted Regulatory SAR Investigation Dossier Modal */}
      <SARInvestigationModal
        isOpen={isSarModalOpen}
        onClose={closeSarModal}
        onStatusUpdated={handleSarStatusUpdated}
        sarId={selectedSarId}
        apiUrl={apiUrl}
      />

      {/* Floating Critical Alert Toast */}
      {activeToast && (
        <div className="fixed bottom-6 right-6 z-50 max-w-md w-full p-4 rounded-2xl glass-card border border-rose-500/60 bg-obsidian-950/95 shadow-glow-rose animate-fade-in">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/40">
                <Flame className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-rose-400 uppercase tracking-wider">
                    CRITICAL SAR ALERT DISPATCHED
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-rose-900/60 text-rose-300">
                    P={((activeToast.score || 0.99) * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="text-xs text-slate-200 mt-1 font-mono">
                  Entity <strong className="text-rose-300">{activeToast.entity_id}</strong> triggered automatic Celery SAR filing protocol: <strong className="text-cyan-300">{activeToast.action}</strong>.
                </p>
              </div>
            </div>
            <button
              onClick={() => setActiveToast(null)}
              className="text-slate-500 hover:text-slate-300 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Enterprise Platform Footer */}
      <footer className="border-t border-slate-800/80 bg-obsidian-950 px-4 lg:px-8 py-4 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-cyan-400" />
            <span>QuantumAML Nexus Compliance Engine</span>
            <span className="text-slate-600">•</span>
            <span>Zero-Downtime Pipeline Architecture</span>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-emerald-400">SLA Enforcement: &lt; 50.0 ms</span>
            <span className="text-slate-600">•</span>
            <span>Target: {apiUrl}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
