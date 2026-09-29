import json
import os

import pandas as pd

datasets = ["IBM-AML", "SAML-D", "Elliptic", "AMLSim", "TimeSeries-AML"]
results = []
for d in datasets:
    p = f"experiments/{d}/metrics_v5.json"
    if os.path.exists(p):
        with open(p, "r") as f:
            m = json.load(f)
            results.append(m)
            print(
                f"{m['Dataset']}: Acc={m.get('Test_Accuracy', 0):.4f}, Rec={m.get('Recall', 0):.4f}, F1={m.get('F1_Score', 0):.4f}, Target_Met={m.get('Target_Met', '-')}"
            )

# Export JSON
with open("five_dataset_results_v5.json", "w") as f:
    json.dump(results, f, indent=4)
with open("experiments/benchmark_phase_1_9.json", "w") as f:
    json.dump(results, f, indent=4)

# Export CSV
df = pd.DataFrame(results)
df.to_csv("five_dataset_results_v5.csv", index=False)
if os.path.exists("experiments"):
    df.to_csv("experiments/benchmark_phase_1_9.csv", index=False)

print(
    "Exported five_dataset_results_v5.json/csv and experiments/benchmark_phase_1_9.json/csv successfully!"
)
