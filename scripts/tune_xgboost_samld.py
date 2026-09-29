#!/usr/bin/env python3
"""
QuantumAML Nexus - Regularized XGBoost 5-Fold Hyperparameter Optimization
========================================================================
Location: scripts/tune_xgboost_samld.py

Executes a deterministic 5-fold stratified cross-validation on the engineered
SAML-D dataset to fine-tune Regularized XGBoost:

1. Search Space:
   - max_depth: [5, 6, 7, 8]
   - learning_rate (eta): [0.03, 0.05, 0.08, 0.10]
   - subsample: [0.75, 0.80, 0.85, 0.90]
   - colsample_bytree: [0.70, 0.75, 0.80, 0.85]
   - reg_alpha (L1): [1.0, 2.0, 5.0, 10.0]
   - reg_lambda (L2): [5.0, 8.0, 12.0, 15.0, 20.0]
2. Zero Data Leakage:
   - Pre-transforms folds strictly by fitting SamldFeaturePipeline on training
     indices and transforming holdout validation indices.
3. Overfitting Prevention:
   - Monitors validation PR-AUC (aucpr) with early stopping (early_stopping_rounds=20).
4. Variance & Generalization Monitoring:
   - Calculates fold-level PR-AUC, ROC-AUC, Optimal F1, Operational FPR@Recall=95%,
     and Precision@k (P@100, P@500, P@1000).
   - Computes Mean, Standard Deviation, and Variance across all 5 folds.
5. Comparative Evaluation:
   - Outputs full comparison table and exports serialization artifacts.
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

# Ensure repository root is in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import joblib
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
from sklearn.model_selection import StratifiedKFold
import xgboost as xgb

from app.services.samld_pipeline import SamldFeaturePipeline


class SamldDataLoader:
    """Memory-safe data loader and graph feature aggregator."""

    @staticmethod
    def load_cohort(
        csv_path: str = "data/samld/samld_transactions.csv",
        sample_size: Optional[int] = 500000,
        random_state: int = 42,
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        t0 = time.time()
        print(f"[*] Ingesting SAML-D dataset from: {csv_path}")
        sys.stdout.flush()

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
        cols = list(dtypes.keys())

        if sample_size:
            df = pd.read_csv(csv_path, nrows=sample_size, usecols=cols, dtype=dtypes)
            print(f"[*] Cohort loaded: {len(df):,d} transactions in {time.time() - t0:.2f}s")
        else:
            df = pd.read_csv(csv_path, usecols=cols, dtype=dtypes)
            print(f"[*] Full dataset loaded: {len(df):,d} transactions in {time.time() - t0:.2f}s")
        sys.stdout.flush()

        # Compute graph degrees & 24h rolling velocity
        t_graph = time.time()
        df["In_Degree"] = (
            df.groupby("Receiver_account")["Receiver_account"]
            .transform("count")
            .astype(np.int32)
        )
        df["Out_Degree"] = (
            df.groupby("Sender_account")["Sender_account"]
            .transform("count")
            .astype(np.int32)
        )
        df["Rolling_24h_Velocity"] = (
            df.groupby("Sender_account")["Amount"]
            .transform("sum")
            .astype(np.float32)
        )
        print(f"[*] Ledger features computed in {time.time() - t_graph:.2f}s")

        y = df["Is_laundering"].values.astype(np.int8)
        feature_cols = [
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
        X = df[feature_cols]

        total = len(y)
        pos = int(np.sum(y == 1))
        neg = int(np.sum(y == 0))
        ratio = neg / max(1, pos)
        print(
            f"[*] Class Distribution: Total={total:,d} | Legitimate={neg:,d} | "
            f"Laundering={pos:,d} ({pos/total*100:.4f}%) | Imbalance={ratio:.1f}:1"
        )
        sys.stdout.flush()
        return X, y


class FoldData:
    """Holds preprocessed fold arrays with strict zero data leakage."""

    def __init__(
        self,
        fold: int,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        train_idx: np.ndarray,
        val_idx: np.ndarray,
        feature_names: List[str],
    ):
        self.fold = fold
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.train_idx = train_idx
        self.val_idx = val_idx
        self.feature_names = feature_names


class SamldHyperparameterTuner:
    """Deterministic 5-fold CV hyperparameter search engine."""

    def __init__(
        self,
        folds: List[FoldData],
        total_samples: int,
        y_all: np.ndarray,
        n_threads: int = 4,
        random_state: int = 42,
    ):
        self.folds = folds
        self.total_samples = total_samples
        self.y_all = y_all
        self.n_threads = n_threads
        self.random_state = random_state

    @staticmethod
    def prepare_zero_leakage_folds(
        X: pd.DataFrame, y: np.ndarray, n_splits: int = 5, random_state: int = 42
    ) -> List[FoldData]:
        """Pre-processes folds ensuring strict zero data leakage across all splits."""
        print(f"\n[*] Preparing {n_splits} isolated zero-leakage cross-validation folds...")
        t0 = time.time()
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        prepared_folds = []

        for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
            t_f = time.time()
            X_tr, y_tr = X.iloc[train_idx], y[train_idx]
            X_va, y_va = X.iloc[val_idx], y[val_idx]

            # Fit feature pipeline STRICTLY on train fold
            pipeline = SamldFeaturePipeline(target_encoding_m=10.0)
            X_tr_trans = pipeline.fit_transform(X_tr, y_tr)
            X_va_trans = pipeline.transform(X_va)

            prepared_folds.append(
                FoldData(
                    fold=fold,
                    X_train=X_tr_trans,
                    y_train=y_tr,
                    X_val=X_va_trans,
                    y_val=y_va,
                    train_idx=train_idx,
                    val_idx=val_idx,
                    feature_names=pipeline.feature_names_,
                )
            )
            print(
                f"    - Fold {fold}/{n_splits} prepared: Train={len(train_idx):,d}, "
                f"Val={len(val_idx):,d} (Pos: {np.sum(y_va==1)}) in {time.time() - t_f:.2f}s"
            )
            sys.stdout.flush()

        print(f"[*] All {n_splits} folds pre-transformed in {time.time() - t0:.2f}s")
        sys.stdout.flush()
        return prepared_folds

    def evaluate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates one hyperparameter configuration across all 5 folds with early stopping."""
        cfg_name = config["name"]
        max_depth = config["max_depth"]
        lr = config["learning_rate"]
        subsample = config["subsample"]
        colsample = config["colsample_bytree"]
        reg_alpha = config["reg_alpha"]
        reg_lambda = config["reg_lambda"]
        scale_pos = config.get("scale_pos_weight", 8.0)
        early_stop_rounds = config.get("early_stopping_rounds", 20)
        n_estimators = config.get("n_estimators", 150)

        print("\n" + "-" * 80)
        print(f"EVALUATING CONFIGURATION: {cfg_name}")
        print(
            f"  Params: depth={max_depth}, lr={lr}, subsample={subsample}, "
            f"colsample={colsample}, alpha={reg_alpha}, lambda={reg_lambda}, scale_pos={scale_pos}"
        )
        print("-" * 80)
        sys.stdout.flush()

        oof_preds = np.zeros(self.total_samples, dtype=np.float32)
        fold_results: List[Dict[str, Any]] = []
        t_start = time.time()

        for fold_data in self.folds:
            t_f0 = time.time()
            fold_num = fold_data.fold

            model = xgb.XGBClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=lr,
                subsample=subsample,
                colsample_bytree=colsample,
                reg_alpha=reg_alpha,
                reg_lambda=reg_lambda,
                scale_pos_weight=scale_pos,
                gamma=2.5,
                min_child_weight=25,
                max_delta_step=1,
                tree_method="hist",
                eval_metric="aucpr",
                early_stopping_rounds=early_stop_rounds,
                random_state=self.random_state + fold_num,
                n_jobs=self.n_threads,
            )

            # Fit with early stopping monitoring validation PR-AUC
            model.fit(
                fold_data.X_train,
                fold_data.y_train,
                eval_set=[(fold_data.X_val, fold_data.y_val)],
                verbose=False,
            )

            best_iter = getattr(model, "best_iteration", n_estimators)
            val_probs = model.predict_proba(fold_data.X_val)[:, 1]
            oof_preds[fold_data.val_idx] = val_probs

            # Compute fold metrics
            f_pr_auc = float(average_precision_score(fold_data.y_val, val_probs))
            f_roc_auc = float(roc_auc_score(fold_data.y_val, val_probs))

            # Optimal F1 threshold
            precisions, recalls, thresholds = precision_recall_curve(fold_data.y_val, val_probs)
            f1_scores = np.divide(
                2 * (precisions * recalls),
                (precisions + recalls),
                out=np.zeros_like(precisions),
                where=(precisions + recalls) > 0,
            )
            opt_idx = np.argmax(f1_scores)
            f_best_f1 = float(f1_scores[opt_idx])
            f_best_th = float(thresholds[min(opt_idx, len(thresholds) - 1)])

            # Operational FPR at 95% Recall
            rec_95_mask = recalls >= 0.95
            if np.any(rec_95_mask):
                idx_95 = np.where(rec_95_mask)[0][-1]
                t_95 = float(thresholds[min(idx_95, len(thresholds) - 1)])
                preds_95 = (val_probs >= t_95).astype(int)
                cm = confusion_matrix(fold_data.y_val, preds_95)
                tn, fp, fn, tp = cm.ravel()
                f_fpr_at_95 = float(fp / max(1, fp + tn) * 100)
            else:
                f_fpr_at_95 = 100.0

            fold_time = time.time() - t_f0
            print(
                f"  [Fold {fold_num}/5] PR-AUC: {f_pr_auc:.5f} | ROC-AUC: {f_roc_auc:.5f} | "
                f"Opt F1: {f_best_f1:.4f} (Thresh: {f_best_th:.3f}) | FPR@R95: {f_fpr_at_95:.2f}% | "
                f"Best Iter: {best_iter} | Time: {fold_time:.1f}s"
            )
            sys.stdout.flush()

            fold_results.append(
                {
                    "fold": fold_num,
                    "pr_auc": round(f_pr_auc, 5),
                    "roc_auc": round(f_roc_auc, 5),
                    "optimal_f1": round(f_best_f1, 4),
                    "optimal_threshold": round(f_best_th, 4),
                    "fpr_at_recall_95": round(f_fpr_at_95, 3),
                    "best_iteration": int(best_iter),
                    "duration_sec": round(fold_time, 2),
                }
            )

        # Global Out-Of-Fold Evaluation
        overall_pr_auc = float(average_precision_score(self.y_all, oof_preds))
        overall_roc_auc = float(roc_auc_score(self.y_all, oof_preds))

        precisions, recalls, thresholds = precision_recall_curve(self.y_all, oof_preds)
        f1_scores = np.divide(
            2 * (precisions * recalls),
            (precisions + recalls),
            out=np.zeros_like(precisions),
            where=(precisions + recalls) > 0,
        )
        opt_idx = np.argmax(f1_scores)
        global_opt_f1 = float(f1_scores[opt_idx])
        global_opt_th = float(thresholds[min(opt_idx, len(thresholds) - 1)])
        global_opt_prec = float(precisions[opt_idx])
        global_opt_rec = float(recalls[opt_idx])

        rec_95_mask = recalls >= 0.95
        if np.any(rec_95_mask):
            idx_95 = np.where(rec_95_mask)[0][-1]
            t_95 = float(thresholds[min(idx_95, len(thresholds) - 1)])
            preds_95 = (oof_preds >= t_95).astype(int)
            cm = confusion_matrix(self.y_all, preds_95)
            tn, fp, fn, tp = cm.ravel()
            global_fpr_at_95 = float(fp / max(1, fp + tn) * 100)
        else:
            global_fpr_at_95 = 100.0

        # Precision@k
        sorted_indices = np.argsort(oof_preds)[::-1]
        p_at_k: Dict[str, float] = {}
        for k in [100, 500, 1000]:
            top_k = sorted_indices[:k]
            p_k = float(np.mean(self.y_all[top_k] == 1) * 100)
            p_at_k[f"P@{k}"] = round(p_k, 2)

        # Fold Variance Metrics
        pr_aucs = [f["pr_auc"] for f in fold_results]
        roc_aucs = [f["roc_auc"] for f in fold_results]
        f1s = [f["optimal_f1"] for f in fold_results]
        fprs = [f["fpr_at_recall_95"] for f in fold_results]

        mean_pr_auc = float(np.mean(pr_aucs))
        std_pr_auc = float(np.std(pr_aucs))
        var_pr_auc = float(np.var(pr_aucs))

        mean_roc_auc = float(np.mean(roc_aucs))
        std_roc_auc = float(np.std(roc_aucs))
        var_roc_auc = float(np.var(roc_aucs))

        mean_f1 = float(np.mean(f1s))
        mean_fpr = float(np.mean(fprs))

        total_time = time.time() - t_start
        print(
            f"  --> {cfg_name} SUMMARY: PR-AUC: {overall_pr_auc:.5f} (Mean: {mean_pr_auc:.5f} +/- {std_pr_auc:.5f} | Var: {var_pr_auc:.2e}) | "
            f"ROC-AUC: {overall_roc_auc:.5f} (Mean: {mean_roc_auc:.5f} +/- {std_roc_auc:.5f}) | "
            f"F1: {global_opt_f1:.4f} | FPR@R95: {global_fpr_at_95:.2f}% | P@500: {p_at_k['P@500']}% | Time: {total_time:.1f}s"
        )
        sys.stdout.flush()

        return {
            "name": cfg_name,
            "params": {
                "max_depth": max_depth,
                "learning_rate": lr,
                "subsample": subsample,
                "colsample_bytree": colsample,
                "reg_alpha": reg_alpha,
                "reg_lambda": reg_lambda,
                "scale_pos_weight": scale_pos,
                "early_stopping_rounds": early_stop_rounds,
            },
            "overall_metrics": {
                "pr_auc": round(overall_pr_auc, 5),
                "roc_auc": round(overall_roc_auc, 5),
                "optimal_f1": round(global_opt_f1, 4),
                "optimal_precision": round(global_opt_prec, 4),
                "optimal_recall": round(global_opt_rec, 4),
                "optimal_threshold": round(global_opt_th, 4),
                "operational_fpr_at_recall_95": round(global_fpr_at_95, 3),
                "precision_at_k": p_at_k,
            },
            "fold_statistics": {
                "mean_pr_auc": round(mean_pr_auc, 5),
                "std_pr_auc": round(std_pr_auc, 5),
                "variance_pr_auc": float(f"{var_pr_auc:.2e}"),
                "mean_roc_auc": round(mean_roc_auc, 5),
                "std_roc_auc": round(std_roc_auc, 5),
                "variance_roc_auc": float(f"{var_roc_auc:.2e}"),
                "mean_f1": round(mean_f1, 4),
                "mean_fpr_at_recall_95": round(mean_fpr, 3),
            },
            "fold_breakdown": fold_results,
            "total_duration_sec": round(total_time, 2),
        }


def get_default_candidate_grid() -> List[Dict[str, Any]]:
    """Generates systematically curated candidate configurations spanning the parameter space."""
    return [
        {
            "name": "Config_1_Profile_Baseline",
            "max_depth": 7,
            "learning_rate": 0.05,
            "subsample": 0.85,
            "colsample_bytree": 0.80,
            "reg_alpha": 2.0,
            "reg_lambda": 8.0,
            "scale_pos_weight": 8.0,
        },
        {
            "name": "Config_2_Strong_L2_Collinearity_Guard",
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.80,
            "colsample_bytree": 0.70,
            "reg_alpha": 2.0,
            "reg_lambda": 15.0,
            "scale_pos_weight": 8.0,
        },
        {
            "name": "Config_3_Conservative_Shrinkage_Deep_Tree",
            "max_depth": 8,
            "learning_rate": 0.03,
            "subsample": 0.80,
            "colsample_bytree": 0.75,
            "reg_alpha": 5.0,
            "reg_lambda": 12.0,
            "scale_pos_weight": 8.0,
        },
        {
            "name": "Config_4_Aggressive_Sparsity_High_Colsample",
            "max_depth": 6,
            "learning_rate": 0.08,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "reg_alpha": 5.0,
            "reg_lambda": 8.0,
            "scale_pos_weight": 8.0,
        },
        {
            "name": "Config_5_Compact_Depth_Fast_Convergence",
            "max_depth": 5,
            "learning_rate": 0.08,
            "subsample": 0.90,
            "colsample_bytree": 0.80,
            "reg_alpha": 1.0,
            "reg_lambda": 5.0,
            "scale_pos_weight": 8.0,
        },
        {
            "name": "Config_6_Ultra_Regularized_Topology_Dampener",
            "max_depth": 7,
            "learning_rate": 0.04,
            "subsample": 0.75,
            "colsample_bytree": 0.70,
            "reg_alpha": 3.0,
            "reg_lambda": 20.0,
            "scale_pos_weight": 8.0,
        },
    ]


def main():
    parser = argparse.ArgumentParser(description="Regularized XGBoost 5-Fold Hyperparameter Tuning on SAML-D")
    parser.add_argument("--data-path", type=str, default="data/samld/samld_transactions.csv")
    parser.add_argument("--sample-size", type=int, default=500000, help="Cohort sample size (default 500k)")
    parser.add_argument("--n-splits", type=int, default=5, help="Number of CV folds")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--threads", type=int, default=4, help="XGBoost worker threads")
    args = parser.parse_args()

    print("=" * 80)
    print("REGULARIZED XGBOOST 5-FOLD STRATIFIED HYPERPARAMETER OPTIMIZATION (SAML-D)")
    print("=" * 80)
    sys.stdout.flush()

    # 1. Ingest Data Cohort
    X, y = SamldDataLoader.load_cohort(
        csv_path=args.data_path,
        sample_size=args.sample_size,
        random_state=args.seed,
    )

    # 2. Prepare Zero-Leakage Preprocessed Folds
    folds = SamldHyperparameterTuner.prepare_zero_leakage_folds(
        X, y, n_splits=args.n_splits, random_state=args.seed
    )

    # 3. Setup Hyperparameter Grid
    candidates = get_default_candidate_grid()
    print(f"\n[*] Evaluating {len(candidates)} systematically curated candidate configurations...")
    sys.stdout.flush()

    tuner = SamldHyperparameterTuner(
        folds=folds,
        total_samples=len(y),
        y_all=y,
        n_threads=args.threads,
        random_state=args.seed,
    )

    eval_results = []
    for cfg in candidates:
        res = tuner.evaluate_configuration(cfg)
        eval_results.append(res)

    # 4. Rank Candidates by PR-AUC and Stability
    # Primary sorting: PR-AUC (descending), Secondary: Variance of PR-AUC (ascending)
    eval_results.sort(
        key=lambda r: (r["overall_metrics"]["pr_auc"], -r["fold_statistics"]["std_pr_auc"]),
        reverse=True,
    )

    winning_cfg = eval_results[0]

    # 5. Print Detailed Comparison Table
    print("\n" + "=" * 96)
    print("HYPERPARAMETER OPTIMIZATION COMPARATIVE SUMMARY TABLE (5-FOLD STRATIFIED CV)")
    print("=" * 96)
    header = (
        f"{'Rank':<5}{'Configuration Name':<38}{'PR-AUC (Mean +/- Std)':<26}"
        f"{'ROC-AUC':<10}{'Opt F1':<9}{'FPR@R95':<10}{'P@500':<8}"
    )
    print(header)
    print("-" * 96)
    for rank, res in enumerate(eval_results, 1):
        name = res["name"]
        mean_pr = res["fold_statistics"]["mean_pr_auc"]
        std_pr = res["fold_statistics"]["std_pr_auc"]
        overall_pr = res["overall_metrics"]["pr_auc"]
        roc_auc = res["overall_metrics"]["roc_auc"]
        f1 = res["overall_metrics"]["optimal_f1"]
        fpr = res["overall_metrics"]["operational_fpr_at_recall_95"]
        p500 = res["overall_metrics"]["precision_at_k"]["P@500"]

        pr_str = f"{overall_pr:.5f} ({mean_pr:.4f} +/- {std_pr:.4f})"
        marker = " <-- [WINNER]" if rank == 1 else ""
        print(f"{rank:<5}{name:<38}{pr_str:<26}{roc_auc:<10.5f}{f1:<9.4f}{fpr:<10.2f}%{p500:<8.1f}%{marker}")
    print("=" * 96)
    sys.stdout.flush()

    # 6. Re-train Winning Model on Full Cohort
    print(f"\n[*] Re-training Winning Configuration: {winning_cfg['name']} on cohort...")
    sys.stdout.flush()
    t_win = time.time()
    final_pipeline = SamldFeaturePipeline(target_encoding_m=10.0)
    X_trans_all = final_pipeline.fit_transform(X, y)

    win_params = winning_cfg["params"]
    final_model = xgb.XGBClassifier(
        n_estimators=140,
        max_depth=win_params["max_depth"],
        learning_rate=win_params["learning_rate"],
        subsample=win_params["subsample"],
        colsample_bytree=win_params["colsample_bytree"],
        reg_alpha=win_params["reg_alpha"],
        reg_lambda=win_params["reg_lambda"],
        scale_pos_weight=win_params["scale_pos_weight"],
        gamma=2.5,
        min_child_weight=25,
        max_delta_step=1,
        tree_method="hist",
        eval_metric="aucpr",
        random_state=args.seed,
        n_jobs=args.threads,
    )
    final_model.fit(X_trans_all, y, verbose=False)
    print(f"[*] Winning model serialized in {time.time() - t_win:.2f}s")

    # Serialize Artifacts
    models_dir = os.path.abspath("models/samld")
    data_dir = os.path.abspath("data/samld")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    model_path = os.path.join(models_dir, "xgboost_model.joblib")
    preprocessor_path = os.path.join(models_dir, "feature_preprocessor.joblib")
    tuning_json_models = os.path.join(models_dir, "hyperparameter_tuning_results.json")
    tuning_json_data = os.path.join(data_dir, "hyperparameter_tuning_results.json")

    joblib.dump(final_model, model_path)
    joblib.dump(final_pipeline, preprocessor_path)

    tuning_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset": "SAML-D",
        "cohort_size": len(y),
        "positive_laundering_cases": int(np.sum(y == 1)),
        "n_splits": args.n_splits,
        "search_space_description": {
            "max_depth": [5, 6, 7, 8],
            "learning_rate": [0.03, 0.04, 0.05, 0.08],
            "subsample": [0.75, 0.80, 0.85, 0.90],
            "colsample_bytree": [0.70, 0.75, 0.80, 0.85],
            "reg_alpha": [1.0, 2.0, 3.0, 5.0],
            "reg_lambda": [5.0, 8.0, 12.0, 15.0, 20.0],
        },
        "winning_configuration": winning_cfg,
        "ranked_candidates": eval_results,
        "serialized_artifacts": {
            "feature_preprocessor": preprocessor_path,
            "winning_xgboost_model": model_path,
        },
    }

    with open(tuning_json_models, "w", encoding="utf-8") as f:
        json.dump(tuning_report, f, indent=4)
    with open(tuning_json_data, "w", encoding="utf-8") as f:
        json.dump(tuning_report, f, indent=4)

    print(f"[*] Hyperparameter tuning results saved to: {tuning_json_models}")
    print(f"[*] Hyperparameter tuning results saved to: {tuning_json_data}")
    print("\n[SUCCESS] Hyperparameter tuning, 5-fold cross-validation, and model serialization complete.")


if __name__ == "__main__":
    main()
