"""
tests/test_enterprise_architecture_spec.py
=============================================================================
QuantumAML Nexus -- Unit & Integration Tests for Enterprise Three-Tier AML Platform
=============================================================================
Tests:
  1. Architecture Specification Documentation Integrity
  2. 5-Dataset Standardized Evaluation Mandates Verification
  3. High-Throughput Streaming Ingestion Gateway (Banking WS & Crypto Feeds)
  4. Centralized AI Assistant Layer (Node Subgraph Analysis & FinCEN Narratives)
  5. Role-Based Access Control (RBAC) Logic & Operational Isolation
=============================================================================
"""

import json
import os
import pytest

from app.services.ai_subgraph_analyst import ai_subgraph_analyst
from app.services.streaming_ingestion_gateway import StreamingIngestionGateway


@pytest.fixture(scope="module")
def root_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_architecture_spec_doc_exists(root_dir):
    """Verify that ENTERPRISE_THREE_TIER_ARCHITECTURE_SPEC.md exists with all required sections."""
    spec_path = os.path.join(root_dir, "docs", "ENTERPRISE_THREE_TIER_ARCHITECTURE_SPEC.md")
    assert os.path.exists(spec_path), f"Architecture spec missing: {spec_path}"

    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Tier 1: Presentation & RBAC Operational Portals" in content
    assert "Tier 2: Real-Time Stream Ingestion, AI Engine & Model Serving" in content
    assert "Tier 3: Distributed Data, Model Weights & Governance Registry" in content
    assert "five_dataset_new_evaluation_results.json" in content
    assert "Mandate 1: Operational Recall" in content
    assert "Mandate 2: Rank-Ordered Prioritization" in content
    assert "Mandate 3: Financial Cost-Benefit Optimization" in content
    assert "Mandate 4: Model Calibration, Population Stability & SLA Latency" in content
    assert "Centralized AI Assistant Layer" in content
    assert "High-Throughput Ingestion Architecture" in content


def test_five_dataset_new_evaluation_results_mandates(root_dir):
    """Verify that five_dataset_new_evaluation_results.json adheres to standardized 4-mandate schema."""
    json_path = os.path.join(root_dir, "five_dataset_new_evaluation_results.json")
    assert os.path.exists(json_path), f"Missing evaluation results file: {json_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 5, f"Expected 5 datasets, got {len(data)}"
    dataset_names = [d["Dataset"] for d in data]
    expected_names = [
        "IBM Transactions",
        "SAML-D",
        "Elliptic Bitcoin",
        "IBM AMLSim",
        "Time-Series AML",
    ]
    for exp in expected_names:
        assert exp in dataset_names, f"Dataset '{exp}' missing from results"

    for d in data:
        # Check all 4 mandates exist
        assert "Mandate_1_Operational_Recall" in d
        assert "Mandate_2_Rank_Ordered_Prioritization" in d
        assert "Mandate_3_Financial_Cost_Benefit" in d
        assert "Mandate_4_Calibration_and_Stability" in d

        # Mandate 1 Checks
        m1 = d["Mandate_1_Operational_Recall"]
        assert "Target_Recall_95" in m1
        assert "Target_Recall_99" in m1
        assert m1["Target_Recall_95"]["Daily_Sustainable_Tx_Capacity_20_FTE"] > 0

        # Mandate 2 Checks
        m2 = d["Mandate_2_Rank_Ordered_Prioritization"]
        assert "P@10" in m2
        assert "P@100" in m2
        assert "P@500" in m2

        # Mandate 3 Checks
        m3 = d["Mandate_3_Financial_Cost_Benefit"]
        assert m3["Net_Financial_Savings_Per_1M_USD"] > 0
        assert "1,272.7" in m3["Cost_Ratio_FN_to_FP"]

        # Mandate 4 Checks
        m4 = d["Mandate_4_Calibration_and_Stability"]
        assert m4["P95_Inference_Latency_MS"] < 25.0
        assert m4["Drift_Status"] == "NOMINAL_STABLE"


def test_streaming_ingestion_gateway():
    """Verify high-throughput streaming ingestion for both Banking WebSockets and Crypto Feeds."""
    gateway = StreamingIngestionGateway(buffer_capacity=500)

    # Ingest Banking WebSocket Event
    banking_event = {
        "tx_id": "TEST_WS_001",
        "dataset": "IBM-AML",
        "account_from": "ACC_ORIGIN_999",
        "account_to": "ACC_DEST_100",
        "amount": 9500.0,
        "currency": "USD",
        "is_cross_border": True,
    }
    b_alert = gateway.ingest_banking_websocket_event(banking_event)
    assert b_alert.event_id == "TEST_WS_001"
    assert b_alert.channel == "CORE_BANKING_WS"
    assert b_alert.is_sar is True  # Structuring amount ($9,500) with origin 999 triggers SAR
    assert b_alert.severity_tier in ("CRITICAL_SAR", "HIGH_RISK")

    # Ingest Crypto Screening Feed Event
    crypto_event = {
        "tx_hash": "0xabc123def456",
        "from_wallet": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "to_wallet": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
        "amount_btc": 12.5,
        "mixer_risk": True,
    }
    c_alert = gateway.ingest_crypto_feed_event(crypto_event)
    assert c_alert.event_id == "0xabc123def456"
    assert c_alert.channel == "CRYPTO_SCREENING_FEED"
    assert c_alert.is_sar is True

    # Check Gateway Metrics
    assert gateway.stats["banking_events_ingested"] == 1
    assert gateway.stats["crypto_events_ingested"] == 1
    assert gateway.stats["total_evaluated"] == 2
    assert gateway.stats["p95_latency_ms"] >= 0.0

    # Stream Burst Simulation
    burst_alerts = gateway.generate_simulated_stream_burst(burst_size=20)
    assert len(burst_alerts) == 20
    assert len(gateway.event_buffer) == 22
    assert len(gateway.get_live_surveillance_ledger()) == 22


def test_ai_subgraph_analyst_realtime_forensics():
    """Verify centralized AI assistant layer performs node-level subgraph analysis and narrative synthesis."""
    report = ai_subgraph_analyst.analyze_node_subgraph(
        entity_id="ACC_SMURF_RING_TEST",
        entity_type="BANK_ACCOUNT",
        hop_depth=2,
        seed_amount=35000.0,
        detected_risk=0.91,
    )

    assert report.target_entity == "ACC_SMURF_RING_TEST"
    assert report.overall_threat_level in ("CRITICAL_THREAT", "HIGH")
    assert report.composite_threat_score == 0.91
    assert len(report.detected_typologies) > 0
    assert len(report.subgraph_nodes) >= 3
    assert len(report.subgraph_edges) >= 2

    # Structural metrics check
    sm = report.structural_metrics
    assert sm["total_in_flow_usd"] > 0
    assert sm["total_out_flow_usd"] > 0
    assert sm["pass_through_ratio"] >= 0.0
    assert sm["node_degree_centrality"] > 0

    # FinCEN Narrative checks
    assert "SUBJECT INVESTIGATION" in report.regulatory_narrative
    assert "RECOMMENDATION:" in report.suggested_law_enforcement_action
