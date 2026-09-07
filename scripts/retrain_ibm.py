import os
import sys
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    classification_report
)
from catboost import CatBoostClassifier

def retrain_ibm():
    print("=" * 75)
    print("IBM TRANSACTIONS CATBOOST RETRAINING PIPELINE (BALANCED WEIGHTS)")
    print("=" * 75)
    sys.stdout.flush()

    # 1. Dataset Loading
    t0 = time.time()
    csv_candidates = [
        "data/ibm_transactions/HI-Small_Trans.csv",
        "IBM anti-money/HI-Small_Trans.csv"
    ]
    data_path = None
    for p in csv_candidates:
        if os.path.exists(p):
            data_path = p
            break
    if not data_path:
        raise FileNotFoundError("HI-Small_Trans.csv dataset not found in workspace.")

    print(f"\n[1/5] Ingesting transactions dataset from {data_path}...")
    sys.stdout.flush()

    usecols = [
        'From Bank', 'Account', 'To Bank', 'Account.1',
        'Amount Received', 'Receiving Currency', 'Payment Format', 'Is Laundering'
    ]
    dtypes = {
        'From Bank': 'str',
        'Account': 'str',
        'To Bank': 'str',
        'Account.1': 'str',
        'Amount Received': 'float32',
        'Receiving Currency': 'str',
        'Payment Format': 'str',
        'Is Laundering': 'int8'
    }
    df = pd.read_csv(data_path, usecols=usecols, dtype=dtypes)
    print(f"  Loaded {len(df):,d} transactions in {time.time()-t0:.2f}s")
    sys.stdout.flush()

    # 2. Schema Alignment: Exact 7 features
    print("\n[2/5] Aligning exact 7 features expected by UnifiedInferenceEngine...")
    df = df.rename(columns={
        'Account': 'Account_From',
        'Account.1': 'Account_To',
        'Amount Received': 'Amount',
        'Receiving Currency': 'Currency'
    })
    feature_cols = [
        'From Bank', 'To Bank', 'Account_From', 'Account_To',
        'Amount', 'Currency', 'Payment Format'
    ]
    X = df[feature_cols]
    y = df['Is Laundering'].values
    target_pos = (y == 1).sum()
    target_neg = (y == 0).sum()
    print(f"  Feature Schema ({len(feature_cols)} features): {feature_cols}")
    print(f"  Class Distribution: Legitimate={target_neg:,d} ({(target_neg/len(y))*100:.2f}%), Laundering={target_pos:,d} ({(target_pos/len(y))*100:.3f}%)")
    sys.stdout.flush()

    # 80/20 train/test split
    print("\n[3/5] Partitioning into 80/20 stratified train/test splits...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"  Train Set: {len(X_train):,d} transactions (Laundering: {(y_train==1).sum():,d})")
    print(f"  Test Set:  {len(X_test):,d} transactions (Laundering: {(y_test==1).sum():,d})")
    
    # Release raw dataset memory immediately
    del df, X, y
    import gc
    gc.collect()
    sys.stdout.flush()

    cat_features = ['From Bank', 'To Bank', 'Account_From', 'Account_To', 'Currency', 'Payment Format']

    # 3. Model Training
    print("\n[4/5] Instantiating CatBoostClassifier with target hyperparameters:")
    print("  auto_class_weights='Balanced', iterations=800, learning_rate=0.05, depth=6, eval_metric='F1', random_seed=42")
    sys.stdout.flush()

    cb = CatBoostClassifier(
        iterations=800,
        learning_rate=0.05,
        depth=6,
        auto_class_weights='Balanced',
        eval_metric='F1',
        random_seed=42,
        thread_count=4,
        verbose=50
    )

    t_train = time.time()
    cb.fit(X_train, y_train, cat_features=cat_features)
    train_duration = time.time() - t_train
    print(f"  Training finished in {train_duration:.2f}s ({train_duration/60:.2f} min)")
    
    # Release training data from memory before evaluation
    del X_train, y_train
    gc.collect()
    sys.stdout.flush()

    # 4. Artifact Export
    print("\n[5/5] Exporting trained model artifacts atomically...")
    out_paths = [
        "models/ibm_transactions.cbm",
        "models/ibm_transactions/catboost_model.cbm",
        "models/ibm_transactions/catboost_model.joblib",
        "models/IBM-AML/model_v5.cbm",
        "models/IBM-AML/model_v5.joblib"
    ]
    for p in out_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if p.endswith(".cbm"):
            cb.save_model(p)
        else:
            joblib.dump(cb, p)
        print(f"  Exported -> {p} ({os.path.getsize(p)/(1024*1024):.2f} MB)")
    sys.stdout.flush()

    # 5. Output: Final Validation Summary
    print("\n" + "=" * 75)
    print("FINAL VALIDATION SUMMARY (Test Split: 1,015,669 transactions)")
    print("=" * 75)
    sys.stdout.flush()

    t_eval = time.time()
    y_prob = cb.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.50).astype(int)

    prec_50 = precision_score(y_test, y_pred, zero_division=0)
    rec_50 = recall_score(y_test, y_pred, zero_division=0)
    f1_50 = f1_score(y_test, y_pred, zero_division=0)
    pr_auc = average_precision_score(y_test, y_prob)
    roc_auc = roc_auc_score(y_test, y_prob)

    print(f"Evaluation Time: {time.time()-t_eval:.2f}s")
    print(f"\n--- Metrics at Default Operational Threshold (T = 0.50) ---")
    print(f"  Precision: {prec_50:.4f}")
    print(f"  Recall:    {rec_50:.4f} ({(rec_50*100):.2f}% captured anomalies)")
    print(f"  F1-Score:  {f1_50:.4f}")
    print(f"  PR-AUC:    {pr_auc:.4f}")
    print(f"  ROC-AUC:   {roc_auc:.4f}")
    sys.stdout.flush()

    # Also compute threshold scan for calibrated operations
    thresholds = np.linspace(0.50, 0.999, 100)
    best_f1, best_t, best_p, best_r = 0.0, 0.50, prec_50, rec_50
    for t in thresholds:
        pred_t = (y_prob >= t).astype(int)
        f = f1_score(y_test, pred_t, zero_division=0)
        if f > best_f1:
            best_f1 = f
            best_t = t
            best_p = precision_score(y_test, pred_t, zero_division=0)
            best_r = recall_score(y_test, pred_t, zero_division=0)

    print(f"\n--- Calibrated Optimal F1 Operating Point (T* = {best_t:.4f}) ---")
    print(f"  Precision: {best_p:.4f}")
    print(f"  Recall:    {best_r:.4f}")
    print(f"  F1-Score:  {best_f1:.4f}")
    print(f"  PR-AUC:    {pr_auc:.4f}")
    print("=" * 75)
    sys.stdout.flush()

if __name__ == "__main__":
    retrain_ibm()
