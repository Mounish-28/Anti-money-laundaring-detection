import React from 'react';
import { ShieldCheck, AlertTriangle, AlertOctagon, Flame } from 'lucide-react';
import { cn } from '../utils/cn';

export function RiskBadge({ tier = 'LOW', size = 'md', showIcon = true, className = '' }) {
  const normalized = String(tier || 'LOW').toUpperCase();

  let config = {
    label: 'LOW RISK',
    bg: 'bg-emerald-500/15',
    text: 'text-emerald-400',
    border: 'border-emerald-500/30',
    icon: ShieldCheck,
    glow: 'shadow-glow-emerald',
    dot: 'bg-emerald-400',
  };

  if (normalized.includes('CRIT')) {
    config = {
      label: 'CRITICAL SAR',
      bg: 'bg-rose-500/20',
      text: 'text-rose-400',
      border: 'border-rose-500/50',
      icon: Flame,
      glow: 'shadow-glow-rose',
      dot: 'bg-rose-400 animate-ping',
    };
  } else if (normalized.includes('HIGH')) {
    config = {
      label: 'HIGH RISK',
      bg: 'bg-orange-500/20',
      text: 'text-orange-400',
      border: 'border-orange-500/40',
      icon: AlertOctagon,
      glow: 'shadow-glow-amber',
      dot: 'bg-orange-400',
    };
  } else if (normalized.includes('ELEV') || normalized.includes('MED')) {
    config = {
      label: 'ELEVATED',
      bg: 'bg-amber-500/15',
      text: 'text-amber-400',
      border: 'border-amber-500/30',
      icon: AlertTriangle,
      glow: 'shadow-glow-amber',
      dot: 'bg-amber-400',
    };
  }

  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
    lg: 'text-sm px-3.5 py-1.5 gap-2 font-bold',
  };

  const IconComponent = config.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border font-mono tracking-wider uppercase transition-all',
        config.bg,
        config.text,
        config.border,
        sizeClasses[size],
        normalized.includes('CRIT') ? config.glow : '',
        className
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full inline-block', config.dot)} />
      {showIcon && <IconComponent className={cn(size === 'sm' ? 'w-3 h-3' : size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5')} />}
      <span>{config.label}</span>
    </span>
  );
}
