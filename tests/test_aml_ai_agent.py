"""
tests/test_aml_ai_agent.py
=============================================================================
QuantumAML Nexus -- Unit Tests for High-Throughput Multi-Tier AML AI Agent
=============================================================================
"""

import os
import pytest
from app.services.aml_ai_agent import aml_ai_agent, HighThroughputAMLAIAgent
from app.services.auth_verifier import create_test_jwt


def test_agent_initialization():
    """Verify that the HighThroughputAMLAIAgent initializes with all engines."""
    agent = HighThroughputAMLAIAgent()
    assert agent.gnn_engine is not None
    assert agent.velocity_engine is not None
    assert agent.analyst is not None
    assert len(agent.audit_hash_chain) >= 1
    assert "IBM-AML" in agent.thresholds
    assert "Elliptic" in agent.thresholds


def test_agent_analyze_banking_stream_structuring():
    """Verify agent evaluation of core banking transaction with structuring typology."""
    event = {
        "tx_id": "TX_TEST_BANK_001",
        "dataset": "IBM-AML",
        "account_from": "ACC_SMURF_RING_999",
        "account_to": "ACC_MULE_COLLECTOR",
        "amount": 9500.0,
        "currency": "USD",
        "is_cross_border": True,
        "velocity_surge": 3.2,
    }
    decision = aml_ai_agent.analyze_transaction_stream(event, channel="CORE_BANKING_WS")

    assert decision.tx_id == "TX_TEST_BANK_001"
    assert decision.channel == "CORE_BANKING_WS"
    assert decision.severity_tier in ("CRITICAL_SAR", "HIGH")
    assert decision.is_escalated_sar is True
    assert decision.gnn_risk_score >= 0.85
    assert decision.composite_posterior_risk >= 0.85
    assert decision.topological_profile["fan_in_degree"] >= 3
    assert decision.velocity_profile["is_velocity_anomalous"] is True

    # Check that Centralized AI Subgraph Analyst was triggered
    assert decision.forensic_subgraph_report is not None
    report = decision.forensic_subgraph_report
    assert report["target_entity"] == "ACC_SMURF_RING_999"
    assert "SUBJECT IDENTIFICATION" in report["regulatory_narrative"] or "SUBJECT INVESTIGATION" in report["regulatory_narrative"]
    assert len(report["subgraph_nodes"]) >= 3
    assert len(decision.audit_hash) == 64


def test_agent_analyze_crypto_feed_mixer():
    """Verify agent evaluation of crypto mempool screening feed with mixer hop."""
    crypto_event = {
        "tx_hash": "0xfe34591a90c",
        "dataset": "Elliptic",
        "from_wallet": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "to_wallet": "3MixerCluster99",
        "amount_btc": 15.5,
        "mixer_risk": True,
    }
    decision = aml_ai_agent.analyze_transaction_stream(crypto_event, channel="CRYPTO_SCREENING_FEED")

    assert decision.channel == "CRYPTO_SCREENING_FEED"
    assert decision.severity_tier in ("CRITICAL_SAR", "HIGH")
    assert "UNHOSTED_MIXER_PROXIMITY" in decision.topological_profile["detected_typologies"]
    assert decision.forensic_subgraph_report is not None


def test_agent_rbac_authorization_and_collaboration():
    """Verify RBAC role enforcement, case creation, and tamper-evident collaboration."""
    leo_token = create_test_jwt(role="LEO_INVESTIGATION_OFFICER", user_id="officer_77")
    bank_token = create_test_jwt(role="BANK_COMPLIANCE_OFFICER", user_id="risk_manager_12")

    # 1. Test Banking Stream Event
    event = {
        "tx_id": "TX_CASE_001",
        "dataset": "SAML-D",
        "account_from": "ACC_SUSPECT_404",
        "account_to": "ACC_SHELL_CORP",
        "amount": 25000.0,
        "is_cycle": True,
        "velocity_surge": 3.0,
    }
    decision = aml_ai_agent.analyze_transaction_stream(event)

    # 2. Case Creation
    case = aml_ai_agent.create_investigative_case(
        decision=decision,
        created_by_user="officer_77",
        created_by_role="LEO_INVESTIGATION_OFFICER",
    )
    assert case.case_id.startswith("CASE-SAM")
    assert case.target_entity == "ACC_SUSPECT_404"

    # 3. LEO appends note -> Should Succeed
    ok, msg, updated_case = aml_ai_agent.append_investigator_note(
        case_id=case.case_id,
        jwt_token=leo_token,
        note_content="Subject linked to offshore entity in FinCEN 314(a) match list.",
    )
    assert ok is True
    assert len(updated_case.investigator_notes) == 1
    assert len(updated_case.tamper_evident_chain) == 2  # initial + note

    # 4. Bank Official tries to append LEO note -> Should Fail RBAC
    ok_bank, msg_bank, _ = aml_ai_agent.append_investigator_note(
        case_id=case.case_id,
        jwt_token=bank_token,
        note_content="Bank trying to add LEO note.",
    )
    assert ok_bank is False
    assert "requires Law Enforcement credentials" in msg_bank

    # 5. Bank Official tunes threshold -> Should Succeed
    tune_ok, tune_msg, new_t = aml_ai_agent.tune_operational_threshold(
        dataset="SAML-D",
        jwt_token=bank_token,
        new_threshold=0.6500,
    )
    assert tune_ok is True
    assert new_t == 0.6500

    # 6. LEO tries to tune threshold -> Should Fail RBAC
    tune_leo_ok, tune_leo_msg, _ = aml_ai_agent.tune_operational_threshold(
        dataset="SAML-D",
        jwt_token=leo_token,
        new_threshold=0.7000,
    )
    assert tune_leo_ok is False
    assert "requires Bank Official credentials" in tune_leo_msg
