"""
Unit Tests for QuantumAML Nexus SAR Exporter (app/services/sar_exporter.py)
===========================================================================

Validates:
1. FIU-IND FINnet 2.0 JSON structure generation and serialization.
2. ReportLab forensic PDF generation (A4, headers, footers, tables).
3. Support for both Fiat (INR) structuring and Crypto (BTC) mixer dossiers.
4. Multi-transaction table formatting without overflow.
"""

import json
from datetime import datetime, timezone
import pytest

from app.schemas.sar import (
    CaseStatus,
    GroundsOfSuspicion,
    MLTelemetry,
    PaymentRail,
    ReportingEntityInfo,
    RiskTier,
    SARCaseRecord,
    SuspectEntityProfile,
    SuspicionTypology,
    TransactionAuditRecord,
    calculate_fiu_deadline,
)
from app.services.sar_exporter import (
    SARExporter,
    export_fiu_json,
    generate_sar_pdf,
    sar_exporter,
)


@pytest.fixture
def sample_fiat_case():
    """Creates a realistic fiat structuring SAR case with 2 aggregated transactions."""
    now = datetime.now(timezone.utc)
    deadline = calculate_fiu_deadline(now)

    tx1 = TransactionAuditRecord(
        transaction_id="UTR992817264510",
        timestamp=now,
        rail=PaymentRail.UPI,
        amount=48500.0,
        currency="INR",
        counterparty_from="smurf_01@okhdfcbank",
        counterparty_to="mule_aggregator@oksbi",
        risk_score=0.94,
        detected_anomalies=["PAN_STRUCTURING_EVASION"],
    )
    tx2 = TransactionAuditRecord(
        transaction_id="UTR992817264511",
        timestamp=now,
        rail=PaymentRail.UPI,
        amount=49200.0,
        currency="INR",
        counterparty_from="smurf_02@okaxis",
        counterparty_to="mule_aggregator@oksbi",
        risk_score=0.96,
        detected_anomalies=["PAN_STRUCTURING_EVASION"],
    )

    return SARCaseRecord(
        sar_id="SAR-IND-20260906-881924",
        created_at=now,
        fiu_deadline=deadline,
        status=CaseStatus.PENDING_REVIEW,
        reporting_entity=ReportingEntityInfo(
            fiureid="FIU-RE-COMM-2026-9081",
            entity_name="QuantumAML Nexus Surveillance Gateway",
            principal_officer_id="PO-REG-8819",
        ),
        suspect=SuspectEntityProfile(
            entity_identifier="mule_aggregator@oksbi",
            entity_name="Rajesh Trading Enterprises",
            entity_type="CORPORATE",
            institution_code="SBIN0001234",
            kyc_risk_tier=RiskTier.CRITICAL_SAR,
            is_pep=False,
            flags=["PAN_MISSING", "HIGH_RISK_IFSC"],
        ),
        counterparty=SuspectEntityProfile(
            entity_identifier="smurf_01@okhdfcbank",
            entity_name="Amit Sharma",
            entity_type="INDIVIDUAL",
            kyc_risk_tier=RiskTier.HIGH,
        ),
        transactions=[tx1, tx2],
        total_exposure_inr=97700.0,
        ml_telemetry=MLTelemetry(
            model_name="CatBoost-Banking-v2.4",
            model_version="v2.4",
            inference_latency_ms=11.4,
            feature_importance={
                "amount_structuring_ratio": 0.42,
                "velocity_burst_delta": 0.31,
                "fan_in_clustering": 0.27,
            },
        ),
        grounds_of_suspicion=GroundsOfSuspicion(
            primary_typology=SuspicionTypology.IN_TYP_STRUCT,
            secondary_typologies=[SuspicionTypology.IN_TYP_MULE],
            rule_triggers=["PMLA-SEC-12", "PMLA-RULE-3", "PAN-MANDATE-50K"],
            narrative_summary=(
                "Coordinated structuring pattern detected: 2 transactions aggregating to "
                "₹97,700.00 executed across UPI within 300s to counterparty mule_aggregator@oksbi, "
                "intentionally structured below the statutory ₹50,000 PAN reporting threshold. "
                "Model confidence: 0.95."
            ),
        ),
        assigned_analyst="INV-PMLA-44",
    )


@pytest.fixture
def sample_crypto_case():
    """Creates a crypto VDA mixer SAR case with 64-char transaction hash."""
    now = datetime.now(timezone.utc)
    deadline = calculate_fiu_deadline(now)

    tx = TransactionAuditRecord(
        transaction_id="3a4b5c6d7e8f90123456789abcdef0123456789abcdef0123456789abcdef012",
        timestamp=now,
        rail=PaymentRail.BTC,
        amount=3.85420000,
        currency="BTC",
        counterparty_from="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        counterparty_to="bc1qmixerpeelcluster0001",
        risk_score=0.975,
        detected_anomalies=["VDA_PEEL_CHAIN", "HIGH_DEGREE_CENTRALITY"],
    )

    return SARCaseRecord(
        sar_id="SAR-IND-20260906-CRYPTO01",
        created_at=now,
        fiu_deadline=deadline,
        status=CaseStatus.ESCALATED,
        reporting_entity=ReportingEntityInfo(),
        suspect=SuspectEntityProfile(
            entity_identifier="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            entity_name="Unhosted Wallet Cluster 49",
            entity_type="UNHOSTED_WALLET",
            kyc_risk_tier=RiskTier.CRITICAL_SAR,
        ),
        transactions=[tx],
        total_exposure_inr=0.0,
        total_exposure_btc=3.85420000,
        ml_telemetry=MLTelemetry(
            model_name="Elliptic-XGBoost-v1.2",
            model_version="v1.2",
            inference_latency_ms=14.8,
            feature_importance={
                "in_degree_centrality": 0.48,
                "peeling_velocity": 0.36,
            },
        ),
        grounds_of_suspicion=GroundsOfSuspicion(
            primary_typology=SuspicionTypology.IN_TYP_VDA_MIX,
            rule_triggers=["PMLA-SEC-12", "VDA-UNHOSTED-PEEL"],
            narrative_summary=(
                "Illicit crypto hop detected: High-velocity peeling or mixer signature "
                "identified across 8 inputs and 16 outputs for transaction hash "
                "3a4b5c6d7e8f90123456789abcdef0123456789abcdef0123456789abcdef012."
            ),
        ),
    )


def test_export_fiu_json_structure(sample_fiat_case):
    """Validates complete compliance of the exported JSON against FINnet 2.0 spec."""
    data = export_fiu_json(sample_fiat_case)

    # 1. Batch header
    assert "batch_header" in data
    assert data["batch_header"]["version"] == "2.0"
    assert data["batch_header"]["report_type"] == "STR"
    assert "BATCH-FIN2-" in data["batch_header"]["batch_id"]

    # 2. Reporting entity
    assert data["reporting_entity"]["fiureid"] == "FIU-RE-COMM-2026-9081"
    assert data["reporting_entity"]["principal_officer_id"] == "PO-REG-8819"

    # 3. Case summary
    assert data["case_summary"]["sar_id"] == "SAR-IND-20260906-881924"
    assert data["case_summary"]["status"] == "PENDING_REVIEW"
    assert data["case_summary"]["cumulative_exposure_inr"] == 97700.0
    assert data["case_summary"]["transaction_count"] == 2

    # 4. Suspect & Counterparty
    assert data["suspect_details"]["entity_identifier"] == "mule_aggregator@oksbi"
    assert data["suspect_details"]["name"] == "Rajesh Trading Enterprises"
    assert data["counterparty_details"]["entity_identifier"] == "smurf_01@okhdfcbank"

    # 5. Grounds of suspicion
    assert data["grounds_of_suspicion"]["primary_typology"] == "IN_TYP_STRUCT"
    assert "IN_TYP_MULE" in data["grounds_of_suspicion"]["secondary_typologies"]
    assert "PAN-MANDATE-50K" in data["grounds_of_suspicion"]["rule_triggers"]

    # 6. Transaction schedule
    assert len(data["transaction_schedule"]) == 2
    assert data["transaction_schedule"][0]["transaction_id"] == "UTR992817264510"
    assert data["transaction_schedule"][0]["amount"] == 48500.0

    # 7. ML Telemetry
    assert data["ml_audit_telemetry"]["model_name"] == "CatBoost-Banking-v2.4"
    assert data["ml_audit_telemetry"]["inference_latency_ms"] == 11.4

    # 8. JSON serialization
    json_str = SARExporter.export_json(sample_fiat_case)
    parsed = json.loads(json_str)
    assert parsed["case_summary"]["sar_id"] == sample_fiat_case.sar_id


def test_generate_sar_pdf_binary_output(sample_fiat_case):
    """Verifies that generate_sar_pdf produces valid PDF byte stream."""
    pdf_bytes = generate_sar_pdf(sample_fiat_case)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000  # Non-trivial PDF size
    # PDF magic bytes header
    assert pdf_bytes.startswith(b"%PDF-")

    # Convenience method alias check
    alias_bytes = sar_exporter.export_pdf(sample_fiat_case)
    assert isinstance(alias_bytes, bytes)
    assert alias_bytes.startswith(b"%PDF-")


def test_generate_sar_pdf_crypto_case(sample_crypto_case):
    """Verifies PDF generation for Crypto VDA cases with long hashes and BTC denomination."""
    pdf_bytes = SARExporter.export_pdf(sample_crypto_case)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_sar_pdf_multi_transaction_table():
    """Verifies that a large multi-transaction case renders across pages with clean numbered canvas."""
    now = datetime.now(timezone.utc)
    deadline = calculate_fiu_deadline(now)

    # Create 12 transactions to trigger multi-page table flow
    txs = []
    for i in range(12):
        txs.append(
            TransactionAuditRecord(
                transaction_id=f"UTR-RING-TX-{i:03d}",
                timestamp=now,
                rail=PaymentRail.IMPS if i % 2 == 0 else PaymentRail.UPI,
                amount=45000.0 + (i * 300),
                currency="INR",
                counterparty_from=f"smurf_{i}@bank",
                counterparty_to="mule_hub@bank",
                risk_score=0.91 + (i * 0.005),
                detected_anomalies=["VELOCITY_BURST"],
            )
        )

    case = SARCaseRecord(
        sar_id="SAR-IND-20260906-BURST12",
        created_at=now,
        fiu_deadline=deadline,
        status=CaseStatus.ESCALATED,
        suspect=SuspectEntityProfile(
            entity_identifier="mule_hub@bank",
            entity_name="Apex Logistics Mule Hub",
        ),
        transactions=txs,
        total_exposure_inr=sum(t.amount for t in txs),
        ml_telemetry=MLTelemetry(inference_latency_ms=9.8),
        grounds_of_suspicion=GroundsOfSuspicion(
            primary_typology=SuspicionTypology.IN_TYP_STRUCT,
            narrative_summary="Multi-account rapid smurfing burst across 12 distinct nodes.",
        ),
    )

    pdf_bytes = generate_sar_pdf(case)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 5000
    assert pdf_bytes.startswith(b"%PDF-")
