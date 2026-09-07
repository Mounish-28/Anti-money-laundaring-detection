import React, { useState, useMemo } from 'react';
import {
  Bitcoin,
  Sparkles,
  AlertOctagon,
  CheckCircle2,
  Clock,
  Radio,
  FileCode,
  Shuffle,
  RefreshCw,
  Layers,
  Bell,
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie } from 'recharts';
import { scoreCrypto } from '../services/api';
import { RiskBadge } from './RiskBadge';
import { RiskGauge } from './RiskGauge';
import { LICIT_EXCHANGE_PRESET, DARKNET_MIXER_PRESET, generateRandomFeatures } from '../utils/cryptoPresets';
import { cn } from '../utils/cn';

export function CryptoTriage({ apiUrl, onScored }) {
  const [nodeId, setNodeId] = useState('btc_node_8492041');
  const [timestep, setTimestep] = useState(24);
  const [featureInputText, setFeatureInputText] = useState(
    LICIT_EXCHANGE_PRESET.join(', ')
  );
  const [loading, setLoading] = useState(false);
  const [verdict, setVerdict] = useState(null);
  const [error, setError] = useState(null);

  // Parse and validate the 165 features from raw text
  const { parsedFeatures, isValidCount, currentCount, parseError } = useMemo(() => {
    if (!featureInputText.trim()) {
      return { parsedFeatures: [], isValidCount: false, currentCount: 0, parseError: null };
    }

    try {
      // Split on commas, spaces, or newlines
      const tokens = featureInputText
        .replace(/[[\]]/g, '') // remove brackets if pasted as JSON array
        .split(/[,\s\n]+/)
        .map((t) => t.trim())
        .filter(Boolean);

      const floats = [];
      for (const token of tokens) {
        const num = parseFloat(token);
        if (isNaN(num)) {
          return {
            parsedFeatures: [],
            isValidCount: false,
            currentCount: floats.length,
            parseError: `Invalid floating point literal "${token}"`,
          };
        }
        floats.push(num);
      }

      return {
        parsedFeatures: floats,
        isValidCount: floats.length === 165,
        currentCount: floats.length,
        parseError: null,
      };
    } catch (err) {
      return {
        parsedFeatures: [],
        isValidCount: false,
        currentCount: 0,
        parseError: err.message,
      };
    }
  }, [featureInputText]);

  // Handle Preset Selection
  const applyPreset = (presetType) => {
    setError(null);
    if (presetType === 'licit') {
      setNodeId(`btc_licit_${Math.floor(100000 + Math.random() * 900000)}`);
      setTimestep(18);
      setFeatureInputText(LICIT_EXCHANGE_PRESET.join(', '));
    } else if (presetType === 'darknet') {
      setNodeId(`btc_darknet_${Math.floor(100000 + Math.random() * 900000)}`);
      setTimestep(34);
      setFeatureInputText(DARKNET_MIXER_PRESET.join(', '));
    } else if (presetType === 'random') {
      setNodeId(`btc_rand_${Math.floor(100000 + Math.random() * 900000)}`);
      setFeatureInputText(generateRandomFeatures(false).join(', '));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isValidCount) {
      setError(`Client validation failed: Expected exactly 165 features, received ${currentCount}.`);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Backend expects a 166-feature tensor: [timestep, ...165_features]
      const fullTensor = [Number(timestep), ...parsedFeatures];

      const payload = {
        node_id: nodeId.trim() || 'btc_node_custom',
        features: fullTensor,
      };

      const response = await scoreCrypto(payload, apiUrl);
      setVerdict(response);

      if (onScored) {
        onScored({
          ...response,
          timestamp: new Date().toISOString(),
          inputSummary: `Node ${payload.node_id} (t=${timestep}, 165 feats)`,
        });
      }
    } catch (err) {
      setError(err.message || 'Crypto scoring failed');
    } finally {
      setLoading(false);
    }
  };

  // Prepare chart data for probability breakdown
  const probData = useMemo(() => {
    if (!verdict) return [];
    const illicitProb = verdict.risk_score;
    const licitProb = Math.max(0, 1 - illicitProb);
    return [
      { name: 'Illicit / Mixer', value: illicitProb, color: '#f43f5e' },
      { name: 'Licit / Normal', value: licitProb, color: '#10b981' },
    ];
  }, [verdict]);

  // Sample mini-feature profile chart (first 12 features)
  const sampleFeatureChartData = useMemo(() => {
    if (parsedFeatures.length < 12) return [];
    return parsedFeatures.slice(0, 12).map((val, idx) => ({
      feature: `F${idx + 1}`,
      value: parseFloat(val.toFixed(3)),
    }));
  }, [parsedFeatures]);

  return (
    <div className="space-y-6">
      {/* Tab Header Banner */}
      <div className="p-4 rounded-xl glass-card border-cyan-500/20 bg-gradient-to-r from-obsidian-950 via-slate-900 to-obsidian-900 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-orange-500/10 text-orange-400 border border-orange-500/30">
            <Bitcoin className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <span>Elliptic Bitcoin Graph Node Triage (XGBoost)</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-orange-500/20 text-orange-400 border border-orange-500/30">
                166-Feature Tensor
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Evaluates temporal graph topology, in/out degree, and transaction clustering for illicit Bitcoin mixer and ransom trails.
            </p>
          </div>
        </div>

        {/* Preset Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-400 font-mono">Presets:</span>
          <button
            type="button"
            onClick={() => applyPreset('licit')}
            className="px-2.5 py-1.5 rounded-lg border border-emerald-500/30 hover:border-emerald-500/60 bg-obsidian-950/80 text-emerald-400 text-xs font-mono transition-all"
          >
            Licit Exchange Inflow
          </button>
          <button
            type="button"
            onClick={() => applyPreset('darknet')}
            className="px-2.5 py-1.5 rounded-lg border border-rose-500/30 hover:border-rose-500/60 bg-obsidian-950/80 text-rose-400 text-xs font-mono transition-all"
          >
            Darknet Mixer Flow
          </button>
          <button
            type="button"
            onClick={() => applyPreset('random')}
            className="px-2 py-1.5 rounded-lg border border-slate-700 hover:border-slate-500 bg-obsidian-950/80 text-slate-300 text-xs font-mono transition-all"
            title="Generate random 165-feature vector"
          >
            <Shuffle className="w-3.5 h-3.5 inline mr-1" />
            Random Tensor
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Form & Vector Input */}
        <div className="lg:col-span-7">
          <div className="p-6 rounded-2xl glass-card border-slate-800 bg-obsidian-950/80 shadow-panel">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-orange-400" />
                <h3 className="font-bold text-sm text-slate-200 uppercase tracking-wider font-mono">
                  Elliptic Node Tensor Payload
                </h3>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">POST /api/v1/score/crypto</span>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Node ID */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Graph Node ID (Bitcoin Transaction / Entity Hash)
                  </label>
                  <input
                    type="text"
                    required
                    value={nodeId}
                    onChange={(e) => setNodeId(e.target.value)}
                    className="w-full input-field font-mono"
                    placeholder="btc_node_901928"
                  />
                </div>

                {/* Timestep Slider (1 to 49) */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-mono text-slate-400">
                      Temporal Timestep (1 to 49)
                    </label>
                    <span className="text-xs font-mono font-bold text-cyan-400 px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800">
                      Step {timestep}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="49"
                    value={timestep}
                    onChange={(e) => setTimestep(parseInt(e.target.value))}
                    className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
                    <span>t=1 (Genesis window)</span>
                    <span>t=49 (Latest block)</span>
                  </div>
                </div>
              </div>

              {/* 165-Feature Vector Textarea */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Local Graph Features Vector (Exactly 165 Floats)</span>
                  </label>

                  {/* Real-Time Client Validation Counter */}
                  <span
                    className={cn(
                      'text-xs font-mono px-2.5 py-0.5 rounded-full border font-bold flex items-center gap-1',
                      isValidCount
                        ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                        : 'bg-rose-500/20 text-rose-400 border-rose-500/40 animate-pulse'
                    )}
                  >
                    {isValidCount ? (
                      <>
                        <CheckCircle2 className="w-3 h-3" />
                        <span>165 / 165 Validated</span>
                      </>
                    ) : (
                      <>
                        <AlertOctagon className="w-3 h-3" />
                        <span>{currentCount} / 165 Features</span>
                      </>
                    )}
                  </span>
                </div>

                <textarea
                  rows="6"
                  value={featureInputText}
                  onChange={(e) => setFeatureInputText(e.target.value)}
                  placeholder="Paste or enter 165 comma-separated or space-separated floating point values..."
                  className={cn(
                    'w-full input-field font-mono text-xs leading-relaxed transition-all resize-y',
                    isValidCount ? 'border-slate-700/80' : 'border-rose-500/60 focus:ring-rose-500/30'
                  )}
                />

                <div className="flex items-center justify-between mt-1 text-[11px] text-slate-500 font-mono">
                  <span>Input supports comma, space, or bracket JSON array notation.</span>
                  {parseError && <span className="text-rose-400">{parseError}</span>}
                </div>
              </div>

              {/* Mini Sample Feature Profile Bar Chart */}
              {sampleFeatureChartData.length > 0 && (
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-mono text-slate-400">
                      Sample Feature Profile (First 12 Features F1 - F12):
                    </span>
                    <span className="text-[10px] font-mono text-slate-500">Normalized Scale</span>
                  </div>
                  <div className="h-16 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={sampleFeatureChartData} margin={{ top: 0, right: 0, left: -25, bottom: 0 }}>
                        <XAxis dataKey="feature" tick={{ fill: '#64748b', fontSize: 9 }} interval={0} />
                        <YAxis tick={{ fill: '#64748b', fontSize: 9 }} />
                        <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                          {sampleFeatureChartData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={entry.value > 1.0 ? '#f43f5e' : entry.value > 0 ? '#06b6d4' : '#3b82f6'}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {error && (
                <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-500/50 text-rose-300 text-xs font-mono flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 text-rose-400 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading || !isValidCount}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-orange-500 via-amber-500 to-yellow-500 hover:from-orange-400 hover:to-yellow-400 text-slate-950 font-mono font-bold text-sm shadow-glow-amber transition-all disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
                      <span>Executing XGBoost Tensor Inference...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 text-slate-950" />
                      <span>Score 166-Feature Crypto Node</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right Column: Classification Verdict Card */}
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
                  <Radio className="w-4 h-4 text-orange-400" />
                  <h3 className="font-bold text-sm text-slate-200 uppercase tracking-wider font-mono">
                    Crypto Classification Output
                  </h3>
                </div>
                {verdict && <RiskBadge tier={verdict.risk_tier} size="sm" />}
              </div>

              {verdict ? (
                <div className="py-4 space-y-5 animate-fade-in">
                  {/* Probability Gauge */}
                  <RiskGauge score={verdict.risk_score} tier={verdict.risk_tier} />

                  {/* Dual Probability Breakdown Mini-Cards */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30">
                      <span className="block text-[10px] font-mono text-rose-300 uppercase">
                        P(Illicit Mixer)
                      </span>
                      <span className="text-lg font-mono font-black text-rose-400">
                        {(verdict.risk_score * 100).toFixed(2)}%
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30">
                      <span className="block text-[10px] font-mono text-emerald-300 uppercase">
                        P(Licit Entity)
                      </span>
                      <span className="text-lg font-mono font-black text-emerald-400">
                        {((1 - verdict.risk_score) * 100).toFixed(2)}%
                      </span>
                    </div>
                  </div>

                  {/* Recharts Probability Breakdown Donut Chart */}
                  {probData.length > 0 && (
                    <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
                      <div className="w-24 h-24 relative flex items-center justify-center">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={probData}
                              cx="50%"
                              cy="50%"
                              innerRadius={26}
                              outerRadius={38}
                              paddingAngle={3}
                              dataKey="value"
                            >
                              {probData.map((entry, index) => (
                                <Cell key={`pie-cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip
                              contentStyle={{
                                backgroundColor: '#070a11',
                                borderColor: '#06b6d4',
                                borderRadius: '0.5rem',
                                fontSize: '11px',
                                fontFamily: 'monospace',
                              }}
                              formatter={(v) => [`${(Number(v) * 100).toFixed(1)}%`]}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="flex-1 pl-4 space-y-1.5 text-xs font-mono">
                        <div className="text-[11px] font-bold text-slate-300">Classification Split</div>
                        <div className="flex items-center justify-between">
                          <span className="flex items-center gap-1.5 text-rose-400">
                            <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
                            <span>Illicit Node:</span>
                          </span>
                          <span className="font-bold text-rose-400">
                            {(verdict.risk_score * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="flex items-center gap-1.5 text-emerald-400">
                            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                            <span>Licit Node:</span>
                          </span>
                          <span className="font-bold text-emerald-400">
                            {((1 - verdict.risk_score) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Latency & SLA Check */}
                  <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/90 border border-slate-800">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-slate-400" />
                      <span className="text-xs font-mono text-slate-300">XGBoost Latency</span>
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

                  {/* Protocol Action & Anomaly Flag */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                      <span className="block text-[10px] font-mono uppercase text-slate-400 mb-1">
                        Graph Anomaly Flag
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
                            ILLICIT HOP
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            LICIT TRAFFIC
                          </>
                        )}
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                      <span className="block text-[10px] font-mono uppercase text-slate-400 mb-1">
                        Triage Recommendation
                      </span>
                      <span className="text-xs font-mono font-bold text-orange-300">
                        {verdict.recommended_action || 'FREEZE_ADDRESS'}
                      </span>
                    </div>
                  </div>

                  {/* Automated Celery SAR Alert Banner */}
                  {(verdict.risk_tier === 'CRITICAL_SAR' || verdict.is_anomaly) && (
                    <div className="p-3.5 rounded-xl bg-rose-950/70 border border-rose-500/50 shadow-glow-rose space-y-1.5 animate-pulse">
                      <div className="flex items-center gap-2 text-rose-400 font-mono font-bold text-xs">
                        <Bell className="w-4 h-4 animate-bounce" />
                        <span>CELERY CRYPTO SAR TASK ENQUEUED</span>
                      </div>
                      <p className="text-[11px] text-rose-200/90 font-mono leading-relaxed">
                        Elliptic node classified with high confidence of mixer taint. Address flagged for automated on-chain tracking and SAR FinCEN package creation.
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-16 text-center space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-600">
                    <Bitcoin className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-400">Node Ingestion Pending</h4>
                    <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
                      Select either the Licit Exchange or Darknet Mixer preset to load 165 graph features, then evaluate to observe the XGBoost classification breakdown.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {verdict && (
              <div className="pt-3 border-t border-slate-800/80 text-[11px] font-mono text-slate-500 flex items-center justify-between">
                <span>Model: elliptic_model.bin</span>
                <span>Node: {verdict.entity_id}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
