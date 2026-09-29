import json
import os

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from utils import (
    PrefitIsotonicCalibrator,
    cleanup_memory,
    optimize_threshold_phase_1_9,
    set_seed,
)


def run_pipeline():
    print("=== DATASET 1: IBM TRANSACTIONS (HI-Small) - PHASE 1.9 ===")
    set_seed(42)

    # Load data
    data_path = "../IBM anti-money/HI-Small_Trans.csv"
    if not os.path.exists(data_path):
        data_path = "IBM anti-money/HI-Small_Trans.csv"

    print("Loading data with memory-efficient categorical schema...")
    dtypes = {
        "Timestamp": "str",
        "From Bank": "int32",
        "Account": "category",
        "To Bank": "int32",
        "Account.1": "category",
        "Amount Received": "float32",
        "Receiving Currency": "category",
        "Amount Paid": "float32",
        "Payment Currency": "category",
        "Payment Format": "category",
        "Is Laundering": "int8",
    }
    df = pd.read_csv(data_path, dtype=dtypes)

    # Target verification
    target_col = "Is Laundering"
    print(f"Target distribution in {data_path}:")
    print(df[target_col].value_counts())
    assert set(df[target_col].unique()).issubset({0, 1}), "Target must be binary {0, 1}"

    # Extract temporal attributes with zero memory overhead
    if "Timestamp" in df.columns:
        print("Extracting temporal features...")
        df["hour"] = df["Timestamp"].str.slice(11, 13).astype(np.int8)
        unique_dates = df["Timestamp"].str.slice(0, 10).unique()
        date_map = {d: pd.to_datetime(d).dayofweek for d in unique_dates}
        df["dayofweek"] = df["Timestamp"].str.slice(0, 10).map(date_map).astype(np.int8)
        df.drop(columns=["Timestamp"], inplace=True)
        del unique_dates, date_map
        cleanup_memory()

    # Stratified index split (70 / 15 / 15)
    print("Performing stratified index split (70/15/15)...")
    indices = np.arange(len(df))
    y_all = df[target_col].values

    idx_temp, idx_test = train_test_split(
        indices, test_size=0.15, stratify=y_all, random_state=42
    )
    idx_train, idx_val = train_test_split(
        idx_temp, test_size=0.15 / 0.85, stratify=y_all[idx_temp], random_state=42
    )
    del idx_temp
    cleanup_memory()

    # Graph typology features strictly on Training split
    print("Computing Sender/Receiver graph typology features on Training split...")
    train_slice = df.iloc[idx_train]
    sender_counts = train_slice["Account"].value_counts()
    receiver_counts = train_slice["Account.1"].value_counts()
    sender_avg_amt = train_slice.groupby("Account", observed=False)[
        "Amount Paid"
    ].mean()
    global_avg_amt = float(train_slice["Amount Paid"].mean())
    del train_slice
    cleanup_memory()

    print("Mapping graph typology features onto dataframe...")
    df["Sender_Tx_Count"] = df["Account"].map(sender_counts).fillna(0).astype(np.int32)
    df["Receiver_Tx_Count"] = (
        df["Account.1"].map(receiver_counts).fillna(0).astype(np.int32)
    )
    avg_s = df["Account"].map(sender_avg_amt).fillna(global_avg_amt).astype(np.float32)
    df["Amount_vs_Sender_Avg"] = (df["Amount Paid"] / (avg_s + 1e-5)).astype(np.float32)
    df["Currency_Exchange"] = (
        df["Receiving Currency"].cat.codes != df["Payment Currency"].cat.codes
    ).astype(np.int8)
    del avg_s, sender_counts, receiver_counts, sender_avg_amt

    # Drop raw IDs
    df.drop(columns=["Account", "Account.1"], inplace=True)
    cleanup_memory()

    cat_features = [
        "From Bank",
        "To Bank",
        "Payment Format",
        "Receiving Currency",
        "Payment Currency",
    ]
    cat_features = [c for c in cat_features if c in df.columns]
    feature_cols = [c for c in df.columns if c != target_col]
    print(f"Engineered features ({len(feature_cols)}): {feature_cols}")

    # Extract splits
    X_train = df.iloc[idx_train][feature_cols]
    y_train = df.iloc[idx_train][target_col].values

    X_val = df.iloc[idx_val][feature_cols]
    y_val = df.iloc[idx_val][target_col].values

    X_test = df.iloc[idx_test][feature_cols]
    y_test = df.iloc[idx_test][target_col].values

    del df, idx_train, idx_val, idx_test, indices, y_all
    cleanup_memory()

    # Negative subsampling for training efficiency while preserving all positives
    pos_idx = np.where(y_train == 1)[0]
    neg_idx = np.where(y_train == 0)[0]
    max_neg = 600000
    if len(neg_idx) > max_neg:
        print(f"Subsampling negative training examples to {max_neg}...")
        np.random.seed(42)
        sampled_neg = np.random.choice(neg_idx, size=max_neg, replace=False)
        sub_idx = np.concatenate([pos_idx, sampled_neg])
        np.random.shuffle(sub_idx)
        X_train = X_train.iloc[sub_idx].copy()
        y_train = y_train[sub_idx]
        del pos_idx, neg_idx, sampled_neg, sub_idx
        cleanup_memory()

    print(f"Train shape: {X_train.shape} (pos: {(y_train == 1).sum()})")
    print(f"Val shape: {X_val.shape} (pos: {(y_val == 1).sum()})")
    print(f"Test shape: {X_test.shape} (pos: {(y_test == 1).sum()})")

    # CatBoost SymmetricTree Architecture
    print(
        "Initializing CatBoostClassifier (Phase 1.9 SymmetricTree depth=7, lr=0.06, SqrtBalanced)..."
    )
    model = CatBoostClassifier(
        iterations=2500,
        depth=7,
        learning_rate=0.06,
        auto_class_weights="SqrtBalanced",
        bootstrap_type="Bayesian",
        grow_policy="SymmetricTree",
        cat_features=cat_features,
        eval_metric="Logloss",
        early_stopping_rounds=60,
        random_seed=42,
        task_type="CPU",
        thread_count=4,
        verbose=100,
    )

    print("Training CatBoost...")
    model.fit(
        X_train, y_train, eval_set=(X_val, y_val), use_best_model=True, verbose=100
    )

    # Isotonic Probability Calibration on Validation Set
    print("Fitting PrefitIsotonicCalibrator on validation split...")
    raw_val_probs = model.predict_proba(X_val)[:, 1]
    calibrator = PrefitIsotonicCalibrator()
    calibrator.fit(raw_val_probs, y_val)
    cal_val_probs = calibrator.predict_proba(raw_val_probs)

    # Dynamic Pareto Threshold Sweep
    print("Tuning threshold via Phase 1.9 Dynamic Pareto Sweeper...")
    best_t_cal = optimize_threshold_phase_1_9(
        y_val,
        cal_val_probs,
        min_acc=0.998,
        baseline_rec=0.30,
        baseline_prec=0.82,
        t_min=0.05,
        t_max=0.95,
        step=0.002,
    )
    best_t_raw = optimize_threshold_phase_1_9(
        y_val,
        raw_val_probs,
        min_acc=0.998,
        baseline_rec=0.30,
        baseline_prec=0.82,
        t_min=0.70,
        t_max=0.99,
        step=0.002,
    )

    # Validation scores
    preds_cal = (cal_val_probs >= best_t_cal).astype(int)
    f1_cal = f1_score(y_val, preds_cal, zero_division=0)
    prec_cal = precision_score(y_val, preds_cal, zero_division=0)

    preds_raw = (raw_val_probs >= best_t_raw).astype(int)
    f1_raw = f1_score(y_val, preds_raw, zero_division=0)
    prec_raw = precision_score(y_val, preds_raw, zero_division=0)

    print(f"Calibrated Val: F1={f1_cal:.4f}, Prec={prec_cal:.4f} at T={best_t_cal:.4f}")
    print(f"Raw Val:        F1={f1_raw:.4f}, Prec={prec_raw:.4f} at T={best_t_raw:.4f}")

    raw_test_probs = model.predict_proba(X_test)[:, 1]
    if (f1_cal >= f1_raw and prec_cal >= 0.75) or prec_raw < 0.70:
        print("Selected Calibrated probability space.")
        best_t = best_t_cal
        cal_test_probs = calibrator.predict_proba(raw_test_probs)
        test_eval_probs = cal_test_probs
        arch_name = "CatBoost Lossguide + Isotonic Calibration"
    else:
        print("Selected Raw probability space to preserve peak Precision/F1 baseline.")
        best_t = best_t_raw
        test_eval_probs = raw_test_probs
        arch_name = "CatBoost Lossguide + Dual Pareto Search"

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
        "Dataset": "IBM Transactions",
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

    print("Dataset 1 Phase 1.9 Test Results:")
    print(json.dumps(metrics, indent=4))

    # Serialization
    out_model_dir = (
        "../models/IBM-AML" if os.path.exists("../models") else "models/IBM-AML"
    )
    out_exp_dir = (
        "../experiments/IBM-AML"
        if os.path.exists("../experiments")
        else "experiments/IBM-AML"
    )
    os.makedirs(out_model_dir, exist_ok=True)
    os.makedirs(out_exp_dir, exist_ok=True)

    model.save_model(os.path.join(out_model_dir, "model_v5.cbm"))
    joblib.dump(model, os.path.join(out_model_dir, "model_v5.joblib"))
    joblib.dump(calibrator, os.path.join(out_model_dir, "calibrator_v5.joblib"))
    with open(os.path.join(out_exp_dir, "metrics_v5.json"), "w") as f:
        json.dump(metrics, f, indent=4)

    print("Dataset 1 Phase 1.9 execution completed successfully.\n")
    cleanup_memory()


if __name__ == "__main__":
    run_pipeline()
