import React, { useState } from 'react';
import {
  Building2,
  ArrowRightLeft,
  DollarSign,
  Sparkles,
  Clock,
  AlertOctagon,
  CheckCircle,
  FileCheck,
  Radio,
  Bell,
  Cpu,
  RefreshCw,
} from 'lucide-react';
import { scoreTransaction } from '../services/api';
import { RiskGauge } from './RiskGauge';
import { RiskBadge } from './RiskBadge';
import { cn } from '../utils/cn';

const PRESETS = {
  payroll: {
    name: 'Standard Payroll',
    badge: 'Clean / Low Risk',
    desc: 'Regular bi-weekly direct deposit. ACH transfer, standard consumer account.',
    style: 'border-emerald-500/30 hover:border-emerald-500/60 text-emerald-400',
    data: {
      transaction_id: 'tx_payroll_9041',
      from_bank: '10',
      to_bank: '12',
      account_from: 'PAYROLL_CORP_881',
      account_to: 'EMP_SAVINGS_104',
      amount: 3250.00,
      currency: 'USD',
      payment_format: 'ACH',
    },
  },
  smurfing: {
    name: 'Rapid Smurfing / Structuring',
    badge: 'Structuring Alert',
    desc: 'Repetitive cash deposit structured just below the $10,000 BSA currency threshold.',
    style: 'border-amber-500/30 hover:border-amber-500/60 text-amber-400',
    data: {
      transaction_id: 'tx_smurf_8832',
      from_bank: '25',
      to_bank: '44',
      account_from: 'SMURF_LAYER_09',
      account_to: 'AGGREGATOR_77',
      amount: 9850.00,
      currency: 'USD',
      payment_format: 'Cash',
    },
  },
  crossBorder: {
    name: 'Cross-Border High-Risk Wire',
    badge: 'SAR Mandate',
    desc: 'Large volume offshore shell company wire to domestic holding account.',
    style: 'border-rose-500/30 hover:border-rose-500/60 text-rose-400',
    data: {
      transaction_id: 'tx_wire_9921',
      from_bank: '99_OFFSHORE',
      to_bank: '12_DOMESTIC',
      account_from: 'SHELL_CYPRUS_401',
      account_to: 'ESCROW_NY_990',
      amount: 485000.00,
      currency: 'USD',
      payment_format: 'Wire',
    },
  },
};

export function TransactionTriage({ apiUrl, onScored }) {
  const [formData, setFormData] = useState(PRESETS.payroll.data);
  const [loading, setLoading] = useState(false);
  const [verdict, setVerdict] = useState(null);
  const [error, setError] = useState(null);

  const handlePresetSelect = (presetKey) => {
    setFormData({ ...PRESETS[presetKey].data });
    setError(null);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'amount' ? (value === '' ? '' : parseFloat(value)) : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.amount || formData.amount <= 0) {
      setError('Amount must be greater than zero.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await scoreTransaction(formData, apiUrl);
      setVerdict(response);
      if (onScored) {
        onScored({
          ...response,
          timestamp: new Date().toISOString(),
          inputSummary: `${formData.payment_format} $${Number(formData.amount).toLocaleString()} (${formData.account_from} → ${formData.account_to})`,
        });
      }
    } catch (err) {
      setError(err.message || 'Failed to score transaction');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Tab Overview Banner */}
      <div className="p-4 rounded-xl glass-card border-cyan-500/20 bg-gradient-to-r from-obsidian-950 via-slate-900 to-obsidian-900 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <span>IBM Transactions CatBoost Triage Engine</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                Balanced Class Weights
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Evaluates 7 canonical tabular banking features against gradient-boosted AML classification trees.
            </p>
          </div>
        </div>

        {/* Quick Ingestion Preset Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-400 font-mono">Load Preset:</span>
          {Object.entries(PRESETS).map(([key, preset]) => (
            <button
              key={key}
              type="button"
              onClick={() => handlePresetSelect(key)}
              className={cn(
                'px-2.5 py-1.5 rounded-lg border text-xs font-mono font-medium transition-all bg-obsidian-950/80',
                preset.style
              )}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Form Specification */}
        <div className="lg:col-span-7">
          <div className="p-6 rounded-2xl glass-card border-slate-800 bg-obsidian-950/80 shadow-panel">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-cyan-400" />
                <h3 className="font-bold text-sm text-slate-200 uppercase tracking-wider font-mono">
                  Transaction Payload Specification
                </h3>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">POST /api/v1/score/transaction</span>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Transaction ID */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Transaction ID
                  </label>
                  <input
                    type="text"
                    name="transaction_id"
                    required
                    value={formData.transaction_id}
                    onChange={handleChange}
                    className="w-full input-field font-mono"
                    placeholder="tx_001928"
                  />
                </div>

                {/* Amount */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Amount ($)
                  </label>
                  <div className="relative">
                    <DollarSign className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      name="amount"
                      required
                      value={formData.amount}
                      onChange={handleChange}
                      className="w-full input-field font-mono pl-9"
                      placeholder="5000.00"
                    />
                  </div>
                </div>

                {/* From Bank */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Originating Bank (From Bank)
                  </label>
                  <div className="relative">
                    <Building2 className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      name="from_bank"
                      required
                      value={formData.from_bank}
                      onChange={handleChange}
                      className="w-full input-field font-mono pl-9"
                      placeholder="10"
                    />
                  </div>
                </div>

                {/* To Bank */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Beneficiary Bank (To Bank)
                  </label>
                  <div className="relative">
                    <Building2 className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      name="to_bank"
                      required
                      value={formData.to_bank}
                      onChange={handleChange}
                      className="w-full input-field font-mono pl-9"
                      placeholder="12"
                    />
                  </div>
                </div>

                {/* Account From */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Account From
                  </label>
                  <input
                    type="text"
                    name="account_from"
                    required
                    value={formData.account_from}
                    onChange={handleChange}
                    className="w-full input-field font-mono"
                    placeholder="ACC_FROM_001"
                  />
                </div>

                {/* Account To */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Account To
                  </label>
                  <input
                    type="text"
                    name="account_to"
                    required
                    value={formData.account_to}
                    onChange={handleChange}
                    className="w-full input-field font-mono"
                    placeholder="ACC_TO_002"
                  />
                </div>

                {/* Currency */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Currency
                  </label>
                  <select
                    name="currency"
                    value={formData.currency}
                    onChange={handleChange}
                    className="w-full select-field font-mono"
                  >
                    <option value="USD">USD - US Dollar</option>
                    <option value="EUR">EUR - Euro</option>
                    <option value="GBP">GBP - British Pound</option>
                    <option value="CHF">CHF - Swiss Franc</option>
                    <option value="CAD">CAD - Canadian Dollar</option>
                    <option value="JPY">JPY - Japanese Yen</option>
                    <option value="AUD">AUD - Australian Dollar</option>
                  </select>
                </div>

                {/* Payment Format */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Payment Format
                  </label>
                  <select
                    name="payment_format"
                    value={formData.payment_format}
                    onChange={handleChange}
                    className="w-full select-field font-mono"
                  >
                    <option value="ACH">ACH - Automated Clearing House</option>
                    <option value="Wire">Wire - Domestic / Swift Wire</option>
                    <option value="Credit Card">Credit Card</option>
                    <option value="Cash">Cash Deposit / Withdrawal</option>
                    <option value="Cheque">Cheque</option>
                    <option value="Cross-Border Wire">Cross-Border Wire</option>
                  </select>
                </div>
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-500/50 text-rose-300 text-xs font-mono flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 text-rose-400 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-mono font-bold text-sm shadow-glow-cyan transition-all disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
                      <span>Executing CatBoost Inference...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 text-slate-950" />
                      <span>Run CatBoost Anomaly Scoring</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right Column: Risk Verdict Card */}
        <div className="lg:col-span-5">
          <div
            className={cn(
              'p-6 rounded-2xl glass-card h-full flex flex-col justify-between transition-all border',
              verdict
                ? verdict.risk_tier === 'CRITICAL_SAR'
                  ? 'border-rose-500/50 bg-gradient-to-b from-rose-950/20 to-obsidian-950'
                  : verdict.risk_tier === 'HIGH'
                  ? 'border-orange-500/40 bg-gradient-to-b from-orange-950/20 to-obsidian-950'
                  : verdict.risk_tier === 'ELEVATED'
                  ? 'border-amber-500/30 bg-gradient-to-b from-amber-950/20 to-obsidian-950'
                  : 'border-emerald-500/30 bg-gradient-to-b from-emerald-950/20 to-obsidian-950'
                : 'border-slate-800 bg-obsidian-950/70'
            )}
          >
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Radio className="w-4 h-4 text-cyan-400" />
                  <h3 className="font-bold text-sm text-slate-200 uppercase tracking-wider font-mono">
                    Risk Verdict Card
                  </h3>
                </div>
                {verdict && <RiskBadge tier={verdict.risk_tier} size="sm" />}
              </div>

              {verdict ? (
                <div className="py-4 space-y-5 animate-fade-in">
                  {/* Probability Gauge */}
                  <RiskGauge score={verdict.risk_score} tier={verdict.risk_tier} />

                  {/* Latency & SLA Indicator */}
                  <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/90 border border-slate-800">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-slate-400" />
                      <span className="text-xs font-mono text-slate-300">Inference Latency</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono font-bold text-slate-100">
                        {verdict.latency_ms} ms
                      </span>
                      <span
                        className={cn(
                          'text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase',
                          verdict.latency_ms < 50
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        )}
                      >
                        {verdict.latency_ms < 50 ? 'SLA PASS (<50ms)' : 'SLA BREACH'}
                      </span>
                    </div>
                  </div>

                  {/* Recommended Action & Anomaly Flag */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                      <span className="block text-[10px] font-mono uppercase text-slate-400 mb-1">
                        Anomaly State
                      </span>
                      <span
                        className={cn(
                          'text-xs font-mono font-bold flex items-center gap-1.5',
                          verdict.is_anomaly ? 'text-rose-400' : 'text-emerald-400'
                        )}
                      >
                        {verdict.is_anomaly ? (
                          <>
                            <AlertOctagon className="w-3.5 h-3.5" />
                            POSITIVE ANOMALY
                          </>
                        ) : (
                          <>
                            <CheckCircle className="w-3.5 h-3.5" />
                            NORMAL TRAFFIC
                          </>
                        )}
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                      <span className="block text-[10px] font-mono uppercase text-slate-400 mb-1">
                        Action Protocol
                      </span>
                      <span className="text-xs font-mono font-bold text-cyan-300">
                        {verdict.recommended_action || 'EVALUATE'}
                      </span>
                    </div>
                  </div>

                  {/* Automated Celery SAR Dispatch Notification Badge */}
                  {(verdict.risk_tier === 'CRITICAL_SAR' || verdict.is_anomaly) && (
                    <div className="p-3.5 rounded-xl bg-rose-950/70 border border-rose-500/50 shadow-glow-rose space-y-1.5 animate-pulse">
                      <div className="flex items-center gap-2 text-rose-400 font-mono font-bold text-xs">
                        <Bell className="w-4 h-4 animate-bounce" />
                        <span>AUTOMATED CELERY SAR DISPATCH ENQUEUED</span>
                      </div>
                      <p className="text-[11px] text-rose-200/90 font-mono leading-relaxed">
                        Transaction exceeds high-risk compliance thresholds. Async task dispatched to Celery worker broker for automatic FinCEN SAR filing pipeline.
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-16 text-center space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-600">
                    <ArrowRightLeft className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-400">Awaiting Ingestion</h4>
                    <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
                      Select a preset above or enter custom attributes, then execute scoring to inspect CatBoost anomaly predictions.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {verdict && (
              <div className="pt-3 border-t border-slate-800/80 text-[11px] font-mono text-slate-500 flex items-center justify-between">
                <span>Model: ibm_transactions.cbm</span>
                <span>Entity: {verdict.entity_id}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
