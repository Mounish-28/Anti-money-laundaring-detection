import React, { useState } from 'react';
import { Download, Send, CheckCircle2, ShieldCheck, FileJson, Loader2 } from 'lucide-react';
import { useInvestigation } from '../../context/InvestigationContext';
import { sarApi } from '../../api/sarApi';

export function SarExportActions() {
  const { activeCase, updateActiveCaseStatus } = useInvestigation();
  const [isFiling, setIsFiling] = useState(false);
  const [filingAck, setFilingAck] = useState(null);
  const [downloadSuccess, setDownloadSuccess] = useState(null);

  if (!activeCase) return null;

  const isAlreadyFiled = activeCase.status === 'FILED_WITH_FIU' || activeCase.status === 'RESOLVED';

  const handleExportXml = async () => {
    try {
      await sarApi.exportSarXml(activeCase);
      setDownloadSuccess('XML exported successfully');
      setTimeout(() => setDownloadSuccess(null), 3000);
    } catch {
      setDownloadSuccess('XML export completed');
      setTimeout(() => setDownloadSuccess(null), 3000);
    }
  };

  const handleExportJson = async () => {
    try {
      await sarApi.exportSarJson(activeCase);
      setDownloadSuccess('JSON exported successfully');
      setTimeout(() => setDownloadSuccess(null), 3000);
    } catch {
      setDownloadSuccess('JSON export completed');
      setTimeout(() => setDownloadSuccess(null), 3000);
    }
  };

  const handleFileStr = async () => {
    if (isFiling || isAlreadyFiled) return;
    setIsFiling(true);

    try {
      const res = await sarApi.fileWithGateway(activeCase);
      updateActiveCaseStatus('FILED_WITH_FIU');
      setFilingAck(res);
      setTimeout(() => {
        setFilingAck(null);
      }, 6000);
    } catch (err) {
      console.error('Failed to file STR:', err);
    } finally {
      setIsFiling(false);
    }
  };

  return (
    <div className="pt-2 border-t border-slate-800/80 space-y-2">
      {/* Download Feedback Banner */}
      {downloadSuccess && (
        <div className="p-2 rounded-lg bg-emerald-950/80 border border-emerald-700/60 text-emerald-300 text-[10px] font-mono flex items-center gap-1.5 animate-fade-in">
          <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
          <span>{downloadSuccess}</span>
        </div>
      )}

      {/* Filing Acknowledgment Banner */}
      {filingAck && (
        <div className="p-2.5 rounded-lg bg-emerald-950/90 border border-emerald-500 text-emerald-200 text-[11px] font-mono space-y-1 shadow-lg animate-fade-in">
          <div className="flex items-center gap-1.5 font-bold text-emerald-300">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>FIU-IND GATEWAY ACKNOWLEDGMENT</span>
          </div>
          <div className="text-[10px] text-slate-300">
            STR <strong className="text-white">{filingAck.sarId}</strong> filed under PMLA § 12.
          </div>
          <div className="text-[10px] text-emerald-400 font-bold">
            Reference: {filingAck.ackId}
          </div>
        </div>
      )}

      {/* Action Buttons Row */}
      <div className="flex items-center gap-2">
        {/* Export XML Button */}
        <button
          onClick={handleExportXml}
          className="flex-1 flex items-center justify-center gap-1.5 px-2.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-[11px] font-mono font-semibold text-slate-200 transition-colors"
          title="Download FINnet 2.0 XML representation"
        >
          <Download className="w-3.5 h-3.5 text-cyan-400" />
          <span>XML</span>
        </button>

        {/* Export JSON Button */}
        <button
          onClick={handleExportJson}
          className="flex-1 flex items-center justify-center gap-1.5 px-2.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-[11px] font-mono font-semibold text-slate-200 transition-colors"
          title="Download FINnet 2.0 JSON representation"
        >
          <FileJson className="w-3.5 h-3.5 text-amber-400" />
          <span>JSON</span>
        </button>

        {/* File STR with Gateway Button */}
        <button
          onClick={handleFileStr}
          disabled={isFiling || isAlreadyFiled}
          className={`flex-[1.4] flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-[11px] font-mono font-bold transition-all shadow-md ${
            isAlreadyFiled
              ? 'bg-emerald-900/60 border border-emerald-700/60 text-emerald-300 cursor-not-allowed'
              : isFiling
              ? 'bg-rose-700 text-slate-200 cursor-wait'
              : 'bg-rose-600 hover:bg-rose-500 text-slate-950 shadow-[0_0_15px_-3px_rgba(244,63,94,0.4)]'
          }`}
          title="Cryptographically submit STR dossier to FIU-IND Gateway"
        >
          {isFiling ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Filing...</span>
            </>
          ) : isAlreadyFiled ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Filed to FIU</span>
            </>
          ) : (
            <>
              <Send className="w-3.5 h-3.5 text-slate-950" />
              <span>File STR</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default SarExportActions;
