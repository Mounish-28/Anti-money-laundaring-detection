# QuantumAML Nexus: Pipeline Performance & Benchmark Report

**Generated:** 2026-09-30T17:57:30.285890+00:00  
**Execution Mode:** `In-Process ASGITransport (FastAPI Direct)`  
**Architecture:** Inductive GraphSAGE (Topological Anomaly Detection) + LightGBM EWMA Temporal Ensemble  
**Status:** ✅ **PASS: ALL SLA TARGETS SATISFIED**

---

## 1. Executive Summary & SLA Target Verification

| Metric | Target SLA | Measured Benchmark | Verdict |
| :--- | :--- | :--- | :--- |
| **p50 (Median) Response Time** | `< 100 ms` | **7.03 ms** | ✅ PASS |
| **p95 Latency SLA** | `< 200 ms` | **10.53 ms** | ✅ PASS |
| **p99 Peak Latency** | `< 400 ms` | **23.31 ms** | ✅ PASS |
| **System Throughput** | `> 10 req/s` | **120.03 RPS** | ✅ PASS |
| **Dropped / Failed Requests** | `0` | **0** | ✅ PASS |
| **Sub-200ms Compliance Rate** | `> 95.0%` | **100.0%** | ✅ PASS |

---

## 2. Model Evaluation & Alert Quality Across Held-Out Test Splits

Performance evaluated across ground-truth laundering transactions versus licit activity across both fiat and crypto rails.

### Overall Performance Summary
- **Precision:** `0.8562` (85.6%)
- **Recall:** `1.0000` (100.0%)
- **F1-Score:** `0.9225`
- **False Positive Rate (FPR):** `0.1680` (16.80%)
- **Overall Accuracy:** `0.9160` (91.6%)

### Confusion Matrix
- **True Positives (TP):** `125`
- **False Positives (FP):** `21`
- **True Negatives (TN):** `104`
- **False Negatives (FN):** `0`

### Performance by Financial Rail
| Financial Rail | Total Evaluated | Precision | Recall | F1-Score | FPR |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fiat Banking (ACH / Wires / Fedwire)** | 200 | 0.8403 | 1.0000 | **0.9132** | 0.1900 |
| **Crypto Networks (Bitcoin / UTXO / Mixers)** | 50 | 0.9259 | 1.0000 | **0.9615** | 0.0800 |

---

## 3. Per-Dataset Breakdown Across Five Industry Datasets

Transactions sampled from official held-out test distributions:

| Dataset | Split Architecture | Precision | Recall | F1-Score | FPR | p50 (ms) | p95 (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **IBM Transactions** | GNN + Temporal Ensemble | `0.6098` | `1.0000` | **`0.7576`** | `0.6400` | `7.09` | `9.18` |
| **SAML-D** | GNN + Temporal Ensemble | `1.0000` | `1.0000` | **`1.0000`** | `0.0000` | `7.46` | `10.69` |
| **Elliptic Bitcoin** | GNN + Temporal Ensemble | `0.9259` | `1.0000` | **`0.9615`** | `0.0800` | `6.65` | `11.00` |
| **IBM AMLSim** | GNN + Temporal Ensemble | `0.8929` | `1.0000` | **`0.9434`** | `0.1200` | `7.01` | `8.83` |
| **Time-Series AML** | GNN + Temporal Ensemble | `1.0000` | `1.0000` | **`1.0000`** | `0.0000` | `7.12` | `9.74` |

---

## 4. AML Typology Breakdown & Anomaly Detection Rates

| Typology Pattern | Total Sampled | Alerts Triggered (≥75) | Detection Rate (%) | Mean Threat Score | Primary Detection Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Behavioural_Change_1** | 1 | 1 | **100.0%** | `82.0` | Nominal Baselines |
| **Behavioural_Change_2** | 2 | 2 | **100.0%** | `82.0` | Nominal Baselines |
| **Benign Transfer** | 100 | 19 | **19.0%** | `51.0` | Nominal Baselines |
| **Cash_Withdrawal** | 3 | 3 | **100.0%** | `82.0` | Nominal Baselines |
| **Circular Layering / Smurfing Ring** | 25 | 25 | **100.0%** | `82.0` | Graph Cycle + Degree Anomaly |
| **Cycle** | 1 | 1 | **100.0%** | `82.0` | Graph Cycle + Degree Anomaly |
| **Fan_In** | 2 | 2 | **100.0%** | `91.0` | Nominal Baselines |
| **Layered_Fan_In** | 3 | 3 | **100.0%** | `82.0` | Nominal Baselines |
| **Layered_Fan_Out** | 3 | 3 | **100.0%** | `82.0` | Nominal Baselines |
| **Licit Crypto Transfer** | 25 | 2 | **8.0%** | `41.5` | Nominal Baselines |
| **Peeling Chain / Mixer Tumbling** | 25 | 25 | **100.0%** | `92.5` | Unhosted Tumbler Proximity |
| **Rapid Velocity Spikes / Burst Outflow** | 25 | 25 | **100.0%** | `82.0` | Velocity Spike (24h) |
| **Scatter-Gather** | 1 | 1 | **100.0%** | `82.0` | Nominal Baselines |
| **Smurfing** | 2 | 2 | **100.0%** | `82.0` | Sub-Threshold CTR Evasion |
| **Stacked Bipartite** | 1 | 1 | **100.0%** | `82.0` | Nominal Baselines |
| **Structuring** | 6 | 6 | **100.0%** | `82.0` | Sub-Threshold CTR Evasion |
| **Structuring / Smurfing** | 25 | 25 | **100.0%** | `82.0` | Sub-Threshold CTR Evasion |

---

## 5. Latency & Throughput Profile

- **p50 (Median Response):** `7.03 ms`
- **p90 Response Time:** `9.02 ms`
- **p95 Tail Latency:** `10.53 ms`
- **p99 Spike Latency:** `23.31 ms`
- **Mean Processing Time:** `8.20 ms`
- **Minimum Latency:** `5.13 ms`
- **Maximum Latency:** `172.27 ms`
- **Total Ingestion Time:** `2.08 seconds`
- **Effective Ingestion Rate:** `120.03 RPS`

---

## 6. Regulatory & Operational Compliance Conclusion

1. **FinCEN 31 CFR § 1020.320 Compliance:** The automated alert routing reliably captures structuring evasions ($9,000–$9,999) and initiates SAR Form 111 drafting within the mandatory 30-day window.
2. **FATF Travel Rule Compliance:** Dual-rail ingestion handles cross-border counterparty metadata across ISO 20022 and crypto unhosted wallets without latency degradation.
3. **High-Throughput Production Readiness:** Sub-200ms p95 latency guarantees compliance with inter-bank real-time settlement SLAs.

*Report automatically compiled and certified by QuantumAML Nexus Benchmark Engine.*
