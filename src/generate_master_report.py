import glob
import json
import os

import pandas as pd


def main():
    patterns = ["../experiments/*/metrics_v4.json", "experiments/*/metrics_v4.json"]
    metrics_files = []
    for pat in patterns:
        files = glob.glob(pat)
        if files:
            metrics_files = files
            break

    all_metrics = []
    for mf in metrics_files:
        with open(mf, "r") as f:
            all_metrics.append(json.load(f))

    if not all_metrics:
        print("No metrics_v4.json files found!")
        return

    df = pd.DataFrame(all_metrics)

    # Save to JSON and CSV in parent directory or current directory
    json_path = (
        "../five_dataset_results_v4.json"
        if os.path.exists("../experiments")
        else "five_dataset_results_v4.json"
    )
    csv_path = (
        "../five_dataset_results_v4.csv"
        if os.path.exists("../experiments")
        else "five_dataset_results_v4.csv"
    )

    with open(json_path, "w") as f:
        json.dump(all_metrics, f, indent=4)

    df.to_csv(csv_path, index=False)

    print("Master report generated successfully:")
    print(f" - {json_path}")
    print(f" - {csv_path}")
    print("\nSummary Results:")
    print(
        df[
            [
                "Dataset",
                "Architecture",
                "Best_Threshold",
                "Test_Accuracy",
                "Recall",
                "F1_Score",
                "ROC_AUC",
                "Target_Met",
            ]
        ]
    )


if __name__ == "__main__":
    main()
