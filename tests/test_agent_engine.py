"""
tests/test_agent_engine.py
=============================================================================
Unit tests for AMLAgent core pipeline in agent_engine.py
=============================================================================
"""

import pytest
from agent_engine import AMLAgent, normalize_transaction_payload


def test_agent_initialization():
    agent = AMLAgent(alert_threshold=75.0)
    assert agent.alert_threshold == 75.0
    assert len(agent.audit_chain) == 1
    assert agent.graph.number_of_nodes() == 0


def test_normal_fiat_no_alert():
    agent = AMLAgent(alert_threshold=75.0)
    payload = {
        "tx_id": "TX_NORM_101",
        "account_from": "ACC_USER_A",
        "account_to": "ACC_USER_B",
        "amount": 150.0,
        "currency": "USD",
    }
    decision = agent.process_transaction(payload)
    assert decision["tx_id"] == "TX_NORM_101"
    assert decision["aggregate_risk_score"] < 75.0
    assert decision["alert_triggered"] is False
    assert decision["alert_payload"] is None
    assert decision["severity_tier"] == "LOW_NOMINAL"


def test_smurfing_structuring_alert():
    agent = AMLAgent(alert_threshold=75.0)
    # Pre-seed 3 inbound transactions to ACC_COLLECTOR
    for i in range(3):
        agent.process_transaction({
            "tx_id": f"SEED_{i}",
            "account_from": f"MULE_{i}",
            "account_to": "ACC_COLLECTOR",
            "amount": 9200.0,
        })

    # Structuring trigger
    trigger_payload = {
        "tx_id": "TX_SMURF_FIRE",
        "account_from": "MULE_99",
        "account_to": "ACC_COLLECTOR",
        "amount": 9650.0,
        "currency": "USD",
    }
    decision = agent.process_transaction(trigger_payload)
    assert decision["alert_triggered"] is True
    assert decision["aggregate_risk_score"] >= 75.0
    assert "SUB_THRESHOLD_STRUCTURING" in decision["reason_codes"]
    assert "FAN_IN_STRUCTURING" in decision["reason_codes"]
    assert decision["alert_payload"] is not None
    assert decision["alert_payload"]["severity_tier"] in ("CRITICAL_SAR", "HIGH_RISK")


def test_directed_cycle_detection():
    agent = AMLAgent(alert_threshold=75.0)
    agent.process_transaction({"tx_id": "CYC_1", "account_from": "NODE_1", "account_to": "NODE_2", "amount": 20000.0})
    agent.process_transaction({"tx_id": "CYC_2", "account_from": "NODE_2", "account_to": "NODE_3", "amount": 19500.0})
    cycle_close = agent.process_transaction({"tx_id": "CYC_3", "account_from": "NODE_3", "account_to": "NODE_1", "amount": 19200.0})

    assert cycle_close["alert_triggered"] is True
    assert cycle_close["aggregate_risk_score"] >= 90.0
    assert "CYCLE_CIRCULAR_LAYERING" in cycle_close["reason_codes"]


def test_crypto_mixer_alert():
    agent = AMLAgent(alert_threshold=75.0)
    crypto_payload = {
        "tx_hash": "0xabc9876543210def",
        "from_wallet": "1WalletAlice",
        "to_wallet": "3MixerProtocol",
        "amount_btc": 10.0,
        "mixer_risk": True,
    }
    decision = agent.process_transaction(crypto_payload)
    assert decision["alert_triggered"] is True
    assert decision["rail"] == "crypto"
    assert "UNHOSTED_MIXER_PROXIMITY" in decision["reason_codes"]


def test_explain_decision_2hop_subgraph():
    agent = AMLAgent(alert_threshold=75.0)
    agent.process_transaction({"tx_id": "TX_EXP_1", "account_from": "ACC_X", "account_to": "ACC_Y", "amount": 30000.0})
    agent.process_transaction({"tx_id": "TX_EXP_2", "account_from": "ACC_Y", "account_to": "ACC_Z", "amount": 29000.0})
    agent.process_transaction({"tx_id": "TX_EXP_3", "account_from": "ACC_Z", "account_to": "ACC_X", "amount": 28500.0})

    explanation = agent.explain_decision("TX_EXP_3")
    assert explanation["tx_id"] == "TX_EXP_3"
    assert explanation["focal_entities"]["source"] == "ACC_Z"
    assert explanation["focal_entities"]["target"] == "ACC_X"
    assert "structural_metrics" in explanation
    assert explanation["structural_metrics"]["cycle_count"] >= 1
    assert len(explanation["subgraph"]["nodes"]) >= 3
    assert len(explanation["subgraph"]["edges"]) >= 3
    assert "FORENSIC INVESTIGATION DOSSIER" in explanation["investigator_summary"]
    assert "DIRECTED CYCLE DETECTED" in explanation["investigator_summary"]
