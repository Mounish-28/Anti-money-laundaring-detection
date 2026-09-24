import React, { useState, useEffect } from 'react';
import {
  UserCheck,
  ShieldAlert,
  ShieldCheck,
  Copy,
  Check,
  Lock,
  Unlock,
  AlertTriangle,
  RotateCcw,
  Fingerprint,
  Calendar,
  Phone,
  CreditCard,
} from 'lucide-react';
import { useInvestigation } from '../../context/InvestigationContext';
import { fetchEntityProfile, toggleEntityFreeze } from '../../api/sarApi';

export function EntityProfileCard() {
  const {
    activeCase,
    activeCaseId,
    selectedNodeId,
    selectedNodeData,
    setSelectedNodeId,
    setSelectedNodeData,
    frozenEntities,
    toggleAccountFreeze,
  } = useInvestigation();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [freezeConfirmVisual, setFreezeConfirmVisual] = useState(false);

  // Fetch or update entity profile whenever active case or selected node changes
  useEffect(() => {
    let isMounted = true;
    fetchEntityProfile(activeCaseId, selectedNodeId)
      .then((data) => {
        if (isMounted) {
          setProfile(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [activeCaseId, selectedNodeId]);

  if (!activeCase) {
    return (
      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono text-slate-500">
        No active case selected
      </div>
    );
  }

  if (loading && !profile) {
    return (
      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono text-slate-500 animate-pulse">
        Retrieving entity KYC & telemetry...
      </div>
    );
  }

  const isInspectingNode = Boolean(selectedNodeId);
  const entityId = profile?.entityId || selectedNodeId || activeCaseId;
  const isFrozen = Boolean(frozenEntities[entityId] ?? profile?.frozenStatus);

  const identifier =
    profile?.vpaOrWallet ||
    (isInspectingNode ? selectedNodeData?.label || selectedNodeId : activeCase.suspectEntity);

  const kycStatus = profile?.kycStatus || (isInspectingNode ? 'PARTIAL' : 'FAILED');
  const accountAge = profile?.accountAgeDays ?? (isInspectingNode ? 12 : 4);
  const linkedPhone = profile?.linkedPhoneMasked || '+91 98*** *2104';
  const panOrTaxId = profile?.panOrTaxIdMasked || 'ABCDE****F';
  const riskTier = profile?.riskTier || activeCase.riskTier || 'CRITICAL';

  const handleCopyIdentifier = () => {
    if (!identifier) return;
    navigator.clipboard?.writeText(identifier);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFreezeToggle = () => {
    toggleAccountFreeze(entityId);
    toggleEntityFreeze(entityId);
    setFreezeConfirmVisual(true);
    setTimeout(() => setFreezeConfirmVisual(false), 3000);
  };

  const handleResetTarget = () => {
    setSelectedNodeId(null);
    setSelectedNodeData(null);
  };

  return (
    <div className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 text-xs font-mono space-y-3 shadow-md relative overflow-hidden select-none">
      {/* Context Banner: Graph Node Inspection vs Primary Suspect */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <div className="flex items-center gap-1.5 font-bold">
          {isInspectingNode ? (
            <>
              <Fingerprint className="w-3.5 h-3.5 text-cyan-400" />
              <span className="uppercase text-[11px] tracking-wider text-cyan-400">
                Node Topology Inspection
              </span>
            </>
          ) : (
            <>
              <UserCheck className="w-3.5 h-3.5 text-rose-400" />
              <span className="uppercase text-[11px] tracking-wider text-rose-400">
                Suspect KYC Entity Profile
              </span>
            </>
          )}
        </div>

        {isInspectingNode ? (
          <button
            onClick={handleResetTarget}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-slate-300 font-medium transition-colors border border-slate-700/60"
            title="Return to primary case suspect"
          >
            <RotateCcw className="w-2.5 h-2.5 text-cyan-400" />
            <span>Reset Target</span>
          </button>
        ) : (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800/60">
            {riskTier} TIER
          </span>
        )}
      </div>

      {/* Freeze Confirmation Alert Banner */}
      {freezeConfirmVisual && (
        <div
          className={`p-2 rounded-lg text-[10px] font-mono flex items-center gap-1.5 animate-fade-in border ${
            isFrozen
              ? 'bg-emerald-950/90 text-emerald-300 border-emerald-500/60'
              : 'bg-amber-950/90 text-amber-300 border-amber-500/60'
          }`}
        >
          {isFrozen ? (
            <>
              <Lock className="w-3 h-3 text-emerald-400 shrink-0" />
              <span>Entity Account [{entityId}] Debit Frozen under PMLA § 12.</span>
            </>
          ) : (
            <>
              <Unlock className="w-3 h-3 text-amber-400 shrink-0" />
              <span>Entity Account [{entityId}] Unfrozen for surveillance.</span>
            </>
          )}
        </div>
      )}

      {/* Target Identifier Box with Copy Button */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[10px] text-slate-400 font-bold uppercase tracking-wider">
          <span>{isInspectingNode ? 'Graph Node Entity' : 'Target Entity Identifier'}</span>
          <span className="text-[9px] text-slate-500 font-mono">ID: {entityId}</span>
        </div>
        <div className="flex items-center justify-between gap-2 bg-slate-950/90 p-2 rounded-lg border border-slate-800">
          <span className="text-[11px] font-semibold text-slate-100 break-all truncate font-mono">
            {identifier}
          </span>
          <button
            onClick={handleCopyIdentifier}
            className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors shrink-0"
            title="Copy identifier"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* KYC Status & Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 text-[11px] pt-0.5">
        {/* KYC Status Tag */}
        <div className="p-2 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1">
          <span className="text-slate-500 text-[10px] block">KYC Verification</span>
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold border ${
              kycStatus === 'VERIFIED'
                ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60'
                : kycStatus === 'PARTIAL'
                ? 'bg-amber-950/80 text-amber-300 border-amber-800/60'
                : 'bg-rose-950/80 text-rose-300 border-rose-800/60'
            }`}
          >
            {kycStatus === 'VERIFIED' ? (
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
            ) : kycStatus === 'PARTIAL' ? (
              <AlertTriangle className="w-3 h-3 text-amber-400" />
            ) : (
              <ShieldAlert className="w-3 h-3 text-rose-400" />
            )}
            {kycStatus}
          </span>
        </div>

        {/* Account Age */}
        <div className="p-2 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1">
          <span className="text-slate-500 text-[10px] flex items-center gap-1">
            <Calendar className="w-2.5 h-2.5 text-slate-400" />
            Account Age
          </span>
          <strong className="text-slate-200 text-xs font-semibold block">
            {accountAge} Days {accountAge < 10 ? '(High Mule Risk)' : ''}
          </strong>
        </div>

        {/* Linked Phone */}
        <div className="p-2 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1">
          <span className="text-slate-500 text-[10px] flex items-center gap-1">
            <Phone className="w-2.5 h-2.5 text-slate-400" />
            Linked Phone
          </span>
          <strong className="text-slate-300 text-xs font-semibold block truncate">
            {linkedPhone}
          </strong>
        </div>

        {/* PAN or Tax ID */}
        <div className="p-2 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1">
          <span className="text-slate-500 text-[10px] flex items-center gap-1">
            <CreditCard className="w-2.5 h-2.5 text-slate-400" />
            PAN / Tax ID
          </span>
          <strong className="text-slate-300 text-xs font-semibold block truncate">
            {panOrTaxId}
          </strong>
        </div>
      </div>

      {/* Freezing Status Toggle Button */}
      <div className="pt-1">
        <button
          onClick={handleFreezeToggle}
          className={`w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-mono font-bold transition-all shadow-md ${
            isFrozen
              ? 'bg-emerald-950/90 hover:bg-emerald-900 border border-emerald-500 text-emerald-300 shadow-[0_0_15px_-3px_rgba(16,185,129,0.3)]'
              : 'bg-rose-950/80 hover:bg-rose-900 border border-rose-600 text-rose-300 shadow-[0_0_15px_-3px_rgba(244,63,94,0.3)]'
          }`}
          title="Toggle regulatory debit freeze on account"
        >
          {isFrozen ? (
            <>
              <Lock className="w-3.5 h-3.5 text-emerald-400" />
              <span>ACCOUNT FROZEN</span>
            </>
          ) : (
            <>
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>FREEZE ACCOUNT</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default EntityProfileCard;
