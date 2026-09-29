import time

import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

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
df = pd.read_csv(
    "data/ibm_transactions/HI-Small_Trans.csv", usecols=usecols, dtype=dtypes
)
df = df.rename(
    columns={
        "Account": "Account_From",
        "Account.1": "Account_To",
        "Amount Received": "Amount",
        "Receiving Currency": "Currency",
    }
)
feature_cols = [
    "From Bank",
    "To Bank",
    "Account_From",
    "Account_To",
    "Amount",
    "Currency",
    "Payment Format",
]
X = df[feature_cols]
y = df["Is Laundering"].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

cat_features = [
    "From Bank",
    "To Bank",
    "Account_From",
    "Account_To",
    "Currency",
    "Payment Format",
]

cb = CatBoostClassifier(
    iterations=50,
    depth=6,
    learning_rate=0.05,
    auto_class_weights="Balanced",
    eval_metric="F1",
    random_seed=42,
    thread_count=4,
    verbose=10,
)
t0 = time.time()
cb.fit(X_train, y_train, cat_features=cat_features)
print(f"50 iterations took {time.time() - t0:.2f}s")

# Evaluate on test set (or 100k sample of test set)
y_pred = cb.predict(X_test)
y_prob = cb.predict_proba(X_test)[:, 1]

print(f"Precision: {precision_score(y_test, y_pred):.4f}")
print(f"Recall:    {recall_score(y_test, y_pred):.4f}")
print(f"F1-Score:  {f1_score(y_test, y_pred):.4f}")
print(f"PR-AUC:    {average_precision_score(y_test, y_prob):.4f}")
