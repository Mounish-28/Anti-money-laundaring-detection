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
    ]
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
      { id: 'be6', source: 'btc-peel-2', target: 'btc-destination', amount: 5.405, currency: 'BTC', formattedAmount: '5.4050 BTC', latencySeconds: 85, isHighVelocity: true, rail: 'BTC', timestamp: '2026-09-23T12:07:58Z' },
    ],
    timeline: [
      { hopIndex: 1, from: 'Genesis Whale (1Boat...)', to: 'Wasabi Mixer Pool', latency: 95, amount: '14.8250 BTC', isRapid: true, rail: 'BTC' },
      { hopIndex: 2, from: 'Wasabi Mixer Pool', to: 'bc1q9x4p...v08k', latency: 65, amount: '9.4120 BTC', isRapid: true, rail: 'BTC' },
      { hopIndex: 3, from: 'bc1q9x4p...v08k', to: 'Layering 3J98t1W...', latency: 110, amount: '8.8500 BTC', isRapid: true, rail: 'BTC' },
      { hopIndex: 4, from: 'Layering 3J98t1W...', to: 'Binance Hot Wallet', latency: 140, amount: '8.8400 BTC', isRapid: false, rail: 'BTC' },
    ]
  },

  'ESC-90814': {
    summary: {
      caseId: 'ESC-90814',
      typology: 'Rapid Hop Transit & Cyclic Ring',
      totalHops: 4,
      totalVolume: '₹1,890,000',
      anomalousHopCount: 4,
      avgLatencySeconds: 46,
    },
    nodes: [
      { id: 'cyc-origin', label: 'Origin: A/C *9284', type: 'ORIGIN', riskTier: 'HIGH', balance: '₹1,890,000', degree: 3 },
      { id: 'cyc-mule-1', label: 'Hop 1: A/C *3746', type: 'MULE', riskTier: 'HIGH', balance: '₹1,885,000', degree: 3 },
      { id: 'cyc-mule-2', label: 'Hop 2: A/C *1038', type: 'MULE', riskTier: 'HIGH', balance: '₹1,880,000', degree: 3 },
      { id: 'cyc-mule-3', label: 'Suspect: A/C *2039', type: 'SUSPECT', riskTier: 'CRITICAL', balance: '₹1,875,000', degree: 3 },
      { id: 'cyc-escrow', label: 'Offshore: Cyprus Escrow', type: 'DESTINATION', riskTier: 'CRITICAL', balance: '₹1,850,000', degree: 2 },
    ],
    edges: [
      { id: 'ce1', source: 'cyc-origin', target: 'cyc-mule-1', amount: 1890000, currency: 'INR', formattedAmount: '₹1,890,000', latencySeconds: 42, isHighVelocity: true, rail: 'IMPS', timestamp: '2026-09-23T11:00:00Z' },
      { id: 'ce2', source: 'cyc-mule-1', target: 'cyc-mule-2', amount: 1885000, currency: 'INR', formattedAmount: '₹1,885,000', latencySeconds: 38, isHighVelocity: true, rail: 'IMPS', timestamp: '2026-09-23T11:00:38Z' },
      { id: 'ce3', source: 'cyc-mule-2', target: 'cyc-mule-3', amount: 1880000, currency: 'INR', formattedAmount: '₹1,880,000', latencySeconds: 49, isHighVelocity: true, rail: 'IMPS', timestamp: '2026-09-23T11:01:27Z' },
      { id: 'ce4', source: 'cyc-mule-3', target: 'cyc-origin', amount: 450000, currency: 'INR', formattedAmount: '₹450,000 (Cyclic)', latencySeconds: 55, isHighVelocity: true, rail: 'IMPS', timestamp: '2026-09-23T11:02:22Z' },
      { id: 'ce5', source: 'cyc-mule-3', target: 'cyc-escrow', amount: 1425000, currency: 'INR', formattedAmount: '₹1,425,000', latencySeconds: 45, isHighVelocity: true, rail: 'IMPS', timestamp: '2026-09-23T11:03:07Z' },
    ],
    timeline: [
      { hopIndex: 1, from: 'Origin (*9284)', to: 'Hop 1 (*3746)', latency: 42, amount: '₹1,890,000', isRapid: true, rail: 'IMPS' },
      { hopIndex: 2, from: 'Hop 1 (*3746)', to: 'Hop 2 (*1038)', latency: 38, amount: '₹1,885,000', isRapid: true, rail: 'IMPS' },
      { hopIndex: 3, from: 'Hop 2 (*1038)', to: 'Suspect (*2039)', latency: 49, amount: '₹1,880,000', isRapid: true, rail: 'IMPS' },
      { hopIndex: 4, from: 'Suspect (*2039)', to: 'Cyprus Escrow', latency: 45, amount: '₹1,425,000', isRapid: true, rail: 'IMPS' },
    ]
  }
};

// Fallback generator for other cases
function generateFallbackTopology(caseId) {
  return {
    summary: {
      caseId,
      typology: 'Structuring & Layering Fanout',
      totalHops: 3,
      totalVolume: '₹1,450,000',
      anomalousHopCount: 2,
      avgLatencySeconds: 74,
    },
    nodes: [
      { id: `${caseId}-orig`, label: `Remitter: ${caseId}`, type: 'ORIGIN', riskTier: 'MEDIUM', balance: '₹1,450,000', degree: 2 },
      { id: `${caseId}-m1`, label: 'Suspect Account #1', type: 'SUSPECT', riskTier: 'HIGH', balance: '₹850,000', degree: 3 },
      { id: `${caseId}-m2`, label: 'Transit Mule #2', type: 'MULE', riskTier: 'MEDIUM', balance: '₹600,000', degree: 2 },
      { id: `${caseId}-dest`, label: 'Settlement Escrow', type: 'DESTINATION', riskTier: 'CRITICAL', balance: '₹1,420,000', degree: 2 },
    ],
    edges: [
      { id: `${caseId}-e1`, source: `${caseId}-orig`, target: `${caseId}-m1`, amount: 850000, currency: 'INR', formattedAmount: '₹850,000', latencySeconds: 55, isHighVelocity: true, rail: 'UPI', timestamp: '2026-09-23T10:00:00Z' },
      { id: `${caseId}-e2`, source: `${caseId}-orig`, target: `${caseId}-m2`, amount: 600000, currency: 'INR', formattedAmount: '₹600,000', latencySeconds: 72, isHighVelocity: true, rail: 'UPI', timestamp: '2026-09-23T10:01:12Z' },
      { id: `${caseId}-e3`, source: `${caseId}-m1`, target: `${caseId}-dest`, amount: 840000, currency: 'INR', formattedAmount: '₹840,000', latencySeconds: 85, isHighVelocity: true, rail: 'UPI', timestamp: '2026-09-23T10:02:37Z' },
      { id: `${caseId}-e4`, source: `${caseId}-m2`, target: `${caseId}-dest`, amount: 590000, currency: 'INR', formattedAmount: '₹590,000', latencySeconds: 94, isHighVelocity: true, rail: 'UPI', timestamp: '2026-09-23T10:04:11Z' },
    ],
    timeline: [
      { hopIndex: 1, from: `Remitter (${caseId})`, to: 'Suspect Account #1', latency: 55, amount: '₹850,000', isRapid: true, rail: 'UPI' },
      { hopIndex: 2, from: 'Suspect Account #1', to: 'Settlement Escrow', latency: 85, amount: '₹840,000', isRapid: true, rail: 'UPI' },
    ]
  };
}

export async function fetchGraphData(caseId = 'ESC-90812') {
  try {
    const res = await apiClient.get(`/api/investigation/graph/${caseId}`, { timeout: 1500 });
    if (res.data?.elements?.length) {
      return res.data;
    }
  } catch {
    // Fallback to local realistic topologies
  }

  const raw = CASE_TOPOLOGIES[caseId] || generateFallbackTopology(caseId);

  // Format into Cytoscape element structures
  const elements = [
    ...raw.nodes.map((n) => ({
      group: 'nodes',
      data: {
        id: n.id,
        label: n.label,
        type: n.type,
        riskTier: n.riskTier,
        balance: n.balance,
        degree: n.degree,
      },
    })),
    ...raw.edges.map((e) => ({
      group: 'edges',
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        amount: e.amount,
        currency: e.currency,
        formattedAmount: e.formattedAmount,
        latencySeconds: e.latencySeconds,
        isHighVelocity: e.isHighVelocity,
        rail: e.rail,
        timestamp: e.timestamp,
      },
    })),
  ];

  return {
    elements,
    nodes: raw.nodes,
    edges: raw.edges,
    summary: raw.summary,
    timeline: raw.timeline,
  };
}

export const graphApi = {
  fetchGraphData,
  getCaseTopology: fetchGraphData,
  getEntityNeighbors: async (entityId) => {
    return { entityId, neighbors: [] };
  },
};

export default graphApi;
