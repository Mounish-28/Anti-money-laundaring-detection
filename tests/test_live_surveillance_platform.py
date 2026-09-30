"""
tests/test_live_surveillance_platform.py
=============================================================================
QuantumAML Nexus -- Live Surveillance Platform Test Suite
Lead Infrastructure Engineer Verification Suite:
Validates modular endpoints for decoupled banking and crypto WebSocket/API
streams, Pydantic mock data schemas for real-time UPI and cryptocurrency
transfers, procedural stream generators, and strict zero-reference data isolation
from historical training datasets.
=============================================================================
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app as main_app
from api_server import app as standalone_api_app
from app.surveillance.schemas import (
    CryptoNetwork,
    CryptoTransferPayload,
    SurveillanceEnvelope,
    SurveillanceIngestResponse,
    SurveillanceStatusResponse,
    SurveillanceStreamType,
    UPIStatus,
    UPITransactionPayload,
)
from app.surveillance.isolation_guard import (
    DataIsolationAuditor,
    isolation_auditor,
)
from app.surveillance.generators import (
    MockCryptoGenerator,
    MockUPIGenerator,
    mock_crypto_generator,
    mock_upi_generator,
)
from app.surveillance.connection_manager import (
    SurveillanceConnectionManager,
    surveillance_manager,
)


@pytest.fixture
def client():
    """Test client bound to main platform application."""
    return TestClient(main_app)


@pytest.fixture
def standalone_client():
    """Test client bound to standalone api_server."""
    return TestClient(standalone_api_app)


# =============================================================================
# 1. DATA SCHEMA VALIDATION (UPI & CRYPTO)
# =============================================================================

def test_upi_transaction_schema_valid():
    """Verify valid UPI transaction payload conforms to NPCI standards."""
    payload = UPITransactionPayload(
        txn_id="UPI-20260930-TXN-998877",
        rrn="627192837461",
        payer_vpa="rahul.sharma@okaxis",
        payee_vpa="techkart.merchant@icici",
        amount_inr=4500.0,
        mcc="5311",
        upi_status=UPIStatus.SUCCESS,
        device_fingerprint="fp_and_9876543210ab",
        ip_address="49.36.120.14",
        city="Mumbai",
    )
    assert payload.txn_id == "UPI-20260930-TXN-998877"
    assert payload.amount_inr == 4500.0
    assert payload.currency == "INR"
    assert payload.rbi_threshold_breach is False
    assert payload.mcc == "5311"
    assert payload.amount_usd > 0.0


def test_upi_transaction_threshold_breach_detection():
    """Verify high-value UPI transaction triggers RBI threshold breach flag."""
    payload = UPITransactionPayload(
        txn_id="UPI-20260930-TXN-HIGHVAL",
        rrn="627192837499",
        payer_vpa="investor.whale@okhdfcbank",
        payee_vpa="escrow.service@axisbank",
        amount_inr=150000.0,  # Exceeds standard P2P 100,000 INR limit
        mcc="6211",
        upi_status=UPIStatus.SUCCESS,
        device_fingerprint="fp_ios_1234567890ef",
        ip_address="103.21.124.5",
        city="Bengaluru",
    )
    assert payload.rbi_threshold_breach is True


def test_crypto_transfer_schema_valid():
    """Verify valid cryptocurrency transfer payload conforms to blockchain standards."""
    payload = CryptoTransferPayload(
        tx_hash="0x3f5ce5fbacfe9bcd8d16853beecf1557d00be74b830d12e694508ecf6fb11234",
        network=CryptoNetwork.ETHEREUM,
        from_wallet="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        to_wallet="0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8",
        amount_crypto=2.5,
        asset_symbol="ETH",
        amount_usd=6250.0,
        mixer_risk=False,
        peeling_chain=False,
        hop_count=1,
    )
    assert payload.asset_symbol == "ETH"
    assert payload.network == CryptoNetwork.ETHEREUM
    assert payload.mixer_risk is False
    assert payload.hop_count == 1


def test_crypto_transfer_mixer_and_peeling_detection():
    """Verify high-risk cryptocurrency flags (mixer proximity, peeling chain)."""
    payload = CryptoTransferPayload(
        tx_hash="4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
        network=CryptoNetwork.BITCOIN,
        from_wallet="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        to_wallet="bc1qc7g07w6w63q0q7eednjyp5xer9hhgqn36tcm53",
        amount_crypto=14.5,
        asset_symbol="BTC",
        amount_usd=942500.0,
        mixer_risk=True,
        peeling_chain=True,
        hop_count=7,
        risk_tags=["UNHOSTED_MIXER_PROXIMITY", "MULTI_HOP_PEELING_CHAIN"],
    )
    assert payload.mixer_risk is True
    assert payload.peeling_chain is True
    assert payload.hop_count == 7
    assert "UNHOSTED_MIXER_PROXIMITY" in payload.risk_tags


# =============================================================================
# 2. CRYPTOGRAPHIC DATA ISOLATION BARRIER (PREVENTS CONTAMINATION)
# =============================================================================

def test_data_isolation_clean_payload():
    """Verify clean procedural payloads pass the zero-reference isolation audit."""
    auditor = DataIsolationAuditor()
    clean_upi = mock_upi_generator.generate_upi_payload().model_dump()
    
    is_clean, proof, violations = auditor.verify_isolation(clean_upi, "UPI_TEST")
    assert is_clean is True
    assert len(violations) == 0
    assert len(proof) == 64  # Valid 64-char HMAC-SHA256 hex digest
    assert auditor.audited_events_count == 1
    assert auditor.contamination_attempts_blocked == 0


def test_data_isolation_detects_historical_training_tokens():
    """
    CRITICAL TEST: Ensure payload containing historical training set artifacts
    (e.g., IBM Transactions, SAML-D, Elliptic, AMLSim) is BLOCKED with 0 tolerance.
    """
    auditor = DataIsolationAuditor()
    
    # Contaminated payload containing IBM Transactions & Elliptic tokens
    contaminated_payload = {
        "txn_id": "UPI-LIVE-TEST",
        "account_id": "BANK_10_SAVINGS_99",      # IBM Transaction pattern
        "peer_entity": "company_970_pty_ltd",    # SAML-D pattern
        "illicit_node": "230425980",              # Elliptic dataset transaction ID
        "source_agent": "AMLSim_ACCT_1002",      # IBM AMLSim pattern
        "reference": "time_series_aml_run",      # Time-Series AML dataset token
    }
    
    is_clean, proof, violations = auditor.verify_isolation(contaminated_payload, "CONTAMINATED_TEST")
    assert is_clean is False
    assert proof == ""  # No isolation proof generated for contaminated events
    assert len(violations) >= 3
    assert any("BANK_10_" in v for v in violations)
    assert any("company_970" in v for v in violations)
    assert any("230425980" in v for v in violations)
    assert auditor.contamination_attempts_blocked == 1


# =============================================================================
# 3. PROCEDURAL SYNTHETIC STREAM GENERATORS
# =============================================================================

def test_procedural_upi_generator_isolation():
    """Verify mock UPI generator creates non-dataset payloads that pass isolation."""
    gen = MockUPIGenerator()
    for _ in range(10):
        payload = gen.generate_upi_payload()
        is_clean, _, violations = isolation_auditor.verify_isolation(
            payload.model_dump(), "GENERATOR_UPI_CHECK"
        )
        assert is_clean is True, f"Generated payload failed isolation: {violations}"
        assert payload.payer_vpa != payload.payee_vpa
        assert payload.amount_inr > 0.0


def test_procedural_crypto_generator_isolation():
    """Verify mock crypto generator creates non-dataset payloads that pass isolation."""
    gen = MockCryptoGenerator()
    for net in [CryptoNetwork.BITCOIN, CryptoNetwork.ETHEREUM, CryptoNetwork.POLYGON]:
        payload = gen.generate_crypto_payload(network=net)
        is_clean, _, violations = isolation_auditor.verify_isolation(
            payload.model_dump(), "GENERATOR_CRYPTO_CHECK"
        )
        assert is_clean is True, f"Generated payload failed isolation: {violations}"
        assert payload.network == net
        assert payload.from_wallet != payload.to_wallet


def test_procedural_upi_anomalies():
    """Verify procedural UPI generator can synthesize specific typologies."""
    gen = MockUPIGenerator()
    structuring = gen.generate_upi_payload(anomaly_mode="STRUCTURING")
    assert structuring.amount_inr >= 90000.0
    assert structuring.amount_inr < 100000.0
    assert "SUB_THRESHOLD_STRUCTURING" in structuring.anomaly_flags

    gambling = gen.generate_upi_payload(anomaly_mode="GAMBLING_BURST")
    assert gambling.mcc == "7995"
    assert "HIGH_RISK_MCC_GAMBLING" in gambling.anomaly_flags


# =============================================================================
# 4. DECOUPLED WEBSOCKET CHANNELS & SUBSCRIBER POOLS
# =============================================================================

@pytest.mark.asyncio
async def test_decoupled_channel_isolation():
    """
    Verify banking subscribers receive UPI events only,
    crypto subscribers receive crypto events only, and
    unified subscribers receive both.
    """
    manager = SurveillanceConnectionManager()

    # Mock WebSocket client receivers
    class MockWS:
        def __init__(self, name: str):
            self.name = name
            self.messages = []

        async def accept(self):
            pass

        async def send_json(self, data):
            self.messages.append(data)

    ws_bank = MockWS("bank_client")
    ws_crypto = MockWS("crypto_client")
    ws_unified = MockWS("unified_client")

    # Connect to respective decoupled channels
    await manager.connect(ws_bank, channel="banking")
    await manager.connect(ws_crypto, channel="crypto")
    await manager.connect(ws_unified, channel="unified")

    counts = manager.get_subscriber_counts()
    assert counts["banking"] == 1
    assert counts["crypto"] == 1
    assert counts["unified"] == 1
    assert counts["total"] == 3

    # 1. Broadcast Banking Payload
    bank_event = {"stream_type": "UPI_BANKING", "txn_id": "UPI-001", "amount": 5000}
    await manager.broadcast_banking(bank_event)

    assert len(ws_bank.messages) == 1
    assert ws_bank.messages[0]["txn_id"] == "UPI-001"
    assert len(ws_crypto.messages) == 0  # Crypto channel receives NO banking noise!
    assert len(ws_unified.messages) == 1

    # 2. Broadcast Crypto Payload
    crypto_event = {"stream_type": "CRYPTO_TRANSFER", "tx_hash": "0xabc123", "amount": 10.0}
    await manager.broadcast_crypto(crypto_event)

    assert len(ws_bank.messages) == 1    # Banking channel receives NO crypto noise!
    assert len(ws_crypto.messages) == 1
    assert ws_crypto.messages[0]["tx_hash"] == "0xabc123"
    assert len(ws_unified.messages) == 2

    # Disconnect
    await manager.disconnect(ws_bank, channel="banking")
    await manager.disconnect(ws_crypto, channel="crypto")
    await manager.disconnect(ws_unified, channel="unified")

    assert manager.get_subscriber_counts()["total"] == 0


# =============================================================================
# 5. REST INGESTION & STATUS API ENDPOINTS
# =============================================================================

def test_api_ingest_banking_clean_payload(client):
    """Verify REST ingestion of a valid, isolated UPI transaction."""
    payload = mock_upi_generator.generate_upi_payload().model_dump()
    res = client.post("/api/v1/surveillance/banking/ingest", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ACCEPTED", "ALERT_TRIGGERED")
    assert data["stream_type"] == "UPI_BANKING"
    assert data["isolation_verified"] is True
    assert "risk_score" in data
    assert "event_id" in data


def test_api_ingest_banking_blocks_cross_contamination(client):
    """Verify REST API rejects contaminated payload referencing historical datasets."""
    contaminated_payload = mock_upi_generator.generate_upi_payload().model_dump()
    contaminated_payload["payer_vpa"] = "BANK_10_account_88921@upi"  # IBM pattern
    contaminated_payload["device_fingerprint"] = "company_970_client"  # SAML-D pattern

    res = client.post("/api/v1/surveillance/banking/ingest", json=contaminated_payload)
    assert res.status_code == 400
    data = res.json()
    assert "CROSS_CONTAMINATION_DETECTED" in str(data)


def test_api_ingest_crypto_clean_payload(client):
    """Verify REST ingestion of a valid, isolated Cryptocurrency transfer."""
    payload = mock_crypto_generator.generate_crypto_payload().model_dump()
    res = client.post("/api/v1/surveillance/crypto/ingest", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ACCEPTED", "ALERT_TRIGGERED")
    assert data["stream_type"] == "CRYPTO_TRANSFER"
    assert data["isolation_verified"] is True
    assert "risk_score" in data
    assert "event_id" in data


def test_api_ingest_crypto_blocks_cross_contamination(client):
    """Verify REST API rejects crypto payload referencing Elliptic training IDs."""
    contaminated_payload = mock_crypto_generator.generate_crypto_payload().model_dump()
    contaminated_payload["tx_hash"] = "230425980"  # Elliptic Bitcoin node ID

    res = client.post("/api/v1/surveillance/crypto/ingest", json=contaminated_payload)
    assert res.status_code == 400
    data = res.json()
    assert "CROSS_CONTAMINATION_DETECTED" in str(data)


def test_api_sample_endpoints(client):
    """Verify procedural live sampling endpoints."""
    # Banking sampler
    res_b = client.get("/api/v1/surveillance/banking/sample?anomaly_mode=STRUCTURING")
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert "SUB_THRESHOLD_STRUCTURING" in data_b["anomaly_flags"]

    # Crypto sampler
    res_c = client.get("/api/v1/surveillance/crypto/sample?anomaly_mode=MIXER_TUMBLER")
    assert res_c.status_code == 200
    data_c = res_c.json()
    assert data_c["mixer_risk"] is True


def test_api_surveillance_status(client):
    """Verify surveillance status telemetry endpoint."""
    res = client.get("/api/v1/surveillance/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert "subscribers" in data
    assert "isolation_guarantee" in data
    assert data["isolation_guarantee"]["status"] == "VERIFIED_ZERO_CONTAMINATION"


def test_standalone_api_server_mount(standalone_client):
    """Verify surveillance router is properly mounted in the standalone api_server as well."""
    res = standalone_client.get("/api/v1/surveillance/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
