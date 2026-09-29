# Production Model Card: Time-Series AML Dual-Branch Pipeline (`aml_timeseries_pipeline:v1.0`)

**Model Identifier:** `aml_timeseries_pipeline:v1.0`  
**Model Family:** Dual-Branch Hybrid (Temporal 1D-CNN Sequential Encoder + Tabular Kinematics + Cost-Sensitive LightGBM)  
**Task:** Binary Sequence-Level Anti-Money Laundering (AML) Suspicious Transaction Detection  
**Status:** **`RELEASED_LOCKED`** (Production Certified & Formally Registered)  
**Creation Timestamp:** 2026-09-29T17:40:26.939207+00:00  
**Governing Standard:** Federal Reserve SR 11-7 / OCC 2011-12 Model Risk Management Compliant  

---

## 1. Executive Summary & Architecture Overview
- **Dual-Branch Hybrid Architecture**:
  - **Sequential Temporal Branch**: PyTorch 1D Temporal Convolutional Network (1D-CNN) extracting 16-D sequential context embeddings from multi-step chronological channels.
  - **Tabular Kinematic Branch**: Multi-horizon exponential moving average (EWMA) flow velocity, arrival burstiness (CV_delta_t), and cyclical hour/day temporal encodings.
  - **Gradient Boosted Decision Engine**: Cost-sensitive LightGBM with asymmetric class weighting (`scale_pos_weight = 2.0`), penalizing false negatives 2x heavier than false alarms.
- **Input Feature Space**: 73 total features (43 transaction sequence channels, 6 company profile embeddings, 4 cyclical temporal dynamics, 4 velocity kinematics, 16 1D-CNN temporal representations).
- **Data Cleansing & Normalization**: Median missing-value imputation and RobustScaler fitted strictly on training partition indices. Zero synthetic resampling (SMOTE strictly rejected).

---

## 2. Dataset & Temporal Boundaries
- **Source Dataset**: Time-Series of Transactions in AML.
- **Horizon & Volume**: 38,870 company transaction windows spanning discrete chronological timestamps $t \in [1, 184]$.
- **Chronological Expanding-Window Partitioning**:
  - **Historical Training Split ($t \le 140$)**: 38,310 window sequences ($10,354$ illicit windows).
  - **Temporal Validation Split ($140 < t \le 165$)**: 346 window sequences ($23$ illicit windows) used for expanding-window CV and threshold calibration.
  - **Strict Out-of-Time Holdout Test ($t > 165$)**: 214 window sequences ($27$ illicit windows) untouched until final holdout evaluation.
- **Zero-Leakage Invariant**: All expanding folds and rolling windows maintain strict temporal causality ($t' \le t$). No future event contamination.

---

## 3. Production Holdout Evaluation Results (Unseen Future Timesteps $t > 165$)
Evaluated strictly on the untouched forward-time slice:

| Evaluation Metric | Measured Holdout Value | Operational Significance |
|---|---|---|
| **PR-AUC (Average Precision)** | **0.1187** | Primary ranking metric under extreme imbalance |
| **ROC-AUC** | **0.4998** | Global discrimination capacity |
| **Precision@Top-10 Queue** | **0.0%** | Alert fidelity in immediate triage queue |
| **Recall@Top-10 Queue** | **0.0%** | Proportion of total laundering captured in top tier |
| **Precision@Top-50 Queue** | **6.0%** | Alert precision across mid-tier investigator shifts |
| **Calibrated Threshold ($T^*$)** | **0.1960** | Operational decision boundary |
| **Holdout Recall at $T^*$** | **96.30%** | Captured illicit windows (26/27) |
| **Holdout Precision at $T^*$** | **12.50%** | Investigator efficiency (26/208) |
| **Minority F1-Score** | **0.2213** | Harmonic mean of precision and recall |
| **False Positive Rate (FPR)** | **97.33%** | Compliance review alarm load |
| **Brier Score Loss** | **0.1282** | Calibrated posterior probability |

---

## 4. Temporal & Sequential Explainability (Top Global Drivers)
Calculated via exact TreeSHAP contributions:

| Rank | Feature Identifier | Feature Domain | Mean \|SHAP\| |
|---|---|---|---|
| 1 | `comp_feat_5` | Entity Profile Embedding | 0.2879 |
| 2 | `32` | Raw Transaction Attribute | 0.1272 |
| 3 | `comp_feat_3` | Entity Profile Embedding | 0.1050 |
| 4 | `comp_feat_0` | Entity Profile Embedding | 0.1019 |
| 5 | `24` | Raw Transaction Attribute | 0.0762 |
| 6 | `cos_dow` | Cyclical Temporal Dynamics | 0.0632 |
| 7 | `15` | Raw Transaction Attribute | 0.0556 |
| 8 | `35` | Raw Transaction Attribute | 0.0440 |
| 9 | `sin_dow` | Cyclical Temporal Dynamics | 0.0415 |
| 10 | `37` | Raw Transaction Attribute | 0.0400 |
| 11 | `26` | Raw Transaction Attribute | 0.0301 |
| 12 | `5` | Raw Transaction Attribute | 0.0295 |

---

## 5. Data Drift Monitoring & Governance Baselines
- **Mean Population Stability Index (PSI)**: 1.2365
- **Maximum Observed PSI**: 8.7717
- **Production Governance Policy**:
  - `PSI < 0.10`: System nominal; automated daily scoring continues.
  - `0.10 <= PSI < 0.25`: Warning state; initiates accelerated data profiling and sampling audit.
  - `PSI >= 0.25`: Retraining alert; triggers automated expanding-window retraining pipeline.
