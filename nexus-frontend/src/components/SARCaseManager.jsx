import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  FileWarning,
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  Download,
  FileJson,
  FileText,
  Shield,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  Hash,
  IndianRupee,
  ArrowUpRight,
  RefreshCw,
  Plus,
  X,
  Loader2,
  Filter,
  Briefcase,
  Scale,
  Activity,
  Zap,
  Copy,
  ChevronDown,
} from 'lucide-react';
import { cn } from '../utils/cn';
import {
  listSarCases,
  getSarCase,
  updateSarStatus,
  exportSar,
  generateSar,
} from '../services/api';

// Status badge config
const STATUS_CONFIG = {
  PENDING_REVIEW: { label: 'Pending Review', color: 'text-amber-400 bg-amber-500/15 border-amber-500/30', icon: Clock },
  ESCALATED: { label: 'Escalated', color: 'text-orange-400 bg-orange-500/15 border-orange-500/30', icon: ArrowUpRight },
  FILED_WITH_FIU: { label: 'Filed with FIU', color: 'text-emerald-400 bg-emerald-500/15 border-emerald-500/30', icon: CheckCircle2 },
  DISMISSED: { label: 'Dismissed', color: 'text-slate-400 bg-slate-500/15 border-slate-500/30', icon: XCircle },
};

const TYPOLOGY_LABELS = {
  IN_TYP_STRUCT: 'PAN Structuring',
  IN_TYP_HAWALA: 'Hawala / RTGS',
  IN_TYP_MULE: 'Mule Burst',
  IN_TYP_VDA_MIX: 'VDA Mixer / Crypto',
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.PENDING_REVIEW;
  const Icon = cfg.icon;
  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono font-semibold border', cfg.color)}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
}

function TypologyBadge({ typology }) {
  const label = TYPOLOGY_LABELS[typology] || typology;
  const colorMap = {
    IN_TYP_STRUCT: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/25',
    IN_TYP_HAWALA: 'text-rose-400 bg-rose-500/10 border-rose-500/25',
    IN_TYP_MULE: 'text-purple-400 bg-purple-500/10 border-purple-500/25',
    IN_TYP_VDA_MIX: 'text-orange-400 bg-orange-500/10 border-orange-500/25',
  };
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-medium border', colorMap[typology] || 'text-slate-400 bg-slate-500/10 border-slate-500/25')}>
      {label}
    </span>
  );
}

export function SARCaseManager({ apiUrl }) {
  // List state
  const [cases, setCases] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState('');
  const [typologyFilter, setTypologyFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Detail panel state
  const [selectedCase, setSelectedCase] = useState(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);

  // Action states
  const [isExporting, setIsExporting] = useState(null); // 'pdf' | 'json' | null
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [actionFeedback, setActionFeedback] = useState(null);

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  // Fetch cases
  const fetchCases = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listSarCases({
        page,
        pageSize,
        status: statusFilter || null,
        typology: typologyFilter || null,
        search: searchQuery || null,
      }, apiUrl);
      setCases(data.items || []);
      setTotalCount(data.total_count || 0);
    } catch (err) {
      setError(err.message);
      setCases([]);
      setTotalCount(0);
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, statusFilter, typologyFilter, searchQuery, apiUrl]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  // Open case detail
  const openCaseDetail = async (sarId) => {
    setIsDetailLoading(true);
    setSelectedCase(null);
    try {
      const data = await getSarCase(sarId, apiUrl);
      setSelectedCase(data);
    } catch (err) {
      showFeedback(`Failed to load case: ${err.message}`, 'error');
    } finally {
      setIsDetailLoading(false);
    }
  };

  // Export handler
  const handleExport = async (sarId, format) => {
    setIsExporting(format);
    try {
      const { blob, filename } = await exportSar(sarId, format, apiUrl);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showFeedback(`Exported ${filename} successfully`, 'success');
    } catch (err) {
      showFeedback(`Export failed: ${err.message}`, 'error');
    } finally {
      setIsExporting(null);
    }
  };

  // Status transition handler
  const handleStatusTransition = async (sarId, newStatus) => {
    setIsTransitioning(true);
    try {
      const updated = await updateSarStatus(sarId, newStatus, 'ANALYST-CONSOLE', `Status transitioned to ${newStatus} via compliance dashboard`, apiUrl);
      setSelectedCase(updated);
      showFeedback(`Case ${sarId} transitioned to ${STATUS_CONFIG[newStatus]?.label || newStatus}`, 'success');
      fetchCases(); // Refresh list
    } catch (err) {
      showFeedback(`Transition failed: ${err.message}`, 'error');
    } finally {
      setIsTransitioning(false);
    }
  };

  // Generate SAR handler
  const handleGenerateSar = async (formData) => {
    setIsGenerating(true);
    try {
      const newCase = await generateSar(formData, apiUrl);
      showFeedback(`SAR case ${newCase.sar_id} created successfully`, 'success');
      setShowGenerateModal(false);
      fetchCases();
    } catch (err) {
      showFeedback(`Generation failed: ${err.message}`, 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const showFeedback = (message, type) => {
    setActionFeedback({ message, type });
    setTimeout(() => setActionFeedback(null), 4000);
  };

  const formatCurrency = (amount) => {
    if (amount == null) return '—';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '—';
    try {
      return new Date(isoStr).toLocaleString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit', hour12: false,
      });
    } catch { return isoStr; }
  };

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/25">
            <Scale className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-100 font-mono">SAR Case Management Console</h2>
            <p className="text-xs text-slate-400 font-mono">PMLA Compliance • FIU-IND FINnet 2.0 • Regulatory Dossier Lifecycle</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchCases}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-mono font-medium text-slate-300 bg-slate-800/60 border border-slate-700/50 hover:bg-slate-700/60 hover:text-slate-100 transition-all"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
            Refresh
          </button>
          <button
            onClick={() => setShowGenerateModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-mono font-semibold text-obsidian-950 bg-gradient-to-r from-amber-400 to-orange-400 hover:from-amber-300 hover:to-orange-300 transition-all shadow-glow-amber"
          >
            <Plus className="w-3.5 h-3.5" />
            Generate SAR
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 p-3 rounded-xl bg-obsidian-900/80 border border-slate-800/60 backdrop-blur-sm">
        <div className="flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">Filters</span>
        </div>
        <div className="relative">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="appearance-none bg-obsidian-950 border border-slate-700/50 rounded-lg px-3 py-1.5 pr-7 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-500/50 cursor-pointer"
          >
            <option value="">All Status</option>
            <option value="PENDING_REVIEW">Pending Review</option>
            <option value="ESCALATED">Escalated</option>
            <option value="FILED_WITH_FIU">Filed with FIU</option>
            <option value="DISMISSED">Dismissed</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500 pointer-events-none" />
        </div>
        <div className="relative">
          <select
            value={typologyFilter}
            onChange={(e) => { setTypologyFilter(e.target.value); setPage(1); }}
            className="appearance-none bg-obsidian-950 border border-slate-700/50 rounded-lg px-3 py-1.5 pr-7 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-500/50 cursor-pointer"
          >
            <option value="">All Typologies</option>
            <option value="IN_TYP_STRUCT">PAN Structuring</option>
            <option value="IN_TYP_HAWALA">Hawala / RTGS</option>
            <option value="IN_TYP_MULE">Mule Burst</option>
            <option value="IN_TYP_VDA_MIX">VDA Mixer / Crypto</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500 pointer-events-none" />
        </div>
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            placeholder="Search SAR ID, suspect, entity name..."
            className="w-full bg-obsidian-950 border border-slate-700/50 rounded-lg pl-8 pr-3 py-1.5 text-xs font-mono text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
        <div className="text-[10px] font-mono text-slate-500">
          {totalCount} case{totalCount !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Action Feedback Toast */}
      {actionFeedback && (
        <div className={cn(
          'flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-mono border animate-fade-in',
          actionFeedback.type === 'success'
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
            : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
        )}>
          {actionFeedback.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {actionFeedback.message}
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs font-mono">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={fetchCases} className="ml-auto text-rose-400 hover:text-rose-200 underline">Retry</button>
        </div>
      )}

      {/* Cases Table */}
      <div className="rounded-xl border border-slate-800/60 bg-obsidian-950/60 backdrop-blur-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16 gap-3 text-slate-400 text-sm font-mono">
            <Loader2 className="w-5 h-5 animate-spin" />
            Loading cases...
          </div>
        ) : cases.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-slate-500">
            <Shield className="w-10 h-10 text-slate-600" />
            <span className="text-sm font-mono">No SAR cases found</span>
            <span className="text-xs font-mono text-slate-600">Cases will appear here as high-risk transactions are detected</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800/60 text-slate-500 uppercase tracking-wider">
                  <th className="text-left px-4 py-3 font-medium">SAR ID</th>
                  <th className="text-left px-4 py-3 font-medium">Suspect</th>
                  <th className="text-left px-4 py-3 font-medium">Typology</th>
                  <th className="text-right px-4 py-3 font-medium">Exposure (₹)</th>
                  <th className="text-left px-4 py-3 font-medium">Status</th>
                  <th className="text-left px-4 py-3 font-medium">Created</th>
                  <th className="text-left px-4 py-3 font-medium">FIU Deadline</th>
                  <th className="text-center px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c) => {
                  const suspectId = c.suspect?.entity_identifier || c.suspect_identifier || '—';
                  const typology = c.grounds?.primary_typology || c.primary_typology || 'IN_TYP_STRUCT';
                  const exposure = c.total_exposure_inr ?? 0;
                  const isOverdue = c.fiu_deadline && new Date(c.fiu_deadline) < new Date();
                  return (
                    <tr
                      key={c.sar_id}
                      className="border-b border-slate-800/30 hover:bg-slate-800/20 transition-colors cursor-pointer group"
                      onClick={() => openCaseDetail(c.sar_id)}
                    >
                      <td className="px-4 py-3">
                        <span className="text-cyan-400 group-hover:text-cyan-300 transition-colors">{c.sar_id}</span>
                      </td>
                      <td className="px-4 py-3 text-slate-300 max-w-[180px] truncate">{suspectId}</td>
                      <td className="px-4 py-3"><TypologyBadge typology={typology} /></td>
                      <td className="px-4 py-3 text-right text-slate-200 tabular-nums">{formatCurrency(exposure)}</td>
                      <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                      <td className="px-4 py-3 text-slate-400">{formatDate(c.created_at)}</td>
                      <td className="px-4 py-3">
                        <span className={cn('text-slate-400', isOverdue && 'text-rose-400 font-semibold')}>
                          {formatDate(c.fiu_deadline)}
                          {isOverdue && ' ⚠'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => openCaseDetail(c.sar_id)}
                            title="View Details"
                            className="p-1.5 rounded-lg text-slate-500 hover:text-cyan-400 hover:bg-cyan-500/10 transition-all"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleExport(c.sar_id, 'pdf')}
                            title="Download PDF"
                            className="p-1.5 rounded-lg text-slate-500 hover:text-amber-400 hover:bg-amber-500/10 transition-all"
                          >
                            <FileText className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleExport(c.sar_id, 'json')}
                            title="Export FINnet JSON"
                            className="p-1.5 rounded-lg text-slate-500 hover:text-emerald-400 hover:bg-emerald-500/10 transition-all"
                          >
                            <FileJson className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalCount > pageSize && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800/40">
            <span className="text-[11px] font-mono text-slate-500">
              Page {page} of {totalPages} • {totalCount} total
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const pn = page <= 3 ? i + 1 : page + i - 2;
                if (pn < 1 || pn > totalPages) return null;
                return (
                  <button
                    key={pn}
                    onClick={() => setPage(pn)}
                    className={cn(
                      'w-7 h-7 rounded-lg text-xs font-mono transition-all',
                      pn === page
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                        : 'text-slate-500 hover:text-slate-300 hover:bg-slate-700/50'
                    )}
                  >
                    {pn}
                  </button>
                );
              })}
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page >= totalPages}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Case Detail Slide-Over Panel */}
      {(selectedCase || isDetailLoading) && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setSelectedCase(null)} />
          {/* Panel */}
          <div className="relative w-full max-w-2xl bg-obsidian-950 border-l border-slate-800/60 overflow-y-auto animate-fade-in">
            {isDetailLoading ? (
              <div className="flex items-center justify-center h-full gap-3 text-slate-400 font-mono">
                <Loader2 className="w-5 h-5 animate-spin" />
                Loading case dossier...
              </div>
            ) : selectedCase && (
              <div className="p-6 space-y-6">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Shield className="w-5 h-5 text-amber-400" />
                      <h3 className="text-base font-bold text-slate-100 font-mono">{selectedCase.sar_id}</h3>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <StatusBadge status={selectedCase.status} />
                      <TypologyBadge typology={selectedCase.grounds?.primary_typology || 'IN_TYP_STRUCT'} />
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedCase(null)}
                    className="p-2 rounded-xl text-slate-500 hover:text-slate-200 hover:bg-slate-800/60 transition-all"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Key Metrics Strip */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 rounded-xl bg-obsidian-900/80 border border-slate-800/40">
                    <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 uppercase mb-1">
                      <IndianRupee className="w-3 h-3" /> Total Exposure
                    </div>
                    <div className="text-lg font-bold text-rose-400 font-mono tabular-nums">
                      {formatCurrency(selectedCase.total_exposure_inr)}
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-obsidian-900/80 border border-slate-800/40">
                    <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 uppercase mb-1">
                      <Hash className="w-3 h-3" /> Transactions
                    </div>
                    <div className="text-lg font-bold text-cyan-400 font-mono tabular-nums">
                      {selectedCase.transaction_ledger?.length || 0}
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-obsidian-900/80 border border-slate-800/40">
                    <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 uppercase mb-1">
                      <Clock className="w-3 h-3" /> FIU Deadline
                    </div>
                    <div className={cn(
                      'text-sm font-semibold font-mono',
                      selectedCase.fiu_deadline && new Date(selectedCase.fiu_deadline) < new Date() ? 'text-rose-400' : 'text-emerald-400'
                    )}>
                      {formatDate(selectedCase.fiu_deadline)}
                    </div>
                  </div>
                </div>

                {/* Suspect Profile */}
                {selectedCase.suspect && (
                  <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800/40 space-y-2">
                    <div className="flex items-center gap-2 text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider">
                      <User className="w-3.5 h-3.5 text-amber-400" /> Suspect Entity Profile
                    </div>
                    <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs font-mono">
                      <div><span className="text-slate-500">Identifier:</span> <span className="text-slate-200">{selectedCase.suspect.entity_identifier || '—'}</span></div>
                      <div><span className="text-slate-500">Legal Name:</span> <span className="text-slate-200">{selectedCase.suspect.legal_name || '—'}</span></div>
                      <div><span className="text-slate-500">Account:</span> <span className="text-slate-200">{selectedCase.suspect.primary_account || '—'}</span></div>
                      <div><span className="text-slate-500">Jurisdiction:</span> <span className="text-slate-200">{selectedCase.suspect.jurisdiction || '—'}</span></div>
                    </div>
                  </div>
                )}

                {/* Narrative */}
                {selectedCase.narrative && (
                  <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800/40 space-y-2">
                    <div className="flex items-center gap-2 text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider">
                      <Briefcase className="w-3.5 h-3.5 text-cyan-400" /> Grounds of Suspicion & Narrative
                    </div>
                    <p className="text-xs font-mono text-slate-400 leading-relaxed whitespace-pre-wrap">{selectedCase.narrative}</p>
                  </div>
                )}

                {/* Transaction Ledger */}
                {selectedCase.transaction_ledger?.length > 0 && (
                  <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800/40 space-y-2">
                    <div className="flex items-center gap-2 text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider">
                      <Activity className="w-3.5 h-3.5 text-emerald-400" /> Transaction Ledger ({selectedCase.transaction_ledger.length})
                    </div>
                    <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                      {selectedCase.transaction_ledger.map((tx, i) => (
                        <div key={i} className="flex items-center justify-between py-1.5 px-2 rounded-lg bg-obsidian-950/60 text-[11px] font-mono">
                          <div className="flex items-center gap-2">
                            <span className="text-cyan-400">{tx.transaction_id || `TX-${i + 1}`}</span>
                            <span className="text-slate-500">{tx.payment_format || tx.rail || '—'}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-slate-300 tabular-nums">{formatCurrency(tx.amount_inr || tx.amount)}</span>
                            <span className="text-slate-500">{formatDate(tx.timestamp)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* ML Telemetry */}
                {selectedCase.ml_telemetry && (
                  <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800/40 space-y-2">
                    <div className="flex items-center gap-2 text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider">
                      <Zap className="w-3.5 h-3.5 text-purple-400" /> ML Inference Telemetry
                    </div>
                    <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs font-mono">
                      <div><span className="text-slate-500">Peak Risk Score:</span> <span className="text-rose-400 font-bold">{selectedCase.ml_telemetry.peak_risk_score?.toFixed(4) || '—'}</span></div>
                      <div><span className="text-slate-500">Avg Latency:</span> <span className="text-slate-200">{selectedCase.ml_telemetry.avg_latency_ms?.toFixed(1) || '—'} ms</span></div>
                      <div><span className="text-slate-500">Model:</span> <span className="text-slate-200">{selectedCase.ml_telemetry.model_version || '—'}</span></div>
                      <div><span className="text-slate-500">Inferences:</span> <span className="text-slate-200">{selectedCase.ml_telemetry.inference_count || '—'}</span></div>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/40">
                  {/* Export Actions */}
                  <button
                    onClick={() => handleExport(selectedCase.sar_id, 'pdf')}
                    disabled={isExporting === 'pdf'}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/25 hover:bg-amber-500/20 transition-all disabled:opacity-50"
                  >
                    {isExporting === 'pdf' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                    Export PDF Dossier
                  </button>
                  <button
                    onClick={() => handleExport(selectedCase.sar_id, 'json')}
                    disabled={isExporting === 'json'}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 hover:bg-emerald-500/20 transition-all disabled:opacity-50"
                  >
                    {isExporting === 'json' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileJson className="w-3.5 h-3.5" />}
                    FINnet 2.0 JSON
                  </button>

                  <div className="flex-1" />

                  {/* Status Transitions (only for active cases) */}
                  {selectedCase.status === 'PENDING_REVIEW' && (
                    <>
                      <button
                        onClick={() => handleStatusTransition(selectedCase.sar_id, 'ESCALATED')}
                        disabled={isTransitioning}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-mono font-medium bg-orange-500/10 text-orange-400 border border-orange-500/25 hover:bg-orange-500/20 transition-all disabled:opacity-50"
                      >
                        {isTransitioning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowUpRight className="w-3.5 h-3.5" />}
                        Escalate
                      </button>
                      <button
                        onClick={() => handleStatusTransition(selectedCase.sar_id, 'DISMISSED')}
                        disabled={isTransitioning}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-mono font-medium bg-slate-500/10 text-slate-400 border border-slate-500/25 hover:bg-slate-500/20 transition-all disabled:opacity-50"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        Dismiss
                      </button>
                    </>
                  )}
                  {selectedCase.status === 'ESCALATED' && (
                    <button
                      onClick={() => handleStatusTransition(selectedCase.sar_id, 'FILED_WITH_FIU')}
                      disabled={isTransitioning}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-mono font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25 transition-all disabled:opacity-50"
                    >
                      {isTransitioning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                      File with FIU-IND
                    </button>
                  )}
                </div>

                {/* Audit Trail */}
                <div className="pt-2 border-t border-slate-800/40 space-y-1">
                  <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">Audit Trail</div>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-[11px] font-mono">
                    <div><span className="text-slate-500">Created:</span> <span className="text-slate-400">{formatDate(selectedCase.created_at)}</span></div>
                    <div><span className="text-slate-500">Updated:</span> <span className="text-slate-400">{formatDate(selectedCase.updated_at)}</span></div>
                    <div><span className="text-slate-500">Analyst:</span> <span className="text-slate-400">{selectedCase.assigned_analyst || '—'}</span></div>
                    <div><span className="text-slate-500">Resolution:</span> <span className="text-slate-400">{selectedCase.resolution_notes || '—'}</span></div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Generate SAR Modal */}
      {showGenerateModal && (
        <GenerateSarModal
          onClose={() => setShowGenerateModal(false)}
          onSubmit={handleGenerateSar}
          isLoading={isGenerating}
        />
      )}
    </div>
  );
}

/** Manual SAR Generation Form Modal */
function GenerateSarModal({ onClose, onSubmit, isLoading }) {
  const [formData, setFormData] = useState({
    transaction_ids: '',
    primary_typology: 'IN_TYP_STRUCT',
    investigator_notes: '',
    assigned_investigator: '',
    suspect_identifier: '',
    reporting_entity: {
      fiureid: 'FIU-RE-COMM-2026-NEXUS',
      entity_name: 'QuantumAML Nexus Surveillance Gateway',
      category: 'SCHEDULED_COMMERCIAL_BANK',
      principal_officer_id: 'PO-REG-0001',
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const txIds = formData.transaction_ids
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (txIds.length === 0) return;

    onSubmit({
      ...formData,
      transaction_ids: txIds,
    });
  };

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg bg-obsidian-950 border border-slate-800/60 rounded-2xl shadow-2xl animate-fade-in overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/40">
          <div className="flex items-center gap-2">
            <Plus className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-bold text-slate-100 font-mono">Generate SAR Case Dossier</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800/60 transition-all">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Transaction IDs */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Transaction IDs *</label>
            <input
              type="text"
              required
              value={formData.transaction_ids}
              onChange={(e) => updateField('transaction_ids', e.target.value)}
              placeholder="UTR-001, UTR-002, ..."
              className="w-full bg-obsidian-900 border border-slate-700/50 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50"
            />
          </div>

          {/* Typology & Investigator */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Typology *</label>
              <select
                value={formData.primary_typology}
                onChange={(e) => updateField('primary_typology', e.target.value)}
                className="w-full bg-obsidian-900 border border-slate-700/50 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500/50"
              >
                <option value="IN_TYP_STRUCT">PAN Structuring</option>
                <option value="IN_TYP_HAWALA">Hawala / RTGS</option>
                <option value="IN_TYP_MULE">Mule Burst</option>
                <option value="IN_TYP_VDA_MIX">VDA Mixer / Crypto</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Assigned Investigator</label>
              <input
                type="text"
                value={formData.assigned_investigator}
                onChange={(e) => updateField('assigned_investigator', e.target.value)}
                placeholder="INV-PMLA-42"
                className="w-full bg-obsidian-900 border border-slate-700/50 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50"
              />
            </div>
          </div>

          {/* Suspect ID */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Suspect Identifier</label>
            <input
              type="text"
              value={formData.suspect_identifier}
              onChange={(e) => updateField('suspect_identifier', e.target.value)}
              placeholder="suspect.vpa@upi or account number"
              className="w-full bg-obsidian-900 border border-slate-700/50 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50"
            />
          </div>

          {/* Investigator Notes */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Investigator Notes</label>
            <textarea
              value={formData.investigator_notes}
              onChange={(e) => updateField('investigator_notes', e.target.value)}
              placeholder="Grounds of suspicion, observed patterns, regulatory references..."
              rows={3}
              className="w-full bg-obsidian-900 border border-slate-700/50 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50 resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-mono font-semibold text-obsidian-950 bg-gradient-to-r from-amber-400 to-orange-400 hover:from-amber-300 hover:to-orange-300 transition-all disabled:opacity-50 shadow-glow-amber"
            >
              {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileWarning className="w-3.5 h-3.5" />}
              Generate SAR Dossier
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
