import json
import os

import joblib
import numpy as np
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
from sklearn.model_selection import train_test_split

from utils import (
    cleanup_memory,
    optimize_threshold_phase_1_9,
    set_seed,
)


def run_pipeline():
    print("=== DATASET 2: SAML-D (REGULARIZED XGBOOST) - PHASE 1.9 ===")
    set_seed(42)

    data_path = "../SAML-D/SAML-D.csv"
    if not os.path.exists(data_path):
        data_path = "SAML-D/SAML-D.csv"

    print("Loading data with optimized memory schema...")
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
    cols = list(dtypes.keys()) + ["Time"]
    df = pd.read_csv(data_path, usecols=cols, dtype=dtypes)

    # Fast vectorized minute_of_day extraction (0 - 1439)
    print("Extracting temporal features...")
    time_series = df["Time"].astype(str)
    hour = time_series.str.slice(0, 2).astype(np.int8)
    minute = time_series.str.slice(3, 5).astype(np.int8)
    df["minute_of_day"] = (hour.astype(np.int16) * 60 + minute.astype(np.int16)).astype(
        np.int16
    )
    df.drop(columns=["Time"], inplace=True)
    del time_series, hour, minute
    cleanup_memory()

    target_col = "Is_laundering"
    print("Target distribution:")
    print(df[target_col].value_counts())
    assert set(df[target_col].unique()).issubset({0, 1}), "Target must be binary {0, 1}"

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

    # Feature Engineering (Graph proxies strictly on Training split)
    print("Engineering Fan-In/Fan-Out and Cross-Border features on Training split...")
    df["cross_border"] = (
        df["Sender_bank_location"].cat.codes != df["Receiver_bank_location"].cat.codes
    ).astype(np.int8)
    df["currency_exchange"] = (
        df["Payment_currency"].cat.codes != df["Received_currency"].cat.codes
    ).astype(np.int8)

    train_slice = df.iloc[idx_train]
    s_out_degree = (
        train_slice.groupby("Sender_account", observed=False)["Receiver_account"]
        .nunique()
        .to_dict()
    )
    s_tx_count = train_slice["Sender_account"].value_counts().to_dict()
    s_avg_amount = (
        train_slice.groupby("Sender_account", observed=False)["Amount"].mean().to_dict()
    )
    global_s_amount = float(train_slice["Amount"].mean())

    r_in_degree = (
        train_slice.groupby("Receiver_account", observed=False)["Sender_account"]
        .nunique()
        .to_dict()
    )
    r_tx_count = train_slice["Receiver_account"].value_counts().to_dict()
    del train_slice
    cleanup_memory()

    print("Mapping topology features to dataframe...")
    df["sender_out_degree"] = (
        df["Sender_account"].map(s_out_degree).fillna(0).astype(np.int32)
    )
    df["sender_tx_count"] = (
        df["Sender_account"].map(s_tx_count).fillna(0).astype(np.int32)
    )
    df["receiver_in_degree"] = (
        df["Receiver_account"].map(r_in_degree).fillna(0).astype(np.int32)
    )
    df["receiver_tx_count"] = (
        df["Receiver_account"].map(r_tx_count).fillna(0).astype(np.int32)
    )

    df["fan_in_ratio"] = (
        df["receiver_in_degree"] / (df["receiver_tx_count"] + 1.0)
    ).astype(np.float32)
    df["fan_out_ratio"] = (
        df["sender_out_degree"] / (df["sender_tx_count"] + 1.0)
    ).astype(np.float32)

    s_avg = df["Sender_account"].map(s_avg_amount).fillna(global_s_amount)
    df["amount_vs_sender_avg"] = (df["Amount"] / (s_avg + 1e-5)).astype(np.float32)
    del s_avg, s_out_degree, s_tx_count, s_avg_amount, r_in_degree, r_tx_count

    # Drop raw account identifiers
    df.drop(columns=["Sender_account", "Receiver_account"], inplace=True)
    cleanup_memory()

    feature_cols = [c for c in df.columns if c != target_col]
    print(f"Engineered features ({len(feature_cols)}): {feature_cols}")

    # Extract Train, Val, Test sets
    print("Extracting train, val, and test splits...")
    X_train = df.iloc[idx_train][feature_cols]
    y_train = df.iloc[idx_train][target_col].values

    X_val = df.iloc[idx_val][feature_cols]
    y_val = df.iloc[idx_val][target_col].values

    X_test = df.iloc[idx_test][feature_cols]
    y_test = df.iloc[idx_test][target_col].values

    del df, idx_train, idx_val, idx_test, indices, y_all
    cleanup_memory()

    # Negative subsampling for training efficiency
    pos_idx = np.where(y_train == 1)[0]
    neg_idx = np.where(y_train == 0)[0]
    max_neg = 1500000
    if len(neg_idx) > max_neg:
        print(
            f"Subsampling negative training examples to {max_neg} for bounded training speed..."
        )
        np.random.seed(42)
        sampled_neg = np.random.choice(neg_idx, size=max_neg, replace=False)
        sub_idx = np.concatenate([pos_idx, sampled_neg])
        np.random.shuffle(sub_idx)
        X_train = X_train.iloc[sub_idx].copy()
        y_train = y_train[sub_idx]
        del pos_idx, neg_idx, sampled_neg, sub_idx
        cleanup_memory()

    print(f"Final Train shape: {X_train.shape} (pos: {(y_train == 1).sum()})")
    print(f"Validation shape: {X_val.shape} (pos: {(y_val == 1).sum()})")
    print(f"Test shape: {X_test.shape} (pos: {(y_test == 1).sum()})")

    # Phase 1.9 Regularized XGBoost Hyperparameters
    print(
        "Training Regularized XGBoost with false-alarm pruning (scale_pos_weight=8.0, min_child_weight=25, gamma=3.0)..."
    )
    model = xgb.XGBClassifier(
        objective="binary:logistic",
        scale_pos_weight=8.0,
        max_delta_step=1,
        max_depth=8,
        learning_rate=0.025,
        min_child_weight=25,
        gamma=3.0,
        tree_method="hist",
        subsample=0.80,
        colsample_bytree=0.75,
        n_estimators=2000,
        early_stopping_rounds=50,
        enable_categorical=True,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=50)

    # Tune Threshold on Validation with Phase 1.9 Dynamic Pareto Sweeper
    print("Tuning threshold on validation set (Phase 1.9 Dynamic Pareto sweep)...")
    val_probs = model.predict_proba(X_val)[:, 1]
    best_t = optimize_threshold_phase_1_9(
        y_val, val_probs, min_acc=0.970, baseline_rec=0.88, baseline_prec=0.85
    )
    print(f"Optimal Threshold T*: {best_t:.4f}")

    # Evaluate on untouched Test set
    print("Evaluating on untouched Test set...")
    test_probs = model.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= best_t).astype(int)

    acc = accuracy_score(y_test, test_preds)
    prec = precision_score(y_test, test_preds, zero_division=0)
    rec = recall_score(y_test, test_preds, zero_division=0)
    f1 = f1_score(y_test, test_preds, zero_division=0)
    roc_auc = roc_auc_score(y_test, test_probs)
    pr_auc = average_precision_score(y_test, test_probs)

    metrics = {
        "Dataset": "SAML-D",
        "Architecture": "Regularized XGBoost (False-Alarm Pruned)",
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

    print("Dataset 2 Phase 1.9 Test Results:")
    print(json.dumps(metrics, indent=4))

    # Save Model & Metrics
    out_model_dir = (
        "../models/SAML-D" if os.path.exists("../models") else "models/SAML-D"
    )
    out_exp_dir = (
        "../experiments/SAML-D"
        if os.path.exists("../experiments")
        else "experiments/SAML-D"
    )
    os.makedirs(out_model_dir, exist_ok=True)
    os.makedirs(out_exp_dir, exist_ok=True)

    joblib.dump(model, os.path.join(out_model_dir, "model_v5.joblib"))
    with open(os.path.join(out_exp_dir, "metrics_v5.json"), "w") as f:
        json.dump(metrics, f, indent=4)

    print("Dataset 2 Phase 1.9 execution completed successfully.\n")
    cleanup_memory()


if __name__ == "__main__":
    run_pipeline()
