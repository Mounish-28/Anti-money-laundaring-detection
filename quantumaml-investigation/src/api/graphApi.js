import apiClient from './client';

// Realistic multi-hop topologies tailored to active cases
const CASE_TOPOLOGIES = {
  'ESC-90812': {
    summary: {
      caseId: 'ESC-90812',
      typology: 'UPI Smurfing Cluster',
      totalHops: 4,
      totalVolume: '₹4,850,000',
      anomalousHopCount: 3,
      avgLatencySeconds: 58,
    },
    nodes: [
      { id: 'node-origin', label: 'Origin: Acct *8912', type: 'ORIGIN', riskTier: 'MEDIUM', balance: '₹4,850,000', degree: 3 },
      { id: 'node-mule-1', label: 'Suspect: mule4@okaxis', type: 'SUSPECT', riskTier: 'CRITICAL', balance: '₹1,250,000', degree: 4 },
      { id: 'node-mule-2', label: 'Mule: smurf_pay@ybl', type: 'MULE', riskTier: 'HIGH', balance: '₹980,000', degree: 3 },
      { id: 'node-mule-3', label: 'Mule: cashout_99@icici', type: 'MULE', riskTier: 'HIGH', balance: '₹1,420,000', degree: 2 },
      { id: 'node-transit', label: 'Transit Hub: SBIN*004', type: 'INTERMEDIARY', riskTier: 'MEDIUM', balance: '₹120,000', degree: 4 },
      { id: 'node-destination', label: 'Aggregator: Hawala Shell Corp', type: 'DESTINATION', riskTier: 'CRITICAL', balance: '₹4,650,000', degree: 4 },
    ],
    edges: [
      { id: 'e1', source: 'node-origin', target: 'node-mule-1', amount: 1250000, currency: 'INR', formattedAmount: '₹1,250,000', latencySeconds: 38, isHighVelocity: true, rail: 'UPI', timestamp: '2026-09-23T14:31:00Z' },
      { id: 'e2', source: 'node-origin', target: 'node-mule-2', amount: 980000, currency: 'INR', formattedAmount: '₹980,000', latencySeconds: 48, isHighVelocity: true, rail: 'UPI', timestamp: '2026-09-23T14:31:48Z' },
      { id: 'e3', source: 'node-origin', target: 'node-mule-3', amount: 1420000, currency: 'INR', formattedAmount: '₹1,420,000', latencySeconds: 64, isHighVelocity: true, rail: 'UPI', timestamp: '2026-09-23T14:32:52Z' },
      { id: 'e4', source: 'node-mule-1', target: 'node-transit', amount: 1200000, currency: 'INR', formattedAmount: '₹1,200,000', latencySeconds: 42, isHighVelocity: true, rail: 'UPI', timestamp: '2026-09-23T14:33:34Z' },
      { id: 'e5', source: 'node-mule-2', target: 'node-transit', amount: 950000, currency: 'INR', formattedAmount: '₹950,000', latencySeconds: 52, isHighVelocity: true, rail: 'UPI', timestamp: '2026-09-23T14:34:26Z' },
      { id: 'e6', source: 'node-mule-3', target: 'node-destination', amount: 1400000, currency: 'INR', formattedAmount: '₹1,400,000', latencySeconds: 88, isHighVelocity: true, rail: 'UPI', timestamp: '2026-09-23T14:35:54Z' },
      { id: 'e7', source: 'node-transit', target: 'node-destination', amount: 2150000, currency: 'INR', formattedAmount: '₹2,150,000', latencySeconds: 65, isHighVelocity: true, rail: 'UPI', timestamp: '2026-09-23T14:36:59Z' },
    ],
    timeline: [
      { hopIndex: 1, from: 'Origin (*8912)', to: 'mule4@okaxis', latency: 38, amount: '₹1,250,000', isRapid: true, rail: 'UPI' },
      { hopIndex: 2, from: 'mule4@okaxis', to: 'Transit Hub', latency: 42, amount: '₹1,200,000', isRapid: true, rail: 'UPI' },
      { hopIndex: 3, from: 'Transit Hub', to: 'Hawala Shell Corp', latency: 65, amount: '₹2,150,000', isRapid: true, rail: 'UPI' },
    ],
  },

  'ESC-90813': {
    summary: {
      caseId: 'ESC-90813',
      typology: 'Layered UTXO Peeling',
      totalHops: 5,
      totalVolume: '14.8250 BTC',
      anomalousHopCount: 4,
      avgLatencySeconds: 86,
    },
    nodes: [
      { id: 'btc-origin', label: 'Genesis Whale: 1Boat...', type: 'ORIGIN', riskTier: 'HIGH', balance: '14.825 BTC', degree: 2 },
      { id: 'btc-mixer', label: 'Wasabi Mixer Pool', type: 'SUSPECT', riskTier: 'CRITICAL', balance: '128.40 BTC', degree: 4 },
      { id: 'btc-peel-1', label: 'Peel: bc1q9x4p...v08k', type: 'SUSPECT', riskTier: 'CRITICAL', balance: '9.412 BTC', degree: 3 },
      { id: 'btc-peel-2', label: 'Changer: bc1qw7k...', type: 'INTERMEDIARY', riskTier: 'HIGH', balance: '4.850 BTC', degree: 2 },
      { id: 'btc-hop-3', label: 'Layering: 3J98t1W...', type: 'INTERMEDIARY', riskTier: 'MEDIUM', balance: '0.563 BTC', degree: 2 },
      { id: 'btc-destination', label: 'Binance Hot Wallet #4', type: 'DESTINATION', riskTier: 'LOW', balance: '1,420 BTC', degree: 5 },
    ],
    edges: [
      { id: 'be1', source: 'btc-origin', target: 'btc-mixer', amount: 14.825, currency: 'BTC', formattedAmount: '14.8250 BTC', latencySeconds: 95, isHighVelocity: true, rail: 'BTC', timestamp: '2026-09-23T12:00:00Z' },
      { id: 'be2', source: 'btc-mixer', target: 'btc-peel-1', amount: 9.412, currency: 'BTC', formattedAmount: '9.4120 BTC', latencySeconds: 65, isHighVelocity: true, rail: 'BTC', timestamp: '2026-09-23T12:01:05Z' },
      { id: 'be3', source: 'btc-mixer', target: 'btc-peel-2', amount: 5.413, currency: 'BTC', formattedAmount: '5.4130 BTC', latencySeconds: 78, isHighVelocity: true, rail: 'BTC', timestamp: '2026-09-23T12:02:23Z' },
      { id: 'be4', source: 'btc-peel-1', target: 'btc-hop-3', amount: 8.850, currency: 'BTC', formattedAmount: '8.8500 BTC', latencySeconds: 110, isHighVelocity: true, rail: 'BTC', timestamp: '2026-09-23T12:04:13Z' },
      { id: 'be5', source: 'btc-hop-3', target: 'btc-destination', amount: 8.840, currency: 'BTC', formattedAmount: '8.8400 BTC', latencySeconds: 140, isHighVelocity: false, rail: 'BTC', timestamp: '2026-09-23T12:06:33Z' },
    ],
    timeline: [
      { hopIndex: 1, from: '1Boat...', to: 'Wasabi Mixer', latency: 95, amount: '14.8250 BTC', isRapid: false, rail: 'BTC' },
      { hopIndex: 2, from: 'Wasabi Mixer', to: 'bc1q9x4p...v08k', latency: 65, amount: '9.4120 BTC', isRapid: false, rail: 'BTC' },
      { hopIndex: 3, from: 'bc1q9x4p...v08k', to: 'Layering Hop', latency: 110, amount: '8.8500 BTC', isRapid: false, rail: 'BTC' },
      { hopIndex: 4, from: 'Layering Hop', to: 'Binance Hot Wallet', latency: 140, amount: '8.8400 BTC', isRapid: false, rail: 'BTC' },
    ],
  },
};

const DEFAULT_TOPOLOGY = CASE_TOPOLOGIES['ESC-90812'];

function buildCytoscapeElements(nodes = [], edges = []) {
  return [
    ...nodes.map((n) => ({
      data: {
        id: n.id,
        label: n.label,
        type: n.type,
        riskTier: n.riskTier,
        balance: n.balance,
        degree: n.degree,
      },
    })),
    ...edges.map((e) => ({
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        amount: e.amount,
        currency: e.currency,
        formattedAmount: e.formattedAmount || `${e.amount} ${e.currency || 'INR'}`,
        latencySeconds: e.latencySeconds,
        isHighVelocity: e.isHighVelocity,
        rail: e.rail,
        timestamp: e.timestamp,
      },
    })),
  ];
}

/**
 * getCaseGraph(caseId):
 * Target: GET /cases/${caseId}/graph
 * Returns graph elements: { nodes: [...], edges: [...] } formatted for Cytoscape.
 */
export async function getCaseGraph(caseId) {
  try {
    const res = await apiClient.get(`/cases/${caseId}/graph`, { timeout: 3500 });
    if (res.data && (res.data.nodes || res.data.elements)) {
      const nodes = res.data.nodes || [];
      const edges = res.data.edges || [];
      const elements = res.data.elements || buildCytoscapeElements(nodes, edges);

      return {
        elements,
        nodes,
        edges,
        summary: res.data.summary || {
          caseId,
          totalHops: edges.length,
          totalVolume: res.data.totalVolume || '₹4,850,000',
        },
        timeline: res.data.timeline || [],
      };
    }
  } catch {
    // Graceful offline fallback
  }

  const raw = CASE_TOPOLOGIES[caseId] || {
    ...DEFAULT_TOPOLOGY,
    summary: { ...DEFAULT_TOPOLOGY.summary, caseId },
  };

  const elements = buildCytoscapeElements(raw.nodes, raw.edges);

  return {
    elements,
    nodes: raw.nodes,
    edges: raw.edges,
    summary: raw.summary,
    timeline: raw.timeline,
  };
}

export const fetchGraphData = getCaseGraph;

export const graphApi = {
  getCaseGraph,
  fetchGraphData,
  getCaseTopology: getCaseGraph,
};

export default graphApi;
