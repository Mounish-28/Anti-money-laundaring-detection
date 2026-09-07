import time
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from catboost import CatBoostClassifier

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
df = pd.read_csv("data/ibm_transactions/HI-Small_Trans.csv", usecols=usecols, dtype=dtypes)
df = df.rename(columns={
    'Account': 'Account_From',
    'Account.1': 'Account_To',
    'Amount Received': 'Amount',
    'Receiving Currency': 'Currency'
})
feature_cols = ['From Bank', 'To Bank', 'Account_From', 'Account_To', 'Amount', 'Currency', 'Payment Format']
X = df[feature_cols]
y = df['Is Laundering'].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"Train: {len(X_train):,d} (Pos: {(y_train==1).sum():,d}), Test: {len(X_test):,d} (Pos: {(y_test==1).sum():,d})")

cat_features = ['From Bank', 'To Bank', 'Account_From', 'Account_To', 'Currency', 'Payment Format']

cb = CatBoostClassifier(
    iterations=5,
    depth=6,
    learning_rate=0.05,
    auto_class_weights='Balanced',
    eval_metric='F1',
    random_seed=42,
    thread_count=4,
    verbose=1
)
t0 = time.time()
cb.fit(X_train, y_train, cat_features=cat_features)
print(f"5 iterations on 4M rows took {time.time()-t0:.2f}s")
