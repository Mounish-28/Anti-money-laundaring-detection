"""
tests/test_xai_explainer.py
=============================================================================
Unit & Integration tests for XAI Explainer in xai_explainer.py
=============================================================================
"""

import networkx as nx
import pytest
from fastapi.testclient import TestClient

from api_server import app
from xai_explainer import AMLThreatExplainer, threat_explainer


@pytest.fixture
def explainer():
    return AMLThreatExplainer()


def test_feature_attribution_extraction_structuring(explainer):
    """Verify local SHAP extraction isolates structuring and velocity surge."""
    features = {
        "amount_usd": 9500.0,
        "vol_1h": 28500.0,
        "vol_24h": 32000.0,
        "surge_ratio": 4.1,
        "is_structuring": 1.0,
        "inter_arrival_sec": 42.0,
        "is_cross_border": 1.0,
    }
    attributions = explainer.extract_feature_attributions(features)

    assert len(attributions) == 7
    total_pct = sum(a.contribution_percentage for a in attributions)
    assert 99.0 <= total_pct <= 101.0  # Normalized to ~100%

    top_feature_names = [a.feature_name for a in attributions[:3]]
    # Structuring or velocity surge should be in the top 3
    assert any(f in top_feature_names for f in ("is_structuring", "surge_ratio", "inter_arrival_sec"))
    assert attributions[0].contribution_percentage > 15.0


def test_topological_context_mapping_cycles(explainer):
    """Verify 2-hop neighborhood extraction and closed cycle detection."""
    g = nx.DiGraph()
    g.add_edge("ACC_1", "ACC_2", amount_usd=50000.0, tx_id="TX_C1")
    g.add_edge("ACC_2", "ACC_3", amount_usd=49500.0, tx_id="TX_C2")
    g.add_edge("ACC_3", "ACC_1", amount_usd=49000.0, tx_id="TX_C3")

    topo_ctx = explainer.map_topological_context(
        graph_data=g,
        source_node="ACC_3",
        target_node="ACC_1",
    )

    assert topo_ctx.focal_source == "ACC_3"
    assert topo_ctx.focal_target == "ACC_1"
    assert topo_ctx.cycle_detected is True
    assert len(topo_ctx.detected_cycles) >= 1
    assert topo_ctx.pass_through_equality >= 0.90
    assert topo_ctx.total_subgraph_nodes == 3
    assert topo_ctx.total_subgraph_edges == 3


def test_topological_context_mixer_hop(explainer):
    """Verify detection of high-risk crypto mixer intermediate hops."""
    g = nx.DiGraph()
    g.add_edge("0xAliceWallet", "0xIntermediaryMule", amount_usd=85000.0, tx_id="TX_M1")
    g.add_edge("0xIntermediaryMule", "0xTornadoCashMixerCluster", amount_usd=84000.0, tx_id="TX_M2")

    topo_ctx = explainer.map_topological_context(
        graph_data=g,
        source_node="0xAliceWallet",
        target_node="0xIntermediaryMule",
    )

    assert any("TORNADO" in hop.upper() for hop in topo_ctx.intermediate_high_risk_hops)


def test_highlighted_graph_path_cycle(explainer):
    """Verify highlighted path isolates the full cycle loop for UI rendering."""
    g = nx.DiGraph()
    g.add_edge("A", "B", amount_usd=10000.0, tx_id="TX_1")
    g.add_edge("B", "C", amount_usd=9800.0, tx_id="TX_2")
    g.add_edge("C", "A", amount_usd=9600.0, tx_id="TX_3")

    topo_ctx = explainer.map_topological_context(g, "C", "A")
    path = explainer.extract_highlighted_graph_path(topo_ctx, g, "TX_3")

    assert path.path_type == "DIRECTED_CYCLE"
    assert len(path.node_ids) >= 4  # e.g. [C, A, B, C]
    assert path.node_ids[0] == path.node_ids[-1]  # Closed loop


def test_generate_sar_narrative(explainer):
    """Verify automated FinCEN Form 111 SAR narrative synthesis."""
    g = nx.DiGraph()
    g.add_edge("ACC_SND", "ACC_RCV", amount_usd=9500.0, tx_id="TX_SAR_TEST")

    topo_ctx = explainer.map_topological_context(g, "ACC_SND", "ACC_RCV")
    attributions = explainer.extract_feature_attributions({
        "amount_usd": 9500.0,
        "is_structuring": 1.0,
        "surge_ratio": 3.5,
    })
    path = explainer.extract_highlighted_graph_path(topo_ctx, g, "TX_SAR_TEST")

    narrative = explainer.generate_sar_narrative(
        tx_id="TX_SAR_TEST",
        focal_source="ACC_SND",
        focal_target="ACC_RCV",
        amount_usd=9500.0,
        currency="USD",
        primary_typology="Bank Secrecy Act CTR Structuring Evasion",
        risk_score=94.5,
        attributions=attributions,
        topo_ctx=topo_ctx,
        highlighted_path=path,
    )

    assert "FINCEN SUSPICIOUS ACTIVITY REPORT (SAR)" in narrative
    assert "TX_SAR_TEST" in narrative
    assert "ACC_SND" in narrative
    assert "ACC_RCV" in narrative
    assert "$9,500.00 USD" in narrative
    assert "Bank Secrecy Act CTR Structuring Evasion" in narrative
    assert "31 CFR § 1020.320" in narrative
    assert "SHA-256:" in narrative


def test_generate_investigation_brief_json(explainer):
    """Verify generate_investigation_brief returns complete structured JSON payload."""
    g = nx.DiGraph()
    g.add_edge("ACC_A", "ACC_B", amount_usd=9450.0, tx_id="TX_BRIEF_01")
    g.add_edge("ACC_B", "ACC_C", amount_usd=9400.0, tx_id="TX_BRIEF_02")
    g.add_edge("ACC_C", "ACC_A", amount_usd=9350.0, tx_id="TX_BRIEF_03")

    brief = explainer.generate_investigation_brief(
        tx_id="TX_BRIEF_03",
        graph_data=g,
        model_features={
            "amount_usd": 9350.0,
            "vol_1h": 28200.0,
            "surge_ratio": 4.0,
            "is_structuring": 1.0,
            "inter_arrival_sec": 30.0,
        },
    )

    assert brief["tx_id"] == "TX_BRIEF_03"
    assert "primary_typology" in brief
    assert "plain_text_narrative" in brief
    assert "key_risk_factors" in brief
    assert len(brief["key_risk_factors"]) >= 3
    assert "highlighted_graph_path" in brief
    assert "structural_metrics" in brief
    assert len(brief["recommended_actions"]) >= 3
    assert len(brief["audit_hash"]) == 64


def test_api_investigation_brief_endpoint():
    """Verify GET /api/v1/investigate/{tx_id}/brief in FastAPI server."""
    client = TestClient(app)

    # Ingest a transaction first
    client.post("/api/v1/transactions/analyze", json={
        "tx_id": "TX_BRIEF_API_999",
        "account_from": "ACC_SUSPECT_ORIGIN",
        "account_to": "ACC_MULE_TERMINUS",
        "amount": 9500.0,
        "currency": "USD",
        "is_cross_border": True,
    })

    response = client.get("/api/v1/investigate/TX_BRIEF_API_999/brief")
    assert response.status_code == 200
    data = response.json()

    assert data["tx_id"] == "TX_BRIEF_API_999"
    assert data["focal_entities"]["source"] == "ACC_SUSPECT_ORIGIN"
    assert data["focal_entities"]["target"] == "ACC_MULE_TERMINUS"
    assert len(data["key_risk_factors"]) >= 3
    assert "plain_text_narrative" in data
    assert "highlighted_graph_path" in data
    assert "recommended_actions" in data
