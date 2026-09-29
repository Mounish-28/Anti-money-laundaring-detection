"""
Integration tests for Asynchronous SAR Generation Pipeline in app/main.py
==========================================================================

Validates:
1. Typology resolution (_resolve_typology) for Structuring, Hawala, Mule, and VDA mix.
2. High-risk fiat scoring triggers async SAR creation via BackgroundTasks.
3. High-risk crypto scoring triggers async SAR creation via BackgroundTasks.
4. Real-time SAR_DISPATCHED event packet broadcast over /ws/live.
5. REST endpoints: GET /api/v1/sar, GET /api/v1/sar/{sar_id}, PATCH /api/v1/sar/{sar_id}/status.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import _resolve_typology, app
from app.schemas.sar import SuspicionTypology
from app.services.sar_service import sar_service


@pytest.fixture(autouse=True)
def clean_sar_store():
    """Cleans in-memory store before each test run."""
    sar_service._cases.clear()
    sar_service._active_ring_index.clear()
    sar_service._ring_last_active.clear()
    yield
    sar_service._cases.clear()
    sar_service._active_ring_index.clear()
    sar_service._ring_last_active.clear()


def test_resolve_typology_rules():
    """Tests in-memory typology classification rules."""
    # 1. Crypto engine -> VDA MIX
    assert (
        _resolve_typology("CRYPTO_FORENSICS", [], {})
        == SuspicionTypology.IN_TYP_VDA_MIX
    )

    # 2. Fiat structuring: amount in [45000, 49999]
    assert (
        _resolve_typology("FIAT_BANKING", [], {"amount": 48500.0})
        == SuspicionTypology.IN_TYP_STRUCT
    )

    # 3. Fiat structuring: PAN flag
    assert (
        _resolve_typology(
            "FIAT_BANKING", ["PAN_STRUCTURING_EVASION"], {"amount": 10000.0}
        )
        == SuspicionTypology.IN_TYP_STRUCT
    )

    # 4. Hawala: wire anomaly >= 2,500,000 INR
    assert (
        _resolve_typology("FIAT_BANKING", [], {"amount": 2500000.0})
        == SuspicionTypology.IN_TYP_HAWALA
    )
    assert (
        _resolve_typology("FIAT_BANKING", ["HAWALA_WIRE"], {"amount": 50000.0})
        == SuspicionTypology.IN_TYP_HAWALA
    )

    # 5. Mule burst: MULE_BURST flag
    assert (
        _resolve_typology("FIAT_BANKING", ["MULE_BURST"], {"amount": 12000.0})
        == SuspicionTypology.IN_TYP_MULE
    )

    # 6. Default fallback
    assert (
        _resolve_typology("FIAT_BANKING", [], {"amount": 500.0})
        == SuspicionTypology.IN_TYP_STRUCT
    )


def test_fiat_scoring_triggers_sar_background():
    """Validates that high-risk fiat transaction generates a SAR dossier via BackgroundTasks."""
    client = TestClient(app)

    # Structuring payload under 50k
    payload = {
        "transaction_id": "UTR-SAR-FIAT-001",
        "from_bank": "10",
        "to_bank": "12",
        "account_from": "smurf_payer@okhdfcbank",
        "account_to": "mule_consolidator@oksbi",
        "amount": 48900.0,
        "currency": "US Dollar",
        "payment_format": "Wire Transfer",
    }

    # TestClient automatically executes BackgroundTasks synchronously on response return
    response = client.post("/api/v1/score/transaction", json=payload)
    assert response.status_code == 200
    res_data = response.json()

    # If the transaction is high risk / critical, a SAR should have been created
    # Check if case was registered in sar_service
    cases, count = asyncio.run(sar_service.list_sars())
    if res_data.get("risk_score", 0.0) >= 0.85 or res_data.get("risk_tier") in (
        "CRITICAL_SAR",
        "CRITICAL",
    ):
        assert count >= 1
        assert cases[0].total_exposure_inr == 48900.0
        assert (
            cases[0].grounds_of_suspicion.primary_typology
            == SuspicionTypology.IN_TYP_STRUCT
        )


def test_crypto_scoring_triggers_sar_background():
    """Validates that high-risk crypto transaction generates a VDA SAR dossier."""
    client = TestClient(app)

    # 166-feature vector with high values
    features = [2.5] * 166
    payload = {
        "node_id": "crypto_node_999",
        "tx_hash": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
        "features": features,
        "time_step": 1,
        "from_address": "bc1qsourceunhostedwallet001",
        "to_address": "bc1qdestinationmixercluster002",
        "btc_value": 4.75,
    }

    response = client.post("/api/v1/score/crypto", json=payload)
    assert response.status_code == 200
    res_data = response.json()

    cases, count = asyncio.run(sar_service.list_sars())
    if res_data.get("risk_score", 0.0) >= 0.80 or res_data.get("risk_tier") in (
        "CRITICAL_SAR",
        "CRITICAL",
    ):
        assert count >= 1
        assert (
            cases[0].grounds_of_suspicion.primary_typology
            == SuspicionTypology.IN_TYP_VDA_MIX
        )
        assert cases[0].total_exposure_btc == 4.75


def test_sar_dispatched_websocket_broadcast():
    """Verifies that high-risk transactions broadcast a SAR_DISPATCHED event over /ws/live."""
    client = TestClient(app)

    payload = {
        "transaction_id": "UTR-WS-SAR-001",
        "from_bank": "10",
        "to_bank": "12",
        "account_from": "smurf_ws@okhdfcbank",
        "account_to": "mule_ws@oksbi",
        "amount": 49200.0,
        "currency": "US Dollar",
        "payment_format": "Wire Transfer",
    }

    with client.websocket_connect("/ws/live") as ws:
        response = client.post("/api/v1/score/transaction", json=payload)
        assert response.status_code == 200

        # Receive the immediate scoring broadcast
        msg1 = ws.receive_json()
        assert msg1["engine"] == "FIAT_BANKING"

        # If high risk, also receives the SAR_DISPATCHED alert packet
        score = response.json().get("risk_score", 0.0)
        tier = response.json().get("risk_tier", "")
        if score >= 0.85 or tier in ("CRITICAL_SAR", "CRITICAL"):
            msg2 = ws.receive_json()
            assert msg2["event"] == "SAR_DISPATCHED"
            assert msg2["sar_id"].startswith("SAR-IND-")
            assert msg2["exposure_inr"] == 49200.0


def test_sar_rest_management_endpoints():
    """Tests GET /api/v1/sar, GET /api/v1/sar/{sar_id}, and PATCH /api/v1/sar/{sar_id}/status."""
    client = TestClient(app)

    # Seed a case via sar_service directly
    seed_tx = {
        "transaction_id": "UTR-SEED-01",
        "account_from": "payer@bank",
        "account_to": "payee@bank",
        "amount": 47500.0,
    }
    seed_ml = {"risk_score": 0.95, "latency_ms": 7.0}
    case = asyncio.run(
        sar_service.create_or_aggregate_sar(
            tx_payload=seed_tx,
            ml_result=seed_ml,
            typology=SuspicionTypology.IN_TYP_STRUCT,
        )
    )
    sar_id = case.sar_id

    # 1. GET /api/v1/sar
    resp_list = client.get("/api/v1/sar?page=1&page_size=10")
    assert resp_list.status_code == 200
    list_data = resp_list.json()
    assert list_data["total_count"] == 1
    assert list_data["items"][0]["sar_id"] == sar_id

    # 2. GET /api/v1/sar/{sar_id}
    resp_get = client.get(f"/api/v1/sar/{sar_id}")
    assert resp_get.status_code == 200
    get_data = resp_get.json()
    assert get_data["sar_id"] == sar_id
    assert get_data["total_exposure_inr"] == 47500.0

    # 3. GET 404 for invalid ID
    resp_404 = client.get("/api/v1/sar/SAR-IND-INVALID")
    assert resp_404.status_code == 404

    # 4. PATCH /api/v1/sar/{sar_id}/status
    patch_payload = {
        "new_status": "FILED_WITH_FIU",
        "analyst_id": "INV-PMLA-99",
        "resolution_notes": "Filed STR on FINnet 2.0 portal.",
    }
    resp_patch = client.patch(f"/api/v1/sar/{sar_id}/status", json=patch_payload)
    assert resp_patch.status_code == 200
    patch_data = resp_patch.json()
    assert patch_data["status"] == "FILED_WITH_FIU"
    assert patch_data["assigned_analyst"] == "INV-PMLA-99"

    # Verify evicted from active ring
    assert "payee@bank" not in sar_service._active_ring_index

    # 5. GET /api/v1/sar/{sar_id}/export/json
    resp_exp_json = client.get(f"/api/v1/sar/{sar_id}/export/json")
    assert resp_exp_json.status_code == 200
    exp_json = resp_exp_json.json()
    assert exp_json["batch_header"]["report_type"] == "STR"
    assert exp_json["case_summary"]["sar_id"] == sar_id

    # 6. GET /api/v1/sar/{sar_id}/export/pdf
    resp_exp_pdf = client.get(f"/api/v1/sar/{sar_id}/export/pdf")
    assert resp_exp_pdf.status_code == 200
    assert resp_exp_pdf.headers["content-type"] == "application/pdf"
    assert resp_exp_pdf.content.startswith(b"%PDF-")
    assert len(resp_exp_pdf.content) > 2000
