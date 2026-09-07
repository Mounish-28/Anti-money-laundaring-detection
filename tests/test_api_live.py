import asyncio
import httpx
import pytest

from app.main import app, engine

# Ensure robust TestClient compatibility across httpx versions
try:
    from fastapi.testclient import TestClient as _FastAPITestClient

    _probe = _FastAPITestClient(app)
    TestClient = _FastAPITestClient
except Exception:

    class TestClient:
        """Robust ASGI TestClient adapter supporting HTTPX 0.28+ and context manager lifespan."""

        __test__ = False

        def __init__(self, app, base_url: str = "http://testserver"):
            self.app = app
            self.base_url = base_url
            self.transport = httpx.ASGITransport(app=app)

        def __enter__(self):
            engine.warmup()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def get(self, url: str, **kwargs):
            async def _req():
                async with httpx.AsyncClient(
                    transport=self.transport, base_url=self.base_url
                ) as client:
                    return await client.get(url, **kwargs)

            return asyncio.run(_req())

        def post(self, url: str, **kwargs):
            async def _req():
                async with httpx.AsyncClient(
                    transport=self.transport, base_url=self.base_url
                ) as client:
                    return await client.post(url, **kwargs)

            return asyncio.run(_req())


@pytest.fixture(scope="session")
def client():
    """Session fixture creating a lifespan-aware TestClient."""
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    """Validates GET /health returns HTTP 200 with HEALTHY status and active loaded models."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "loaded_models" in data
    assert isinstance(data["loaded_models"], list)
    assert len(data["loaded_models"]) > 0

    expected_models = {
        "ibm_transactions",
        "samld",
        "elliptic",
        "amlsim_lgbm",
        "timeseries_xgb",
        "timeseries_cb",
    }
    if "amlsim_gcn" in engine.models:
        expected_models.add("amlsim_gcn")
    assert expected_models.issubset(set(data["loaded_models"]))


def test_score_ibm_transaction(client):
    """Validates POST /api/v1/score/transaction evaluates IBM transactions with complete schema conformity."""
    payload = {
        "transaction_id": "ibm_tx_live_001",
        "from_bank": "10",
        "to_bank": "12",
        "account_from": "ACC_SEND_88",
        "account_to": "ACC_RECV_99",
        "amount": 2500.50,
        "currency": "US Dollar",
        "payment_format": "Credit Card",
    }
    response = client.post("/api/v1/score/transaction", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["entity_id"] == "ibm_tx_live_001"
    assert data["dataset"] == "IBM Transactions"
    assert 0.0 <= data["risk_score"] <= 1.0
    assert isinstance(data["risk_tier"], str)
    assert data["risk_tier"] in {"LOW", "ELEVATED", "HIGH", "CRITICAL_SAR"}
    assert isinstance(data["is_anomaly"], bool)
    assert "recommended_action" in data
    assert data["latency_ms"] > 0


def test_score_timeseries(client):
    """Validates POST /api/v1/score/timeseries evaluates rolling EMAs and cyclical features under 50ms latency."""
    payload = {
        "account_id": "ts_acc_live_002",
        "amount": 450.0,
        "ema_1h": 420.0,
        "ema_24h": 380.0,
        "ema_7d": 350.0,
        "delta_t_seconds": 60.0,
        "burstiness_index": 0.72,
        "sin_hour": 0.7071,
        "cos_hour": 0.7071,
        "sin_dow": 0.4339,
        "cos_dow": 0.9010,
    }
    # Initial warm-up request
    client.post("/api/v1/score/timeseries", json=payload)

    response = client.post("/api/v1/score/timeseries", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["entity_id"] == "ts_acc_live_002"
    assert data["dataset"] == "Time-Series AML"
    assert isinstance(data["risk_score"], float)
    assert 0.0 <= data["risk_score"] <= 1.0
    assert data["latency_ms"] < 50.0


def test_score_crypto_valid(client):
    """Validates POST /api/v1/score/crypto evaluates an Elliptic Bitcoin node with exact 166 features."""
    payload = {"node_id": "btc_node_live_003", "features": [0.05] * 166}
    response = client.post("/api/v1/score/crypto", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["entity_id"] == "btc_node_live_003"
    assert data["dataset"] == "Elliptic Bitcoin"
    assert 0.0 <= data["risk_score"] <= 1.0
    assert isinstance(data["risk_tier"], str)
    assert data["risk_tier"] in {"LOW", "ELEVATED", "HIGH", "CRITICAL_SAR"}
    assert isinstance(data["is_anomaly"], bool)


def test_score_crypto_invalid_dimensions(client):
    """Validates POST /api/v1/score/crypto rejects invalid vector length (e.g. 10 floats) with HTTP 422."""
    payload = {
        "node_id": "btc_invalid_node",
        "features": [
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
        ],  # Only 10 floats
    }
    response = client.post("/api/v1/score/crypto", json=payload)
    assert response.status_code == 422


def test_score_samld(client):
    """Validates POST /api/v1/score/samld evaluates SAML-D transactions with velocity and degree metrics."""
    payload = {
        "transaction_id": "samld_tx_live_004",
        "sender_id": "sender_101",
        "receiver_id": "receiver_202",
        "amount": 7500.0,
        "fan_in_count": 8,
        "fan_out_count": 2,
        "sender_velocity_24h": 12.5,
    }
    response = client.post("/api/v1/score/samld", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["entity_id"] == "samld_tx_live_004"
    assert data["dataset"] == "SAML-D"
    assert 0.0 <= data["risk_score"] <= 1.0
    assert data["risk_tier"] in {"LOW", "CRITICAL_SAR"}
    assert isinstance(data["is_anomaly"], bool)


def test_score_amlsim(client):
    """Validates POST /api/v1/score/amlsim evaluates agent-based AMLSim transactions with schema conformity."""
    payload = {
        "transaction_id": "amlsim_tx_live_005",
        "from_bank": "1",
        "to_bank": "2",
        "account_from": "AGENT_ACC_A",
        "account_to": "AGENT_ACC_B",
        "amount": 850.0,
        "currency": "US Dollar",
        "payment_format": "Cheque",
    }
    response = client.post("/api/v1/score/amlsim", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["entity_id"] == "amlsim_tx_live_005"
    assert data["dataset"] == "IBM AMLSim"
    assert 0.0 <= data["risk_score"] <= 1.0
    assert data["risk_tier"] in {"LOW", "CRITICAL_SAR"}
    assert isinstance(data["is_anomaly"], bool)


def test_score_batch_success(client):
    """Validates POST /api/v1/score/batch?dataset=ibm_transactions evaluates 3 items
    and returns consolidated evaluations."""
    items = [
        {
            "transaction_id": f"batch_tx_{i}",
            "from_bank": "10",
            "to_bank": "12",
            "account_from": f"ACC_S_{i}",
            "account_to": f"ACC_R_{i}",
            "amount": 100.0 * (i + 1),
            "currency": "US Dollar",
            "payment_format": "Credit Card",
        }
        for i in range(3)
    ]
    response = client.post("/api/v1/score/batch?dataset=ibm_transactions", json=items)
    assert response.status_code == 200
    data = response.json()
    assert data["dataset"] == "ibm_transactions"
    assert data["total_evaluated"] == 3
    assert isinstance(data["anomalies_detected"], int)
    assert data["anomalies_detected"] >= 0
    assert len(data["evaluations"]) == 3
    assert data["evaluations"][0]["entity_id"] == "batch_tx_0"
    assert data["evaluations"][1]["entity_id"] == "batch_tx_1"
    assert data["evaluations"][2]["entity_id"] == "batch_tx_2"


def test_score_batch_invalid_dataset(client):
    """Validates POST /api/v1/score/batch?dataset=invalid_dataset returns HTTP 400 with explicit error message."""
    items = [{"transaction_id": "tx_bad", "amount": 100.0}]
    response = client.post(
        "/api/v1/score/batch?dataset=invalid_dataset_name", json=items
    )
    assert response.status_code == 400
    data = response.json()
    assert "Invalid dataset 'invalid_dataset_name'" in data["detail"]
    assert "Must be one of" in data["detail"]


def test_prometheus_metrics_endpoint(client):
    """Validates GET /metrics exposes Prometheus metrics including custom AML telemetry."""
    response = client.get("/metrics")
    assert response.status_code == 200
    content = response.text
    assert "aml_inference_latency_seconds" in content
    assert "aml_transactions_evaluated_total" in content
    assert "aml_anomalies_detected_total" in content
