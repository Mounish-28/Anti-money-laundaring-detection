import React, { useState } from 'react';
import { FileEdit, Sparkles, Copy, Check } from 'lucide-react';
import { useInvestigation } from '../../context/InvestigationContext';

function generateCaseNarrative(caseObj) {
  if (!caseObj) return '';

  const isCrypto = caseObj.currency === 'BTC' || caseObj.rail === 'BTC';
  const volumeStr = isCrypto
    ? `${caseObj.amount} BTC (approx. ₹${(caseObj.exposure_inr || 81500000).toLocaleString('en-IN')})`
    : `₹${Number(caseObj.amount || 0).toLocaleString('en-IN')}`;

  const subject = caseObj.suspectEntity || 'Identified Target Subject';
  const cluster = caseObj.clusterSize || 6;
  const hops = caseObj.hopCount || 4;

  if (isCrypto) {
    return `SUSPICIOUS TRANSACTION REPORT [PMLA-2002 / FINnet 2.0]: Subject address [${subject}] exhibits high-entropy UTXO peeling and mixer interaction across ${cluster} topological nodes with aggregate exposure of ${volumeStr}. Transaction propagation traces through a darknet mixer pool across ${hops} rapid on-chain hops, matching FIU Typology Code T-VDA-MIX. Recommended regulatory freeze and LEA referral under Section 12 of Prevention of Money Laundering Act.`;
  }

  if (caseObj.rail === 'IMPS') {
    return `SUSPICIOUS TRANSACTION REPORT [PMLA-2002 / FINnet 2.0]: Target account [${subject}] was observed executing rapid-fire pass-through transit transfers across ${cluster} intermediary accounts. An aggregate quantum of ${volumeStr} was funneled with hop latency under 60 seconds across ${hops} sequential banking hops. Observed cyclic routing and off-hours settlement strongly indicate professional money mule layering under FIU Typology Code T-402 (Rapid Wire Transit).`;
  }

  // Default UPI smurfing
  return `SUSPICIOUS TRANSACTION REPORT [PMLA-2002 / FINnet 2.0]: Domestic surveillance intercepted structured UPI funneling linked to primary subject [${subject}]. The cluster distributed an aggregate sum of ${volumeStr} across ${cluster} mule nodes in sub-₹50,000 tranches to evade mandatory PAN verification thresholds. Propagation completed within ${hops} propagation hops at high velocity, matching FIU-IND Typology Code T-STRUCT-UPI. Immediate account debit freeze recommended under Section 12 PMLA.`;
}

export function SarNarrativeEditor() {
  const { activeCase } = useInvestigation();
  const [narrative, setNarrative] = useState(() => generateCaseNarrative(activeCase));
  const [copied, setCopied] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleRegenerate = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setNarrative(generateCaseNarrative(activeCase));
      setIsGenerating(false);
    }, 250);
  };

  const handleCopy = () => {
    if (!narrative) return;
    navigator.clipboard?.writeText(narrative);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const charCount = narrative.length;
  const wordCount = narrative.trim() ? narrative.trim().split(/\s+/).length : 0;

  return (
    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono space-y-2.5 shadow-md flex flex-col">
      {/* Header with AI Drafter & Copy */}
      <div className="flex items-center justify-between pb-1 border-b border-slate-800/80">
        <div className="flex items-center gap-1.5 font-bold text-amber-400">
          <FileEdit className="w-3.5 h-3.5 text-amber-400" />
          <span className="uppercase text-[11px] tracking-wider">Statutory Narrative (FIU-IND STR)</span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleRegenerate}
            disabled={isGenerating}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] transition-colors"
            title="Regenerate FIU compliant draft"
          >
            <Sparkles className={`w-3 h-3 text-amber-400 ${isGenerating ? 'animate-spin' : ''}`} />
            <span>AI Draft</span>
          </button>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-[10px] transition-colors"
            title="Copy narrative to clipboard"
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

      {/* Narrative Editor Textarea */}
      <div className="relative">
        <textarea
          value={narrative}
          onChange={(e) => setNarrative(e.target.value)}
          rows={5}
          placeholder="Enter qualitative compliance investigation grounds and grounds of suspicion..."
          className="w-full p-2.5 rounded-lg bg-slate-950/90 border border-slate-800 text-[11px] font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500/50 resize-y leading-relaxed transition-colors selection:bg-amber-500/20"
        />
      </div>

      {/* Telemetry Counter */}
      <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
        <span>Statutory Standard: FINnet 2.0 / PMLA § 12</span>
        <span>{wordCount} words · {charCount} chars</span>
      </div>
    </div>
  );
}

export default SarNarrativeEditor;
