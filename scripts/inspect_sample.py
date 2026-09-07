import pandas as pd

df = pd.read_csv("data/ibm_transactions/HI-Small_Trans.csv", nrows=10)
print("Columns:", list(df.columns))
print(df.head(5))
print("Dtypes:")
print(df.dtypes)
