export function getGraphTheme(showEdgeLabels = true) {
  return [
    // Base Node Styling
    {
      selector: 'node',
      style: {
        'shape': 'round-rectangle',
        'width': 36,
        'height': 36,
        'background-color': '#0284c7', // Default Sky-600
        'border-width': 2,
        'border-color': '#38bdf8',
        'border-opacity': 0.8,
        'label': 'data(label)',
        'color': '#f8fafc',
        'font-family': 'ui-monospace, SFMono-Regular, monospace',
        'font-size': '10px',
        'font-weight': 600,
        'text-valign': 'bottom',
        'text-margin-y': 6,
        'text-wrap': 'wrap',
        'text-max-width': '90px',
        'text-background-color': '#020617',
        'text-background-opacity': 0.85,
        'text-background-padding': '2px',
        'text-background-shape': 'roundrectangle',
        'transition-property': 'background-color, border-color, width, height',
        'transition-duration': '0.2s',
      },
    },

    // Origin / Source Entities
    {
      selector: 'node[type="ORIGIN"]',
      style: {
        'background-color': '#3b82f6', // blue-500
        'border-color': '#93c5fd',
        'shape': 'ellipse',
        'width': 34,
        'height': 34,
      },
    },

    // Suspect Entities (Critical)
    {
      selector: 'node[type="SUSPECT"], node[riskTier="CRITICAL"]',
      style: {
        'background-color': '#e11d48', // rose-600
        'border-color': '#fda4af',
        'border-width': 2.5,
        'width': 42,
        'height': 42,
        'shadow-blur': 12,
        'shadow-color': '#f43f5e',
        'shadow-opacity': 0.5,
      },
    },

    // Mule Entities (High Risk)
    {
      selector: 'node[type="MULE"], node[riskTier="HIGH"]',
      style: {
        'background-color': '#f59e0b', // amber-500
        'border-color': '#fde68a',
        'width': 36,
        'height': 36,
      },
    },

    // Intermediary / Transit Nodes
    {
      selector: 'node[type="INTERMEDIARY"]',
      style: {
        'background-color': '#0284c7', // sky-600
        'border-color': '#7dd3fc',
        'width': 32,
        'height': 32,
      },
    },

    // Destination / Exchange Nodes
    {
      selector: 'node[type="DESTINATION"]',
      style: {
        'background-color': '#10b981', // emerald-500
        'border-color': '#6ee7b7',
        'shape': 'round-diamond',
        'width': 38,
        'height': 38,
      },
    },

    // Selected Node Active Halo
    {
      selector: 'node:selected, node.selected',
      style: {
        'border-width': 3.5,
        'border-color': '#38bdf8', // cyan-400
        'shadow-blur': 18,
        'shadow-color': '#06b6d4',
        'shadow-opacity': 0.9,
      },
    },

    // Hovered Node
    {
      selector: 'node:active',
      style: {
        'overlay-opacity': 0.2,
        'overlay-color': '#38bdf8',
      },
    },

    // Base Edges
    {
      selector: 'edge',
      style: {
        'curve-style': 'bezier',
        'width': 2,
        'line-color': '#475569', // slate-600
        'target-arrow-shape': 'triangle',
        'target-arrow-color': '#475569',
        'arrow-scale': 0.9,
        'label': showEdgeLabels ? 'data(formattedAmount)' : '',
        'color': '#cbd5e1',
        'font-family': 'ui-monospace, monospace',
        'font-size': '9px',
        'font-weight': 600,
        'text-rotation': 'autorotate',
        'text-margin-y': -8,
        'text-background-color': '#020617',
        'text-background-opacity': 0.9,
        'text-background-padding': '3px',
        'text-background-shape': 'roundrectangle',
      },
    },

    // High Velocity Anomaly Hops (< 120s latency)
    {
      selector: 'edge[isHighVelocity]',
      style: {
        'line-color': '#f43f5e', // rose-500
        'target-arrow-color': '#f43f5e',
        'width': 2.8,
        'line-style': 'dashed',
        'line-dash-pattern': [6, 3],
      },
    },

    // Bulk Primary Transfers (Larger volume)
    {
      selector: 'edge[amount > 1000000], edge[amount > 5]',
      style: {
        'width': 3.8,
      },
    },

    // Selected Edge
    {
      selector: 'edge:selected',
      style: {
        'line-color': '#38bdf8',
        'target-arrow-color': '#38bdf8',
        'width': 3.5,
      },
    },
  ];
}

export const graphTheme = getGraphTheme(true);
export default graphTheme;
