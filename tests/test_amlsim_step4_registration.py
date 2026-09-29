"""
tests/test_amlsim_step4_registration.py
=============================================================================
Unit tests verifying Step 4 registration of 'ibm_amlsim_pipeline:v1.0',
MODEL_CARD.md integrity, TreeSHAP explainability outputs, and drift baselines.
=============================================================================
"""

import json
import os
import pytest


@pytest.fixture(scope="module")
def paths():
    return {
        "registry": "models/registry.json",
        "entry": "models/AMLSim/registry_entry.json",
        "model_card": "models/AMLSim/MODEL_CARD.md",
        "step4_report": "experiments/AMLSim/step4_final_evaluation_report.json",
    }


def test_registry_contains_ibm_amlsim(paths):
    """Verify 'ibm_amlsim_pipeline:v1.0' is formally registered in centralized registry.json."""
    assert os.path.exists(paths["registry"]), "registry.json not found"
    with open(paths["registry"], "r") as f:
        reg = json.load(f)

    assert "ibm_amlsim_pipeline:v1.0" in reg, "Missing 'ibm_amlsim_pipeline:v1.0' key in registry"
    entry = reg["ibm_amlsim_pipeline:v1.0"]
    assert entry["model_id"] == "ibm_amlsim_pipeline"
    assert entry["version"] == "v1.0"
    assert entry["status"] == "RELEASED_LOCKED"
    assert entry["feature_count"] == 56
    assert len(entry["feature_names"]) == 56
    assert entry["metrics"]["holdout_pr_auc"] > 0.35
    assert entry["metrics"]["precision_at_100"] >= 50.0


def test_dedicated_registry_entry_matches(paths):
    """Verify dedicated registry_entry.json is consistent with centralized registry."""
    assert os.path.exists(paths["entry"]), "registry_entry.json missing"
    with open(paths["entry"], "r") as f:
        entry = json.load(f)

    assert entry["model_id"] == "ibm_amlsim_pipeline"
    assert entry["version"] == "v1.0"
    assert "artifacts" in entry
    assert "model_weights" in entry["artifacts"]
    assert "fused_pyg_data" in entry["artifacts"]
    assert "fused_sparse_tensors" in entry["artifacts"]
    assert "feature_imputer" in entry["artifacts"]
    assert "robust_scaler" in entry["artifacts"]


def test_model_card_contents(paths):
    """Verify MODEL_CARD.md contains all required regulatory sections."""
    assert os.path.exists(paths["model_card"]), "MODEL_CARD.md missing"
    with open(paths["model_card"], "r", encoding="utf-8") as f:
        content = f.read()

    assert "ibm_amlsim_pipeline:v1.0" in content
    assert "Executive Summary & Architecture Overview" in content
    assert "Dataset & Temporal Boundaries" in content
    assert "Production Holdout Evaluation Results" in content
    assert "TreeSHAP Regulatory Explainability" in content
    assert "Data Drift Monitoring & Governance Baselines" in content


def test_step4_explainability_report(paths):
    """Verify Step 4 report contains TreeSHAP rankings and drift telemetry."""
    assert os.path.exists(paths["step4_report"]), "step4_final_evaluation_report.json missing"
    with open(paths["step4_report"], "r") as f:
        rep = json.load(f)

    assert rep["registry_key"] == "ibm_amlsim_pipeline:v1.0"
    assert len(rep["explainability"]["global_top_drivers"]) >= 10
    assert len(rep["explainability"]["local_case_studies"]) >= 2
    assert rep["drift_baselines"]["mean_psi"] < 0.10
