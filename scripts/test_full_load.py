import time

import pandas as pd

t0 = time.time()
print("Loading HI-Small_Trans.csv with optimized dtypes...")
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
print(
    f"Loaded {len(df):,d} rows in {time.time() - t0:.2f}s. Memory: {df.memory_usage().sum() / (1024 * 1024):.1f} MB"
)
print(f"Positives: {(df['Is Laundering'] == 1).sum():,d}")
