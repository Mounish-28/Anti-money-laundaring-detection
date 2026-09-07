import json
import os

import joblib
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from utils import (
    PrefitIsotonicCalibrator,
    cleanup_memory,
    optimize_threshold_phase_1_9,
    set_seed,
)


def run_pipeline():
    print("=== DATASET 3: ELLIPTIC BITCOIN (TOPOLOGICAL XGBOOST) - PHASE 1.9 ===")
    set_seed(42)

    features_path = "../elliptic_bitcoin_dataset/elliptic_txs_features.csv"
    classes_path = "../elliptic_bitcoin_dataset/elliptic_txs_classes.csv"
    if not os.path.exists(features_path):
        features_path = "elliptic_bitcoin_dataset/elliptic_txs_features.csv"
        classes_path = "elliptic_bitcoin_dataset/elliptic_txs_classes.csv"

    print("Loading Elliptic data...")
    features_df = pd.read_csv(features_path, header=None)
    classes_df = pd.read_csv(classes_path)

    # 167 columns: txId, timestep, feat_0 .. feat_164
    cols = ["txId", "timestep"] + [f"feat_{i}" for i in range(165)]
    features_df.columns = cols

    # Merge classes and filter out unknown nodes
    df = features_df.merge(classes_df, on="txId")
    df = df[df["class"] != "unknown"].copy()

    # Explicit Target Check: 1 = Illicit, 0 = Licit
    # In original dataset, '1' = illicit, '2' = licit
    df["class"] = df["class"].map({"1": 1, "2": 0}).astype(int)
    print("Target distribution in filtered Elliptic:")
    print(df["class"].value_counts())

    # 166 features: timestep (1) + local & aggregate features (165)
    feature_cols = ["timestep"] + [f"feat_{i}" for i in range(165)]
    X = df[feature_cols]
    y = df["class"]

    # Strict Chronological Splitting
    print("Applying chronological split: Train (1-34), Val (35-41), Test (42-49)...")
    train_mask = df["timestep"] <= 34
    val_mask = (df["timestep"] > 34) & (df["timestep"] <= 41)
    test_mask = df["timestep"] > 41

    X_train, y_train = X[train_mask].copy(), y[train_mask].values
    X_val, y_val = X[val_mask].copy(), y[val_mask].values
    X_test, y_test = X[test_mask].copy(), y[test_mask].values

    print(f"Train size: {len(X_train)} (illicit: {(y_train == 1).sum()})")
    print(f"Val size: {len(X_val)} (illicit: {(y_val == 1).sum()})")
    print(f"Test size: {len(X_test)} (illicit: {(y_test == 1).sum()})")

    del df, features_df, classes_df, X, y
    cleanup_memory()

    # Phase 1.9 Hyperparameters
    print(
        "Training XGBoost on 166 topological features (scale_pos_weight=6.0, max_depth=7, lr=0.035)..."
    )
    model = xgb.XGBClassifier(
        objective="binary:logistic",
        scale_pos_weight=6.0,
        max_depth=7,
        learning_rate=0.035,
        tree_method="hist",
        subsample=0.85,
        colsample_bytree=0.80,
        n_estimators=1800,
        early_stopping_rounds=50,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=100)

    # Isotonic Probability Calibration on Validation Set
    print("Fitting PrefitIsotonicCalibrator on validation split...")
    raw_val_probs = model.predict_proba(X_val)[:, 1]
    calibrator = PrefitIsotonicCalibrator()
    calibrator.fit(raw_val_probs, y_val)
    cal_val_probs = calibrator.predict_proba(raw_val_probs)

    # Tune Threshold on Validation via Phase 1.9 Pareto Sweeper on both spaces
    print("Tuning threshold on validation set (Phase 1.9 Dynamic Pareto sweep)...")
    best_t_cal = optimize_threshold_phase_1_9(
        y_val,
        cal_val_probs,
        min_acc=0.970,
        baseline_rec=0.47,
        baseline_prec=0.85,
        t_min=0.10,
        t_max=0.90,
        step=0.002,
    )
    best_t_raw = optimize_threshold_phase_1_9(
        y_val,
        raw_val_probs,
        min_acc=0.970,
        baseline_rec=0.47,
        baseline_prec=0.85,
        t_min=0.50,
        t_max=0.95,
        step=0.002,
    )

    preds_cal = (cal_val_probs >= best_t_cal).astype(int)
    f1_cal = f1_score(y_val, preds_cal, zero_division=0)
    prec_cal = precision_score(y_val, preds_cal, zero_division=0)

    preds_raw = (raw_val_probs >= best_t_raw).astype(int)
    f1_raw = f1_score(y_val, preds_raw, zero_division=0)
    prec_raw = precision_score(y_val, preds_raw, zero_division=0)

    print(f"Calibrated Val: F1={f1_cal:.4f}, Prec={prec_cal:.4f} at T={best_t_cal:.4f}")
    print(f"Raw Val:        F1={f1_raw:.4f}, Prec={prec_raw:.4f} at T={best_t_raw:.4f}")

    raw_test_probs = model.predict_proba(X_test)[:, 1]
    if (f1_cal >= f1_raw and prec_cal >= 0.70) or prec_raw < 0.70:
        print("Selected Calibrated probability space.")
        best_t = best_t_cal
        test_eval_probs = calibrator.predict_proba(raw_test_probs)
        arch_name = "Topological XGBoost + Isotonic Calibration"
    else:
        print("Selected Raw probability space to preserve peak Precision/F1 baseline.")
        best_t = best_t_raw
        test_eval_probs = raw_test_probs
        arch_name = "Topological XGBoost + Dual Pareto Search"

    print(f"Optimal Threshold T*: {best_t:.4f}")

    # Evaluate on untouched Test set
    print("Evaluating on untouched Test set...")
    test_preds = (test_eval_probs >= best_t).astype(int)

    acc = accuracy_score(y_test, test_preds)
    prec = precision_score(y_test, test_preds, zero_division=0)
    rec = recall_score(y_test, test_preds, zero_division=0)
    f1 = f1_score(y_test, test_preds, zero_division=0)
    roc_auc = roc_auc_score(y_test, test_eval_probs)
    pr_auc = average_precision_score(y_test, test_eval_probs)

    metrics = {
        "Dataset": "Elliptic Bitcoin",
        "Architecture": arch_name,
        "Best_Threshold": float(best_t),
        "Test_Accuracy": float(acc),
        "Precision": float(prec),
        "Recall": float(rec),
        "F1_Score": float(f1),
        "PR_AUC": float(pr_auc),
        "ROC_AUC": float(roc_auc),
        "Target_Met": "YES"
        if (acc >= 0.97 and (rec >= 0.90 or f1 >= 0.85))
        else "PARTIAL",
    }

    print("Dataset 3 Phase 1.9 Test Results:")
    print(json.dumps(metrics, indent=4))

    out_model_dir = (
        "../models/Elliptic" if os.path.exists("../models") else "models/Elliptic"
    )
    out_exp_dir = (
        "../experiments/Elliptic"
        if os.path.exists("../experiments")
        else "experiments/Elliptic"
    )
    os.makedirs(out_model_dir, exist_ok=True)
    os.makedirs(out_exp_dir, exist_ok=True)

    joblib.dump(model, os.path.join(out_model_dir, "model_v5.joblib"))
    joblib.dump(calibrator, os.path.join(out_model_dir, "calibrator_v5.joblib"))
    with open(os.path.join(out_exp_dir, "metrics_v5.json"), "w") as f:
        json.dump(metrics, f, indent=4)

    print("Dataset 3 Phase 1.9 execution completed successfully.\n")
    cleanup_memory()


if __name__ == "__main__":
    run_pipeline()
