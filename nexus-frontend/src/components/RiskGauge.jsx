import React, { useMemo } from 'react';
import { cn } from '../utils/cn';

/**
 * Enterprise Risk Probability Gauge
 * Visualizes ML model probability [0.0000 -> 1.0000] with dynamic color graduation.
 */
export function RiskGauge({ score = 0, tier = 'LOW', _size = 200, className = '' }) {
  const clampedScore = Math.max(0, Math.min(1, Number(score) || 0));
  const percentage = (clampedScore * 100).toFixed(1);

  // SVG Gauge calculations (Semi-circle arc from 180deg to 360deg)
  const radius = 70;
  const strokeWidth = 12;
  const cx = 100;
  const cy = 95;
  const circumference = Math.PI * radius; // Half-circle circumference
  const strokeDashoffset = circumference - (clampedScore * circumference);

  const { strokeColor, glowClass, textGradient } = useMemo(() => {
    if (clampedScore >= 0.985 || tier === 'CRITICAL_SAR') {
      return {
        strokeColor: '#f43f5e',
        glowClass: 'drop-shadow-[0_0_12px_rgba(244,63,94,0.6)]',
        textGradient: 'from-rose-400 to-red-500',
      };
    } else if (clampedScore >= 0.95 || tier === 'HIGH') {
      return {
        strokeColor: '#f97316',
        glowClass: 'drop-shadow-[0_0_10px_rgba(249,115,22,0.5)]',
        textGradient: 'from-orange-400 to-amber-500',
      };
    } else if (clampedScore >= 0.85 || tier === 'ELEVATED') {
      return {
        strokeColor: '#f59e0b',
        glowClass: 'drop-shadow-[0_0_8px_rgba(245,158,11,0.4)]',
        textGradient: 'from-amber-300 to-yellow-500',
      };
    }
    return {
      strokeColor: '#10b981',
      glowClass: 'drop-shadow-[0_0_8px_rgba(16,185,129,0.35)]',
      textGradient: 'from-emerald-400 to-teal-400',
    };
  }, [clampedScore, tier]);

  return (
    <div className={cn('relative flex flex-col items-center justify-center', className)}>
      <svg
        viewBox="0 0 200 120"
        className="w-full max-w-[220px] overflow-visible"
        style={{ filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.4))' }}
      >
        <defs>
          <linearGradient id="gaugeBgGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#1e293b" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#0f172a" stopOpacity="0.8" />
          </linearGradient>
          <linearGradient id="riskTrackGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#10b981" />
            <stop offset="60%" stopColor="#f59e0b" />
            <stop offset="85%" stopColor="#f97316" />
            <stop offset="100%" stopColor="#f43f5e" />
          </linearGradient>
        </defs>

        {/* Track Background */}
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke="url(#gaugeBgGradient)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />

        {/* Subtle threshold tick marks */}
        {/* 85% tick */}
        <line
          x1={cx + radius * Math.cos(Math.PI * (1 - 0.85))}
          y1={cy - radius * Math.sin(Math.PI * (1 - 0.85))}
          x2={cx + (radius + 6) * Math.cos(Math.PI * (1 - 0.85))}
          y2={cy - (radius + 6) * Math.sin(Math.PI * (1 - 0.85))}
          stroke="#f59e0b"
          strokeWidth="1.5"
          opacity="0.7"
        />
        {/* 95% tick */}
        <line
          x1={cx + radius * Math.cos(Math.PI * (1 - 0.95))}
          y1={cy - radius * Math.sin(Math.PI * (1 - 0.95))}
          x2={cx + (radius + 6) * Math.cos(Math.PI * (1 - 0.95))}
          y2={cy - (radius + 6) * Math.sin(Math.PI * (1 - 0.95))}
          stroke="#f97316"
          strokeWidth="1.5"
          opacity="0.8"
        />

        {/* Dynamic Animated Meter Fill */}
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={cn('transition-all duration-700 ease-out', glowClass)}
        />
      </svg>

      {/* Numerical Readout */}
      <div className="absolute top-[52px] flex flex-col items-center">
        <span className={cn('text-3xl font-extrabold font-mono tracking-tight bg-gradient-to-r bg-clip-text text-transparent', textGradient)}>
          {percentage}%
        </span>
        <span className="text-[11px] text-slate-400 font-mono tracking-wider uppercase mt-0.5">
          P(Anomaly) = {Number(clampedScore).toFixed(4)}
        </span>
      </div>

      {/* Threshold Legenda */}
      <div className="flex items-center justify-between w-full max-w-[200px] text-[10px] text-slate-500 font-mono pt-1">
        <span>0.00 CLEAN</span>
        <span className="text-amber-400/80">0.85 ELEV</span>
        <span className="text-rose-400/90">0.98 SAR</span>
      </div>
    </div>
  );
}
