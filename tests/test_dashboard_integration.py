"""
tests/test_dashboard_integration.py
=============================================================================
Integration and unit tests for the investigator dashboard and triage endpoints.
Validates:
- GET /api/v1/alerts and query filtering
- POST /api/v1/alerts/{tx_id}/action state transitions
- GET /api/v1/investigate/{tx_id}/brief XAI integration
- GET /api/v1/investigate/{tx_id}/subgraph graph structure
- Dashboard helper functions (KPI calculation, role filtering)
=============================================================================
"""

import pytest
from fastapi.testclient import TestClient

from api_server import app
from agent_engine import agent_engine


def compute_kpis(alerts_data):
    total = len(alerts_data)
    open_count = sum(1 for a in alerts_data if a.get("triage_status") in ("OPEN", "PENDING"))
    escalated = sum(1 for a in alerts_data if a.get("triage_status") in ("ESCALATED", "ESCALATED_LEO"))
    approved = sum(1 for a in alerts_data if a.get("triage_status") in ("APPROVED", "APPROVED_SAR"))
    cleared = sum(1 for a in alerts_data if a.get("triage_status") in ("CLEARED", "CLEARED_FALSE_POSITIVE", "DISMISSED"))
    breaches = sum(1 for a in alerts_data if a.get("regulatory_breach") or a.get("amount_usd", 0.0) >= 10000.0 or a.get("amount", 0.0) >= 10000.0)
    scores = [a.get("risk_score", 0.0) for a in alerts_data if "risk_score" in a]
    avg_risk = round(sum(scores) / len(scores), 1) if scores else 0.0
    return {
        "total": total,
        "open": open_count,
        "escalated": escalated,
        "approved": approved,
        "cleared": cleared,
        "breaches": breaches,
        "avg_risk": avg_risk,
    }


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_dashboard_alert_triage_flow(client):
    """Test full cycle: analyze suspicious tx -> alert appears -> triage action applied."""
    # 1. Inject a high-risk transaction
    high_risk_tx = {
        "tx_id": "TX_DASH_ALERT_01",
        "account_from": "ACC_SUSPECT_DASH_1",
        "account_to": "ACC_SUSPECT_DASH_2",
        "amount": 9999.0,
        "currency": "USD",
        "is_peeling_chain": True,
        "hop_count": 6,
        "is_mixer": True,
    }
    analyze_res = client.post("/api/v1/transactions/analyze", json=high_risk_tx)
    assert analyze_res.status_code == 200
    res_data = analyze_res.json()
    assert res_data["risk_score"] >= 75.0
    assert res_data["alert_triggered"] is True

    # 2. Query /api/v1/alerts
    alerts_res = client.get("/api/v1/alerts?min_risk=70&triage_status=OPEN")
    assert alerts_res.status_code == 200
    alerts_data = alerts_res.json()
    assert alerts_data["total"] >= 1
    found_alert = next((a for a in alerts_data["alerts"] if a["tx_id"] == "TX_DASH_ALERT_01"), None)
    assert found_alert is not None
    assert found_alert["triage_status"] == "OPEN"

    # 3. Apply an action: ESCALATE
    action_payload = {
        "action": "ESCALATE",
        "analyst_id": "ANALYST_007",
        "notes": "Escalated to FinCEN and FIU due to multi-hop peeling and mixer flags.",
    }
    action_res = client.post("/api/v1/alerts/TX_DASH_ALERT_01/action", json=action_payload)
    assert action_res.status_code == 200
    action_data = action_res.json()
    assert action_data["status"] == "success"
    assert action_data["tx_id"] == "TX_DASH_ALERT_01"
    assert action_data["new_triage_status"] == "ESCALATED_LEO"

    # 4. Verify /api/v1/alerts filtered by triage_status=ESCALATED_LEO returns it
    esc_res = client.get("/api/v1/alerts?triage_status=ESCALATED_LEO")
    assert esc_res.status_code == 200
    esc_data = esc_res.json()
    assert any(a["tx_id"] == "TX_DASH_ALERT_01" for a in esc_data["alerts"])

    # 5. Apply an action: APPROVE
    approve_payload = {
        "action": "APPROVE",
        "analyst_id": "COMPLIANCE_HEAD",
        "notes": "SAR narrative approved for regulatory filing.",
    }
    approve_res = client.post("/api/v1/alerts/TX_DASH_ALERT_01/action", json=approve_payload)
    assert approve_res.status_code == 200
    assert approve_res.json()["new_triage_status"] == "APPROVED_SAR"


def test_investigate_brief_endpoint(client):
    """Test GET /api/v1/investigate/{tx_id}/brief returns XAI narrative and SHAP contributions."""
    tx_id = "TX_BRIEF_TEST_99"
    high_risk_tx = {
        "tx_id": tx_id,
        "account_from": "ACC_ORIGIN_99",
        "account_to": "ACC_DEST_99",
        "amount": 9850.0,
        "currency": "USD",
        "velocity_1h": 14,
    }
    client.post("/api/v1/transactions/analyze", json=high_risk_tx)

    brief_res = client.get(f"/api/v1/investigate/{tx_id}/brief")
    assert brief_res.status_code == 200
    brief_data = brief_res.json()
    assert brief_data["tx_id"] == tx_id
    assert "plain_text_narrative" in brief_data
    assert "SUSPICIOUS ACTIVITY REPORT" in brief_data["plain_text_narrative"]
    assert "key_risk_factors" in brief_data
    assert isinstance(brief_data["key_risk_factors"], list)
    assert "structural_metrics" in brief_data


def test_investigate_subgraph_endpoint(client):
    """Test GET /api/v1/investigate/{tx_id}/subgraph returns nodes and edges formatted for visualization."""
    tx_id = "TX_GRAPH_TEST_77"
    tx_payload = {
        "tx_id": tx_id,
        "account_from": "ACC_NODE_A",
        "account_to": "ACC_NODE_B",
        "amount": 4500.0,
        "currency": "EUR",
    }
    client.post("/api/v1/transactions/analyze", json=tx_payload)

    graph_res = client.get(f"/api/v1/investigate/{tx_id}/subgraph")
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert "tx_id" in graph_data
    assert graph_data["tx_id"] == tx_id

    # Check node attributes
    node_ids = [n.get("node_id") or n.get("id") for n in graph_data["nodes"]]
    assert "ACC_NODE_A" in node_ids
    assert "ACC_NODE_B" in node_ids

    # Check edge attributes
    edge = next((e for e in graph_data["edges"] if e["source"] == "ACC_NODE_A" and e["target"] == "ACC_NODE_B"), None)
    assert edge is not None
    assert edge["amount"] == 4500.0


def test_dashboard_kpis_calculation():
    """Test compute_kpis logic on a list of alert dictionaries."""
    mock_alerts = [
        {"risk_score": 90.0, "triage_status": "OPEN", "regulatory_breach": True},
        {"risk_score": 85.0, "triage_status": "ESCALATED", "regulatory_breach": True},
        {"risk_score": 80.0, "triage_status": "APPROVED", "regulatory_breach": False},
        {"risk_score": 76.0, "triage_status": "CLEARED", "regulatory_breach": False},
    ]
    kpis = compute_kpis(mock_alerts)
    assert kpis["total"] == 4
    assert kpis["open"] == 1
    assert kpis["escalated"] == 1
    assert kpis["approved"] == 1
    assert kpis["cleared"] == 1
    assert kpis["breaches"] == 2
    assert kpis["avg_risk"] == 82.8


def test_invalid_action_rejected(client):
    """Test that unrecognized alert action is rejected with 400 or 422."""
    invalid_payload = {
        "action": "INVALID_ACTION_NAME",
        "analyst_id": "TEST_USER",
    }
    res = client.post("/api/v1/alerts/NONEXISTENT_TX/action", json=invalid_payload)
    assert res.status_code in (400, 422)
