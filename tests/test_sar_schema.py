from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.schemas.sar import (
    ReportingEntityType,
    PaymentRail,
    RiskTier,
    CaseStatus,
    SuspicionTypology,
    ReportingEntityInfo,
    SuspectEntityProfile,
    TransactionAuditRecord,
    MLTelemetry,
    GroundsOfSuspicion,
    SARCreateRequest,
    SARCaseRecord,
    SARListResponse,
    calculate_fiu_deadline,
    generate_sar_id,
)


def test_enumerations():
    assert ReportingEntityType.SCHEDULED_COMMERCIAL_BANK == "SCHEDULED_COMMERCIAL_BANK"
    assert ReportingEntityType.PAYMENT_AGGREGATOR == "PAYMENT_AGGREGATOR"
    assert ReportingEntityType.VIRTUAL_DIGITAL_ASSET_SERVICE_PROVIDER == "VIRTUAL_DIGITAL_ASSET_SERVICE_PROVIDER"

    assert PaymentRail.UPI == "UPI"
    assert PaymentRail.IMPS == "IMPS"
    assert PaymentRail.NEFT == "NEFT"
    assert PaymentRail.RTGS == "RTGS"
    assert PaymentRail.BTC == "BTC"
    assert PaymentRail.ETH == "ETH"

    assert RiskTier.CRITICAL_SAR == "CRITICAL_SAR"
    assert RiskTier.HIGH == "HIGH"
    assert RiskTier.ELEVATED == "ELEVATED"
    assert RiskTier.LOW == "LOW"

    # Backward-compatible aliases
    assert RiskTier.HIGH_RISK == "HIGH"
    assert RiskTier.ELEVATED_RISK == "ELEVATED"
    assert RiskTier.LOW_RISK == "LOW"

    assert CaseStatus.PENDING_REVIEW == "PENDING_REVIEW"
    assert CaseStatus.ESCALATED == "ESCALATED"
    assert CaseStatus.FILED_WITH_FIU == "FILED_WITH_FIU"
    assert CaseStatus.DISMISSED == "DISMISSED"

    assert SuspicionTypology.IN_TYP_STRUCT == "IN_TYP_STRUCT"
    assert SuspicionTypology.IN_TYP_HAWALA == "IN_TYP_HAWALA"
    assert SuspicionTypology.IN_TYP_MULE == "IN_TYP_MULE"
    assert SuspicionTypology.IN_TYP_VDA_MIX == "IN_TYP_VDA_MIX"


def test_calculate_fiu_deadline_7_working_days():
    # Fixed test date: Monday, Sept 7, 2026
    start_monday = datetime(2026, 9, 7, 10, 0, 0, tzinfo=timezone.utc)
    deadline = calculate_fiu_deadline(start_monday)

    # 7 working days from Monday:
    # Day 1: Tue Sept 8
    # Day 2: Wed Sept 9
    # Day 3: Thu Sept 10
    # Day 4: Fri Sept 11
    # Sat/Sun skipped (Sept 12, 13)
    # Day 5: Mon Sept 14
    # Day 6: Tue Sept 15
    # Day 7: Wed Sept 16
    assert deadline.year == 2026
    assert deadline.month == 9
    assert deadline.day == 16
    assert deadline.weekday() == 2  # Wednesday


def test_generate_sar_id_format():
    sar_id = generate_sar_id()
    assert sar_id.startswith("SAR-IND-")
    parts = sar_id.split("-")
    assert len(parts) == 4
    assert len(parts[2]) == 8  # YYYYMMDD
    assert len(parts[3]) == 6  # 6-char hex code


def test_reporting_entity_info_defaults():
    re_info = ReportingEntityInfo()
    assert re_info.fiureid == "FIU-RE-COMM-2026-9081"
    assert re_info.entity_name == "QuantumAML Nexus Surveillance Gateway"
    assert re_info.entity_category == ReportingEntityType.SCHEDULED_COMMERCIAL_BANK
    assert re_info.principal_officer_id == "PO-REG-8819"


def test_suspect_entity_profile():
    suspect = SuspectEntityProfile(
        entity_identifier="rohit.sharma@oksbi",
        entity_name="Rohit Sharma",
        entity_type="individual",
        institution_code="SBIN0001234",
        kyc_risk_tier=RiskTier.CRITICAL_SAR,
        is_pep=False,
        flags=["PAN_STRUCTURING_ATTEMPT", "HIGH_VELOCITY_BURST"],
    )
    assert suspect.entity_identifier == "rohit.sharma@oksbi"
    assert suspect.entity_type == "INDIVIDUAL"
    assert len(suspect.flags) == 2


def test_transaction_audit_record_validation():
    tx = TransactionAuditRecord(
        transaction_id="UTR-20260906-990182",
        timestamp=datetime.now(timezone.utc),
        rail=PaymentRail.UPI,
        amount=49850.00,
        currency="INR",
        counterparty_from="mule01@oksbi",
        counterparty_to="aggregator@okhdfcbank",
        risk_score=0.992,
        detected_anomalies=["IN_TYP_STRUCT"],
    )
    assert tx.amount == 49850.00
    assert tx.currency == "INR"
    assert tx.risk_score == 0.992

    # Amount must be strictly greater than 0
    with pytest.raises(ValidationError):
        TransactionAuditRecord(
            transaction_id="UTR-INVALID",
            rail=PaymentRail.UPI,
            amount=-100.0,
            counterparty_from="a",
            counterparty_to="b",
            risk_score=0.5,
        )

    # Risk score must be between 0.0 and 1.0
    with pytest.raises(ValidationError):
        TransactionAuditRecord(
            transaction_id="UTR-INVALID",
            rail=PaymentRail.UPI,
            amount=100.0,
            counterparty_from="a",
            counterparty_to="b",
            risk_score=1.5,
        )


def test_ml_telemetry():
    telemetry = MLTelemetry(
        model_name="CatBoost-Banking-v2.4",
        model_version="v2.4",
        inference_latency_ms=18.4,
        feature_importance={"amount_p99_ratio": 0.42, "velocity_burst": 0.31},
    )
    assert telemetry.model_name == "CatBoost-Banking-v2.4"
    assert telemetry.inference_latency_ms == 18.4
    assert telemetry.feature_importance["amount_p99_ratio"] == 0.42


def test_grounds_of_suspicion():
    grounds = GroundsOfSuspicion(
        primary_typology=SuspicionTypology.IN_TYP_STRUCT,
        secondary_typologies=[SuspicionTypology.IN_TYP_MULE],
        rule_triggers=["PMLA-RULE-3", "PAN-THRESHOLD-EVASION"],
        narrative_summary="Suspect conducted 8 consecutive UPI transactions strictly between ₹48,000 and ₹49,950 to evade PAN reporting.",
    )
    assert grounds.primary_typology == SuspicionTypology.IN_TYP_STRUCT
    assert len(grounds.secondary_typologies) == 1
    assert "PMLA-RULE-3" in grounds.rule_triggers


def test_sar_create_request():
    req = SARCreateRequest(
        transaction_ids=["UTR-20260906-881920", "UTR-20260906-881921"],
        primary_typology=SuspicionTypology.IN_TYP_STRUCT,
        investigator_notes="Flagged during real-time surveillance triage.",
        assigned_investigator="INV-PO-902",
    )
    assert len(req.transaction_ids) == 2
    assert req.primary_typology == SuspicionTypology.IN_TYP_STRUCT

    # Must contain at least one transaction ID
    with pytest.raises(ValidationError):
        SARCreateRequest(transaction_ids=[], primary_typology=SuspicionTypology.IN_TYP_STRUCT)


def test_sar_case_record_auto_exposure_calculation():
    tx1 = TransactionAuditRecord(
        transaction_id="UTR-20260906-001",
        rail=PaymentRail.UPI,
        amount=49000.00,
        currency="INR",
        counterparty_from="sender1@oksbi",
        counterparty_to="aggregator@okhdfcbank",
        risk_score=0.98,
    )
    tx2 = TransactionAuditRecord(
        transaction_id="UTR-20260906-002",
        rail=PaymentRail.IMPS,
        amount=49500.00,
        currency="INR",
        counterparty_from="sender2@okaxis",
        counterparty_to="aggregator@okhdfcbank",
        risk_score=0.99,
    )
    tx_btc = TransactionAuditRecord(
        transaction_id="btc_tx_hash_abc123",
        rail=PaymentRail.BTC,
        amount=1.542,
        currency="BTC",
        counterparty_from="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        counterparty_to="3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
        risk_score=0.96,
    )

    case = SARCaseRecord(
        suspect=SuspectEntityProfile(entity_identifier="aggregator@okhdfcbank"),
        transactions=[tx1, tx2, tx_btc],
        ml_telemetry=MLTelemetry(inference_latency_ms=22.1),
        grounds_of_suspicion=GroundsOfSuspicion(
            primary_typology=SuspicionTypology.IN_TYP_STRUCT,
            narrative_summary="Smurfing into aggregator VPA.",
        ),
    )

    assert case.sar_id.startswith("SAR-IND-")
    assert case.fiu_deadline is not None
    # Auto-computed exposure
    assert case.total_exposure_inr == 98500.00
    assert case.total_exposure_btc == 1.542
    assert case.status == CaseStatus.PENDING_REVIEW

    # Test JSON serialization
    json_data = case.model_dump_json()
    assert "SAR-IND-" in json_data
    assert "98500.0" in json_data
    assert "1.542" in json_data


def test_sar_list_response():
    resp = SARListResponse(
        total_count=0,
        page=1,
        page_size=20,
        items=[],
    )
    assert resp.total_count == 0
    assert resp.page == 1
    assert resp.items == []
