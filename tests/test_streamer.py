import pytest
from streamer import (
    EntityGenerator,
    generate_baseline_transaction,
    generate_typology_a_structuring,
    generate_typology_b_hawala_rtgs,
    generate_typology_c_velocity_draining,
    format_log_line,
    ResilientDispatcher,
)


def test_entity_generator_formats():
    """Validates procedural identity, VPA, bank IFSC, and UTR generation formats."""
    name = EntityGenerator.generate_person_name()
    assert len(name.split()) == 2

    vpa = EntityGenerator.generate_vpa(name)
    assert "@" in vpa
    assert any(h in vpa for h in ["@oksbi", "@okhdfcbank", "@okicici", "@okaxis", "@paytm", "@ybl"])

    bank_name, bank_str = EntityGenerator.generate_bank()
    assert "(" in bank_str and ")" in bank_str

    high_risk_name, high_risk_str = EntityGenerator.generate_bank(high_risk=True)
    assert any(code in high_risk_str for code in ["SBIN0061299", "HDFC0009941", "UTIB0004812", "ICIC0007781", "BARB0098231"])

    utr = EntityGenerator.generate_utr()
    assert utr.startswith("UTR-")
    assert len(utr.split("-")) == 3

    iso_ts = EntityGenerator.get_iso_timestamp()
    assert "T" in iso_ts and iso_ts.endswith("Z")


def test_baseline_transaction_contract():
    """Validates baseline transactions match the required FastAPI schema contract."""
    payload, tag = generate_baseline_transaction()
    assert tag == "BASELINE_LEGITIMATE"
    assert payload["payment_format"] in ["UPI", "IMPS", "NEFT", "RTGS"]
    assert payload["currency"] == "INR"
    assert payload["amount"] > 0
    assert "transaction_id" in payload
    assert "timestamp" in payload
    assert "from_bank" in payload
    assert "to_bank" in payload
    assert "account_from" in payload
    assert "account_to" in payload


def test_typology_a_pan_structuring():
    """
    Validates Typology A: PAN Structuring / Smurfing.
    Amounts must be strictly between ₹48,000 and ₹49,950, sent from 4-8 distinct mules
    to a single aggregator VPA on UPI.
    """
    burst = generate_typology_a_structuring()
    assert 4 <= len(burst) <= 8

    aggregator_vpa = burst[0][0]["account_to"]
    mule_senders = set()

    for tx, tag in burst:
        assert 48000.0 <= tx["amount"] <= 49950.0
        assert tx["account_to"] == aggregator_vpa
        assert tx["payment_format"] == "UPI"
        assert tx["currency"] == "INR"
        assert "PAN_STRUCTURING_SMURFING" in tag
        mule_senders.add(tx["account_from"])

    # All mules in sequence must be distinct
    assert len(mule_senders) == len(burst)


def test_typology_b_hawala_rtgs():
    """
    Validates Typology B: High-Value Hawala RTGS.
    Amounts must be ₹25 Lakh to ₹1.2 Crore on RTGS using high-risk branch IFSCs.
    """
    burst = generate_typology_b_hawala_rtgs()
    assert len(burst) == 1
    tx, tag = burst[0]

    assert 2500000.0 <= tx["amount"] <= 12000000.0
    assert tx["payment_format"] == "RTGS"
    assert tx["currency"] == "INR"
    assert "HIGH_VALUE_HAWALA_RTGS" in tag


def test_typology_c_velocity_draining():
    """
    Validates Typology C: Velocity / Mule Draining.
    Single consumer account firing 6-10 rapid IMPS transfers (₹10,000 to ₹25,000 each)
    to different beneficiary accounts.
    """
    burst = generate_typology_c_velocity_draining()
    assert 6 <= len(burst) <= 10

    victim_account = burst[0][0]["account_from"]
    beneficiaries = set()

    for tx, tag in burst:
        assert 10000.0 <= tx["amount"] <= 25000.0
        assert tx["account_from"] == victim_account
        assert tx["payment_format"] == "IMPS"
        assert tx["currency"] == "INR"
        assert "VELOCITY_MULE_DRAINING" in tag
        beneficiaries.add(tx["account_to"])

    # All beneficiaries must be distinct
    assert len(beneficiaries) == len(burst)


def test_format_log_line():
    """Validates terminal log formatter produces expected structure."""
    payload, tag = generate_baseline_transaction()
    mock_resp = {
        "risk_tier": "LOW",
        "risk_score": 0.0412,
        "latency_ms": 14.5,
    }
    line = format_log_line(payload, tag, mock_resp, "")
    assert payload["payment_format"] in line
    assert "HTTP 200" in line
    assert "LOW" in line
