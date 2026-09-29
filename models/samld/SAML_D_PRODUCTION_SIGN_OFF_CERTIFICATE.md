# FORMAL PRODUCTION SIGN-OFF CERTIFICATE
================================================================================
Dataset Milestone:     SAML-D Synthetic Financial Crime Transactions (9.5M Rows)
Registry Version:      saml_d_xgboost:v1.0
Release Status:        RELEASED_LOCKED (Production Deployed & Frozen)
Sign-Off Timestamp:    2026-09-28T17:43:16.450042+00:00
Model Architecture:    Regularized XGBoost (Hist-Gradient Boosting Head)
Zero Leakage Pipeline: SamldFeaturePipeline (26 Engineered AML Features)

1. HOLDOUT EVALUATION PERFORMANCE (1,900,971 Test Samples | 961.7:1 Imbalance):
--------------------------------------------------------------------------------
- PR-AUC:                           0.80207
- ROC-AUC:                          0.99495
- Optimal F1 Score:                 0.8200 (at threshold T* = 0.6148)
- Precision @ Optimal F1:           93.69%
- Recall @ Optimal F1:              72.91%
- False Positive Rate:              0.0051%
- Operational High Recall (95%):    Achieved Recall = 95.04% (T = 0.0125)
- Operational FPR @ 95% Recall:     3.182%
- Precision @ Top 100 / 500 / 1000: 100.0% / 100.0% / 99.90%

2. INFERENCE LATENCY & THROUGHPUT BENCHMARKS:
--------------------------------------------------------------------------------
- Single-Row Streaming p50:        0.3352 ms
- Single-Row Streaming p95:        0.8103 ms (Production SLA <= 1.0 ms: PASS)
- Streaming Real-Time Throughput:  1,805.7 transactions/sec
- Mini-Batch (10k) Throughput:     90,575.4 records/sec (11.04 us/record)
- Raw XGBoost Model Throughput:    266,341.4 records/sec

3. OPERATIONAL READINESS & DRIFT MONITORING:
--------------------------------------------------------------------------------
- REST / Contract Tests:           9 / 9 Passed (HTTP 200, 422, 400 validations)
- Simulated Concurrency:           25 / 25 Concurrent Requests Passed (100% 200 OK)
- Drift Detection Baselines:       12 Top TreeSHAP Features + risk_score Initialized
- In-Distribution Baseline PSI:    0.011740 (STABLE_NO_DRIFT)
- Out-of-Distribution Drift PSI:   12.325970 (ALERT_TRIGGERED)
- Artifact Checksum Verification:  13 / 13 Cryptographic SHA-256 Hashes Verified

4. TRANSITION READINESS:
--------------------------------------------------------------------------------
SAML-D Dataset Milestone is officially 100% COMPLETE, VERIFIED, and LOCKED.
Transition to Dataset #3 (Elliptic Bitcoin / Crypto Forensic Detection) is UNLOCKED.
================================================================================
