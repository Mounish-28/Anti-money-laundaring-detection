"""
tests/test_api_server.py
=============================================================================
Integration & Unit tests for FastAPI server in api_server.py
=============================================================================
"""

import pytest
from fastapi.testclient import TestClient

from api_server import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """Verify /health returns healthy status and model telemetry."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "QuantumAML Nexus Agent Server"
    assert "models" in data
    assert data["models"]["gnn_module"]["status"] == "online"
    assert data["models"]["temporal_ensemble"]["status"] == "online"
    assert "graph_state" in data


def test_cors_headers(client):
    """Verify CORS headers for localhost:3000 and localhost:8501."""
    # Origin 1: http://localhost:3000
    res1 = client.options(
        "/api/v1/transactions/analyze",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert res1.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # Origin 2: http://localhost:8501
    res2 = client.options(
        "/api/v1/transactions/analyze",
        headers={"Origin": "http://localhost:8501", "Access-Control-Request-Method": "POST"},
    )
    assert res2.headers.get("access-control-allow-origin") == "http://localhost:8501"


def test_analyze_fiat_transaction_low_risk(client):
    """Verify fiat transaction evaluation resulting in low risk."""
    payload = {
        "tx_id": "TX_API_NORM_001",
        "account_from": "ACC_CUSTOMER_10",
        "account_to": "ACC_GROCERY_STORE",
        "amount": 85.50,
        "currency": "USD",
    }
    response = client.post("/api/v1/transactions/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["tx_id"] == "TX_API_NORM_001"
    assert data["risk_score"] < 75.0
    assert data["risk_level"] in ("Low", "Medium")
    assert data["alert_triggered"] is False
    assert data["financial_rail"] == "fiat"
    assert data["entities"]["source"] == "ACC_CUSTOMER_10"
    assert data["entities"]["target"] == "ACC_GROCERY_STORE"
    assert data["inference_latency_ms"] >= 0.0


def test_analyze_fiat_transaction_structuring_alert(client):
    """Verify fiat transaction structuring triggers alert rules and high/critical risk."""
    # Pre-seed in-degree
    for i in range(3):
        client.post("/api/v1/transactions/analyze", json={
            "tx_id": f"SEED_API_{i}",
            "account_from": f"SMURF_API_{i}",
            "account_to": "ACC_MULE_HUB",
            "amount": 9300.0,
        })

    payload = {
        "tx_id": "TX_API_STRUCT_999",
        "account_from": "SMURF_API_BOSS",
        "account_to": "ACC_MULE_HUB",
        "amount": 9500.0,
        "currency": "USD",
        "is_cross_border": True,
    }
    response = client.post("/api/v1/transactions/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["tx_id"] == "TX_API_STRUCT_999"
    assert data["risk_score"] >= 75.0
    assert data["risk_level"] in ("High", "Critical")
    assert data["alert_triggered"] is True
    assert "SUB_THRESHOLD_STRUCTURING" in data["fired_rules"]
    assert "FAN_IN_STRUCTURING" in data["fired_rules"]


def test_analyze_crypto_transaction_mixer_alert(client):
    """Verify crypto schema ingestion with mixer interaction."""
    payload = {
        "tx_hash": "0xfe34591a90c12847",
        "from_wallet": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "to_wallet": "3MixerTumblingProtocol",
        "amount_btc": 14.5,
        "currency": "BTC",
        "mixer_risk": True,
    }
    response = client.post("/api/v1/transactions/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["financial_rail"] == "crypto"
    assert data["risk_score"] >= 75.0
    assert data["risk_level"] in ("High", "Critical")
    assert data["alert_triggered"] is True
    assert "UNHOSTED_MIXER_PROXIMITY" in data["fired_rules"]


def test_batch_transactions_endpoint(client):
    """Verify /api/v1/transactions/batch evaluates list of transactions."""
    batch_payload = {
        "transactions": [
            {
                "tx_id": "TX_BATCH_01",
                "account_from": "ACC_USER_1",
                "account_to": "ACC_USER_2",
                "amount": 350.0,
            },
            {
                "tx_hash": "0xbatch_crypto_02",
                "from_wallet": "1CryptoUser",
                "to_wallet": "3DarknetMixer",
                "amount_btc": 5.0,
                "mixer_risk": True,
            },
            {
                "tx_id": "TX_BATCH_03",
                "account_from": "ACC_USER_3",
                "account_to": "ACC_USER_4",
                "amount": 9500.0,
            },
        ]
    }
    response = client.post("/api/v1/transactions/batch", json=batch_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 3
    assert len(data["results"]) == 3
    assert data["batch_id"].startswith("BATCH_")
    assert data["total_latency_ms"] >= 0.0


def test_investigate_subgraph_success(client):
    """Verify /api/v1/investigate/{tx_id}/subgraph returns vis.js & Cytoscape data."""
    # First inject a directed cycle: A -> B -> C -> A
    client.post("/api/v1/transactions/analyze", json={"tx_id": "CYC_API_1", "account_from": "NODE_A", "account_to": "NODE_B", "amount": 40000.0})
    client.post("/api/v1/transactions/analyze", json={"tx_id": "CYC_API_2", "account_from": "NODE_B", "account_to": "NODE_C", "amount": 39500.0})
    client.post("/api/v1/transactions/analyze", json={"tx_id": "CYC_API_3", "account_from": "NODE_C", "account_to": "NODE_A", "amount": 39000.0})

    response = client.get("/api/v1/investigate/CYC_API_3/subgraph")
    assert response.status_code == 200
    data = response.json()

    assert data["tx_id"] == "CYC_API_3"
    assert data["focal_entities"]["source"] == "NODE_C"
    assert data["focal_entities"]["target"] == "NODE_A"
    assert data["structural_metrics"]["cycle_count"] >= 1
    assert "FORENSIC INVESTIGATION DOSSIER" in data["investigator_summary"]

    # Verify vis.js format
    vis = data["vis_network"]
    assert "nodes" in vis and "edges" in vis
    assert len(vis["nodes"]) >= 3
    assert len(vis["edges"]) >= 3
    assert "color" in vis["nodes"][0]
    assert "from" in vis["edges"][0]
    assert "to" in vis["edges"][0]

    # Verify Cytoscape format
    cyto = data["cytoscape_elements"]
    assert len(cyto) >= 6
    assert any("source" in el["data"] for el in cyto)
    assert any("entity_type" in el["data"] for el in cyto)


def test_investigate_subgraph_not_found(client):
    """Verify 404 response when tx_id does not exist."""
    response = client.get("/api/v1/investigate/NON_EXISTENT_TX_ID/subgraph")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "HTTP_404"
    assert "not found" in data["error"]["message"].lower()


def test_validation_error_handling(client):
    """Verify 422 error response when payload fails Pydantic validation."""
    response = client.post("/api/v1/transactions/analyze", json={"amount": -50.0})
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
