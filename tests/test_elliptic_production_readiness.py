"""
Unit and integration tests for Elliptic Bitcoin Step 4 & 5 Production Readiness:
- Holdout evaluation integrity (Timesteps 35..49)
- GNN inference on dynamic streaming graphs
- Decision threshold calibration validity
- Registry packaging and SHA-256 cryptographic checksum authentication
- Model card and drift monitoring baseline completeness
"""

import json
import os
import pytest
import torch
import numpy as np

from app.services.model_registry import EnterpriseModelRegistry, compute_sha256
from scripts.tune_elliptic_gnn import EllipticGraphSAGE

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="module")
def models_dir():
    return os.path.join(ROOT_DIR, "models", "elliptic")


@pytest.fixture(scope="module")
def registry():
    return EnterpriseModelRegistry()


def test_holdout_evaluation_results(models_dir):
    """Verify that holdout evaluation JSON exists and meets performance baselines."""
    eval_path = os.path.join(models_dir, "holdout_evaluation.json")
    assert os.path.exists(eval_path), f"Missing {eval_path}"

    with open(eval_path, "r") as f:
        data = json.load(f)

    assert data["evaluation_timesteps"] == "35..49"
    assert data["total_holdout_nodes"] == 67504
    assert data["illicit_count"] == 1083
    assert data["licit_count"] == 15587

    metrics = data["metrics"]
    assert metrics["pr_auc"] > 0.50, f"PR-AUC {metrics['pr_auc']} fell below expected minimum 0.50"
    assert metrics["roc_auc"] > 0.80, f"ROC-AUC {metrics['roc_auc']} fell below expected minimum 0.80"
    assert metrics["optimal_f1"] > 0.55, f"Optimal F1 {metrics['optimal_f1']} fell below 0.55"
    assert metrics["optimal_threshold"] > 0.50, "Optimal threshold should be calibrated above standard 0.50"


def test_optimal_threshold_calibration_profiles(models_dir):
    """Verify default, optimal F1, high-recall, and high-precision operating points."""
    eval_path = os.path.join(models_dir, "holdout_evaluation.json")
    with open(eval_path, "r") as f:
        data = json.load(f)

    ops = data["operating_points"]
    assert "default_0_50" in ops
    assert "optimal_f1" in ops
    assert "high_recall_operational" in ops
    assert "high_precision_operational" in ops

    # Optimal F1 should achieve higher F1 than default 0.50
    assert ops["optimal_f1"]["f1"] > ops["default_0_50"]["f1"]
    # High-recall should achieve >= 85% recall
    assert ops["high_recall_operational"]["recall"] >= 0.85
    # High-precision should achieve >= 80% precision
    assert ops["high_precision_operational"]["precision"] >= 0.80


def test_model_inference_on_holdout_subgraph(models_dir):
    """Verify model can load checkpoint and run inductive inference on holdout timestep."""
    config_path = os.path.join(models_dir, "optimal_hyperparameters.json")
    checkpoint_path = os.path.join(models_dir, "best_elliptic_graphsage.pt")
    subgraphs_path = os.path.join(ROOT_DIR, "data", "elliptic", "processed", "elliptic_subgraphs_pyg.pt")

    with open(config_path, "r") as f:
        config = json.load(f)

    model = EllipticGraphSAGE(
        in_channels=174,
        hidden_dim=config["hidden_dim"],
        num_layers=config["num_layers"],
        dropout=config["dropout"]
    )
    model.load_state_dict(torch.load(checkpoint_path, map_location="cpu", weights_only=True))
    model.eval()

    subgraphs = torch.load(subgraphs_path, map_location="cpu", weights_only=False)
    # Test on timestep 35 (index 34)
    data_t35 = subgraphs[34]
    with torch.no_grad():
        logits = model(data_t35.x, data_t35.edge_index)
        probs = torch.sigmoid(logits)

    assert logits.shape == (data_t35.num_nodes,)
    assert not torch.isnan(probs).any()
    assert (probs >= 0.0).all() and (probs <= 1.0).all()


def test_enterprise_model_registry_registration(registry):
    """Verify that elliptic_gnn:v1.0 is registered, locked, and checksum-verified."""
    entry = registry.get_model("elliptic_gnn", "v1.0")
    assert entry is not None, "elliptic_gnn:v1.0 not found in EnterpriseModelRegistry"
    assert entry["status"] == "RELEASED_LOCKED"
    assert entry["feature_count"] == 174
    assert len(entry["feature_names"]) == 174

    # Verify SHA-256 integrity of all registered artifacts
    integrity = registry.verify_integrity("elliptic_gnn", "v1.0", base_dir=ROOT_DIR)
    assert len(integrity) > 0, "No artifacts verified"
    for art_name, is_valid in integrity.items():
        assert is_valid, f"Artifact {art_name} failed cryptographic checksum verification!"


def test_drift_monitoring_baselines(models_dir):
    """Verify drift monitoring baselines are recorded with valid PSIs and thresholds."""
    drift_path = os.path.join(models_dir, "drift_baselines.json")
    assert os.path.exists(drift_path), f"Missing {drift_path}"

    with open(drift_path, "r") as f:
        drift = json.load(f)

    pred_drift = drift["prediction_drift"]
    assert "psi" in pred_drift
    assert "wasserstein_distance" in pred_drift
    assert pred_drift["psi"] >= 0.0
    assert pred_drift["alert_threshold_moderate"] == 0.10
    assert pred_drift["alert_threshold_critical"] == 0.25

    feat_drift = drift["feature_drift_baselines"]
    assert len(feat_drift) >= 5, "Expected at least 5 tracked feature baselines"


def test_production_model_card_completeness(models_dir):
    """Verify MODEL_CARD.md exists and contains all required regulatory audit sections."""
    card_path = os.path.join(models_dir, "MODEL_CARD.md")
    assert os.path.exists(card_path), f"Missing {card_path}"

    with open(card_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "elliptic_gnn:v1.0" in content
    assert "RELEASED_LOCKED" in content
    assert "PR-AUC" in content
    assert "GNNExplainer" in content
    assert "Operating Points" in content
    assert "Drift Monitoring" in content
    assert "Cryptographic Signatures" in content
