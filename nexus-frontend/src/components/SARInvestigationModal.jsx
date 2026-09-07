import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ShieldAlert,
  FileText,
  Download,
  CheckCircle2,
  X,
  AlertCircle,
  Clock,
  ArrowRight,
  Copy,
  Check,
  Loader2,
  RefreshCw,
  User,
  Building2,
  Scale,
  Layers,
  Activity,
} from 'lucide-react';
import { DEFAULT_API_URL } from '../services/api';
import { cn } from '../utils/cn';

/**
 * Human-readable mapping for FIU-IND typologies.
 */
const TYPOLOGY_LABELS = {
  IN_TYP_STRUCT: 'IN_TYP_STRUCT — PAN Structuring Evasion (< ₹50,000)',
  IN_TYP_HAWALA: 'IN_TYP_HAWALA — Abnormal High-Value Wire Flow',
  IN_TYP_MULE: 'IN_TYP_MULE — High-Velocity Mule Account Smurfing',
  IN_TYP_VDA_MIX: 'IN_TYP_VDA_MIX — Unhosted Mixer / Peel Chain Flow',
};

/**
 * Regulatory Case Status styling definitions.
 */
const STATUS_CONFIG = {
  PENDING_REVIEW: {
    label: 'PENDING_REVIEW',
    badge: 'bg-amber-950/70 text-amber-300 border-amber-500/50 shadow-glow-amber',
    dot: 'bg-amber-400',
  },
  FILED_WITH_FIU: {
    label: 'FILED_WITH_FIU',
    badge: 'bg-emerald-950/70 text-emerald-300 border-emerald-500/50 shadow-glow-emerald',
    dot: 'bg-emerald-400',
  },
  DISMISSED: {
    label: 'DISMISSED',
    badge: 'bg-slate-800/80 text-slate-400 border-slate-700',
    dot: 'bg-slate-400',
  },
  ESCALATED: {
    label: 'ESCALATED',
    badge: 'bg-purple-950/70 text-purple-300 border-purple-500/50 shadow-glow-purple',
    dot: 'bg-purple-400',
  },
};

/**
 * SARInvestigationModal
 * 
 * Standalone regulatory dossier investigation modal for QuantumAML Nexus.
 * Fetches, displays, and manages an individual Suspicious Transaction Report (STR / SAR)
 * conforming to FIU-IND FINnet 2.0 / FINGate specifications under India's PMLA.
 */
export function SARInvestigationModal({
  isOpen,
  onClose,
  sarId,
  onStatusUpdated,
  apiUrl = DEFAULT_API_URL,
}) {
  // Data ingestion & form states
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [notesInput, setNotesInput] = useState('');
  const [successMessage, setSuccessMessage] = useState(null);

  // File export states
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingJson, setDownloadingJson] = useState(false);
  const [copiedId, setCopiedId] = useState(false);

  // Remote data fetcher
  const fetchCase = useCallback(async () => {
    if (!sarId) return;
    setLoading(true);
    setError(null);

    try {
      const cleanUrl = apiUrl.replace(/\/+$/, '');
      const response = await fetch(`${cleanUrl}/api/v1/sar/${encodeURIComponent(sarId)}`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setCaseData(data);
    } catch (err) {
      console.error('Failed to load SAR case:', err);
      setError(err.message || 'Unable to retrieve regulatory SAR dossier.');
    } finally {
      setLoading(false);
    }
  }, [sarId, apiUrl]);

  // Fetch when modal opens with valid sarId
  useEffect(() => {
    if (isOpen && sarId) {
      fetchCase();
      setNotesInput('');
      setSuccessMessage(null);
    } else if (!isOpen) {
      setCaseData(null);
      setError(null);
    }
  }, [isOpen, sarId, fetchCase]);

  // ESC key listener & body scroll lock
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [isOpen, onClose]);

  // Copy SAR ID helper
  const handleCopyId = () => {
    if (!sarId) return;
    navigator.clipboard.writeText(sarId).then(() => {
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    });
  };

  // Statutory FIU Deadline formatted string & countdown
  const deadlineInfo = useMemo(() => {
    if (!caseData?.fiu_deadline) {
      return { formatted: '7 Working Days (PMLA Rule 3)', remaining: 'Regulatory Window Active', isExpired: false };
    }
    try {
      const deadline = new Date(caseData.fiu_deadline);
      const now = new Date();
      const diffMs = deadline - now;
      const formatted = deadline.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });

      if (diffMs <= 0) {
        return { formatted, remaining: 'EXPIRED — IMMEDIATE ACTION REQUIRED', isExpired: true };
      }

      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      return {
        formatted,
        remaining: `${diffDays}d ${diffHours}h remaining`,
        isExpired: false,
      };
    } catch {
      return { formatted: String(caseData.fiu_deadline), remaining: '7 Working Days', isExpired: false };
    }
  }, [caseData?.fiu_deadline]);

  // Export PDF Handler
  const handleExportPdf = async () => {
    if (!sarId) return;
    setDownloadingPdf(true);
    try {
      const cleanUrl = apiUrl.replace(/\/+$/, '');
      const response = await fetch(`${cleanUrl}/api/v1/sar/${encodeURIComponent(sarId)}/export?format=pdf`);
      if (!response.ok) {
        throw new Error(`Export failed with HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const objectUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = `${sarId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(objectUrl);
    } catch (err) {
      console.error('PDF export error:', err);
      alert(`Failed to download PDF dossier: ${err.message}`);
    } finally {
      setDownloadingPdf(false);
    }
  };

  // Export JSON Handler (FINnet 2.0)
  const handleExportJson = async () => {
    if (!sarId) return;
    setDownloadingJson(true);
    try {
      const cleanUrl = apiUrl.replace(/\/+$/, '');
      const response = await fetch(`${cleanUrl}/api/v1/sar/${encodeURIComponent(sarId)}/export?format=json`);
      if (!response.ok) {
        throw new Error(`Export failed with HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const objectUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = `${sarId}_FINNET2.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(objectUrl);
    } catch (err) {
      console.error('JSON export error:', err);
      alert(`Failed to export FINnet 2.0 JSON: ${err.message}`);
    } finally {
      setDownloadingJson(false);
    }
  };

  // Status transition handler (FILED_WITH_FIU / DISMISSED / ESCALATED)
  const handleTransitionStatus = async (newStatus) => {
    if (!sarId) return;
    setActionLoading(true);
    setSuccessMessage(null);

    try {
      const cleanUrl = apiUrl.replace(/\/+$/, '');
      const response = await fetch(`${cleanUrl}/api/v1/sar/${encodeURIComponent(sarId)}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          new_status: newStatus,
          analyst_id: 'INV-PMLA-99',
          resolution_notes: notesInput || `Status transitioned to ${newStatus} via Regulatory Console`,
        }),
      });

      if (!response.ok) {
        throw new Error(`Status update failed with HTTP ${response.status}`);
      }

      const updated = await response.json();
      setCaseData(updated);
      setSuccessMessage(`Regulatory case status successfully updated to ${newStatus}`);
      if (onStatusUpdated) {
        onStatusUpdated(sarId, newStatus);
      }
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err) {
      console.error('Status transition error:', err);
      alert(`Failed to update case status: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (!isOpen) return null;

  const currentStatusConfig = STATUS_CONFIG[caseData?.status] || STATUS_CONFIG.PENDING_REVIEW;
  const typologyKey = caseData?.grounds_of_suspicion?.primary_typology;
  const typologyLabel = TYPOLOGY_LABELS[typologyKey] || typologyKey || 'PAN Structuring Evasion';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 lg:p-6 bg-obsidian-950/80 backdrop-blur-md animate-fade-in"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl max-h-[92vh] flex flex-col rounded-2xl bg-obsidian-900 border border-slate-700/80 shadow-2xl shadow-cyan-950/40 text-slate-100 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ==================================================================== */}
        {/* Header Banner */}
        {/* ==================================================================== */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-obsidian-950/90 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/40">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-mono font-bold tracking-wider text-amber-400 uppercase">
                FIU-IND FORM STR // REGULATORY DOSSIER
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <h2 className="text-base sm:text-lg font-mono font-bold text-slate-100">
                  {sarId || 'SAR-IND-CASE'}
                </h2>
                {sarId && (
                  <button
                    onClick={handleCopyId}
                    className="p-1 rounded text-slate-400 hover:text-cyan-300 hover:bg-slate-800 transition-colors"
                    title="Copy SAR Identifier"
                  >
                    {copiedId ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {caseData?.status && (
              <span
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold border',
                  currentStatusConfig.badge
                )}
              >
                <span className={cn('w-2 h-2 rounded-full animate-pulse', currentStatusConfig.dot)} />
                {currentStatusConfig.label}
              </span>
            )}

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
              title="Close (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* ==================================================================== */}
        {/* Scrollable Modal Body */}
        {/* ==================================================================== */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6">
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 space-y-3">
              <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
              <p className="text-sm font-mono text-slate-400">Loading statutory case dossier from repository...</p>
            </div>
          )}

          {error && !loading && (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/50 text-rose-200 flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold">Failed to Retrieve SAR Dossier</p>
                  <p className="text-xs font-mono text-rose-300/80 mt-1">{error}</p>
                </div>
              </div>
              <button
                onClick={fetchCase}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-900/60 hover:bg-rose-800/80 text-xs font-mono text-rose-200 border border-rose-700 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry</span>
              </button>
            </div>
          )}

          {caseData && !loading && (
            <>
              {/* Status Success Message */}
              {successMessage && (
                <div className="p-3 rounded-xl bg-emerald-950/50 border border-emerald-500/40 text-emerald-300 text-xs font-mono flex items-center gap-2 animate-fade-in">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>{successMessage}</span>
                </div>
              )}

              {/* -------------------------------------------------------------- */}
              {/* Executive Summary Strip (3-column metadata card) */}
              {/* -------------------------------------------------------------- */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 rounded-xl bg-slate-950/70 border border-slate-800 shadow-sm">
                <div className="space-y-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                    Total Cumulative Exposure
                  </span>
                  <div className="text-base sm:text-lg font-mono font-bold text-emerald-400">
                    {caseData.total_exposure_inr
                      ? `₹${Number(caseData.total_exposure_inr).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                      : caseData.total_exposure_btc
                      ? `${caseData.total_exposure_btc} BTC`
                      : '₹0.00'}
                  </div>
                </div>

                <div className="space-y-1 border-t md:border-t-0 md:border-l border-slate-800/80 pt-2 md:pt-0 md:pl-4">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Clock className="w-3 h-3 text-amber-400" />
                    Statutory Deadline (PMLA Rule 3)
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs sm:text-sm font-mono font-bold text-slate-200">
                      {deadlineInfo.formatted}
                    </span>
                    <span
                      className={cn(
                        'text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded',
                        deadlineInfo.isExpired
                          ? 'bg-rose-950 text-rose-300 border border-rose-700'
                          : 'bg-amber-950/60 text-amber-300 border border-amber-800/60'
                      )}
                    >
                      {deadlineInfo.remaining}
                    </span>
                  </div>
                </div>

                <div className="space-y-1 border-t md:border-t-0 md:border-l border-slate-800/80 pt-2 md:pt-0 md:pl-4">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                    Primary Grounds Typology
                  </span>
                  <div className="text-xs font-mono font-bold text-cyan-300 truncate" title={typologyLabel}>
                    {typologyKey || 'IN_TYP_STRUCT'}
                  </div>
                </div>
              </div>

              {/* -------------------------------------------------------------- */}
              {/* Section 1: Grounds of Suspicion & Legal Narrative */}
              {/* -------------------------------------------------------------- */}
              <div className="rounded-xl border border-amber-500/30 bg-gradient-to-br from-amber-950/20 via-obsidian-950 to-slate-900/60 p-4 space-y-2.5">
                <div className="flex items-center justify-between border-b border-amber-500/20 pb-2">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-mono font-bold text-slate-200">
                      Section 1: Grounds of Suspicion & Legal Narrative
                    </span>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold">
                    {typologyLabel}
                  </span>
                </div>

                <p className="text-xs sm:text-sm text-slate-200 font-mono leading-relaxed bg-obsidian-950/80 p-3.5 rounded-xl border border-slate-800">
                  {caseData.grounds_of_suspicion?.narrative_summary ||
                    'Synthesized regulatory audit narrative pending or not provided.'}
                </p>
              </div>

              {/* -------------------------------------------------------------- */}
              {/* Section 2: Suspect & Counterparty Ledger */}
              {/* -------------------------------------------------------------- */}
              <div className="rounded-xl border border-slate-800 bg-obsidian-950/60 p-4 space-y-3">
                <div className="flex items-center gap-2 border-b border-slate-800/80 pb-2">
                  <User className="w-4 h-4 text-rose-400" />
                  <span className="text-xs font-mono font-bold text-slate-200">
                    Section 2: Suspect & Counterparty Ledger
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Suspect Profile */}
                  <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs font-mono">
                    <div className="flex items-center justify-between border-b border-slate-800/60 pb-1.5">
                      <span className="text-rose-400 font-bold">Primary Suspect Entity</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                        {caseData.suspect?.kyc_risk_rating || 'CRITICAL'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Entity ID / VPA:</span>
                      <span className="text-slate-200 font-semibold truncate max-w-[200px]" title={caseData.suspect?.entity_identifier}>
                        {caseData.suspect?.entity_identifier || 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Entity Type:</span>
                      <span className="text-slate-300">{caseData.suspect?.entity_type || 'Individual'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Institution:</span>
                      <span className="text-cyan-400">{caseData.suspect?.institution_name || caseData.suspect?.ifsc_or_routing || 'Payer Switch'}</span>
                    </div>
                    {caseData.suspect?.risk_indicators && caseData.suspect.risk_indicators.length > 0 && (
                      <div className="pt-1 flex flex-wrap gap-1">
                        {caseData.suspect.risk_indicators.map((flag, idx) => (
                          <span key={idx} className="text-[10px] px-1.5 py-0.2 rounded bg-rose-900/40 text-rose-300 border border-rose-800/60">
                            {flag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Counterparty Profile */}
                  <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs font-mono">
                    <div className="flex items-center justify-between border-b border-slate-800/60 pb-1.5">
                      <span className="text-cyan-400 font-bold">Counterparty Destination</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                        {caseData.counterparty?.kyc_risk_rating || 'CONSOLIDATOR'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Destination VPA / ID:</span>
                      <span className="text-slate-200 font-semibold truncate max-w-[200px]" title={caseData.counterparty?.entity_identifier}>
                        {caseData.counterparty?.entity_identifier || 'Aggregator Destination'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Settlement Switch:</span>
                      <span className="text-cyan-400">{caseData.counterparty?.institution_name || caseData.counterparty?.ifsc_or_routing || 'Domestic Switch'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Entity Jurisdiction:</span>
                      <span className="text-slate-300">IN / Domestic Banking Rail</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* -------------------------------------------------------------- */}
              {/* Section 3: Aggregated Transactions Table */}
              {/* -------------------------------------------------------------- */}
              <div className="rounded-xl border border-slate-800 bg-obsidian-950/60 overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Layers className="w-4 h-4 text-cyan-400" />
                    <span className="text-xs font-mono font-bold text-slate-200">
                      Section 3: Aggregated Transactions Table
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    {caseData.transactions?.length || 0} Linked Record(s)
                  </span>
                </div>

                <div className="max-h-48 overflow-y-auto no-scrollbar">
                  <table className="w-full text-left text-xs font-mono border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-900/70 text-slate-400 uppercase text-[10px]">
                        <th className="py-2.5 px-3">Timestamp (UTC)</th>
                        <th className="py-2.5 px-3">Rail</th>
                        <th className="py-2.5 px-3">Counterparty From → To</th>
                        <th className="py-2.5 px-3 text-right">Amount</th>
                        <th className="py-2.5 px-3 text-right">Anomaly Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300">
                      {(!caseData.transactions || caseData.transactions.length === 0) ? (
                        <tr>
                          <td colSpan={5} className="py-6 text-center text-slate-500 font-mono">
                            No individual transactions linked to this dossier.
                          </td>
                        </tr>
                      ) : (
                        caseData.transactions.map((tx, idx) => (
                          <tr key={tx.transaction_id || idx} className="hover:bg-slate-800/40">
                            <td className="py-2 px-3 text-slate-400 whitespace-nowrap text-[11px]">
                              {tx.timestamp ? String(tx.timestamp).slice(0, 19).replace('T', ' ') : 'N/A'}
                            </td>
                            <td className="py-2 px-3 whitespace-nowrap">
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-cyan-300 border border-slate-700">
                                {tx.rail || 'UPI'}
                              </span>
                            </td>
                            <td className="py-2 px-3 max-w-[220px] truncate text-slate-300 text-[11px]">
                              {tx.from_account || 'Payer'} → {tx.to_account || 'Payee'}
                            </td>
                            <td className="py-2 px-3 text-right font-bold text-slate-100">
                              {tx.currency === 'BTC'
                                ? `${tx.amount} BTC`
                                : `₹${Number(tx.amount || 0).toLocaleString('en-IN')}`}
                            </td>
                            <td className="py-2 px-3 text-right font-bold text-rose-400">
                              {((tx.risk_score || 0.95) * 100).toFixed(1)}%
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* -------------------------------------------------------------- */}
              {/* Section 4: Status Transition & Qualitative Commentary */}
              {/* -------------------------------------------------------------- */}
              <div className="rounded-xl border border-slate-800 bg-obsidian-950/80 p-4 space-y-3">
                <div className="flex items-center gap-2 border-b border-slate-800/60 pb-2">
                  <Scale className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-mono font-bold text-slate-200">
                    Section 4: Remediation Controls & Status Transition
                  </span>
                </div>

                <div className="space-y-2 pt-1">
                  <div className="space-y-1">
                    <label className="text-[11px] font-mono text-slate-400">Investigator Resolution Notes / Docket</label>
                    <input
                      type="text"
                      value={notesInput}
                      onChange={(e) => setNotesInput(e.target.value)}
                      placeholder="e.g. Filed via FINnet 2.0 gateway; ack ref IND-STR-88291..."
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <button
                      onClick={() => handleTransitionStatus('FILED_WITH_FIU')}
                      disabled={actionLoading || caseData.status === 'FILED_WITH_FIU'}
                      className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-xs font-mono font-bold text-slate-950 transition-all shadow-glow-emerald"
                    >
                      {actionLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                      <span>Mark as FILED_WITH_FIU</span>
                    </button>

                    <button
                      onClick={() => handleTransitionStatus('DISMISSED')}
                      disabled={actionLoading || caseData.status === 'DISMISSED'}
                      className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-xs font-mono font-bold text-slate-300 border border-slate-700 transition-colors"
                    >
                      <span>Mark as DISMISSED</span>
                    </button>

                    <button
                      onClick={() => handleTransitionStatus('PENDING_REVIEW')}
                      disabled={actionLoading || caseData.status === 'PENDING_REVIEW'}
                      className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-amber-900/60 hover:bg-amber-800/80 disabled:opacity-40 text-xs font-mono font-bold text-amber-300 border border-amber-700 transition-colors"
                    >
                      <span>Revert to PENDING_REVIEW</span>
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* ==================================================================== */}
        {/* Regulatory Action Toolbar (Footer) */}
        {/* ==================================================================== */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-6 py-4 border-t border-slate-800 bg-obsidian-950/90 shrink-0">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>FINnet 2.0 Compliant Regulatory Exporter</span>
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
            <button
              onClick={handleExportJson}
              disabled={downloadingJson || !caseData}
              className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-bold border border-slate-700 transition-colors disabled:opacity-50"
            >
              {downloadingJson ? (
                <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
              ) : (
                <Download className="w-4 h-4 text-cyan-400" />
              )}
              <span>Export JSON</span>
            </button>

            <button
              onClick={handleExportPdf}
              disabled={downloadingPdf || !caseData}
              className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-slate-50 text-xs font-mono font-bold transition-all shadow-glow-rose disabled:opacity-50"
            >
              {downloadingPdf ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              <span>Export PDF</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
