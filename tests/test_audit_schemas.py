import os
import sys

_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base not in sys.path:
    sys.path.insert(0, _base)

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from app.schemas import (  # noqa: E402
    TransactionInput,
    TimeSeriesInput,
    EllipticNodeInput,
    SAMLDInput,
    RiskEvaluationResponse,
)


def test_transaction_input():
    tx = TransactionInput(
        transaction_id="tx_test_001",
        from_bank="Bank_A",
        to_bank="Bank_B",
        account_from="ACC_1001",
        account_to="ACC_2002",
        amount=1250.50,
        currency="USD",
        payment_format="Wire Transfer",
    )
    assert tx.transaction_id == "tx_test_001"
    assert tx.amount == 1250.50

    # Negative or zero amount should fail
    with pytest.raises(ValidationError):
        TransactionInput(
            transaction_id="tx_bad",
            from_bank="A",
            to_bank="B",
            account_from="1",
            account_to="2",
            amount=-10.0,
            currency="USD",
            payment_format="Wire",
        )


def test_time_series_input():
    ts = TimeSeriesInput(
        account_id="ACC_TS_01",
        amount=750.25,
        ema_1h=720.0,
        ema_24h=710.0,
        ema_7d=690.0,
        delta_t_seconds=3600.0,
        burstiness_index=1.23,
        sin_hour=0.5,
        cos_hour=0.866,
        sin_dow=0.0,
        cos_dow=1.0,
    )
    assert ts.account_id == "ACC_TS_01"
    assert ts.burstiness_index == 1.23


def test_elliptic_node_input_enforces_166():
    # Exactly 166 features should succeed
    valid_features = [0.123] * 166
    node = EllipticNodeInput(node_id="node_valid_166", features=valid_features)
    assert node.node_id == "node_valid_166"
    assert len(node.features) == 166

    # 165 features should fail
    with pytest.raises(ValidationError):
        EllipticNodeInput(node_id="node_fail_165", features=[0.123] * 165)

    # 167 features should fail
    with pytest.raises(ValidationError):
        EllipticNodeInput(node_id="node_fail_167", features=[0.123] * 167)


def test_samld_input():
    saml = SAMLDInput(
        transaction_id="saml_tx_999",
        sender_id="SND_500",
        receiver_id="RCV_600",
        amount=50000.0,
        fan_in_count=25,
        fan_out_count=8,
        sender_velocity_24h=12.4,
    )
    assert saml.transaction_id == "saml_tx_999"
    assert saml.fan_in_count == 25


def test_risk_evaluation_response():
    resp = RiskEvaluationResponse(
        entity_id="entity_eval_01",
        dataset="ibm_transactions",
        risk_score=0.988,
        risk_tier="CRITICAL_SAR",
        is_anomaly=True,
        recommended_action="FILE_SAR_IMMEDIATELY",
        latency_ms=2.15,
        metadata={"model_type": "XGBoost", "version": "1.0"},
    )
    assert resp.entity_id == "entity_eval_01"
    assert resp.risk_tier == "CRITICAL_SAR"
    assert resp.is_anomaly is True


if __name__ == "__main__":
    test_transaction_input()
    test_time_series_input()
    test_elliptic_node_input_enforces_166()
    test_samld_input()
    test_risk_evaluation_response()
    print("All Pydantic schema validation tests passed successfully!")
