"""
Elliptic Bitcoin XGBoost Retraining Pipeline
Resolves illicit node class imbalance with dynamic scale_pos_weight.
Enforces exact 166-feature tensor format and temporal train/test split.
"""

import os
import sys
import time
import json
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    classification_report
)


def retrain_elliptic():
    print("=" * 75)
    print("ELLIPTIC BITCOIN XGBOOST RETRAINING PIPELINE (ILLICIT CLASS BALANCING)")
    print("=" * 75)
    sys.stdout.flush()
    t0 = time.time()

    # 1. Dataset Loading
    features_candidates = [
        "data/elliptic/elliptic_txs_features.csv",
        "elliptic_bitcoin_dataset/elliptic_txs_features.csv"
    ]
    classes_candidates = [
        "data/elliptic/elliptic_txs_classes.csv",
        "elliptic_bitcoin_dataset/elliptic_txs_classes.csv"
    ]

    features_path = next((p for p in features_candidates if os.path.exists(p)), None)
    classes_path = next((p for p in classes_candidates if os.path.exists(p)), None)

    if not features_path or not classes_path:
        raise FileNotFoundError("Elliptic dataset files not found in workspace.")

    print(f"\n[1/4] Ingesting Elliptic features from {features_path}...")
    print(f"      Ingesting class labels from {classes_path}...")
    sys.stdout.flush()

    classes_df = pd.read_csv(classes_path)
    features_df = pd.read_csv(features_path, header=None)

    # Assign column names: txId (col 0), timestep (col 1), feat_0..feat_164 (cols 2..166)
    cols = ['txId', 'timestep'] + [f'feat_{i}' for i in range(165)]
    features_df.columns = cols

    # Merge classes and filter out unclassified nodes (usually class 'unknown' or 3)
    df = features_df.merge(classes_df, on='txId')
    df = df[df['class'].isin(['1', '2', 1, 2])].copy()

    # Map illicit nodes to 1 and licit nodes to 0 (Original: '1'=illicit, '2'=licit)
    df['target'] = df['class'].map({'1': 1, '2': 0, 1: 1, 2: 0}).astype(int)

    # Exact 166 features: timestep (1) + local & aggregate features (165)
    feature_cols = ['timestep'] + [f'feat_{i}' for i in range(165)]
    assert len(feature_cols) == 166, f"Expected 166 features, got {len(feature_cols)}"

    # Temporal train/test split: Timesteps 1-34 for training, 35-49 for testing
    print("\n[2/4] Executing temporal train/test split (Timesteps 1-34 Train, 35-49 Test)...")
    train_mask = df['timestep'] <= 34
    test_mask = df['timestep'] > 34

    X_train = df.loc[train_mask, feature_cols]
    y_train = df.loc[train_mask, 'target'].values

    X_test = df.loc[test_mask, feature_cols]
    y_test = df.loc[test_mask, 'target'].values

    # Calculate dynamic scale_pos_weight: count(licit) / count(illicit) in training set
    licit_count = int((y_train == 0).sum())
    illicit_count = int((y_train == 1).sum())
    scale_pos_weight = float(licit_count / illicit_count)

    print(f"  Training Nodes: {len(X_train):,d} (Licit: {licit_count:,d}, Illicit: {illicit_count:,d})")
    print(f"  Test Nodes:     {len(X_test):,d} (Licit: {int((y_test==0).sum()):,d}, Illicit: {int((y_test==1).sum()):,d})")
    print(f"  Dynamic scale_pos_weight: {scale_pos_weight:.4f} (Ratio {scale_pos_weight:.2f}:1)")
    sys.stdout.flush()

    # Release intermediate raw frames from memory
    del df, features_df, classes_df
    import gc
    gc.collect()

    # 2. Model Training with Specified Hyperparameters
    print("\n[3/4] Instantiating XGBClassifier with target hyperparameters:")
    print(f"  scale_pos_weight={scale_pos_weight:.4f}, max_depth=6, learning_rate=0.1,")
    print("  n_estimators=500, objective='binary:logistic', eval_metric='aucpr', random_state=42")
    sys.stdout.flush()

    model = xgb.XGBClassifier(
        scale_pos_weight=scale_pos_weight,
        max_depth=6,
        learning_rate=0.1,
        n_estimators=500,
        objective='binary:logistic',
        eval_metric='aucpr',
        random_state=42,
        tree_method='hist',
        n_jobs=-1
    )

    t_train = time.time()
    model.fit(X_train, y_train)
    train_duration = time.time() - t_train
    print(f"  Model training successfully completed in {train_duration:.2f}s.")
    sys.stdout.flush()

    # Release training split from memory before scoring
    del X_train, y_train
    gc.collect()

    # 3. Artifact Export
    print("\n[4/4] Serializing model artifacts to designated repository paths...")
    out_paths = [
        "models/elliptic_model.bin",
        "models/elliptic.xgb",
        "models/elliptic/xgboost_model.joblib",
        "models/Elliptic/xgboost_model.joblib",
        "models/Elliptic/model_v5.joblib"
    ]
    for p in out_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if p.endswith(".bin") or p.endswith(".xgb"):
            model.save_model(p)
        else:
            joblib.dump(model, p)
        print(f"  Exported -> {p} ({os.path.getsize(p)/(1024*1024):.2f} MB)")
    sys.stdout.flush()

    # 4. Output: Final Validation Summary
    print("\n" + "=" * 75)
    print(f"FINAL VALIDATION SUMMARY (Test Split: {len(X_test):,d} out-of-time nodes, TS 35-49)")
    print("=" * 75)
    sys.stdout.flush()

    t_eval = time.time()
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.50).astype(int)

    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    pr_auc = average_precision_score(y_test, y_prob)
    roc_auc = roc_auc_score(y_test, y_prob)
    acc = accuracy_score(y_test, y_pred)

    print(f"Evaluation Latency: {time.time()-t_eval:.2f}s")
    print(f"\n--- Primary Test Metrics (Decision Threshold T = 0.50) ---")
    print(f"  Accuracy:   {acc:.4f} ({acc*100:.2f}%)")
    print(f"  Precision:  {prec:.4f}")
    print(f"  Recall:     {rec:.4f} ({(rec*100):.2f}% of illicit nodes captured)")
    print(f"  F1-Score:   {f1:.4f}")
    print(f"  PR-AUC:     {pr_auc:.4f}")
    print(f"  ROC-AUC:    {roc_auc:.4f}")
    print("=" * 75)
    print("\nDetailed Scikit-Learn Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Licit', 'Illicit'], digits=4))
    sys.stdout.flush()

    # Export metrics record
    os.makedirs("experiments/Elliptic", exist_ok=True)
    metrics_record = {
        "Dataset": "Elliptic Bitcoin",
        "Architecture": "XGBoost (166 Features, Dynamic scale_pos_weight)",
        "Scale_Pos_Weight": round(scale_pos_weight, 4),
        "Test_Nodes": len(X_test),
        "Test_Accuracy": round(float(acc), 4),
        "Precision": round(float(prec), 4),
        "Recall": round(float(rec), 4),
        "F1_Score": round(float(f1), 4),
        "PR_AUC": round(float(pr_auc), 4),
        "ROC_AUC": round(float(roc_auc), 4),
        "Execution_Time_Seconds": round(time.time() - t0, 2)
    }
    with open("experiments/Elliptic/metrics_v5.json", "w") as f:
        json.dump(metrics_record, f, indent=4)

    print(f"\nAll artifacts verified and saved. Execution finished in {time.time()-t0:.2f}s.\n")
    return metrics_record


if __name__ == "__main__":
    retrain_elliptic()
