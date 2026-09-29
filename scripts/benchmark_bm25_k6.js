/**
 * STEP 5.3.1: BM25 SEARCH ENGINE STRESS TESTING & SATURATION PROFILING (k6 Script)
 * High-concurrency load testing harness targeting the BM25 evidence retrieval endpoint.
 *
 * Execution Profile:
 *   - Dataset Scale: 100,000+ indexed legal briefs, subpoena returns, and transaction narratives.
 *   - Concurrency: Up to 500 concurrent Virtual Users (VUs).
 *   - Query Patterns: Multi-term search queries with faceted filters (case:, tx:, min_score:).
 *   - Strict SLA Gates:
 *       * p95 latency < 35ms
 *       * p99 latency < 50ms
 *       * 0% query failure rate under sustained load.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

// Custom latency trends and error rates for strict SLA gating
export const bm25Latency = new Trend('bm25_search_latency_ms', true);
export const bm25FailureRate = new Rate('bm25_failure_rate');
export const facetedQueriesCount = new Counter('bm25_faceted_queries_executed');

export const options = {
  scenarios: {
    bm25_saturation_stress: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [
        { duration: '30s', target: 100 },  // Warmup stage
        { duration: '1m', target: 300 },   // Linear ramp to high load
        { duration: '2m', target: 500 },   // Peak saturation load (500 VUs)
        { duration: '30s', target: 0 },    // Cooldown stage
      ],
      gracefulRampDown: '15s',
    },
  },
  thresholds: {
    // SLA Gate 1: 95th percentile latency must be under 35ms
    'bm25_search_latency_ms': [
      { threshold: 'p(95)<35.0', abortOnFail: true, delayAbortEval: '1m' },
      { threshold: 'p(99)<50.0', abortOnFail: true, delayAbortEval: '1m' }
    ],
    // SLA Gate 2: 0% failure rate under sustained load
    'http_req_failed': ['rate==0'],
    'bm25_failure_rate': ['rate==0'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

// Realistic financial crime queries with faceted filter chips
const SAMPLE_QUERIES = [
  {
    query: 'offshore shell entity Cayman wire routing 021000021 case:CASE-2026-NYSD-0982 min_score:0.25',
    k1: 1.25,
    b: 0.75,
    top_k: 20
  },
  {
    query: 'structuring smurfing cash deposit 9800 Manhattan branch tx:TX-99882 min_score:0.30',
    k1: 1.25,
    b: 0.75,
    top_k: 25
  },
  {
    query: 'subpoena MT103 wire transfer escrow Orion Global Trust case:CASE-2026-SDNY-4401',
    k1: 1.4,
    b: 0.8,
    top_k: 15
  },
  {
    query: 'nominee director Delaware registered agent layering velocity min_score:0.20',
    k1: 1.2,
    b: 0.7,
    top_k: 30
  },
  {
    query: 'OFAC sanctions PEP high-risk beneficiary correspondent account clearing tx:TX-77102',
    k1: 1.5,
    b: 0.75,
    top_k: 50
  }
];

export default function () {
  const payloadData = SAMPLE_QUERIES[Math.floor(Math.random() * SAMPLE_QUERIES.length)];
  const payload = JSON.stringify(payloadData);

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + (__ENV.AUTH_TOKEN || 'test-investigator-jwt-token'),
      'X-Domain-Enclave': 'INVESTIGATION_ENCLAVE'
    },
    timeout: '5s'
  };

  const startTime = Date.now();
  const res = http.post(`${BASE_URL}/api/v1/investigation/evidence/search`, payload, params);
  const elapsed = Date.now() - startTime;

  bm25Latency.add(elapsed);
  facetedQueriesCount.add(1);

  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'latency is within SLA (< 50ms)': () => elapsed < 50.0,
    'has search results': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.results);
      } catch (e) {
        return false;
      }
    }
  });

  if (!success) {
    bm25FailureRate.add(1);
  } else {
    bm25FailureRate.add(0);
  }

  // Micro-sleep simulating user think-time between searches
  sleep(0.05);
}
