import React from 'react';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Tag,
  Share2,
} from 'lucide-react';

const LAYOUTS = [
  { id: 'cose', label: 'Force (COSE)' },
  { id: 'concentric', label: 'Concentric' },
  { id: 'breadthfirst', label: 'Tree (Flow)' },
  { id: 'circle', label: 'Circle' },
];

export function GraphControls({
  currentLayout = 'cose',
  onLayoutChange,
  onZoomIn,
  onZoomOut,
  onFit,
  onReset,
  showEdgeLabels = true,
  onToggleLabels,
}) {
  return (
    <div className="flex items-center gap-1.5 p-1 rounded-xl bg-surface-950/85 backdrop-blur-md border border-slate-800 shadow-xl select-none text-xs font-mono">
      {/* Layout Selector Dropdown */}
      <div className="flex items-center gap-1 px-1 border-r border-slate-800 pr-2">
        <Share2 className="w-3.5 h-3.5 text-slate-500 hidden sm:inline" />
        <select
          value={currentLayout}
          onChange={(e) => onLayoutChange && onLayoutChange(e.target.value)}
          className="bg-surface-900 border border-slate-700/80 rounded-lg px-2 py-1 text-[11px] font-mono text-cyan-300 focus:outline-none focus:border-cyan-500 cursor-pointer"
        >
          {LAYOUTS.map((l) => (
            <option key={l.id} value={l.id} className="bg-slate-900 text-slate-200">
              {l.label}
            </option>
          ))}
        </select>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-0.5">
        <button
          onClick={onZoomIn}
          title="Zoom In (+)"
          className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={onZoomOut}
          title="Zoom Out (-)"
          className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={onFit}
          title="Fit Canvas to View"
          className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-cyan-300 transition-colors"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={onReset}
          title="Reset & Re-run Layout Animation"
          className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-amber-300 transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={onToggleLabels}
          title={showEdgeLabels ? 'Hide Edge Transfer Labels' : 'Show Edge Transfer Labels'}
          className={`p-1.5 rounded-lg transition-colors ${
            showEdgeLabels
              ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-800/40'
              : 'hover:bg-slate-800 text-slate-500 hover:text-slate-300'
          }`}
        >
          <Tag className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

export default GraphControls;
