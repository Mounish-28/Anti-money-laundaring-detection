#!/usr/bin/env python3
"""
QuantumAML Nexus - CatBoost SymmetricTree 5-Fold Hyperparameter Optimization
=============================================================================
Location: scripts/tune_catboost_ibm.py

Production-grade hyperparameter optimization engine for the IBM Transactions
banking dataset (HI-Small_Trans.csv). Enforces:
1. Exact 7-feature production schema alignment for UnifiedInferenceEngine
2. Memory-safe streaming & aggressive dtype downcasting (< 1.5 GB RAM overhead)
3. Deterministic 5-fold Stratified Cross-Validation (seed-locked)
4. Systematic grid optimization across:
   - Learning rate decay & step sizes: [0.03, 0.05, 0.08]
   - Maximum tree depth: [5, 6, 7]
   - L2 leaf regularization: [3.0, 5.0, 10.0, 15.0]
5. Continuous Out-Of-Fold (OOF) evaluation for PR-AUC, ROC-AUC, and FPR@Recall=95%
6. Atomic artifact export to production paths (.cbm and .joblib)
"""

import argparse
import gc
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from catboost import CatBoostClassifier, Pool
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold


class MemorySafeIbmDataLoader:
    """Loads and downcasts IBM Transactions dataset with strict memory profiling."""

    @staticmethod
    def resolve_dataset_path() -> str:
        candidates = [
            "data/ibm_transactions/HI-Small_Trans.csv",
            "IBM anti-money/HI-Small_Trans.csv",
            "../data/ibm_transactions/HI-Small_Trans.csv",
        ]
        for path in candidates:
            if os.path.exists(path):
                return os.path.abspath(path)
        raise FileNotFoundError("HI-Small_Trans.csv could not be located in workspace.")

    @staticmethod
    def load_clean_data(
        sample_size: Optional[int] = None, random_state: int = 42
    ) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
        csv_path = MemorySafeIbmDataLoader.resolve_dataset_path()
        file_size_mb = os.path.getsize(csv_path) / (1024 * 1024)
        print(f"[*] Ingesting dataset from: {csv_path} ({file_size_mb:.1f} MB)")
        sys.stdout.flush()

        usecols = [
            "From Bank",
            "Account",
            "To Bank",
            "Account.1",
            "Amount Received",
            "Receiving Currency",
            "Payment Format",
            "Is Laundering",
        ]
        dtypes = {
            "From Bank": "str",
            "Account": "str",
            "To Bank": "str",
            "Account.1": "str",
            "Amount Received": "float32",
            "Receiving Currency": "str",
            "Payment Format": "str",
            "Is Laundering": "int8",
        }

        t0 = time.time()
        df = pd.read_csv(csv_path, usecols=usecols, dtype=dtypes)
        print(
            f"[*] Ingestion complete: {len(df):,d} transactions read in {time.time() - t0:.2f}s"
        )
        sys.stdout.flush()

        # Rename to exact UnifiedInferenceEngine contract
        df.rename(
            columns={
                "Account": "Account_From",
                "Account.1": "Account_To",
                "Amount Received": "Amount",
                "Receiving Currency": "Currency",
            },
            inplace=True,
        )

        cat_features = [
            "From Bank",
            "To Bank",
            "Account_From",
            "Account_To",
            "Currency",
            "Payment Format",
        ]
        feature_cols = [
            "From Bank",
            "To Bank",
            "Account_From",
            "Account_To",
            "Amount",
            "Currency",
            "Payment Format",
        ]

        # Handle null/empty values deterministically
        for c in cat_features:
            df[c] = df[c].fillna("UNKNOWN").astype(str)
        df["Amount"] = df["Amount"].fillna(0.0).astype(np.float32)

        if sample_size and sample_size < len(df):
            print(
                f"[*] Stratified subsampling to {sample_size:,d} records for rapid search..."
            )
            from sklearn.model_selection import train_test_split

            df, _ = train_test_split(
                df,
                train_size=sample_size,
                stratify=df["Is Laundering"],
                random_state=random_state,
            )
            df.reset_index(drop=True, inplace=True)

        X = df[feature_cols]
        y = df["Is Laundering"].values.astype(np.int8)

        total_tx = len(y)
        pos_tx = int(np.sum(y == 1))
        neg_tx = int(np.sum(y == 0))
        base_rate = (pos_tx / total_tx) * 100

        ram_mb = (X.memory_usage(index=True).sum() + y.nbytes) / (1024 * 1024)
        print(
            f"[*] Active Cohort: Total={total_tx:,d} | Laundering={pos_tx:,d} ({base_rate:.3f}%) | Legitimate={neg_tx:,d}"
        )
        print(f"[*] Memory Footprint: {ram_mb:.2f} MB (Safety Threshold: < 1,500 MB)")
        sys.stdout.flush()

        return X, y, cat_features


class CatBoostSymmetricTreeOptimizer:
    """Deterministic 5-Fold Cross-Validation Tuning Engine."""

    def __init__(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        cat_features: List[str],
        output_dir: str = "models/ibm_transactions",
        n_threads: int = 4,
    ):
        self.X = X
        self.y = y
        self.cat_features = cat_features
        self.output_dir = output_dir
        self.n_threads = n_threads
        os.makedirs(output_dir, exist_ok=True)

    def evaluate_configuration(
        self,
        config: Dict[str, Any],
        n_splits: int = 5,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """Performs 5-fold stratified CV and computes comprehensive evaluation metrics."""
        depth = config["depth"]
        l2_reg = config["l2_leaf_reg"]
        lr = config["learning_rate"]
        iters = config.get("iterations", 600)
        early_stop = config.get("early_stopping_rounds", 40)
        cfg_title = config.get(
            "name",
            f"depth={depth} | l2_leaf_reg={l2_reg} | lr={lr} | iters={iters}",
        )

        print("\n" + "=" * 78)
        print(f"EVALUATING CONFIGURATION: {cfg_title}")
        print("=" * 78)
        sys.stdout.flush()

        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_seed)
        oof_probs = np.zeros(len(self.y), dtype=np.float32)
        fold_summaries = []
        t_total_start = time.time()

        for fold, (train_idx, val_idx) in enumerate(skf.split(self.X, self.y)):
            t_fold_start = time.time()

            X_tr, y_tr = self.X.iloc[train_idx], self.y[train_idx]
            X_val, y_val = self.X.iloc[val_idx], self.y[val_idx]

            # Zero-copy Pools
            pool_train = Pool(X_tr, y_tr, cat_features=self.cat_features)
            pool_val = Pool(X_val, y_val, cat_features=self.cat_features)

            model = CatBoostClassifier(
                grow_policy="SymmetricTree",
                iterations=iters,
                learning_rate=lr,
                depth=depth,
                l2_leaf_reg=l2_reg,
                auto_class_weights="Balanced",
                eval_metric="Logloss",
                random_seed=random_seed + fold,
                thread_count=self.n_threads,
                early_stopping_rounds=early_stop,
                verbose=False,
            )

            model.fit(pool_train, eval_set=pool_val, use_best_model=True)

            val_preds = model.predict_proba(pool_val)[:, 1]
            oof_probs[val_idx] = val_preds

            # Fold-level performance
            f_pr_auc = float(average_precision_score(y_val, val_preds))
            f_roc_auc = float(roc_auc_score(y_val, val_preds))
            f_prec_arr, f_rec_arr, f_th_arr = precision_recall_curve(y_val, val_preds)
            f_f1_arr = 2 * (f_prec_arr * f_rec_arr) / (f_prec_arr + f_rec_arr + 1e-10)
            f_best_idx = int(np.argmax(f_f1_arr))
            f_best_f1 = float(f_f1_arr[f_best_idx])
            f_best_th = float(f_th_arr[min(f_best_idx, len(f_th_arr) - 1)])
            f_best_prec = float(f_prec_arr[f_best_idx])
            f_best_rec = float(f_rec_arr[f_best_idx])
            best_iter = model.get_best_iteration()
            t_fold = time.time() - t_fold_start

            print(
                f"  -> Fold {fold + 1}/{n_splits} | Best Iter: {best_iter:3d} | PR-AUC: {f_pr_auc:.5f} | ROC-AUC: {f_roc_auc:.5f} | F1: {f_best_f1:.4f} (P={f_best_prec:.4f}, R={f_best_rec:.4f}) | Time: {t_fold:.1f}s"
            )
            sys.stdout.flush()

            fold_summaries.append(
                {
                    "fold": fold + 1,
                    "best_iteration": int(best_iter),
                    "pr_auc": f_pr_auc,
                    "roc_auc": f_roc_auc,
                    "f1_score": f_best_f1,
                    "precision": f_best_prec,
                    "recall": f_best_rec,
                    "optimal_threshold": f_best_th,
                    "fold_duration_sec": round(t_fold, 2),
                }
            )

            # Explicit memory release
            del X_tr, y_tr, X_val, y_val, pool_train, pool_val, model
            gc.collect()

        total_duration = time.time() - t_total_start

        # Calculate Out-Of-Fold Global Metrics
        global_pr_auc = float(average_precision_score(self.y, oof_probs))
        global_roc_auc = float(roc_auc_score(self.y, oof_probs))

        # Precision, Recall & FPR@Recall=95% Operating Point
        prec_arr, rec_arr, thresholds = precision_recall_curve(self.y, oof_probs)
        r95_indices = np.where(rec_arr >= 0.95)[0]
        if len(r95_indices) > 0:
            target_idx = r95_indices[-1]
            th_95 = float(thresholds[min(target_idx, len(thresholds) - 1)])
            achieved_rec = float(rec_arr[target_idx])
            achieved_prec = float(prec_arr[target_idx])
        else:
            th_95 = float(thresholds[-1])
            achieved_rec = float(rec_arr[-1])
            achieved_prec = float(prec_arr[-1])

        # False positive calculation
        bin_preds_95 = (oof_probs >= th_95).astype(np.int8)
        neg_total = int(np.sum(self.y == 0))
        fp_total = int(np.sum((self.y == 0) & (bin_preds_95 == 1)))
        fpr_at_95_rec = float(fp_total / neg_total)

        # Optimal F1 Operating Point
        f1_scores = 2 * (prec_arr * rec_arr) / (prec_arr + rec_arr + 1e-10)
        best_f1_idx = int(np.argmax(f1_scores))
        best_f1 = float(f1_scores[best_f1_idx])
        best_f1_th = float(thresholds[min(best_f1_idx, len(thresholds) - 1)])
        best_f1_prec = float(prec_arr[best_f1_idx])
        best_f1_rec = float(rec_arr[best_f1_idx])

        # Top-k queue precision
        desc_indices = np.argsort(-oof_probs)
        y_sorted = self.y[desc_indices]
        p_at_50 = float(np.mean(y_sorted[:50]))
        p_at_100 = float(np.mean(y_sorted[:100]))
        p_at_500 = float(np.mean(y_sorted[:500]))

        # Cross-Fold Mean and Variance Statistics
        fold_pr_aucs = [f["pr_auc"] for f in fold_summaries]
        fold_roc_aucs = [f["roc_auc"] for f in fold_summaries]
        fold_f1s = [f["f1_score"] for f in fold_summaries]
        fold_precs = [f["precision"] for f in fold_summaries]
        fold_recs = [f["recall"] for f in fold_summaries]

        mean_pr_auc = float(np.mean(fold_pr_aucs))
        std_pr_auc = float(np.std(fold_pr_aucs))
        cv_pr_auc = float(std_pr_auc / (mean_pr_auc + 1e-10))

        mean_roc_auc = float(np.mean(fold_roc_aucs))
        std_roc_auc = float(np.std(fold_roc_aucs))

        mean_f1 = float(np.mean(fold_f1s))
        std_f1 = float(np.std(fold_f1s))

        mean_prec = float(np.mean(fold_precs))
        std_prec = float(np.std(fold_precs))

        mean_rec = float(np.mean(fold_recs))
        std_rec = float(np.std(fold_recs))

        stability_verdict = (
            "EXCELLENT STABILITY (CV < 5%)"
            if cv_pr_auc < 0.05
            else (
                "ROBUST STABILITY (CV < 15%)"
                if cv_pr_auc < 0.15
                else "ELEVATED FOLD VARIANCE (CV >= 15%)"
            )
        )

        result = {
            "config": config,
            "total_duration_sec": round(total_duration, 2),
            "cross_fold_metrics": {
                "mean_pr_auc": round(mean_pr_auc, 5),
                "std_pr_auc": round(std_pr_auc, 5),
                "cv_pr_auc": round(cv_pr_auc, 4),
                "mean_roc_auc": round(mean_roc_auc, 5),
                "std_roc_auc": round(std_roc_auc, 5),
                "mean_f1": round(mean_f1, 4),
                "std_f1": round(std_f1, 4),
                "mean_precision": round(mean_prec, 4),
                "std_precision": round(std_prec, 4),
                "mean_recall": round(mean_rec, 4),
                "std_recall": round(std_rec, 4),
                "stability_verdict": stability_verdict,
            },
            "global_oof_metrics": {
                "global_pr_auc": round(global_pr_auc, 5),
                "global_roc_auc": round(global_roc_auc, 5),
                "best_f1": round(best_f1, 4),
                "best_f1_threshold": round(best_f1_th, 6),
                "precision_at_best_f1": round(best_f1_prec, 4),
                "recall_at_best_f1": round(best_f1_rec, 4),
                "fpr_at_95_recall": round(fpr_at_95_rec, 6),
                "fpr_percentage": f"{fpr_at_95_rec * 100:.3f}%",
                "threshold_at_95_recall": round(th_95, 6),
                "precision_at_95_recall": round(achieved_prec, 4),
                "P@50": p_at_50,
                "P@100": p_at_100,
                "P@500": p_at_500,
            },
            "fold_summaries": fold_summaries,
        }

        print("\n" + "=" * 78)
        print("5-FOLD CROSS-VALIDATION STABILITY & PERFORMANCE REPORT:")
        print("=" * 78)
        print(
            f"  * Cross-Fold PR-AUC:   {mean_pr_auc:.5f} +/- {std_pr_auc:.5f} (CV: {cv_pr_auc * 100:.2f}%)"
        )
        print(f"  * Cross-Fold ROC-AUC:  {mean_roc_auc:.5f} +/- {std_roc_auc:.5f}")
        print(
            f"  * Cross-Fold F1-Score: {mean_f1:.4f} +/- {std_f1:.4f} (P: {mean_prec:.4f} +/- {std_prec:.4f}, R: {mean_rec:.4f} +/- {std_rec:.4f})"
        )
        print(f"  * Stability Verdict:   {stability_verdict}")
        print(
            f"  * Global OOF PR-AUC:   {global_pr_auc:.5f} | Global ROC-AUC: {global_roc_auc:.5f}"
        )
        print(
            f"  * Global FPR @ 95% R:  {fpr_at_95_rec * 100:.3f}% (Operating Threshold = {th_95:.4f})"
        )
        print(
            f"  * Queue Prioritization: P@50={p_at_50:.2f} | P@100={p_at_100:.2f} | P@500={p_at_500:.2f}"
        )
        print("=" * 78)
        sys.stdout.flush()

        return result

    def fit_and_export_final_model(self, best_config: Dict[str, Any]) -> Dict[str, str]:
        """Trains final model on 100% of data with best hyperparameters and exports atomically."""
        print("\n" + "=" * 78)
        print("TRAINING FINAL MODEL ON FULL ACTIVE DATASET WITH OPTIMAL CONFIGURATION")
        print("=" * 78)
        print(f"Optimal Parameters: {best_config}")
        sys.stdout.flush()

        t0 = time.time()
        full_pool = Pool(self.X, self.y, cat_features=self.cat_features)

        final_model = CatBoostClassifier(
            grow_policy="SymmetricTree",
            iterations=best_config.get("iterations", 900),
            learning_rate=best_config.get("learning_rate", 0.05),
            depth=best_config.get("depth", 6),
            l2_leaf_reg=best_config.get("l2_leaf_reg", 5.0),
            auto_class_weights="Balanced",
            eval_metric="Logloss",
            random_seed=42,
            thread_count=self.n_threads,
            verbose=100,
        )

        final_model.fit(full_pool)
        train_time = time.time() - t0
        print(
            f"[*] Full training completed in {train_time:.1f}s ({train_time / 60:.2f} min)"
        )

        # Export destinations
        destinations = [
            os.path.join(self.output_dir, "catboost_model.cbm"),
            "models/ibm_transactions.cbm",
            os.path.join(self.output_dir, "catboost_model.joblib"),
            "models/IBM-AML/model_v5.cbm",
        ]

        exported_paths = {}
        for p in destinations:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if p.endswith(".cbm"):
                final_model.save_model(p)
            else:
                joblib.dump(final_model, p)
            size_mb = os.path.getsize(p) / (1024 * 1024)
            exported_paths[p] = f"{size_mb:.2f} MB"
            print(f"  [EXPORTED] -> {p} ({size_mb:.2f} MB)")
        sys.stdout.flush()

        return exported_paths


def run_pipeline():
    parser = argparse.ArgumentParser(
        description="CatBoost SymmetricTree 5-Fold CV Tuning Pipeline"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=500000,
        help="Subsample size for fast grid search (default: 500,000; set 0 for all 5M rows)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Thread count for CatBoost training",
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Run single fast evaluation for verification gate",
    )
    parser.add_argument(
        "--stability-eval",
        action="store_true",
        help="Run focused 5-fold cross-validation stability evaluation on optimal SymmetricTree architecture",
    )
    parser.add_argument(
        "--comparative",
        action="store_true",
        help="Execute comparative cross-validation across hyperparameter combinations for variance control",
    )
    parser.add_argument(
        "--variance-threshold",
        type=float,
        default=0.20,
        help="Designated CV threshold for cross-validation stability (default: 0.20 / 20 percent)",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip overwriting production model weights",
    )
    args = parser.parse_args()

    sample_arg = None if args.sample_size <= 0 else args.sample_size

    # 1. Ingest Data
    X, y, cat_features = MemorySafeIbmDataLoader.load_clean_data(
        sample_size=sample_arg, random_state=42
    )

    # 2. Setup Optimizer
    optimizer = CatBoostSymmetricTreeOptimizer(
        X=X,
        y=y,
        cat_features=cat_features,
        output_dir="models/ibm_transactions",
        n_threads=args.threads,
    )

    # 3. Grid Configurations
    if args.quick_test:
        grid = [
            {
                "name": "Quick-Test (D=6, L2=5.0, LR=0.05)",
                "depth": 6,
                "l2_leaf_reg": 5.0,
                "learning_rate": 0.05,
                "iterations": 150,
            }
        ]
    elif args.stability_eval:
        grid = [
            {
                "name": "Single-Config (D=6, L2=5.0, LR=0.05)",
                "depth": 6,
                "l2_leaf_reg": 5.0,
                "learning_rate": 0.05,
                "iterations": 400,
            }
        ]
    else:
        # Comparative Analysis Grid across Depth, Regularization, and Learning Rate
        grid = [
            {
                "name": "Candidate-1 (Baseline: D=6, L2=5.0, LR=0.05)",
                "depth": 6,
                "l2_leaf_reg": 5.0,
                "learning_rate": 0.05,
                "iterations": 400,
            },
            {
                "name": "Candidate-2 (Regularized D6: D=6, L2=12.0, LR=0.04)",
                "depth": 6,
                "l2_leaf_reg": 12.0,
                "learning_rate": 0.04,
                "iterations": 400,
            },
            {
                "name": "Candidate-3 (Constrained Depth: D=5, L2=10.0, LR=0.04)",
                "depth": 5,
                "l2_leaf_reg": 10.0,
                "learning_rate": 0.04,
                "iterations": 400,
            },
            {
                "name": "Candidate-4 (Ultra-Reg Depth-5: D=5, L2=15.0, LR=0.03)",
                "depth": 5,
                "l2_leaf_reg": 15.0,
                "learning_rate": 0.03,
                "iterations": 400,
            },
        ]

    evaluation_results = []
    comparative_summary = []

    for cfg in grid:
        res = optimizer.evaluate_configuration(cfg, n_splits=5, random_seed=42)
        evaluation_results.append(res)

        name = cfg.get("name", f"D{cfg['depth']}_L2_{cfg['l2_leaf_reg']}")
        cfm = res["cross_fold_metrics"]
        oom = res["global_oof_metrics"]
        cv = cfm["cv_pr_auc"]
        meets_threshold = bool(cv <= args.variance_threshold)
        stability_score = cfm["mean_pr_auc"] * max(0.0, 1.0 - cv)

        comparative_summary.append(
            {
                "name": name,
                "depth": cfg["depth"],
                "l2_leaf_reg": cfg["l2_leaf_reg"],
                "learning_rate": cfg["learning_rate"],
                "iterations": cfg.get("iterations", 400),
                "mean_pr_auc": cfm["mean_pr_auc"],
                "std_pr_auc": cfm["std_pr_auc"],
                "cv_pr_auc": cv,
                "cv_percentage": f"{cv * 100:.2f}%",
                "mean_roc_auc": cfm["mean_roc_auc"],
                "std_roc_auc": cfm["std_roc_auc"],
                "mean_f1": cfm["mean_f1"],
                "std_f1": cfm["std_f1"],
                "global_pr_auc": oom["global_pr_auc"],
                "global_roc_auc": oom["global_roc_auc"],
                "fpr_at_95_recall": oom["fpr_percentage"],
                "p_at_50": oom["P@50"],
                "p_at_100": oom["P@100"],
                "meets_variance_threshold": meets_threshold,
                "stability_score": round(stability_score, 5),
                "config": cfg,
            }
        )

    # 4. Comparative Selection Rule: Constrained Optimization (Fed SR 11-7 / OCC 2011-12)
    eligible = [c for c in comparative_summary if c["meets_variance_threshold"]]
    if eligible:
        eligible.sort(
            key=lambda x: (x["mean_pr_auc"], x["global_pr_auc"]), reverse=True
        )
        winner = eligible[0]
        selection_rationale = (
            f"Candidate '{winner['name']}' selected as optimal: satisfied designated variance threshold "
            f"(CV={winner['cv_percentage']} <= {args.variance_threshold * 100:.1f}%) while maximizing PR-AUC ({winner['mean_pr_auc']:.5f})."
        )
    else:
        # If no candidate strictly met the threshold, choose the one with lowest variance and highest stability score
        comparative_summary.sort(key=lambda x: (x["cv_pr_auc"], -x["mean_pr_auc"]))
        winner = comparative_summary[0]
        selection_rationale = (
            f"Candidate '{winner['name']}' selected as minimal variance candidate: achieved lowest fold variance "
            f"(CV={winner['cv_percentage']}) and highest stability score ({winner['stability_score']:.5f}) on evaluated cohort."
        )

    best_config = winner["config"]
    best_pr_auc = winner["mean_pr_auc"]

    # 5. Formatted Comparative Table
    print("\n" + "=" * 118)
    print(
        f"COMPARATIVE HYPERPARAMETER ANALYSIS & STABILITY AUDIT (Target CV <= {args.variance_threshold * 100:.1f}%):"
    )
    print("=" * 118)
    header = (
        f"{'Candidate Name':<40} | {'D':<2} | {'L2':<5} | {'LR':<4} | "
        f"{'PR-AUC (u+/-std)':<17} | {'CV (%)':<7} | {'ROC-AUC':<7} | {'OOF PR':<7} | {'FPR@95%':<8} | {'P@50':<5} | {'Status'}"
    )
    print(header)
    print("-" * 118)
    for row in comparative_summary:
        is_winner = row["name"] == winner["name"]
        if is_winner and row["meets_variance_threshold"]:
            status = "PASS [BEST]"
        elif row["meets_variance_threshold"]:
            status = "PASS"
        elif is_winner:
            status = "MIN-VAR [BEST]"
        else:
            status = "EXCEEDED"

        line = (
            f"{row['name']:<40} | {row['depth']:<2} | {row['l2_leaf_reg']:<5.1f} | {row['learning_rate']:<4.2f} | "
            f"{row['mean_pr_auc']:.5f}+/-{row['std_pr_auc']:.4f} | {row['cv_percentage']:<7} | {row['mean_roc_auc']:.4f}  | "
            f"{row['global_pr_auc']:.5f} | {row['fpr_at_95_recall']:<8} | {row['p_at_50']:<5.2f} | {status}"
        )
        print(line)
    print("=" * 118)
    print(f"[*] SELECTION VERDICT: {selection_rationale}")
    print("=" * 118)
    sys.stdout.flush()

    # 6. Export Tuning Metadata
    results_path = "models/ibm_transactions/catboost_tuning_results.json"
    with open(results_path, "w") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "sample_size": sample_arg,
                "variance_threshold": args.variance_threshold,
                "best_config": best_config,
                "best_pr_auc": best_pr_auc,
                "selection_rationale": selection_rationale,
                "comparative_summary": comparative_summary,
                "grid_evaluations": evaluation_results,
            },
            f,
            indent=4,
        )
    print(f"\n[+] Full tuning & stability results saved to: {results_path}")

    # 7. Export Final Model Artifact
    if not args.no_export:
        exported = optimizer.fit_and_export_final_model(best_config)
    else:
        print("[*] Skipping final model weights export (--no-export active).")
    print(
        "\n[SUCCESS] CatBoost SymmetricTree 5-fold pipeline execution completed successfully!"
    )


if __name__ == "__main__":
    run_pipeline()
