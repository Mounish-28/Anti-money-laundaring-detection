#!/usr/bin/env python3
"""
QuantumAML Nexus - SAML-D Data & Prediction Drift Baseline Initialization
=========================================================================
Location: scripts/initialize_drift_baselines.py

Calculates and serializes the empirical statistical distribution baselines
(Population Stability Index decile bins and Wasserstein empirical quantiles)
for top TreeSHAP features and model output probabilities from the test split.
"""

import json
import os
import sys
import time
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import joblib
import numpy as np
import pandas as pd
from scipy import stats

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.services.samld_pipeline import LaplaceTargetEncoder, SamldFeaturePipeline


def compute_psi(ref_dist: np.ndarray, prod_dist: np.ndarray, bin_edges: np.ndarray, epsilon: float = 1e-6) -> float:
    """Computes Population Stability Index (PSI) using pre-calculated reference bin edges."""
    ref_counts, _ = np.histogram(ref_dist, bins=bin_edges)
    prod_counts, _ = np.histogram(prod_dist, bins=bin_edges)

    ref_pct = (ref_counts / max(1, len(ref_dist))) + epsilon
    prod_pct = (prod_counts / max(1, len(prod_dist))) + epsilon

    # Normalize to sum to 1.0
    ref_pct = ref_pct / np.sum(ref_pct)
    prod_pct = prod_pct / np.sum(prod_pct)

    psi_val = np.sum((prod_pct - ref_pct) * np.log(prod_pct / ref_pct))
    return float(psi_val)


def main():
    print("=" * 80)
    print("QUANTUMAML NEXUS - SAML-D DRIFT BASELINE INITIALIZATION")
    print("=" * 80)

    model_dir = os.path.join(ROOT_DIR, "models", "samld")
    preprocessor_path = os.path.join(model_dir, "feature_preprocessor.joblib")
    model_path = os.path.join(model_dir, "xgboost_model.joblib")
    data_path = os.path.join(ROOT_DIR, "data", "samld", "samld_transactions.csv")

    print(f"[*] Loading preprocessor: {preprocessor_path}")
    preprocessor: SamldFeaturePipeline = joblib.load(preprocessor_path)
    print(f"[*] Loading XGBoost model: {model_path}")
    model = joblib.load(model_path)

    # Ingest a stratified holdout cohort of 100,000 samples for drift baseline calculation
    sample_size = 100000
    print(f"[*] Ingesting {sample_size:,d} transactions from SAML-D dataset...")
    dtypes = {
        "Sender_account": "int64",
        "Receiver_account": "int64",
        "Amount": "float32",
        "Payment_currency": "category",
        "Received_currency": "category",
        "Sender_bank_location": "category",
        "Receiver_bank_location": "category",
        "Payment_type": "category",
        "Is_laundering": "int8",
    }
    usecols = list(dtypes.keys())

    # Read 100,000 samples with usecols and dtypes
    df = pd.read_csv(
        data_path,
        nrows=sample_size,
        usecols=usecols,
        dtype=dtypes,
    )
    print(f"[✓] Loaded {len(df):,d} holdout records.")

    # Compute graph degrees & rolling velocity
    print("[*] Computing ledger degrees and rolling velocity...")
    df["In_Degree"] = df.groupby("Receiver_account")["Receiver_account"].transform("count").astype(np.int32)
    df["Out_Degree"] = df.groupby("Sender_account")["Sender_account"].transform("count").astype(np.int32)
    df["Rolling_24h_Velocity"] = df.groupby("Sender_account")["Amount"].transform("sum").astype(np.float32)

    eval_cols = [
        "Amount",
        "In_Degree",
        "Out_Degree",
        "Rolling_24h_Velocity",
        "Payment_type",
        "Sender_bank_location",
        "Receiver_bank_location",
        "Payment_currency",
        "Received_currency",
    ]
    X_input = df[eval_cols]

    print("[*] Transforming features through SamldFeaturePipeline...")
    t0 = time.time()
    X_features = preprocessor.transform(X_input)
    print(f"[✓] Feature transformation completed in {time.time() - t0:.2f}s: shape={X_features.shape}")

    print("[*] Generating model prediction probabilities...")
    t0 = time.time()
    risk_scores = model.predict_proba(X_features)[:, 1]
    print(f"[✓] Model scoring completed in {time.time() - t0:.2f}s: mean_score={float(np.mean(risk_scores)):.6f}")

    # Top features identified via TreeSHAP
    top_shap_features = [
        "Degree_Difference",
        "In_Degree",
        "Out_Degree",
        "Network_Activity",
        "Amount_to_Velocity_Ratio",
        "Degree_Ratio",
        "Amount",
        "Cash_Velocity_Risk",
        "Rolling_24h_Velocity",
        "Log_Velocity",
        "Velocity_Per_Out_Degree",
        "Is_Currency_Exchange",
    ]

    feature_names = preprocessor.feature_names_
    feat_index_map = {name: i for i, name in enumerate(feature_names)}

    drift_baselines: Dict[str, Any] = {
        "metadata": {
            "model_id": "saml_d_xgboost",
            "version": "v1.0",
            "initialized_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reference_sample_size": sample_size,
            "top_shap_feature_count": len(top_shap_features),
            "psi_bins_count": 10,
            "drift_alert_thresholds": {
                "no_drift": "< 0.10",
                "moderate_drift_warning": "0.10 - 0.25",
                "critical_drift_retrain": ">= 0.25",
            },
        },
        "features": {},
        "prediction_distribution": {},
    }

    print("\n[*] Initializing Empirical Drift Baselines for Top Features:")
    for feat_name in top_shap_features:
        if feat_name not in feat_index_map:
            continue
        idx = feat_index_map[feat_name]
        vals = X_features[:, idx]

        # 1. 10 Decile Bin Edges for PSI
        quantiles = np.linspace(0, 100, 11)
        bin_edges = np.percentile(vals, quantiles)
        # Ensure bin edges are strictly monotonically increasing
        for k in range(1, len(bin_edges)):
            if bin_edges[k] <= bin_edges[k - 1]:
                bin_edges[k] = bin_edges[k - 1] + 1e-5

        counts, _ = np.histogram(vals, bins=bin_edges)
        proportions = [float(c / len(vals)) for c in counts]

        # 2. 100-point Quantile Grid for Wasserstein Distance
        grid_quantiles = np.linspace(0.01, 0.99, 99)
        wasserstein_grid = [float(q) for q in np.percentile(vals, grid_quantiles * 100)]

        # 3. Parametric Summary
        mean_val = float(np.mean(vals))
        std_val = float(np.std(vals))
        median_val = float(np.median(vals))
        iqr_val = float(stats.iqr(vals))
        min_val = float(np.min(vals))
        max_val = float(np.max(vals))
        skew_val = float(stats.skew(vals))

        drift_baselines["features"][feat_name] = {
            "feature_index": idx,
            "psi_decile_edges": [float(b) for b in bin_edges],
            "reference_proportions": proportions,
            "wasserstein_quantile_grid": wasserstein_grid,
            "summary_statistics": {
                "mean": round(mean_val, 4),
                "std": round(std_val, 4),
                "median": round(median_val, 4),
                "iqr": round(iqr_val, 4),
                "min": round(min_val, 4),
                "max": round(max_val, 4),
                "skewness": round(skew_val, 4),
            },
        }
        print(f"  - {feat_name:26s}: Mean={mean_val:8.3f} | Std={std_val:8.3f} | Median={median_val:8.3f} | PSI Deciles=10 [OK]")

    # Baseline for Model Prediction Distribution (risk_score)
    print("\n[*] Initializing Model Prediction Drift Baseline (risk_score):")
    pred_quantiles = np.linspace(0, 100, 11)
    pred_bin_edges = np.percentile(risk_scores, pred_quantiles)
    for k in range(1, len(pred_bin_edges)):
        if pred_bin_edges[k] <= pred_bin_edges[k - 1]:
            pred_bin_edges[k] = pred_bin_edges[k - 1] + 1e-5

    pred_counts, _ = np.histogram(risk_scores, bins=pred_bin_edges)
    pred_proportions = [float(c / len(risk_scores)) for c in pred_counts]

    grid_quantiles = np.linspace(0.01, 0.99, 99)
    pred_wasserstein_grid = [float(q) for q in np.percentile(risk_scores, grid_quantiles * 100)]

    drift_baselines["prediction_distribution"] = {
        "metric_name": "risk_score",
        "psi_decile_edges": [float(b) for b in pred_bin_edges],
        "reference_proportions": pred_proportions,
        "wasserstein_quantile_grid": pred_wasserstein_grid,
        "summary_statistics": {
            "mean": round(float(np.mean(risk_scores)), 6),
            "std": round(float(np.std(risk_scores)), 6),
            "median": round(float(np.median(risk_scores)), 6),
            "iqr": round(float(stats.iqr(risk_scores)), 6),
            "min": round(float(np.min(risk_scores)), 6),
            "max": round(float(np.max(risk_scores)), 6),
            "skewness": round(float(stats.skew(risk_scores)), 4),
        },
    }
    print(f"  - {'risk_score':26s}: Mean={np.mean(risk_scores):.6f} | Median={np.median(risk_scores):.6f} | Max={np.max(risk_scores):.6f} [OK]")

    # Self-validation sanity check: PSI between reference and itself should be 0.0
    self_psi = compute_psi(risk_scores, risk_scores, pred_bin_edges)
    print(f"\n[*] Self-Consistency Test (Baseline vs Baseline PSI): {self_psi:.6f} (< 1e-4: PASS)")
    assert self_psi < 1e-3, f"Self-PSI failed: {self_psi}"

    # Serialize baselines
    out_path_models = os.path.join(model_dir, "drift_baselines.json")
    with open(out_path_models, "w", encoding="utf-8") as f:
        json.dump(drift_baselines, f, indent=2)
    print(f"[✓] Serialized drift baselines to: {out_path_models}")

    data_dir = os.path.join(ROOT_DIR, "data", "samld")
    if os.path.exists(data_dir):
        out_path_data = os.path.join(data_dir, "drift_baselines.json")
        with open(out_path_data, "w", encoding="utf-8") as f:
            json.dump(drift_baselines, f, indent=2)
        print(f"[✓] Mirrored drift baselines to: {out_path_data}")

    print("\n" + "=" * 80)
    print("SAML-D DRIFT BASELINE INITIALIZATION COMPLETED SUCCESSFULLY")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
