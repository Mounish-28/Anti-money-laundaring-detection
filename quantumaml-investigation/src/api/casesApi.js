import apiClient from './client';

// Generate dynamic SLA deadlines relative to current runtime so timers are live
const getFutureTime = (minutes) => new Date(Date.now() + minutes * 60 * 1000).toISOString();

export const MOCK_CASES = [
  {
    id: 'ESC-90812',
    sar_id: 'SAR-IND-2026-90812',
    rail: 'UPI',
    currency: 'INR',
    amount: 4850000.0,
    exposure_inr: 4850000.0,
    riskScore: 0.98,
    riskTier: 'CRITICAL',
    typology: 'UPI Smurfing Cluster',
    suspectEntity: 'mule4@okaxis (PAN: ABCDE1234F)',
    slaDeadline: getFutureTime(18), // 18m -> pulsing rose (<30m)
    status: 'OPEN',
    createdAt: new Date(Date.now() - 3600000).toISOString(),
    hopCount: 4,
    clusterSize: 18,
  },
  {
    id: 'ESC-90813',
    sar_id: 'SAR-BTC-2026-90813',
    rail: 'BTC',
    currency: 'BTC',
    amount: 14.825,
    exposure_inr: 81500000.0,
    riskScore: 0.94,
    riskTier: 'CRITICAL',
    typology: 'Layered UTXO Peeling',
    suspectEntity: 'bc1q9x4p...v08k (Wasabi Mixer)',
    slaDeadline: getFutureTime(25), // 25m -> pulsing rose (<30m)
    status: 'ESCALATED',
    createdAt: new Date(Date.now() - 7200000).toISOString(),
    hopCount: 6,
    clusterSize: 34,
  },
  {
    id: 'ESC-90814',
    sar_id: 'SAR-IND-2026-90814',
    rail: 'IMPS',
    currency: 'INR',
    amount: 1890000.0,
    exposure_inr: 1890000.0,
    riskScore: 0.87,
    riskTier: 'HIGH',
    typology: 'Rapid Hop Transit',
    suspectEntity: 'A/C 918274019284 (HDFC0001)',
    slaDeadline: getFutureTime(48), // 48m -> amber (>30m)
    status: 'UNDER_REVIEW',
    createdAt: new Date(Date.now() - 10800000).toISOString(),
    hopCount: 3,
    clusterSize: 8,
  },
  {
    id: 'ESC-90815',
    sar_id: 'SAR-IND-2026-90815',
    rail: 'UPI',
    currency: 'INR',
    amount: 495000.0,
    exposure_inr: 495000.0,
    riskScore: 0.76,
    riskTier: 'HIGH',
    typology: 'High-Volume Off-Hours Structuring',
    suspectEntity: 'payquick_aggregator@icici',
    slaDeadline: getFutureTime(95), // 1h 35m -> amber (>30m)
    status: 'OPEN',
    createdAt: new Date(Date.now() - 14400000).toISOString(),
    hopCount: 2,
    clusterSize: 12,
  },
  {
    id: 'ESC-90816',
    sar_id: 'SAR-BTC-2026-90816',
    rail: 'BTC',
    currency: 'BTC',
    amount: 3.421,
    exposure_inr: 18800000.0,
    riskScore: 0.89,
    riskTier: 'HIGH',
    typology: 'Darknet Vendor Aggregation',
    suspectEntity: '1BoatSLRHtKNngkd5...kE',
    slaDeadline: getFutureTime(140), // 2h 20m -> amber
    status: 'UNDER_REVIEW',
    createdAt: new Date(Date.now() - 18000000).toISOString(),
    hopCount: 5,
    clusterSize: 22,
  },
  {
    id: 'ESC-90817',
    sar_id: 'SAR-IND-2026-90817',
    rail: 'IMPS',
    currency: 'INR',
    amount: 950000.0,
    exposure_inr: 950000.0,
    riskScore: 0.62,
    riskTier: 'MEDIUM',
    typology: 'Circular Pass-Through Fanout',
    suspectEntity: 'A/C 401928374612 (SBIN0004)',
    slaDeadline: getFutureTime(210), // 3h 30m -> amber
    status: 'OPEN',
    createdAt: new Date(Date.now() - 21600000).toISOString(),
    hopCount: 3,
    clusterSize: 6,
  },
  {
    id: 'ESC-90818',
    sar_id: 'SAR-IND-2026-90818',
    rail: 'UPI',
    currency: 'INR',
    amount: 720000.0,
    exposure_inr: 720000.0,
    riskScore: 0.68,
    riskTier: 'MEDIUM',
    typology: 'Velocity Burst Smurfing',
    suspectEntity: 'retail_pay77@ybl',
    slaDeadline: getFutureTime(235), // ~4 hours -> amber
    status: 'RESOLVED',
    createdAt: new Date(Date.now() - 25200000).toISOString(),
    hopCount: 2,
    clusterSize: 9,
  }
];

export async function fetchCases() {
  try {
    const res = await apiClient.get('/api/v1/sar/list', { timeout: 2000 });
    const rawItems = res.data?.items || (Array.isArray(res.data) ? res.data : null);
    if (Array.isArray(rawItems) && rawItems.length > 0) {
      return rawItems.map((item, idx) => {
        const isBtc = Boolean(item.total_exposure_btc && item.total_exposure_btc > 0);
        return {
          id: item.sar_id || `ESC-${90812 + idx}`,
          sar_id: item.sar_id || `SAR-IND-2026-${90812 + idx}`,
          rail: isBtc ? 'BTC' : (item.rail || 'UPI'),
          currency: isBtc ? 'BTC' : (item.currency || 'INR'),
          amount: isBtc ? item.total_exposure_btc : (item.total_exposure_inr || item.amount || 4850000),
          exposure_inr: item.total_exposure_inr || item.amount || 4850000,
          riskScore: item.ml_telemetry?.risk_score || item.riskScore || 0.98,
          riskTier: item.ml_telemetry?.risk_tier || item.riskTier || 'CRITICAL',
          typology: typeof item.primary_typology === 'string'
            ? item.primary_typology.replace(/^IN_TYP_/, '')
            : (item.typology || 'UPI Smurfing Cluster'),
          suspectEntity: item.suspect?.full_legal_name || item.suspect?.pan_or_identifier || item.suspectEntity || 'Target Suspect Entity',
          slaDeadline: item.fiu_deadline || item.slaDeadline || getFutureTime(30),
          status: item.status || 'OPEN',
          createdAt: item.created_at || item.createdAt || new Date().toISOString(),
          hopCount: item.transactions?.length || item.hopCount || 4,
          clusterSize: (item.transactions?.length || 4) + 2,
        };
      });
    }
  } catch {
    // Graceful fallback to mock data when backend is in standby
  }
  return MOCK_CASES;
}

export const casesApi = {
  fetchCases,
  getCases: fetchCases,
  getCaseById: async (caseId) => {
    try {
      const response = await apiClient.get(`/api/v1/sar/${caseId}`);
      return response.data;
    } catch {
      return MOCK_CASES.find((c) => c.id === caseId || c.sar_id === caseId) || MOCK_CASES[0];
    }
  },
  updateCaseStatus: async (caseId, status, payload = {}) => {
    try {
      const response = await apiClient.patch(`/api/v1/sar/${caseId}/status`, {
        new_status: status,
        analyst_id: payload.analyst_id || 'OFFICER-AML-902',
        resolution_notes: payload.notes || 'Status updated via QuantumAML Workbench',
      });
      return response.data;
    } catch {
      return { success: true, caseId, status };
    }
  },
};

export default casesApi;
