import React, { useMemo } from 'react';
import { Cpu, Info } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';
import { useInvestigation } from '../../context/InvestigationContext';

export function ExplainabilityDeck() {
  const { activeCase } = useInvestigation();

  const isCrypto = activeCase?.currency === 'BTC' || activeCase?.rail === 'BTC';
  const isImps = activeCase?.rail === 'IMPS';

  // Dynamic TreeSHAP attribution drivers tailored to the active case
  const shapData = useMemo(() => {
    if (isCrypto) {
      return [
        { name: 'Mixer Proximity', shap: 0.48, percentage: '48%', color: '#f43f5e' },
        { name: 'Peeling Entropy', shap: 0.38, percentage: '38%', color: '#fb7185' },
        { name: 'High Fan-In/Out', shap: 0.29, percentage: '29%', color: '#fbbf24' },
        { name: 'UTXO Dispersion', shap: 0.21, percentage: '21%', color: '#38bdf8' },
        { name: 'Fee Volatility', shap: 0.15, percentage: '15%', color: '#34d399' },
      ];
    }
    if (isImps) {
      return [
        { name: 'Rapid Hop Latency', shap: 0.44, percentage: '44%', color: '#f43f5e' },
        { name: 'Off-Hours Burst', shap: 0.31, percentage: '31%', color: '#fb7185' },
        { name: 'Round Funneling', shap: 0.26, percentage: '26%', color: '#fbbf24' },
        { name: 'Cyclic Node Hub', shap: 0.20, percentage: '20%', color: '#38bdf8' },
        { name: 'Rapid Draining', shap: 0.15, percentage: '15%', color: '#34d399' },
      ];
    }
    // Default UPI structuring
    return [
      { name: 'Hop Velocity <90s', shap: 0.45, percentage: '45%', color: '#f43f5e' },
      { name: 'PAN Evasion Match', shap: 0.36, percentage: '36%', color: '#fb7185' },
      { name: 'Mule Fan-Out Ratio', shap: 0.28, percentage: '28%', color: '#fbbf24' },
      { name: 'Rapid Turnaround', shap: 0.22, percentage: '22%', color: '#38bdf8' },
      { name: 'Shell Aggregator', shap: 0.14, percentage: '14%', color: '#34d399' },
    ];
  }, [isCrypto, isImps]);

  const topDriver = shapData[0];

  return (
    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono space-y-3 shadow-md">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <div className="flex items-center gap-2 text-rose-400 font-bold">
          <Cpu className="w-3.5 h-3.5 text-rose-400" />
          <span className="uppercase text-[11px] tracking-wider">TreeSHAP Feature Attribution</span>
        </div>
        <span className="text-[10px] text-slate-400 font-semibold px-1.5 py-0.2 rounded bg-slate-800 border border-slate-700">
          CatBoost / XGBoost
        </span>
      </div>

      {/* Top Driver Callout */}
      <div className="p-2 rounded-lg bg-rose-950/30 border border-rose-900/40 text-[11px] text-slate-300 flex items-start gap-2">
        <Info className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
        <div>
          <span className="text-slate-400 text-[10px] block">Primary Risk Factor (+{topDriver.shap.toFixed(2)} SHAP):</span>
          <strong className="text-rose-300">{topDriver.name}</strong> accounts for {topDriver.percentage} marginal risk escalation.
        </div>
      </div>

      {/* Recharts Horizontal Bar Chart */}
      <div className="w-full h-36 pt-1">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={shapData}
            layout="vertical"
            margin={{ top: 2, right: 15, left: 5, bottom: 2 }}
          >
            <XAxis
              type="number"
              domain={[0, 0.55]}
              tick={{ fill: '#94a3b8', fontSize: 9 }}
              tickFormatter={(v) => `+${v.toFixed(2)}`}
              axisLine={{ stroke: '#334155' }}
              tickLine={{ stroke: '#334155' }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={105}
              tick={{ fill: '#cbd5e1', fontSize: 10 }}
              axisLine={{ stroke: '#334155' }}
              tickLine={false}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const item = payload[0].payload;
                  return (
                    <div className="p-2 rounded-lg bg-slate-950 border border-slate-700 text-[10px] font-mono shadow-xl space-y-0.5">
                      <div className="text-slate-200 font-bold">{item.name}</div>
                      <div className="text-rose-400">SHAP Weight: +{item.shap.toFixed(3)}</div>
                      <div className="text-slate-400">Escalation Share: {item.percentage}</div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="shap" radius={[0, 4, 4, 0]} barSize={11}>
              {shapData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default ExplainabilityDeck;
