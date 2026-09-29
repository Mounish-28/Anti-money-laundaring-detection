"""
QuantumAML Nexus - SAML-D Production Readiness & Schema Drift Tests
===================================================================
Location: tests/test_samld_production_readiness.py

Pytest suite validating:
- Feature preprocessor outputs 26 features with float32 dtype.
- Strict feature ordering and zero schema drift.
- Single-row inference execution and reasonable latency SLAs.
- Edge case handling (structuring, novel categories, zero velocity).
- Model registry packaging and cryptographic SHA-256 integrity.
"""

import json
import os
import time
import numpy as np
import pandas as pd
import pytest

from app.services.inference_engine import UnifiedInferenceEngine
from app.services.model_registry import EnterpriseModelRegistry, compute_sha256
from app.services.samld_pipeline import SamldFeaturePipeline


@pytest.fixture(scope="module")
def engine():
    return UnifiedInferenceEngine(model_dir="models")


@pytest.fixture(scope="module")
def preprocessor(engine):
    assert "samld_preprocessor" in engine.models, "SAML-D Preprocessor must be loaded."
    return engine.models["samld_preprocessor"]


@pytest.fixture(scope="module")
def model(engine):
    assert "samld" in engine.models, "SAML-D XGBoost model must be loaded."
    return engine.models["samld"]


def test_samld_model_and_preprocessor_artifacts_exist():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    model_path = os.path.join(base_dir, "models", "samld", "xgboost_model.joblib")
    prep_path = os.path.join(base_dir, "models", "samld", "feature_preprocessor.joblib")
    card_path = os.path.join(base_dir, "models", "samld", "MODEL_CARD.md")

    assert os.path.exists(model_path), f"Missing model artifact: {model_path}"
    assert os.path.exists(prep_path), f"Missing preprocessor artifact: {prep_path}"
    assert os.path.exists(card_path), f"Missing model card: {card_path}"


def test_samld_feature_preprocessor_shape_and_names(preprocessor):
    assert hasattr(preprocessor, "feature_names_")
    assert len(preprocessor.feature_names_) == 26

    expected_cols = [
        "Amount", "Log_Amount", "Rolling_24h_Velocity", "Log_Velocity",
        "In_Degree", "Out_Degree", "Amount_to_Velocity_Ratio", "Degree_Ratio",
        "Degree_Difference", "Network_Activity", "Velocity_Per_Out_Degree",
        "Cash_Velocity_Risk", "Structuring_Proximity", "Payment_type_TE",
        "Sender_bank_location_TE", "Receiver_bank_location_TE", "Payment_currency_TE",
        "Received_currency_TE", "Location_Risk_Differential", "Currency_Risk_Differential",
        "Is_Cross_Border", "Is_Currency_Exchange", "Cross_Border_Currency_Mismatch",
        "Is_Cash", "Is_Structuring_Band", "Round_Amount_Flag",
    ]
    assert preprocessor.feature_names_ == expected_cols


def test_samld_feature_transformation_zero_nan(preprocessor):
    df_sample = pd.DataFrame([{
        "Amount": 9500.0,
        "In_Degree": 5,
        "Out_Degree": 2,
        "Rolling_24h_Velocity": 19000.0,
        "Payment_type": "Cash Deposit",
        "Sender_bank_location": "UK",
        "Receiver_bank_location": "UK",
        "Payment_currency": "UK pounds",
        "Received_currency": "UK pounds",
    }])

    feat = preprocessor.transform(df_sample)
    assert feat.shape == (1, 26)
    assert feat.dtype == np.float32
    assert not np.isnan(feat).any()
    assert not np.isinf(feat).any()


def test_samld_edge_case_unseen_categorical(preprocessor, model):
    df_unseen = pd.DataFrame([{
        "Amount": 12000.0,
        "In_Degree": 1,
        "Out_Degree": 1,
        "Rolling_24h_Velocity": 12000.0,
        "Payment_type": "UnknownNovelMethod",
        "Sender_bank_location": "Atlantis",
        "Receiver_bank_location": "Utopia",
        "Payment_currency": "MoonCurrency",
        "Received_currency": "MarsCurrency",
    }])

    feat = preprocessor.transform(df_unseen)
    assert feat.shape == (1, 26)
    assert not np.isnan(feat).any()

    probs = model.predict_proba(feat)
    assert probs.shape == (1, 2)
    assert 0.0 <= probs[0, 1] <= 1.0


def test_samld_single_row_inference_latency_sla(engine):
    payload = {
        "transaction_id": "test_latency_tx",
        "amount": 9900.0,
        "fan_in_count": 2,
        "fan_out_count": 1,
        "sender_velocity_24h": 15000.0,
        "payment_type": "Cash Deposit",
        "sender_bank_location": "UK",
        "receiver_bank_location": "UK",
        "payment_currency": "UK pounds",
        "received_currency": "UK pounds",
    }

    # Warmup
    for _ in range(10):
        engine.score_samld(payload)

    # 100 timed runs
    times = []
    for _ in range(100):
        t0 = time.perf_counter()
        res = engine.score_samld(payload)
        times.append((time.perf_counter() - t0) * 1000.0)

    p95 = np.percentile(times, 95)
    # Pytest runner has slight overhead compared to pure python, allow generous threshold
    assert p95 < 5.0, f"P95 latency {p95:.2f} ms exceeded test ceiling of 5.0 ms"
    assert "risk_score" in res
    assert "risk_tier" in res
    assert "is_anomaly" in res


def test_samld_model_registry_integrity():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    reg_path = os.path.join(base_dir, "models", "registry.json")

    # If registry exists, verify saml_d_xgboost:v1.0
    if os.path.exists(reg_path):
        registry = EnterpriseModelRegistry(reg_path)
        entry = registry.get_model("saml_d_xgboost", "v1.0")
        if entry is not None:
            assert entry["status"] in ("LOCKED_PRODUCTION", "RELEASED_LOCKED")
            assert entry["optimal_threshold"] == 0.6148
            assert entry["feature_count"] == 26

            integrity = registry.verify_integrity("saml_d_xgboost", "v1.0", base_dir=base_dir)
            for artifact_name, is_valid in integrity.items():
                assert is_valid, f"Artifact {artifact_name} failed checksum verification!"


def test_samld_rest_contract_validation():
    from starlette.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. Valid payload
    payload = {
        "transaction_id": "TEST_REST_01",
        "sender_id": "S_01",
        "receiver_id": "R_01",
        "amount": 1500.0,
        "fan_in_count": 2,
        "fan_out_count": 1,
        "sender_velocity_24h": 3000.0,
    }
    r = client.post("/api/v1/score/samld", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["dataset"] == "SAML-D"
    assert "risk_score" in data
    assert "risk_tier" in data

    # 2. Schema rejection: missing required amount
    r_bad = client.post("/api/v1/score/samld", json={"transaction_id": "BAD_01"})
    assert r_bad.status_code == 422

    # 3. Schema rejection: negative amount
    r_neg = client.post("/api/v1/score/samld", json={"transaction_id": "NEG_01", "amount": -10.0})
    assert r_neg.status_code == 422


def test_samld_drift_detector_initialization():
    from app.services.drift_detector import DriftDetector

    detector = DriftDetector()
    assert detector.is_initialized
    assert "features" in detector.baselines
    assert len(detector.baselines["features"]) >= 10
    assert "prediction_distribution" in detector.baselines

