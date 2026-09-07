import time
import pandas as pd
from catboost import CatBoostClassifier

# Test 10 iterations with default vs MVS
X = pd.DataFrame({
    'From Bank': ['10', '12'] * 50000,
    'To Bank': ['1', '2'] * 50000,
    'Account_From': [f'A{i}' for i in range(1000)] * 100,
    'Account_To': [f'B{i}' for i in range(1000)] * 100,
    'Amount': [100.0, 200.0] * 50000,
    'Currency': ['USD', 'EUR'] * 50000,
    'Payment Format': ['Card', 'Cheque'] * 50000,
})
y = [0] * 99900 + [1] * 100
cat_features = ['From Bank', 'To Bank', 'Account_From', 'Account_To', 'Currency', 'Payment Format']

t0 = time.time()
cb1 = CatBoostClassifier(iterations=10, depth=6, learning_rate=0.05, auto_class_weights='Balanced', random_seed=42, thread_count=4, verbose=0)
cb1.fit(X, y, cat_features=cat_features)
print(f"Default: {time.time()-t0:.2f}s")

t0 = time.time()
cb2 = CatBoostClassifier(iterations=10, depth=6, learning_rate=0.05, auto_class_weights='Balanced', random_seed=42, thread_count=4, max_ctr_complexity=1, verbose=0)
cb2.fit(X, y, cat_features=cat_features)
print(f"max_ctr_complexity=1: {time.time()-t0:.2f}s")
