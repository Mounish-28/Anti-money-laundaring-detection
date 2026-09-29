"""
tests/test_amlsim_tuning.py
=============================================================================
Verification of Ensemble Model Checkpoint, Expanding-Window Tuning,
and Holdout Evaluation Telemetry for IBM AMLSim.
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
        "model": "models/AMLSim/best_amlsim_ensemble.joblib",
        "results": "experiments/AMLSim/tuning_results.json",
    }


def test_model_and_results_exist(paths):
    """Verify that the model checkpoint and tuning report exist and are non-empty."""
    for name, path in paths.items():
        assert os.path.exists(path), f"Artifact missing: {path}"
        assert os.path.getsize(path) > 0, f"Artifact empty: {path}"


def test_model_predict_capability(paths):
    """Verify that the serialized ensemble model can execute valid inference."""
    model = joblib.load(paths["model"])
    # Synthetic input with 56 features
    dummy_x = np.random.randn(5, 56).astype(np.float32)
    preds = model.predict(dummy_x)
    assert len(preds) == 5, f"Expected 5 predictions, got {len(preds)}"
    assert (preds >= 0.0).all() and (preds <= 1.0).all(), "Predictions outside valid probability [0, 1]"


def test_tuning_results_metrics(paths):
    """Verify tuning telemetry metrics adhere to AML quality bars."""
    with open(paths["results"], "r") as f:
        res = json.load(f)

    assert res["dataset"] == "IBM AMLSim"
    assert res["cross_validation"]["strategy"] == "Chronological Expanding-Window (Rolling-Origin)"
    assert res["cross_validation"]["num_folds"] == 3

    # Test metrics check
    test_m = res["final_holdout_test_metrics"]
    assert test_m["pr_auc"] > 0.35, f"Expected test PR-AUC > 0.35, got {test_m['pr_auc']}"
    assert test_m["roc_auc"] > 0.68, f"Expected test ROC-AUC > 0.68, got {test_m['roc_auc']}"
    assert test_m["precision_at_100"] >= 0.50, f"Expected P@100 >= 50%, got {test_m['precision_at_100']}"
    assert test_m["confusion_matrix"]["TP"] > 0
    assert test_m["confusion_matrix"]["TN"] > 0
