import time
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier

print("Testing CatBoost on sample of 7 features...")
df = pd.read_csv("data/ibm_transactions/HI-Small_Trans.csv", nrows=100000)
df = df.rename(columns={
    'Account': 'Account_From',
    'Account.1': 'Account_To',
    'Amount Received': 'Amount',
    'Receiving Currency': 'Currency'
})
features = ['From Bank', 'To Bank', 'Account_From', 'Account_To', 'Amount', 'Currency', 'Payment Format']
X = df[features].copy()
X['From Bank'] = X['From Bank'].astype(str)
X['To Bank'] = X['To Bank'].astype(str)
X['Account_From'] = X['Account_From'].astype(str)
X['Account_To'] = X['Account_To'].astype(str)
X['Amount'] = X['Amount'].astype(float)
X['Currency'] = X['Currency'].astype(str)
X['Payment Format'] = X['Payment Format'].astype(str)
y = df['Is Laundering'].values

cat_features = ['From Bank', 'To Bank', 'Account_From', 'Account_To', 'Currency', 'Payment Format']

print(f"Dataset shape: {X.shape}, Positives: {(y==1).sum()}")
t0 = time.time()
cb = CatBoostClassifier(
    iterations=20,
    depth=6,
    learning_rate=0.05,
    auto_class_weights='Balanced',
    eval_metric='F1',
    random_seed=42,
    verbose=5
)
cb.fit(X, y, cat_features=cat_features)
print(f"20 iterations took {time.time()-t0:.2f}s")
