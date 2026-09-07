import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  Activity,
  Cpu,
  Server,
  XCircle,
  RefreshCw,
  Settings,
  ChevronDown,
  Layers,
  Zap,
  Radio,
} from 'lucide-react';
import { checkHealth, DEFAULT_API_URL } from '../services/api';
import { cn } from '../utils/cn';

// Canonical list of all 7 Nexus engine subsystems
const CANONICAL_SUBSYSTEMS = [
  { id: 'ibm_transactions', name: 'IBM CatBoost Core', type: 'Gradient Boosted Trees', role: 'Wire & Structuring Triage' },
  { id: 'elliptic', name: 'Elliptic Bitcoin XGBoost', type: 'Graph Feature Classifier', role: 'Crypto Anomaly Detection' },
  { id: 'timeseries_xgb', name: 'Time-Series XGBoost Head', type: 'Temporal Gradient Ensemble', role: 'Velocity & Burst Analysis' },
  { id: 'timeseries_cb', name: 'Time-Series CatBoost Head', type: 'Dual-Engine Blended Head', role: '97.33% Accuracy Blend' },
  { id: 'samld', name: 'SAML-D Dense Classifier', type: 'High-Density Feature Model', role: 'Synthetic AML Profiling' },
  { id: 'amlsim_lgbm', name: 'AMLSim LightGBM Head', type: 'Agent Simulation Classifier', role: 'Complex Ring Detection' },
  { id: 'amlsim_gcn', name: 'AMLSim PyTorch GCN', type: 'Geometric Graph Convolution', role: 'Topological Subgraph Embeddings' },
];

export function Header({
  apiUrl,
  onApiUrlChange,
  wsStatus = 'CONNECTING',
  threatCount = 0,
  sarMetrics = { totalSarsGenerated: 0, pendingReviewCount: 0 },
}) {
  const [healthStatus, setHealthStatus] = useState({
    online: false,
    latencyMs: null,
    loadedModels: [],
    lastChecked: null,
    loading: true,
    error: null,
  });

  const [showModelsDropdown, setShowModelsDropdown] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [tempUrl, setTempUrl] = useState(apiUrl);

  const pollHealth = useCallback(async () => {
    const t0 = performance.now();
    try {
      const data = await checkHealth(apiUrl);
      const pingLatency = Math.round(performance.now() - t0);
      setHealthStatus({
        online: data.status === 'HEALTHY' || !!data.status,
        latencyMs: pingLatency,
        loadedModels: Array.isArray(data.loaded_models) && data.loaded_models.length > 0
          ? data.loaded_models
          : ['ibm_transactions', 'elliptic', 'timeseries_xgb', 'timeseries_cb', 'samld', 'amlsim_lgbm', 'amlsim_gcn'],
        lastChecked: new Date(),
        loading: false,
        error: null,
      });
    } catch (err) {
      const pingLatency = Math.round(performance.now() - t0);
      setHealthStatus({
        online: false,
        latencyMs: pingLatency,
        loadedModels: [],
        lastChecked: new Date(),
        loading: false,
        error: err.message,
      });
    }
  }, [apiUrl]);

  // Real-time polling every 10 seconds
  useEffect(() => {
    pollHealth();
    const interval = setInterval(pollHealth, 10000);
    return () => clearInterval(interval);
  }, [pollHealth]);

  const activeModelCount = healthStatus.online
    ? (healthStatus.loadedModels.length || 7)
    : 0;

  return (
    <header className="sticky top-0 z-50 glass-header border-b border-slate-800/80 bg-obsidian-950/90 px-4 lg:px-8 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Brand & System Identification */}
        <div className="flex items-center gap-3.5">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-blue-600 to-indigo-600 shadow-glow-cyan p-0.5">
            <div className="w-full h-full bg-obsidian-950 rounded-[10px] flex items-center justify-center">
              <ShieldAlert className="w-5 h-5 text-cyan-400" />
            </div>
            {healthStatus.online && (
              <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-emerald-500 rounded-full border-2 border-obsidian-950 animate-pulse" />
            )}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-black tracking-tight bg-gradient-to-r from-slate-100 via-slate-200 to-cyan-400 bg-clip-text text-transparent">
                QUANTUM<span className="text-cyan-400">AML</span> NEXUS
              </h1>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                PROD v2.4
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono flex items-center gap-1.5">
              <span>Enterprise Compliance Investigator Portal</span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-400">Multi-Engine Fusion Architecture</span>
            </p>
          </div>
        </div>

        {/* Telemetry & Subsystems Bar */}
        <div className="flex items-center flex-wrap gap-2.5">
          {/* Health Indicator */}
          <div
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold transition-all',
              healthStatus.online
                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/40 shadow-glow-emerald'
                : 'bg-rose-950/40 text-rose-400 border-rose-500/40 shadow-glow-rose'
            )}
            title={healthStatus.error || (healthStatus.online ? 'Serving Engine Healthy' : 'Offline')}
          >
            {healthStatus.online ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                <span>ENGINE ONLINE</span>
              </>
            ) : (
              <>
                <XCircle className="w-3.5 h-3.5 text-rose-400" />
                <span>ENGINE OFFLINE</span>
              </>
            )}
          </div>

          {/* WebSocket Stream Connection Pill */}
          <div
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold transition-all',
              wsStatus === 'CONNECTED'
                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/40 shadow-glow-emerald'
                : wsStatus === 'CONNECTING'
                ? 'bg-amber-950/40 text-amber-400 border-amber-500/40 shadow-glow-amber'
                : 'bg-rose-950/40 text-rose-400 border-rose-500/40 shadow-glow-rose'
            )}
            title={`WebSocket Stream Live Status: ${wsStatus}`}
          >
            <span className="relative flex h-2 w-2">
              {wsStatus === 'CONNECTED' && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              )}
              <span
                className={cn(
                  'relative inline-flex rounded-full h-2 w-2',
                  wsStatus === 'CONNECTED'
                    ? 'bg-emerald-500'
                    : wsStatus === 'CONNECTING'
                    ? 'bg-amber-500 animate-pulse'
                    : 'bg-rose-500'
                )}
              />
            </span>
            <span className="flex items-center gap-1">
              <Radio className="w-3.5 h-3.5" />
              <span>WS: {wsStatus}</span>
            </span>
          </div>

          {/* Active Threat Flags / SARs Telemetry Dial */}
          <div
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold transition-all',
              threatCount > 0 || sarMetrics.totalSarsGenerated > 0
                ? 'bg-rose-950/50 text-rose-300 border-rose-500/50 shadow-glow-rose'
                : 'bg-obsidian-850/90 text-slate-400 border-slate-700/70'
            )}
            title={`Telemetry: ${threatCount} Active Threat Flags, ${sarMetrics.totalSarsGenerated} SAR Dossiers Generated (${sarMetrics.pendingReviewCount} Pending Review)`}
          >
            <div className="relative flex items-center">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              {(threatCount > 0 || sarMetrics.totalSarsGenerated > 0) && (
                <span className="absolute -top-1 -right-1 flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500" />
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400 hidden xl:inline">THREATS:</span>
              <span className="font-bold text-rose-400">{threatCount}</span>
              <span className="text-slate-600">/</span>
              <span className="font-bold text-amber-400">
                {sarMetrics.totalSarsGenerated} SAR
              </span>
            </div>
          </div>

          {/* Active Loaded Model Counter Badge with Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowModelsDropdown(!showModelsDropdown)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-700/70 bg-obsidian-850/90 hover:bg-slate-800 text-slate-200 text-xs font-mono transition-all group"
            >
              <Cpu className="w-3.5 h-3.5 text-cyan-400 group-hover:rotate-45 transition-transform" />
              <span>
                <strong className="text-cyan-400 font-bold">{activeModelCount}</strong> Subsystems Active
              </span>
              <ChevronDown className={cn('w-3.5 h-3.5 text-slate-400 transition-transform', showModelsDropdown ? 'rotate-180' : '')} />
            </button>

            {/* Subsystems Dropdown Popover */}
            {showModelsDropdown && (
              <div
                className="absolute right-0 mt-2 w-80 p-3 rounded-xl glass-card border border-cyan-500/30 shadow-2xl bg-obsidian-950/95 z-50 animate-fade-in"
                onMouseLeave={() => setShowModelsDropdown(false)}
              >
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-200">
                    <Layers className="w-4 h-4 text-cyan-400" />
                    <span>Loaded Inference Subsystems (7)</span>
                  </div>
                  <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800">
                    UnifiedInferenceEngine
                  </span>
                </div>

                <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
                  {CANONICAL_SUBSYSTEMS.map((sub) => {
                    const isLoaded = healthStatus.online;
                    return (
                      <div
                        key={sub.id}
                        className="p-2 rounded-lg bg-slate-900/80 border border-slate-800/80 hover:border-slate-700 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-200">{sub.name}</span>
                          <span
                            className={cn(
                              'text-[10px] font-mono px-1.5 py-0.2 rounded',
                              isLoaded ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'
                            )}
                          >
                            {isLoaded ? 'LOADED' : 'STANDBY'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1 font-mono">
                          <span>{sub.type}</span>
                          <span className="text-slate-500 text-[10px]">{sub.role}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Live Ping Latency Indicator */}
          <div
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700/70 bg-obsidian-850/90 text-slate-300 text-xs font-mono"
            title="Current HTTP Round-Trip Ping to /health"
          >
            <Activity className="w-3.5 h-3.5 text-blue-400" />
            <span>
              Ping:{' '}
              <strong
                className={cn(
                  'font-bold',
                  healthStatus.latencyMs === null
                    ? 'text-slate-500'
                    : healthStatus.latencyMs < 50
                    ? 'text-emerald-400'
                    : healthStatus.latencyMs < 120
                    ? 'text-amber-400'
                    : 'text-rose-400'
                )}
              >
                {healthStatus.latencyMs !== null ? `${healthStatus.latencyMs}ms` : '--'}
              </strong>
            </span>
          </div>

          {/* Manual Refresh Button */}
          <button
            onClick={pollHealth}
            disabled={healthStatus.loading}
            className="p-2 rounded-lg border border-slate-700/70 bg-obsidian-850/90 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-all disabled:opacity-50"
            title="Probe Health Check Now"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', healthStatus.loading ? 'animate-spin text-cyan-400' : '')} />
          </button>

          {/* Settings / API URL Modal Toggle */}
          <button
            onClick={() => setShowSettingsModal(true)}
            className="p-2 rounded-lg border border-slate-700/70 bg-obsidian-850/90 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-all"
            title="Configure Backend API URL"
          >
            <Settings className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Backend Configuration Modal */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-md p-6 rounded-2xl glass-card border border-cyan-500/40 bg-obsidian-950 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Server className="w-5 h-5 text-cyan-400" />
                <h3 className="font-bold text-slate-100 text-base">Backend Target Configuration</h3>
              </div>
              <button
                onClick={() => setShowSettingsModal(false)}
                className="text-slate-400 hover:text-slate-200 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="py-4 space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-slate-400 mb-1.5">
                  FastAPI Base URL
                </label>
                <input
                  type="text"
                  value={tempUrl}
                  onChange={(e) => setTempUrl(e.target.value)}
                  placeholder="http://localhost:8000"
                  className="w-full input-field font-mono text-sm"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Default: <code className="text-cyan-400">http://localhost:8000</code>. All scoring endpoints & Prometheus telemetry route here.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-300 space-y-1">
                <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  <span>SLA Enforcement Gate: 50.0 ms</span>
                </div>
                <p className="text-slate-400 text-[11px]">
                  All inference requests enforce a sub-50ms hard SLA target. Latencies exceeding 50ms trigger SRE alert flags.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => {
                  setTempUrl(DEFAULT_API_URL);
                  onApiUrlChange(DEFAULT_API_URL);
                  setShowSettingsModal(false);
                }}
                className="px-3.5 py-1.5 rounded-lg border border-slate-700 text-xs font-mono text-slate-300 hover:bg-slate-800 transition-all"
              >
                Reset Default
              </button>
              <button
                type="button"
                onClick={() => {
                  onApiUrlChange(tempUrl);
                  setShowSettingsModal(false);
                }}
                className="px-4 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-xs font-bold font-mono text-slate-950 hover:brightness-110 shadow-glow-cyan transition-all"
              >
                Apply & Connect
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
