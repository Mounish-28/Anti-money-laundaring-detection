"""
tests/test_timeseries_aml_step3.py
=============================================================================
Verification of Time-Series AML Step 3: Dual-Branch Architecture,
Expanding-Window Tuning, Model Checkpoint & Inference Validation.
=============================================================================
"""

import json
import os
import pytest
import joblib
import numpy as np


@pytest.fixture(scope="module")
def paths():
    return {
        "checkpoint": "models/TimeSeries-AML/best_timeseries_dual_branch.joblib",
        "checkpoint_alt": "models/timeseries/best_timeseries_dual_branch.joblib",
        "results": "experiments/TimeSeries-AML/step3_tuning_results.json",
    }


def test_step3_artifacts_exist(paths):
    """Verify that model checkpoint and tuning results exist and are non-empty."""
    for name, path in paths.items():
        assert os.path.exists(path), f"Artifact missing: {path}"
        assert os.path.getsize(path) > 0, f"Artifact empty: {path}"


def test_model_predict_inference(paths):
    """Verify that the serialized dual-branch ensemble executes valid inference."""
    model = joblib.load(paths["checkpoint"])
    # Synthetic input with 73 features
    dummy_x = np.random.randn(5, 73).astype(np.float32)
    preds = model.predict(dummy_x)
    assert len(preds) == 5
    assert (preds >= 0.0).all() and (preds <= 1.0).all(), "Predictions outside valid probability [0, 1]"


def test_tuning_results_metrics(paths):
    """Verify step 3 tuning telemetry metrics and expanding-window structure."""
    with open(paths["results"], "r") as f:
        res = json.load(f)

    assert res["dataset"] == "Time-Series of Transactions in AML"
    assert res["feature_count"] == 73
    assert res["cross_validation_strategy"] == "Chronological Expanding-Window (Rolling-Origin)"
    assert len(res["cv_folds_cutoffs"]) == 3

    # Holdout test metrics check
    holdout = res["holdout_test_metrics"]
    assert holdout["recall"] >= 0.80, f"Expected Recall >= 80%, got {holdout['recall']:.2%}"
    assert holdout["confusion_matrix"]["TP"] > 0
    assert holdout["confusion_matrix"]["TN"] > 0
