import React, { useState, useEffect } from 'react';
import { Cpu, Sparkles, Activity } from 'lucide-react';
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
import { fetchExplainability } from '../../api/sarApi';

/**
 * Dynamic bar color based on TreeSHAP weight thresholds
 * Weight >= 25: #e11d48 (rose-600)
 * Weight >= 15: #f59e0b (amber-500)
 * Weight < 15:  #0284c7 (sky-500)
 */
function getBarColor(weight) {
  if (weight >= 25) return '#e11d48';
  if (weight >= 15) return '#f59e0b';
  return '#0284c7';
}

export function ExplainabilityDeck() {
  const { activeCaseId } = useInvestigation();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    fetchExplainability(activeCaseId)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [activeCaseId]);

  const confidencePct = data?.modelConfidence ? (data.modelConfidence * 100).toFixed(1) : '94.2';
  const engineName = data?.engineName || 'CatBoost + XGBoost Ensemble v4';
  const features = data?.featureImportance || [];

  // Radial gauge calculations for mini circular progress
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (Number(confidencePct) / 100) * circumference;

  return (
    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono space-y-3 shadow-md relative overflow-hidden select-none">
      {/* Background ambient glow */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/5 rounded-full blur-2xl pointer-events-none" />

      {/* Header Section */}
      <div className="flex items-center justify-between pb-2.5 border-b border-slate-800/80">
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 font-bold text-rose-400">
            <Cpu className="w-3.5 h-3.5 text-rose-400" />
            <span className="uppercase text-[11px] tracking-wider">ML Explainability Deck</span>
          </div>
          {/* Model Engine Badge */}
          <span className="inline-flex items-center gap-1 text-[10px] text-slate-400 font-mono px-2 py-0.5 rounded bg-slate-800/90 border border-slate-700/60">
            <Sparkles className="w-2.5 h-2.5 text-rose-400" />
            {engineName}
          </span>
        </div>

        {/* Anomaly Confidence: Mini Radial Gauge & Bold Pill */}
        <div className="flex items-center gap-2 bg-slate-950/80 p-1.5 rounded-xl border border-slate-800">
          <div className="relative w-10 h-10 flex items-center justify-center">
            <svg className="w-10 h-10 transform -rotate-90" viewBox="0 0 44 44">
              <circle
                cx="22"
                cy="22"
                r={radius}
                stroke="#1e293b"
                strokeWidth="3.5"
                fill="transparent"
              />
              <circle
                cx="22"
                cy="22"
                r={radius}
                stroke="#e11d48"
                strokeWidth="3.5"
                fill="transparent"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                className="transition-all duration-700 ease-out"
              />
            </svg>
            <span className="absolute text-[9px] font-black text-rose-300">
              {Math.round(Number(confidencePct))}%
            </span>
          </div>
          <div className="text-right pr-1">
            <span className="text-[9px] font-bold text-slate-400 uppercase block tracking-tight">
              Confidence
            </span>
            <span className="text-[11px] font-black text-rose-400 tracking-tight">
              {confidencePct}% Prob.
            </span>
          </div>
        </div>
      </div>

      {/* Primary Driver Summary */}
      <div className="flex items-center justify-between text-[11px] text-slate-300 bg-slate-950/70 p-2 rounded-lg border border-slate-800/80">
        <span className="flex items-center gap-1.5 text-slate-400 text-[10px]">
          <Activity className="w-3 h-3 text-rose-400" />
          Primary Attribution:
        </span>
        <strong className="text-rose-300 text-[11px] font-bold">
          {features[0]?.feature || 'Off-Hours Burst Velocity'} (+{features[0]?.weight || 34}%)
        </strong>
      </div>

      {/* Horizontal Feature Importance Bar Chart */}
      <div className="w-full h-44 pt-1">
        {loading ? (
          <div className="w-full h-full flex items-center justify-center text-slate-500 text-xs font-mono">
            Evaluating TreeSHAP attribution...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={features}
              layout="vertical"
              margin={{ top: 2, right: 16, left: -8, bottom: 2 }}
            >
              <XAxis
                type="number"
                domain={[0, 40]}
                tick={{ fill: '#64748b', fontSize: 9 }}
                tickFormatter={(v) => `${v}%`}
                axisLine={{ stroke: '#334155' }}
                tickLine={{ stroke: '#334155' }}
              />
              <YAxis
                type="category"
                dataKey="feature"
                width={140}
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                axisLine={{ stroke: '#334155' }}
                tickLine={false}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload;
                    const impactColor =
                      d.impact === 'HIGH'
                        ? 'text-rose-400'
                        : d.impact === 'MEDIUM'
                        ? 'text-amber-400'
                        : 'text-sky-400';

                    return (
                      <div className="p-2.5 rounded-lg bg-slate-950/95 border border-slate-700 text-xs font-mono shadow-xl space-y-1">
                        <div className="font-bold text-slate-100">{d.feature}</div>
                        <div className="flex items-center justify-between gap-4 text-[11px]">
                          <span className="text-slate-400">Risk Weight:</span>
                          <span className="text-rose-400 font-bold">{d.weight}%</span>
                        </div>
                        <div className="flex items-center justify-between gap-4 text-[11px]">
                          <span className="text-slate-400">Risk Impact:</span>
                          <span className={`font-bold ${impactColor}`}>{d.impact}</span>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="weight" radius={[0, 4, 4, 0]} barSize={12}>
                {features.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getBarColor(entry.weight)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Legend Footer */}
      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-800/60 font-mono">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-rose-600" />
          High Risk (&ge;25%)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          Medium (&ge;15%)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-sky-500" />
          Low (&lt;15%)
        </span>
      </div>
    </div>
  );
}

export default ExplainabilityDeck;
