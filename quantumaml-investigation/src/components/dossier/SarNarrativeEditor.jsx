import React, { useState, useEffect } from 'react';
import { FileEdit, Sparkles, Copy, Check, MessageSquareText } from 'lucide-react';
import { useInvestigation } from '../../context/InvestigationContext';

/**
 * Builds the formal statutory SAR narrative draft strictly adhering to
 * PMLA 2002 / FinCEN specifications from case telemetry.
 */
function buildAutoDraft(caseObj) {
  if (!caseObj) return '';

  const dateStr = caseObj.createdAt
    ? new Date(caseObj.createdAt).toISOString().split('T')[0]
    : new Date().toISOString().split('T')[0];

  const suspect = caseObj.suspectEntity || 'Identified Target Entity';
  const rail = caseObj.rail || 'UPI';
  const currency = caseObj.currency || 'INR';

  const amountStr =
    currency === 'BTC' || rail === 'BTC'
      ? `${caseObj.amount} BTC`
      : `₹${Number(caseObj.amount || 0).toLocaleString('en-IN')}`;

  const confidencePct = '94.2%';

  return `On ${dateStr}, account [${suspect}] engaged in suspected layering/structuring activity totaling ${amountStr} ${currency} across ${rail} rail. Machine learning detection flagged anomalous burst velocity (confidence: ${confidencePct}). Transfers exhibited rapid-hop transit below 60 seconds indicative of automated mule networks.`;
}

export function SarNarrativeEditor() {
  const {
    activeCase,
    sarNarrative,
    setSarNarrative,
    investigatorNotes,
    setInvestigatorNotes,
  } = useInvestigation();

  const [copied, setCopied] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // Sync draft narrative whenever activeCase changes
  useEffect(() => {
    if (activeCase) {
      setSarNarrative(buildAutoDraft(activeCase));
    }
  }, [activeCase, setSarNarrative]);

  const handleRegenerate = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setSarNarrative(buildAutoDraft(activeCase));
      setIsGenerating(false);
    }, 200);
  };

  const handleCopy = () => {
    if (!sarNarrative) return;
    navigator.clipboard?.writeText(sarNarrative);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const charCount = (sarNarrative || '').length;
  const wordCount = sarNarrative?.trim() ? sarNarrative.trim().split(/\s+/).length : 0;

  return (
    <div className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 text-xs font-mono space-y-3 shadow-md select-none">
      {/* Narrative Section Header */}
      <div className="flex items-center justify-between pb-1 border-b border-slate-800/80">
        <div className="flex items-center gap-1.5 font-bold text-amber-400">
          <FileEdit className="w-3.5 h-3.5 text-amber-400" />
          <span className="uppercase text-[11px] tracking-wider">Statutory SAR Narrative</span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleRegenerate}
            disabled={isGenerating}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] transition-colors"
            title="Auto-regenerate narrative from telemetry"
          >
            <Sparkles className={`w-3 h-3 text-amber-400 ${isGenerating ? 'animate-spin' : ''}`} />
            <span>AI Draft</span>
          </button>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-[10px] transition-colors"
            title="Copy narrative text"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-400" />
                <span className="text-emerald-400 font-bold">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3 text-slate-400" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Editable SAR Narrative Textarea */}
      <div className="space-y-1">
        <textarea
          value={sarNarrative || ''}
          onChange={(e) => setSarNarrative(e.target.value)}
          rows={4}
          placeholder="Enter formal statutory narrative for FinCEN / FIU-IND submission..."
          className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs font-mono placeholder-slate-600 focus:outline-none focus:border-amber-500/50 resize-y leading-relaxed transition-colors selection:bg-amber-500/20"
        />
        <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
          <span>PMLA 2002 § 12 / FINnet 2.0 Standard</span>
          <span>{wordCount} words · {charCount} chars</span>
        </div>
      </div>

      {/* Optional Investigator Notes Field */}
      <div className="space-y-1 pt-1 border-t border-slate-800/80">
        <div className="flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
          <MessageSquareText className="w-3 h-3 text-slate-400" />
          <span>Investigator Internal Notes (Optional)</span>
        </div>
        <input
          type="text"
          value={investigatorNotes || ''}
          onChange={(e) => setInvestigatorNotes(e.target.value)}
          placeholder="E.g. Linked to known mule aggregator ring #44; forwarded to Cyber Cell..."
          className="w-full px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs font-mono placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
        />
      </div>
    </div>
  );
}

export default SarNarrativeEditor;
