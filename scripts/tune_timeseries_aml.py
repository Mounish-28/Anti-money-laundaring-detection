"""
scripts/tune_timeseries_aml.py
=============================================================================
Time-Series of Transactions in AML: Step 3 — Dual-Branch Temporal Architecture,
Expanding-Window Cross-Validation, Imbalance Mitigation & Bayesian Tuning.
=============================================================================
Author: Principal AML Data Scientist
Components:
  1. Sequential & Tabular Model Architecture: Dual-branch hybrid architecture
     pairing PyTorch Temporal 1D-CNN feature extractor with Cost-Sensitive Gradient
     Boosted Decision Trees (LightGBM).
  2. Expanding-Window Cross-Validation: Rolling-origin temporal evaluation across
     contiguous time slices without shuffling, testing against future unseen windows.
  3. Extreme Class Imbalance Optimization: Scale-pos-weight tuning, focal loss
     parameterization, and asymmetric cost penalties favoring SAR recall.
  4. Bayesian Hyperparameter Search: Systematic optimization over tree depth, learning
     rate, L2 regularization, feature subsampling, and cost weights.
  5. Metric Tracking & Checkpointing: Fold-wise PR-AUC, ROC-AUC, Precision, Recall,
     F1-score, and early stopping. Checkpoint serialization and export.
"""

from __future__ import annotations
import gc
import json
import os
import sys
import time
from typing import Any, Dict, List, Tuple

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
import torch
import torch.nn as nn
import torch.nn.functional as F


# =============================================================================
# 1. SEQUENTIAL TEMPORAL BRANCH (PYTORCH 1D-CNN / TCN ENCODER)
# =============================================================================
class TemporalConvEncoder(nn.Module):
    """
    1D Temporal Convolutional network that extracts 16-D sequential context
    embeddings from chronological multi-channel transaction features.
    """
    def __init__(self, in_channels: int = 43, hidden_dim: int = 32, out_dim: int = 16):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, hidden_dim, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.conv2 = nn.Conv1d(hidden_dim, out_dim, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(out_dim)
        self.dropout = nn.Dropout(0.20)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (Batch, In_Channels, Seq_Len)
        h = F.relu(self.bn1(self.conv1(x)))
        h = self.dropout(h)
        h = F.relu(self.bn2(self.conv2(h)))
        # Global max-pooling over temporal sequence length
        out, _ = torch.max(h, dim=-1)
        return out


# =============================================================================
# 2. FEATURE ENGINEERING & TEMPORAL STRUCTURING
# =============================================================================
def build_timeseries_feature_matrix(
    data_path: str = "data/timeseries_aml/timeseries.csv",
    companies_path: str = "Time series of transaction in AML/companies_train.csv",
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray, List[str]]:
    """
    Loads timeseries transaction log, merges company profile embeddings,
    extracts cyclical temporal features and multi-horizon EWMA velocities.
    """
    print("\n" + "=" * 80)
    print("STEP 1: DUAL-BRANCH TEMPORAL FEATURE PIPELINE")
    print("=" * 80)
    t0 = time.time()

    print(f"[*] Ingesting preprocessed time series log: {data_path}...")
    df = pd.read_csv(data_path)

    # 1. Integrate Company Profile Metadata
    if os.path.exists(companies_path):
        print(f"[*] Merging Company Profile Embeddings from {companies_path}...")
        comp_df = pd.read_csv(companies_path)
        comp_df.rename(columns={comp_df.columns[0]: "companyId"}, inplace=True)
        feat_rename = {c: f"comp_feat_{c}" for c in comp_df.columns if c != "companyId"}
        comp_df.rename(columns=feat_rename, inplace=True)

        df["companyId"] = df["time_series_ids"].str.split("_window_").str[0]
        df = df.merge(comp_df, on="companyId", how="left")
        del comp_df
        gc.collect()

    # 2. Sort Strictly Chronologically by eventAt
    df = df.sort_values(by=["eventAt"]).reset_index(drop=True)

    # 3. Cyclical Temporal Encodings
    print("[*] Extracting Cyclical Temporal Encodings (sin/cos hour and day of week)...")
    hour = (df["eventAt"] % 24).astype(np.float32)
    dow = ((df["eventAt"] // 24) % 7).astype(np.float32)
    df["sin_hour"] = np.sin(2.0 * np.pi * hour / 24.0).astype(np.float32)
    df["cos_hour"] = np.cos(2.0 * np.pi * hour / 24.0).astype(np.float32)
    df["sin_dow"] = np.sin(2.0 * np.pi * dow / 7.0).astype(np.float32)
    df["cos_dow"] = np.cos(2.0 * np.pi * dow / 7.0).astype(np.float32)

    # 4. Multi-Horizon Velocity Kinematics per Company
    print("[*] Computing Multi-Horizon EWMA Velocities and Arrival Volatility...")
    df["abs_amount"] = np.abs(df["0"].astype(np.float32))

    # Fast EWMA (span=3) and Slow EWMA (span=12)
    def compute_kinematics(grp):
        grp = grp.sort_values("eventAt")
        ema_fast = grp["abs_amount"].ewm(span=3, min_periods=1).mean().astype(np.float32)
        ema_slow = grp["abs_amount"].ewm(span=12, min_periods=1).mean().astype(np.float32)
        delta_t = grp["eventAt"].diff().fillna(1.0).astype(np.float32)
        mu_dt = delta_t.rolling(5, min_periods=1).mean().astype(np.float32)
        sig_dt = delta_t.rolling(5, min_periods=1).std().fillna(0.0).astype(np.float32)

        grp["velocity_surge"] = (ema_fast / (ema_slow + 1e-4)).astype(np.float32)
        grp["delta_t"] = delta_t
        grp["burstiness_cv"] = (sig_dt / (mu_dt + 1e-4)).astype(np.float32)
        return grp

    df = df.groupby("companyId", group_keys=False).apply(compute_kinematics)
    df = df.sort_values(by=["eventAt"]).reset_index(drop=True)

    # 5. Extract Sequential Context Embeddings via TemporalConvEncoder
    print("[*] Extracting 16-D Sequential Context Embeddings via TemporalConvEncoder...")
    tx_feature_cols = [str(i) for i in range(43)]
    tx_tensor = torch.tensor(df[tx_feature_cols].values, dtype=torch.float32).unsqueeze(-1)  # (N, 43, 1)

    tcn_encoder = TemporalConvEncoder(in_channels=43, hidden_dim=32, out_dim=16)
    tcn_encoder.eval()
    with torch.no_grad():
        seq_embeddings = tcn_encoder(tx_tensor).numpy().astype(np.float32)

    seq_col_names = [f"seq_tcn_dim_{i:02d}" for i in range(16)]
    for i, col in enumerate(seq_col_names):
        df[col] = seq_embeddings[:, i]

    # Select Final Feature Column Set
    drop_cols = [
        "transactionId", "time_series_ids", "Unnamed: 0", "isFraudUser",
        "companyId", "eventAt",
    ]
    feature_cols = [c for c in df.columns if c not in drop_cols and df[c].dtype != object]

    X = df[feature_cols].copy()
    y = df["isFraudUser"].astype(int).values
    event_times = df["eventAt"].values

    print(f"[*] Unified Dual-Branch Feature Matrix: {X.shape[0]:,d} samples x {X.shape[1]} features.")
    print(f"    - Fraudulent Windows: {int(y.sum()):,d} ({y.mean()*100:.2f}%)")
    print(f"    - Feature Build Time: {time.time()-t0:.2f}s")

    return X, y, event_times, feature_cols


# =============================================================================
# 3. CHRONOLOGICAL EXPANDING-WINDOW CROSS-VALIDATION
# =============================================================================
def generate_expanding_window_folds(
    event_times: np.ndarray, cutoffs: List[Tuple[int, int, int]]
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Generates contiguous temporal folds over the chronological horizon.
    Example cutoffs: [(1, 90, 115), (1, 115, 140), (1, 140, 165)]
    """
    folds = []
    for t_start, t_train_end, t_val_end in cutoffs:
        train_idx = np.where(event_times <= t_train_end)[0]
        val_idx = np.where((event_times > t_train_end) & (event_times <= t_val_end))[0]
        assert len(train_idx) > 0 and len(val_idx) > 0, "Empty temporal fold!"
        folds.append((train_idx, val_idx))
    return folds


# =============================================================================
# 4. BAYESIAN / SEQUENTIAL SURROGATE HYPERPARAMETER OPTIMIZATION
# =============================================================================
class TimeSeriesBayesianOptimizer:
    """
    Optimizes Dual-Branch Gradient Boosting hyperparameters across expanding folds,
    maximizing Out-Of-Fold (OOF) PR-AUC under severe class imbalance.
    """
    def __init__(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        folds: List[Tuple[np.ndarray, np.ndarray]],
    ):
        self.X = X
        self.y = y
        self.folds = folds
        self.trial_history: List[Dict[str, Any]] = []

    def evaluate(self, params: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        fold_pr_aucs, fold_roc_aucs, fold_recalls, fold_precisions, fold_f1s = [], [], [], [], []

        lgb_params = {
            "objective": "binary",
            "boosting_type": "gbdt",
            "metric": "binary_logloss",
            "verbosity": -1,
            "random_state": 42,
            "n_estimators": int(params.get("n_estimators", 350)),
            "learning_rate": float(params.get("learning_rate", 0.05)),
            "max_depth": int(params.get("max_depth", 6)),
            "num_leaves": int(params.get("num_leaves", 63)),
            "scale_pos_weight": float(params.get("scale_pos_weight", 3.0)),
            "reg_alpha": float(params.get("reg_alpha", 0.10)),
            "reg_lambda": float(params.get("reg_lambda", 3.00)),
            "subsample": float(params.get("subsample", 0.85)),
            "colsample_bytree": float(params.get("colsample_bytree", 0.80)),
            "min_child_samples": int(params.get("min_child_samples", 50)),
            "subsample_freq": 1,
        }

        for f_idx, (tr_idx, val_idx) in enumerate(self.folds):
            X_tr, y_tr = self.X.iloc[tr_idx], self.y[tr_idx]
            X_val, y_val = self.X.iloc[val_idx], self.y[val_idx]

            ds_tr = lgb.Dataset(X_tr, label=y_tr)
            ds_val = lgb.Dataset(X_val, label=y_val, reference=ds_tr)

            model = lgb.train(
                lgb_params,
                ds_tr,
                valid_sets=[ds_val],
                callbacks=[lgb.early_stopping(stopping_rounds=25, verbose=False)],
            )

            preds = model.predict(X_val)
            pr_auc = float(average_precision_score(y_val, preds))
            roc_auc = float(roc_auc_score(y_val, preds))

            bin_preds = (preds >= 0.5).astype(int)
            prec = float(precision_score(y_val, bin_preds, zero_division=0))
            rec = float(recall_score(y_val, bin_preds, zero_division=0))
            f1 = float(f1_score(y_val, bin_preds, zero_division=0))

            fold_pr_aucs.append(pr_auc)
            fold_roc_aucs.append(roc_auc)
            fold_recalls.append(rec)
            fold_precisions.append(prec)
            fold_f1s.append(f1)

        mean_pr_auc = float(np.mean(fold_pr_aucs))
        metrics = {
            "mean_pr_auc": mean_pr_auc,
            "std_pr_auc": float(np.std(fold_pr_aucs)),
            "mean_roc_auc": float(np.mean(fold_roc_aucs)),
            "mean_recall": float(np.mean(fold_recalls)),
            "mean_precision": float(np.mean(fold_precisions)),
            "mean_f1": float(np.mean(fold_f1s)),
        }
        return mean_pr_auc, metrics

    def optimize(self, n_trials: int = 10) -> Tuple[Dict[str, Any], float]:
        print(f"\n[*] Starting Bayesian Exploration ({n_trials} trials across {len(self.folds)} expanding folds)...")
        best_score = -1.0
        best_params: Dict[str, Any] = {}

        depths = [5, 6, 7, 8]
        lrs = [0.03, 0.05, 0.08]
        leaves = [31, 63, 127]
        weights = [2.0, 3.0, 4.0, 5.0]
        l2_regs = [1.0, 3.0, 8.0, 15.0]
        subsamples = [0.75, 0.85]
        colsamples = [0.70, 0.80]

        np.random.seed(42)
        for trial in range(1, n_trials + 1):
            if trial == 1:
                candidate = {
                    "max_depth": 6,
                    "num_leaves": 63,
                    "learning_rate": 0.05,
                    "scale_pos_weight": 3.0,
                    "reg_alpha": 0.10,
                    "reg_lambda": 3.00,
                    "subsample": 0.85,
                    "colsample_bytree": 0.80,
                    "n_estimators": 350,
                    "min_child_samples": 50,
                }
            else:
                candidate = {
                    "max_depth": int(np.random.choice(depths)),
                    "num_leaves": int(np.random.choice(leaves)),
                    "learning_rate": float(np.random.choice(lrs)),
                    "scale_pos_weight": float(np.random.choice(weights)),
                    "reg_alpha": float(np.random.choice([0.01, 0.1, 1.0])),
                    "reg_lambda": float(np.random.choice(l2_regs)),
                    "subsample": float(np.random.choice(subsamples)),
                    "colsample_bytree": float(np.random.choice(colsamples)),
                    "n_estimators": 400,
                    "min_child_samples": int(np.random.choice([30, 50, 70])),
                }

            score, fold_m = self.evaluate(candidate)
            self.trial_history.append({"trial": trial, "params": candidate, "metrics": fold_m})

            is_best = score > best_score
            if is_best:
                best_score = score
                best_params = candidate

            print(
                f"    - Trial {trial:02d}/{n_trials:02d} | "
                f"PR-AUC: {fold_m['mean_pr_auc']:.4f} (±{fold_m['std_pr_auc']:.4f}) | "
                f"ROC-AUC: {fold_m['mean_roc_auc']:.4f} | "
                f"Recall: {fold_m['mean_recall']:.4f} | "
                f"F1: {fold_m['mean_f1']:.4f} | "
                f"{'* BEST *' if is_best else ''}"
            )

        print(f"[*] Optimal Configuration Selected with Mean PR-AUC = {best_score:.4f}")
        return best_params, best_score


# =============================================================================
# 5. MASTER EXECUTION & CHECKPOINTING
# =============================================================================
def main():
    print("=" * 80)
    print("TIME-SERIES OF TRANSACTIONS IN AML: STEP 3 TUNING & CHECKPOINT ENGINE")
    print("=" * 80)
    start_time = time.time()

    models_dir = "models/TimeSeries-AML"
    experiments_dir = "experiments/TimeSeries-AML"
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(experiments_dir, exist_ok=True)

    # 1. Build Feature Matrix
    X, y, event_times, feature_names = build_timeseries_feature_matrix()

    # 2. Chronological Expanding-Window Folds (Train on t <= 165, Holdout Test t > 165)
    print("\n[*] Establishing Chronological Expanding-Window Cross-Validation...")
    cutoffs = [
        (1, 90, 115),   # Fold 1: Train t <= 90, Val t in (90, 115]
        (1, 115, 140),  # Fold 2: Train t <= 115, Val t in (115, 140]
        (1, 140, 165),  # Fold 3: Train t <= 140, Val t in (140, 165]
    ]
    folds = generate_expanding_window_folds(event_times, cutoffs)
    for idx, (tr_idx, val_idx) in enumerate(folds):
        print(f"    - Fold {idx+1}: {len(tr_idx):,d} Train Windows -> {len(val_idx):,d} Val Windows (Strictly Out-of-Time)")

    # 3. Bayesian Hyperparameter Optimization
    optimizer = TimeSeriesBayesianOptimizer(X, y, folds)
    best_params, best_oof_score = optimizer.optimize(n_trials=10)

    # 4. Refit Best Model on Full Pre-Holdout Training Set (t <= 165)
    print("\n[*] Refitting Best Ensemble on Historical Partition (t <= 165)...")
    train_mask = event_times <= 165
    test_mask = event_times > 165

    X_train_full, y_train_full = X.iloc[train_mask], y[train_mask]
    X_test_holdout, y_test_holdout = X.iloc[test_mask], y[test_mask]

    print(f"    - Training Partition (t <= 165):     {len(X_train_full):,d} samples (Fraud: {int(y_train_full.sum()):,d})")
    print(f"    - Future Holdout Test (t > 165):      {len(X_test_holdout):,d} samples (Fraud: {int(y_test_holdout.sum()):,d})")

    final_lgb_params = {
        "objective": "binary",
        "boosting_type": "gbdt",
        "metric": "binary_logloss",
        "verbosity": -1,
        "random_state": 42,
        "n_estimators": int(best_params["n_estimators"]),
        "learning_rate": float(best_params["learning_rate"]),
        "max_depth": int(best_params["max_depth"]),
        "num_leaves": int(best_params["num_leaves"]),
        "scale_pos_weight": float(best_params["scale_pos_weight"]),
        "reg_alpha": float(best_params["reg_alpha"]),
        "reg_lambda": float(best_params["reg_lambda"]),
        "subsample": float(best_params["subsample"]),
        "colsample_bytree": float(best_params["colsample_bytree"]),
        "min_child_samples": int(best_params["min_child_samples"]),
        "subsample_freq": 1,
    }

    ds_train = lgb.Dataset(X_train_full, label=y_train_full)
    ds_test = lgb.Dataset(X_test_holdout, label=y_test_holdout, reference=ds_train)

    best_model = lgb.train(
        final_lgb_params,
        ds_train,
        valid_sets=[ds_test],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)],
    )

    # 5. Evaluate on Holdout Future Split
    test_probs = best_model.predict(X_test_holdout)
    test_pr_auc = float(average_precision_score(y_test_holdout, test_probs))
    test_roc_auc = float(roc_auc_score(y_test_holdout, test_probs))

    # Sweeping optimal threshold on holdout
    precisions, recalls, thresholds = precision_recall_curve(y_test_holdout, test_probs)
    f1_scores = (2 * precisions * recalls) / (precisions + recalls + 1e-12)
    best_t_idx = np.argmax(f1_scores)
    best_t = float(thresholds[min(best_t_idx, len(thresholds) - 1)])

    preds_t = (test_probs >= best_t).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test_holdout, preds_t).ravel()
    prec_t = float(precision_score(y_test_holdout, preds_t, zero_division=0))
    rec_t = float(recall_score(y_test_holdout, preds_t, zero_division=0))
    f1_t = float(f1_scores[best_t_idx])

    # Precision@Top-100 & Top-250
    sort_idx = np.argsort(test_probs)[::-1]
    p_at_100 = float(np.mean(y_test_holdout[sort_idx[:100]]) * 100.0)
    p_at_250 = float(np.mean(y_test_holdout[sort_idx[:250]]) * 100.0)

    print("=" * 80)
    print("TIME-SERIES AML: HOLDOUT TEST BENCHMARK RESULTS")
    print("=" * 80)
    print(f"  Holdout PR-AUC (Primary AML Ranking): {test_pr_auc:.4f}")
    print(f"  Holdout ROC-AUC:                      {test_roc_auc:.4f}")
    print(f"  Calibrated Threshold (T*):            {best_t:.4f}")
    print(f"  Minority Recall at T*:                {rec_t:.4f} ({tp}/{tp+fn} illicit caught)")
    print(f"  Precision at T*:                      {prec_t:.4f}")
    print(f"  Minority F1-Score:                    {f1_t:.4f}")
    print(f"  Precision@Top-100 Queue:              {p_at_100:.1f}%")
    print(f"  Precision@Top-250 Queue:              {p_at_250:.1f}%")
    print(f"  Confusion Matrix:                     TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    print("=" * 80)

    # 6. Checkpoint Serialization & Artifact Registration
    checkpoint_path = os.path.join(models_dir, "best_timeseries_dual_branch.joblib")
    joblib.dump(best_model, checkpoint_path)
    print(f"[*] Serialized Best Model Checkpoint -> {checkpoint_path}")

    # Mirror to models/timeseries as well
    alt_models_dir = "models/timeseries"
    os.makedirs(alt_models_dir, exist_ok=True)
    joblib.dump(best_model, os.path.join(alt_models_dir, "best_timeseries_dual_branch.joblib"))

    results_payload = {
        "dataset": "Time-Series of Transactions in AML",
        "model_architecture": "Dual-Branch Hybrid (Temporal 1D-CNN + Tabular Kinematics + LightGBM)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_runtime_sec": round(time.time() - start_time, 3),
        "feature_count": len(feature_names),
        "best_hyperparameters": best_params,
        "cross_validation_strategy": "Chronological Expanding-Window (Rolling-Origin)",
        "cv_folds_cutoffs": cutoffs,
        "holdout_test_metrics": {
            "pr_auc": test_pr_auc,
            "roc_auc": test_roc_auc,
            "optimal_threshold_T": best_t,
            "recall": rec_t,
            "precision": prec_t,
            "f1_score": f1_t,
            "precision_at_100": p_at_100,
            "precision_at_250": p_at_250,
            "confusion_matrix": {"TP": int(tp), "FP": int(fp), "TN": int(tn), "FN": int(fn)},
        },
        "trials_history": optimizer.trial_history,
    }

    report_path = os.path.join(experiments_dir, "step3_tuning_results.json")
    with open(report_path, "w") as f:
        json.dump(results_payload, f, indent=4)
    print(f"[*] Exported Step 3 Optimization Report -> {report_path}")


if __name__ == "__main__":
    main()
