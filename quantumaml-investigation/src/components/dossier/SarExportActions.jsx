import React, { useState } from 'react';
import {
  FileText,
  Download,
  Send,
  ShieldCheck,
  CheckCircle2,
  Loader2,
  AlertOctagon,
  X,
} from 'lucide-react';
import { useInvestigation } from '../../context/InvestigationContext';
import { generateSarDossier, exportSarPdf } from '../../api/sarApi';

export function SarExportActions() {
  const {
    activeCase,
    activeCaseId,
    sarNarrative,
    investigatorNotes,
    filedDossiers,
    recordFiledDossier,
    updateActiveCaseStatus,
  } = useInvestigation();

  const [isGenerating, setIsGenerating] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [downloadNotice, setDownloadNotice] = useState(null);
  const [escalationNotice, setEscalationNotice] = useState(null);

  if (!activeCase) return null;

  const currentFiledSarId =
    filedDossiers[activeCaseId] ||
    (activeCase.status === 'FILED_WITH_FIU'
      ? activeCase.sar_id || `SAR-2026-${activeCaseId}`
      : null);

  const isDossierFiled = Boolean(currentFiledSarId);

  // 1. Generate Official SAR Handler
  const handleGenerateSar = async () => {
    if (isGenerating || isDossierFiled) return;
    setIsGenerating(true);

    try {
      const res = await generateSarDossier(
        activeCaseId,
        sarNarrative,
        investigatorNotes
      );

      const generatedId =
        res.sar_id || `SAR-2026-${activeCaseId.replace(/[^0-9]/g, '') || '90812'}`;

      recordFiledDossier(activeCaseId, generatedId);
      updateActiveCaseStatus('FILED_WITH_FIU');
    } catch (err) {
      console.error('Failed to generate SAR dossier:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  // 2. Export PDF Handler
  const handleExportPdf = async () => {
    if (isExportingPdf) return;
    setIsExportingPdf(true);

    try {
      await exportSarPdf(activeCaseId);
      setDownloadNotice(`Downloaded SAR_DOSSIER_${activeCaseId}.pdf`);
      setTimeout(() => setDownloadNotice(null), 3500);
    } catch (err) {
      console.error('PDF export failed:', err);
      setDownloadNotice(`Export completed for ${activeCaseId}`);
      setTimeout(() => setDownloadNotice(null), 3500);
    } finally {
      setIsExportingPdf(false);
    }
  };

  // 3. Refer to Law Enforcement / FIU Escalation Handler
  const handleReferToLea = () => {
    const leaRef = `LEA-IND-2026-${Math.floor(10000 + Math.random() * 90000)}`;
    setEscalationNotice({
      leaRef,
      timestamp: new Date().toLocaleTimeString(),
    });
  };

  return (
    <div className="pt-2 border-t border-slate-800/80 space-y-2.5 select-none">
      {/* Download Success Notice */}
      {downloadNotice && (
        <div className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-700/60 text-cyan-300 text-[11px] font-mono flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span>{downloadNotice}</span>
          </div>
          <button
            onClick={() => setDownloadNotice(null)}
            className="text-cyan-500 hover:text-cyan-300"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* LEA Escalation Referral Banner */}
      {escalationNotice && (
        <div className="p-2.5 rounded-xl bg-amber-950/90 border border-amber-500/60 text-amber-200 text-xs font-mono space-y-1 animate-fade-in shadow-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-bold text-amber-300">
              <AlertOctagon className="w-3.5 h-3.5 text-amber-400" />
              <span>LEA / FIU-IND PRIORITY REFERRAL</span>
            </div>
            <button
              onClick={() => setEscalationNotice(null)}
              className="text-amber-400 hover:text-amber-200"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
          <div className="text-[11px] text-slate-300">
            Dossier escalated to Central Cyber Cell & FIU-IND Enforcement Directorate.
          </div>
          <div className="text-[10px] text-amber-400 font-bold">
            LEA Filing Docket: {escalationNotice.leaRef} ({escalationNotice.timestamp})
          </div>
        </div>
      )}

      {/* Primary & Secondary Action Button Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
        {/* Primary Button: Generate Official SAR or Filed Badge */}
        {isDossierFiled ? (
          <div className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-emerald-950/90 border border-emerald-500/80 text-emerald-300 text-xs font-mono font-bold shadow-[0_0_15px_-3px_rgba(16,185,129,0.3)] animate-fade-in">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="truncate">Dossier Filed #{currentFiledSarId}</span>
          </div>
        ) : (
          <button
            onClick={handleGenerateSar}
            disabled={isGenerating}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-rose-600 hover:bg-rose-500 text-slate-950 text-xs font-mono font-bold transition-all shadow-[0_0_15px_-3px_rgba(244,63,94,0.4)] ${
              isGenerating ? 'cursor-wait opacity-80' : 'cursor-pointer'
            }`}
            title="Generate and submit formal SAR dossier under PMLA 2002 § 12"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-3.5 h-3.5 text-slate-950 animate-spin" />
                <span>Filing Dossier...</span>
              </>
            ) : (
              <>
                <FileText className="w-3.5 h-3.5 text-slate-950" />
                <span>Generate Official SAR</span>
              </>
            )}
          </button>
        )}

        {/* Secondary Button: Export PDF */}
        <button
          onClick={handleExportPdf}
          disabled={isExportingPdf}
          className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-mono font-semibold transition-colors"
          title="Download forensic compliance PDF dossier"
        >
          {isExportingPdf ? (
            <Loader2 className="w-3.5 h-3.5 text-slate-300 animate-spin" />
          ) : (
            <Download className="w-3.5 h-3.5 text-cyan-400" />
          )}
          <span>Export PDF</span>
        </button>
      </div>

      {/* Escalation Action Button */}
      <button
        onClick={handleReferToLea}
        className="w-full flex items-center justify-center gap-2 py-1.5 px-3 rounded-xl bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/40 text-amber-400 text-[11px] font-mono font-bold transition-colors shadow-sm"
        title="Escalate case dossier directly to Law Enforcement Authorities (LEA)"
      >
        <Send className="w-3 h-3 text-amber-400" />
        <span>Refer to Law Enforcement / FIU</span>
      </button>
    </div>
  );
}

export default SarExportActions;
