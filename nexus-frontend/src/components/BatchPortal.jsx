import React, { useState, useMemo } from 'react';
import {
  UploadCloud,
  FileJson,
  Layers,
  Sparkles,
  AlertOctagon,
  CheckCircle2,
  Filter,
  ArrowUpDown,
  Search,
  RefreshCw,
  PlusCircle,
  Database,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { scoreBatch } from '../services/api';
import { RiskBadge } from './RiskBadge';
import { cn } from '../utils/cn';

// Sample batch generator for rapid zero-friction investigator testing
function generateSampleBatch(dataset = 'ibm_transactions', count = 12) {
  if (dataset === 'ibm_transactions') {
    const formats = ['ACH', 'Wire', 'Cash', 'Credit Card', 'Cross-Border Wire'];
    const currencies = ['USD', 'EUR', 'GBP'];
    return Array.from({ length: count }, (_, i) => {
      const isHighRisk = i % 4 === 0;
      const isCritical = i % 7 === 0;
      const amount = isCritical ? 350000 + i * 25000 : isHighRisk ? 9850 : 2500 + i * 450;
      return {
        transaction_id: `batch_ibm_${String(i + 1).padStart(4, '0')}`,
        from_bank: isCritical ? '99_OFFSHORE' : String(10 + (i % 5)),
        to_bank: String(20 + (i % 6)),
        account_from: isCritical ? `SHELL_HOLDING_${i}` : `CORP_ACCT_${100 + i}`,
        account_to: `BENEFICIARY_${200 + i}`,
        amount: parseFloat(amount.toFixed(2)),
        currency: currencies[i % currencies.length],
        payment_format: isCritical ? 'Wire' : isHighRisk ? 'Cash' : formats[i % formats.length],
      };
    });
  } else {
    // Elliptic node batch
    return Array.from({ length: count }, (_, i) => {
      const isIllicit = i % 3 === 0;
      const baseVal = isIllicit ? 1.5 : -0.1;
      const tensor166 = [
        (i % 49) + 1, // Timestep 1-49
        ...Array.from({ length: 165 }, (_, j) => parseFloat((baseVal + Math.sin(j + i) * 0.4).toFixed(4))),
      ];
      return {
        node_id: `batch_btc_${String(i + 1).padStart(4, '0')}`,
        features: tensor166,
      };
    });
  }
}

export function BatchPortal({ apiUrl, onAddBatchToLedger }) {
  const [selectedDataset, setSelectedDataset] = useState('ibm_transactions');
  const [jsonText, setJsonText] = useState('');
  const [fileName, setFileName] = useState('');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [batchResults, setBatchResults] = useState(null);
  const [error, setError] = useState(null);

  // Table filtering, sorting, pagination state
  const [searchQuery, setSearchQuery] = useState('');
  const [tierFilter, setTierFilter] = useState('ALL');
  const [sortField, setSortField] = useState('risk_score');
  const [sortDirection, setSortDirection] = useState('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;

  // Load sample JSON into textarea
  const handleLoadSample = (type = selectedDataset) => {
    const sample = generateSampleBatch(type, 12);
    setJsonText(JSON.stringify(sample, null, 2));
    setFileName(`sample_${type}_batch.json`);
    setError(null);
  };

  // Handle file drop or selection
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target?.result;
        const parsed = JSON.parse(content);
        if (!Array.isArray(parsed)) {
          setError('Invalid JSON: Root element must be an array of transaction/node objects.');
          return;
        }
        setJsonText(JSON.stringify(parsed, null, 2));
        setError(null);
      } catch (err) {
        setError(`Failed to parse JSON file: ${err.message}`);
      }
    };
    reader.readAsText(file);
  };

  // Execute Batch Evaluation
  const handleExecuteBatch = async () => {
    let items;
    try {
      items = JSON.parse(jsonText);
      if (!Array.isArray(items) || items.length === 0) {
        setError('Please provide a non-empty JSON array of items.');
        return;
      }
    } catch (err) {
      setError(`JSON Syntax Error: ${err.message}`);
      return;
    }

    setLoading(true);
    setError(null);
    setProgress(20);

    const progressTimer = setInterval(() => {
      setProgress((prev) => (prev < 90 ? prev + 15 : prev));
    }, 150);

    try {
      const res = await scoreBatch(selectedDataset, items, apiUrl);
      clearInterval(progressTimer);
      setProgress(100);

      // Backend returns either an array or an object with evaluations
      const evaluations = Array.isArray(res)
        ? res
        : Array.isArray(res.evaluations)
        ? res.evaluations
        : [];

      setBatchResults({
        totalEvaluated: evaluations.length,
        dataset: selectedDataset,
        evaluations,
        timestamp: new Date().toISOString(),
      });
      setCurrentPage(1);
    } catch (err) {
      clearInterval(progressTimer);
      setError(err.message || 'Batch evaluation failed');
      setProgress(0);
    } finally {
      setLoading(false);
    }
  };

  // Compute aggregate statistics
  const stats = useMemo(() => {
    if (!batchResults || !batchResults.evaluations.length) {
      return { total: 0, criticalPct: 0, highPct: 0, cleanPct: 0, avgScore: 0 };
    }
    const total = batchResults.evaluations.length;
    let crit = 0;
    let high = 0;
    let clean = 0;
    let scoreSum = 0;

    for (const item of batchResults.evaluations) {
      const tier = String(item.risk_tier || '').toUpperCase();
      const score = Number(item.risk_score || 0);
      scoreSum += score;

      if (tier.includes('CRIT')) crit++;
      else if (tier.includes('HIGH')) high++;
      else clean++;
    }

    return {
      total,
      criticalPct: ((crit / total) * 100).toFixed(1),
      highPct: ((high / total) * 100).toFixed(1),
      cleanPct: ((clean / total) * 100).toFixed(1),
      avgScore: (scoreSum / total).toFixed(4),
      critCount: crit,
      highCount: high,
      cleanCount: clean,
    };
  }, [batchResults]);

  // Filtered & Sorted evaluations for high-throughput table
  const filteredEvaluations = useMemo(() => {
    if (!batchResults?.evaluations) return [];

    return batchResults.evaluations
      .filter((item) => {
        // Search query by Entity ID
        if (searchQuery.trim()) {
          const id = String(item.entity_id || '').toLowerCase();
          if (!id.includes(searchQuery.toLowerCase())) return false;
        }

        // Tier filter
        if (tierFilter !== 'ALL') {
          const tier = String(item.risk_tier || '').toUpperCase();
          if (tierFilter === 'CRITICAL' && !tier.includes('CRIT')) return false;
          if (tierFilter === 'HIGH' && !tier.includes('HIGH')) return false;
          if (tierFilter === 'ELEVATED' && !tier.includes('ELEV') && !tier.includes('MED')) return false;
          if (tierFilter === 'LOW' && (tier.includes('CRIT') || tier.includes('HIGH') || tier.includes('ELEV'))) return false;
        }

        return true;
      })
      .sort((a, b) => {
        let valA = a[sortField];
        let valB = b[sortField];

        if (sortField === 'risk_score' || sortField === 'latency_ms') {
          valA = Number(valA || 0);
          valB = Number(valB || 0);
        } else {
          valA = String(valA || '').toLowerCase();
          valB = String(valB || '').toLowerCase();
        }

        if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
        if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
      });
  }, [batchResults, searchQuery, tierFilter, sortField, sortDirection]);

  // Pagination slice
  const paginatedEvaluations = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage;
    return filteredEvaluations.slice(start, start + rowsPerPage);
  }, [filteredEvaluations, currentPage]);

  const totalPages = Math.max(1, Math.ceil(filteredEvaluations.length / rowsPerPage));

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const handleAddAllToLedger = () => {
    if (!batchResults?.evaluations || !onAddBatchToLedger) return;
    onAddBatchToLedger(
      batchResults.evaluations.map((e) => ({
        ...e,
        timestamp: new Date().toISOString(),
        inputSummary: `Batch evaluated via ${batchResults.dataset}`,
      }))
    );
  };

  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="p-4 rounded-xl glass-card border-cyan-500/20 bg-gradient-to-r from-obsidian-950 via-slate-900 to-obsidian-900 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <span>High-Throughput Batch Ingestion & Triage Portal</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                Vectorized Parallel Scoring
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Ingest multi-record transaction payloads, evaluate risk distributions, and sort anomalous clusters at scale.
            </p>
          </div>
        </div>

        {/* Quick Sample & Action Bar */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => handleLoadSample(selectedDataset)}
            className="px-3 py-1.5 rounded-lg border border-cyan-500/30 hover:border-cyan-500/60 bg-obsidian-950/80 text-cyan-400 text-xs font-mono font-medium transition-all"
          >
            <Sparkles className="w-3.5 h-3.5 inline mr-1" />
            Load Sample 12-Item Batch
          </button>
        </div>
      </div>

      {/* Ingestion & Upload Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Upload & Config (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-6 rounded-2xl glass-card border-slate-800 bg-obsidian-950/80 shadow-panel">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
              <h3 className="font-bold text-sm text-slate-200 uppercase tracking-wider font-mono flex items-center gap-2">
                <Database className="w-4 h-4 text-cyan-400" />
                Batch Source & Target
              </h3>
              <span className="text-[11px] text-slate-500 font-mono">POST /api/v1/score/batch</span>
            </div>

            {/* Target Dataset Selector */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1.5">
                  Target Inference Pipeline
                </label>
                <select
                  value={selectedDataset}
                  onChange={(e) => {
                    setSelectedDataset(e.target.value);
                    if (jsonText) handleLoadSample(e.target.value);
                  }}
                  className="w-full select-field font-mono text-sm"
                >
                  <option value="ibm_transactions">IBM Transactions (CatBoost Classifier)</option>
                  <option value="elliptic">Elliptic Bitcoin (XGBoost Classifier)</option>
                  <option value="timeseries">Time-Series AML (Dual-Engine Blend)</option>
                  <option value="samld">SAML-D Dense Classifier</option>
                  <option value="amlsim">AMLSim LightGBM + GCN</option>
                </select>
              </div>

              {/* File Dropzone */}
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1.5">
                  Multi-Transaction JSON File
                </label>
                <label className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-700/70 hover:border-cyan-500/60 rounded-xl cursor-pointer bg-obsidian-950 hover:bg-slate-900/50 transition-all">
                  <UploadCloud className="w-8 h-8 text-slate-500 mb-1.5" />
                  <span className="text-xs font-mono text-slate-300">
                    {fileName ? fileName : 'Click to select or drop JSON file'}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono mt-0.5">
                    Accepts .json file with array of items
                  </span>
                  <input
                    type="file"
                    accept=".json"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
              </div>

              {/* Dispatch Action */}
              <button
                type="button"
                onClick={handleExecuteBatch}
                disabled={loading || !jsonText.trim()}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-mono font-bold text-sm shadow-glow-cyan transition-all disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
                    <span>Scoring Batch Records ({progress}%)...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-slate-950" />
                    <span>Execute High-Throughput Batch Scoring</span>
                  </>
                )}
              </button>

              {/* Progress Bar */}
              {loading && (
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-cyan-400 to-blue-500 h-2 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              )}

              {error && (
                <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-500/50 text-rose-300 text-xs font-mono flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 text-rose-400 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: JSON Editor / Preview (7 cols) */}
        <div className="lg:col-span-7">
          <div className="p-6 rounded-2xl glass-card border-slate-800 bg-obsidian-950/80 shadow-panel h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <FileJson className="w-4 h-4 text-cyan-400" />
                  <h3 className="font-bold text-sm text-slate-200 uppercase tracking-wider font-mono">
                    Batch Payload Editor (JSON Array)
                  </h3>
                </div>
                <button
                  onClick={() => setJsonText('')}
                  className="text-[11px] font-mono text-slate-500 hover:text-slate-300"
                >
                  Clear Buffer
                </button>
              </div>

              <textarea
                rows="11"
                value={jsonText}
                onChange={(e) => setJsonText(e.target.value)}
                placeholder="[ { ... }, { ... } ] - Or click 'Load Sample Batch' to test instantly"
                className="w-full input-field font-mono text-xs leading-relaxed transition-all resize-y"
              />
            </div>

            <div className="pt-2 text-[11px] text-slate-500 font-mono flex items-center justify-between">
              <span>Ready for parallel dispatch via FastAPI endpoint</span>
              {jsonText && (
                <span className="text-cyan-400">
                  Buffer length: {jsonText.length.toLocaleString()} chars
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Aggregate Risk Breakdown Statistics */}
      {batchResults && (
        <div className="space-y-4 animate-fade-in">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {/* Total Evaluated */}
            <div className="p-4 rounded-xl glass-card border-slate-800 bg-obsidian-950/80">
              <span className="block text-[11px] font-mono uppercase text-slate-400">
                Total Evaluated
              </span>
              <span className="text-2xl font-black font-mono text-slate-100 mt-1 block">
                {stats.total}
              </span>
              <span className="text-[10px] font-mono text-slate-500">100% vector completion</span>
            </div>

            {/* % Critical SAR */}
            <div className="p-4 rounded-xl glass-card border-rose-500/30 bg-rose-950/20">
              <span className="block text-[11px] font-mono uppercase text-rose-300">
                % Critical SAR
              </span>
              <span className="text-2xl font-black font-mono text-rose-400 mt-1 block">
                {stats.criticalPct}%
              </span>
              <span className="text-[10px] font-mono text-rose-300/80">
                {stats.critCount} entities flagged
              </span>
            </div>

            {/* % High Risk */}
            <div className="p-4 rounded-xl glass-card border-orange-500/30 bg-orange-950/20">
              <span className="block text-[11px] font-mono uppercase text-orange-300">
                % High Risk
              </span>
              <span className="text-2xl font-black font-mono text-orange-400 mt-1 block">
                {stats.highPct}%
              </span>
              <span className="text-[10px] font-mono text-orange-300/80">
                {stats.highCount} due diligence
              </span>
            </div>

            {/* % Clean / Low */}
            <div className="p-4 rounded-xl glass-card border-emerald-500/30 bg-emerald-950/20">
              <span className="block text-[11px] font-mono uppercase text-emerald-300">
                % Clean Traffic
              </span>
              <span className="text-2xl font-black font-mono text-emerald-400 mt-1 block">
                {stats.cleanPct}%
              </span>
              <span className="text-[10px] font-mono text-emerald-300/80">
                {stats.cleanCount} auto-cleared
              </span>
            </div>
          </div>

          {/* High-Throughput Scored Batch Table */}
          <div className="p-6 rounded-2xl glass-card border-slate-800 bg-obsidian-950/90 shadow-panel space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <h3 className="font-bold text-sm text-slate-200 uppercase tracking-wider font-mono">
                  Scored Batch Ledger ({filteredEvaluations.length} Results)
                </h3>
                {onAddBatchToLedger && (
                  <button
                    onClick={handleAddAllToLedger}
                    className="flex items-center gap-1.5 px-3 py-1 rounded-lg border border-cyan-500/40 bg-cyan-950/50 hover:bg-cyan-900/60 text-cyan-300 text-xs font-mono transition-all"
                  >
                    <PlusCircle className="w-3.5 h-3.5" />
                    <span>Append All to Global Ledger</span>
                  </button>
                )}
              </div>

              {/* Table Controls (Search & Filter) */}
              <div className="flex items-center gap-3 flex-wrap">
                {/* Search Bar */}
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      setCurrentPage(1);
                    }}
                    placeholder="Search Entity ID..."
                    className="input-field text-xs pl-8 py-1.5 font-mono w-44"
                  />
                </div>

                {/* Tier Filter */}
                <div className="flex items-center gap-1">
                  <Filter className="w-3.5 h-3.5 text-slate-500" />
                  <select
                    value={tierFilter}
                    onChange={(e) => {
                      setTierFilter(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="select-field text-xs py-1.5 font-mono"
                  >
                    <option value="ALL">All Tiers</option>
                    <option value="CRITICAL">Critical SAR</option>
                    <option value="HIGH">High Risk</option>
                    <option value="ELEVATED">Elevated</option>
                    <option value="LOW">Low Risk</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Responsive Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider">
                    <th
                      className="py-3 px-3 cursor-pointer hover:text-slate-200"
                      onClick={() => toggleSort('entity_id')}
                    >
                      <div className="flex items-center gap-1">
                        <span>Entity ID</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th
                      className="py-3 px-3 cursor-pointer hover:text-slate-200"
                      onClick={() => toggleSort('risk_score')}
                    >
                      <div className="flex items-center gap-1">
                        <span>Risk Score</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-3 px-3">Risk Tier</th>
                    <th className="py-3 px-3">Anomaly State</th>
                    <th className="py-3 px-3">Protocol Action</th>
                    <th
                      className="py-3 px-3 cursor-pointer hover:text-slate-200"
                      onClick={() => toggleSort('latency_ms')}
                    >
                      <div className="flex items-center gap-1">
                        <span>Latency</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {paginatedEvaluations.length > 0 ? (
                    paginatedEvaluations.map((item, idx) => (
                      <tr
                        key={`${item.entity_id}-${idx}`}
                        className="hover:bg-slate-900/50 transition-colors"
                      >
                        <td className="py-3 px-3 font-bold text-slate-200">
                          {item.entity_id}
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={cn(
                              'font-bold',
                              item.risk_score >= 0.985
                                ? 'text-rose-400'
                                : item.risk_score >= 0.95
                                ? 'text-orange-400'
                                : item.risk_score >= 0.85
                                ? 'text-amber-400'
                                : 'text-emerald-400'
                            )}
                          >
                            {(item.risk_score * 100).toFixed(1)}%
                          </span>
                          <span className="text-[10px] text-slate-500 ml-1">
                            ({item.risk_score.toFixed(4)})
                          </span>
                        </td>
                        <td className="py-3 px-3">
                          <RiskBadge tier={item.risk_tier} size="sm" />
                        </td>
                        <td className="py-3 px-3">
                          {item.is_anomaly ? (
                            <span className="text-rose-400 font-semibold flex items-center gap-1">
                              <AlertOctagon className="w-3 h-3" />
                              POSITIVE
                            </span>
                          ) : (
                            <span className="text-emerald-400 font-semibold flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" />
                              NORMAL
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-slate-300">
                          {item.recommended_action || 'AUTO_EVALUATED'}
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={cn(
                              'px-2 py-0.5 rounded text-[10px] font-bold',
                              item.latency_ms < 50
                                ? 'bg-emerald-500/10 text-emerald-400'
                                : 'bg-rose-500/10 text-rose-400'
                            )}
                          >
                            {item.latency_ms} ms
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6" className="py-8 text-center text-slate-500 font-mono">
                        No batch items match current filter criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-3 border-t border-slate-800 text-xs font-mono text-slate-400">
                <span>
                  Showing Page {currentPage} of {totalPages} ({filteredEvaluations.length} items)
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="p-1.5 rounded bg-slate-900 border border-slate-800 disabled:opacity-40 hover:bg-slate-800"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="p-1.5 rounded bg-slate-900 border border-slate-800 disabled:opacity-40 hover:bg-slate-800"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
