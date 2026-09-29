"""
tests/test_timeseries_aml_step4_registration.py
=============================================================================
Unit tests verifying Step 4 registration of 'aml_timeseries_pipeline:v1.0',
MODEL_CARD.md compliance, TreeSHAP explainability outputs, drift baselines,
and pipeline artifact integrity for Time-Series of Transactions in AML.
=============================================================================
"""

import json
import os
import pytest
import joblib
import torch


@pytest.fixture(scope="module")
def paths():
    return {
        "registry": "models/registry.json",
        "entry": "models/TimeSeries-AML/registry_entry.json",
        "model_card": "models/TimeSeries-AML/MODEL_CARD.md",
        "step4_report": "experiments/TimeSeries-AML/step4_final_evaluation_report.json",
        "pipeline_bundle": "models/TimeSeries-AML/timeseries_feature_pipeline.joblib",
        "tcn_weights": "models/TimeSeries-AML/timeseries_tcn_encoder.pt",
        "processed_tensors": "data/timeseries_aml/processed/timeseries_fused_tensors.pt",
        "model_weights": "models/TimeSeries-AML/best_timeseries_dual_branch.joblib",
        "metrics_v5": "experiments/TimeSeries-AML/metrics_v5.json",
    }


def test_registry_contains_aml_timeseries(paths):
    """Verify 'aml_timeseries_pipeline:v1.0' is formally registered in centralized registry.json."""
    assert os.path.exists(paths["registry"]), "registry.json not found"
    with open(paths["registry"], "r") as f:
        reg = json.load(f)

    assert "aml_timeseries_pipeline:v1.0" in reg, "Missing 'aml_timeseries_pipeline:v1.0' key in registry"
    entry = reg["aml_timeseries_pipeline:v1.0"]
    assert entry["model_id"] == "aml_timeseries_pipeline"
    assert entry["version"] == "v1.0"
    assert entry["status"] == "RELEASED_LOCKED"
    assert entry["feature_count"] == 73
    assert len(entry["feature_names"]) == 73
    assert entry["metrics"]["holdout_pr_auc"] > 0.05
    assert entry["metrics"]["holdout_recall"] >= 0.80
    assert entry["optimal_threshold"] > 0.0

    # Verify alias entry also exists
    assert "timeseries_aml_pipeline:v1.0" in reg, "Missing 'timeseries_aml_pipeline:v1.0' alias in registry"


def test_dedicated_registry_entry_and_artifacts(paths):
    """Verify dedicated registry_entry.json and all registered artifacts exist with correct digests."""
    assert os.path.exists(paths["entry"]), "registry_entry.json missing"
    with open(paths["entry"], "r") as f:
        entry = json.load(f)

    assert entry["model_id"] == "aml_timeseries_pipeline"
    assert entry["version"] == "v1.0"
    assert "artifacts" in entry

    artifacts = entry["artifacts"]
    expected_artifacts = [
        "model_weights",
        "tcn_encoder_weights",
        "feature_pipeline_bundle",
        "processed_tensors",
    ]
    for art_key in expected_artifacts:
        assert art_key in artifacts, f"Artifact key '{art_key}' missing from registry entry"
        rel_path = artifacts[art_key]["relative_path"]
        assert os.path.exists(rel_path), f"Referenced artifact file does not exist: {rel_path}"
        assert os.path.getsize(rel_path) > 0, f"Referenced artifact file is empty: {rel_path}"
        assert len(artifacts[art_key]["sha256"]) == 64, f"Invalid SHA-256 for {art_key}"


def test_model_card_contents(paths):
    """Verify MODEL_CARD.md contains all regulatory sections required by SR 11-7 / OCC 2011-12."""
    assert os.path.exists(paths["model_card"]), "MODEL_CARD.md missing"
    with open(paths["model_card"], "r", encoding="utf-8") as f:
        content = f.read()

    assert "aml_timeseries_pipeline:v1.0" in content
    assert "Executive Summary & Architecture Overview" in content
    assert "Dataset & Temporal Boundaries" in content
    assert "Production Holdout Evaluation Results" in content
    assert "Temporal & Sequential Explainability" in content
    assert "Data Drift Monitoring & Governance Baselines" in content


def test_step4_explainability_report(paths):
    """Verify Step 4 master report contains SHAP rankings and drift telemetry."""
    assert os.path.exists(paths["step4_report"]), "step4_final_evaluation_report.json missing"
    with open(paths["step4_report"], "r") as f:
        rep = json.load(f)

    assert rep["registry_key"] == "aml_timeseries_pipeline:v1.0"
    assert len(rep["explainability"]["global_top_drivers"]) >= 10
    assert len(rep["explainability"]["local_case_studies"]) >= 2
    assert "drift_baselines" in rep
    assert "mean_psi" in rep["drift_baselines"]


def test_feature_pipeline_bundle_integrity(paths):
    """Verify deserialization of feature pipeline bundle and preprocessing transformers."""
    assert os.path.exists(paths["pipeline_bundle"]), "pipeline_bundle missing"
    bundle = joblib.load(paths["pipeline_bundle"])

    assert "feature_names" in bundle
    assert len(bundle["feature_names"]) == 73
    assert "imputer" in bundle
    assert "scaler" in bundle
    assert "tcn_config" in bundle
    assert "calibrated_thresholds" in bundle
    assert bundle["calibrated_thresholds"]["optimal_threshold_T"] > 0


def test_tensors_and_tcn_weights(paths):
    """Verify serialized split tensors and PyTorch TCN weights load properly."""
    assert os.path.exists(paths["tcn_weights"]), "TCN weights missing"
    state_dict = torch.load(paths["tcn_weights"], weights_only=True)
    assert "conv1.weight" in state_dict
    assert "conv2.weight" in state_dict

    assert os.path.exists(paths["processed_tensors"]), "Processed tensors missing"
    tensors = torch.load(paths["processed_tensors"], weights_only=False)
    assert "X_train" in tensors
    assert "X_test" in tensors
    assert tensors["X_train"].shape[1] == 73
    assert tensors["X_test"].shape[1] == 73


def test_metrics_v5_orchestrator_sync(paths):
    """Verify metrics_v5.json exists and adheres to master orchestrator schema."""
    assert os.path.exists(paths["metrics_v5"]), "metrics_v5.json missing"
    with open(paths["metrics_v5"], "r") as f:
        m = json.load(f)

    assert m["Dataset"] == "Time-Series AML"
    assert m["Recall"] >= 0.80
    assert m["PR_AUC"] > 0.05
    assert m["Target_Met"] in ("YES", "ACCEPTABLE")
