"""
Unit & Integration Tests for QuantumAML Nexus SAR Router (app/routers/sar.py)
=============================================================================

Validates:
1. GET /api/v1/sar/list: Pagination, sorting, and query filtering.
2. GET /api/v1/sar/{sar_id}: Retrieval and 404 error handling.
3. POST /api/v1/sar/generate: Manual case creation and investigation escalation.
4. PATCH /api/v1/sar/{sar_id}/status: State transitions and active ring eviction.
5. GET /api/v1/sar/{sar_id}/export: Streaming PDF and FINnet 2.0 JSON downloads.
"""

import asyncio
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas.sar import (
    CaseStatus,
    ReportingEntityInfo,
    SuspicionTypology,
)
from app.services.sar_service import sar_service


@pytest.fixture(autouse=True)
def clean_sar_repository():
    """Ensures clean in-memory repository before and after each test."""
    sar_service._cases.clear()
    sar_service._active_ring_index.clear()
    sar_service._ring_last_active.clear()
    yield
    sar_service._cases.clear()
    sar_service._active_ring_index.clear()
    sar_service._ring_last_active.clear()


@pytest.fixture
def test_client():
    return TestClient(app)


def seed_test_case(sar_id_suffix: str = "TEST01", amount: float = 48500.0) -> str:
    """Helper to synchronously seed a SARCaseRecord into sar_service."""
    tx_payload = {
        "transaction_id": f"UTR-{sar_id_suffix}",
        "account_from": f"smurf_{sar_id_suffix}@okhdfc",
        "account_to": f"mule_target_{sar_id_suffix}@oksbi",
        "amount": amount,
        "currency": "INR",
        "payment_format": "UPI",
    }
    ml_result = {"risk_score": 0.94, "latency_ms": 8.0}
    case = asyncio.run(
        sar_service.create_or_aggregate_sar(
            tx_payload=tx_payload,
            ml_result=ml_result,
            typology=SuspicionTypology.IN_TYP_STRUCT,
        )
    )
    return case.sar_id


# ------------------------------------------------------------------------------
# 1. GET /api/v1/sar/list
# ------------------------------------------------------------------------------
def test_list_sars_endpoint(test_client):
    """Verifies paginated list retrieval, search, and typology filtering."""
    # Seed 3 distinct cases
    id1 = seed_test_case("ALPHA", 46000.0)
    id2 = seed_test_case("BETA", 47000.0)
    id3 = seed_test_case("GAMMA", 48000.0)

    # 1. Standard pagination
    resp = test_client.get("/api/v1/sar/list?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2

    # 2. Search filtering
    resp_search = test_client.get("/api/v1/sar/list?search=ALPHA")
    assert resp_search.status_code == 200
    data_search = resp_search.json()
    assert data_search["total_count"] == 1
    assert data_search["items"][0]["sar_id"] == id1

    # 3. Typology filtering
    resp_typo = test_client.get("/api/v1/sar/list?typology=IN_TYP_STRUCT")
    assert resp_typo.status_code == 200
    assert resp_typo.json()["total_count"] == 3

    # 4. Root path alias check
    resp_root = test_client.get("/api/v1/sar?page=1&page_size=10")
    assert resp_root.status_code == 200
    assert resp_root.json()["total_count"] == 3


# ------------------------------------------------------------------------------
# 2. GET /api/v1/sar/{sar_id}
# ------------------------------------------------------------------------------
def test_get_sar_by_id_endpoint(test_client):
    """Verifies retrieval by valid ID and 404 for invalid ID."""
    sar_id = seed_test_case("LOOKUP", 49500.0)

    # Valid ID
    resp = test_client.get(f"/api/v1/sar/{sar_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sar_id"] == sar_id
    assert data["total_exposure_inr"] == 49500.0
    assert data["status"] == "PENDING_REVIEW"

    # Non-existent ID -> 404
    resp_404 = test_client.get("/api/v1/sar/SAR-IND-NONEXISTENT")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()


# ------------------------------------------------------------------------------
# 3. POST /api/v1/sar/generate
# ------------------------------------------------------------------------------
def test_generate_sar_manual_initiation(test_client):
    """Verifies manual escalation and generation via SARCreateRequest."""
    create_payload = {
        "transaction_ids": ["UTR-MANUAL-001", "UTR-MANUAL-002"],
        "primary_typology": "IN_TYP_STRUCT",
        "investigator_notes": "Ad-hoc compliance escalation for suspicious structuring burst.",
        "assigned_investigator": "INV-PMLA-77",
        "suspect_identifier": "flagged_mule_pool@oksbi",
        "reporting_entity": {
            "fiureid": "FIU-RE-COMM-2026-9081",
            "entity_name": "QuantumAML Nexus Surveillance Gateway",
        },
    }

    resp = test_client.post("/api/v1/sar/generate", json=create_payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["sar_id"].startswith("SAR-IND-")
    assert data["status"] == "PENDING_REVIEW"
    assert data["assigned_analyst"] == "INV-PMLA-77"
    assert data["suspect"]["entity_identifier"] == "flagged_mule_pool@oksbi"
    # Aggregated both transactions
    assert len(data["transactions"]) == 2
    assert data["total_exposure_inr"] == 49000.0 + 48500.0

    # Test bad request: empty transaction_ids
    resp_bad = test_client.post("/api/v1/sar/generate", json={"transaction_ids": []})
    assert resp_bad.status_code in (400, 422)


# ------------------------------------------------------------------------------
# 4. PATCH /api/v1/sar/{sar_id}/status
# ------------------------------------------------------------------------------
def test_update_sar_status_and_eviction(test_client):
    """Verifies status transition to FILED_WITH_FIU and active ring eviction."""
    sar_id = seed_test_case("STATUS_TEST", 48000.0)

    # Verify ring is initially active
    assert "mule_target_STATUS_TEST@oksbi" in sar_service._active_ring_index

    # 1. Update status to FILED_WITH_FIU via body payload
    patch_body = {
        "new_status": "FILED_WITH_FIU",
        "analyst_id": "OFFICER-PMLA-01",
        "resolution_notes": "Successfully uploaded to FIU-IND FINnet 2.0 portal with ack ACK-9081.",
    }
    resp = test_client.patch(f"/api/v1/sar/{sar_id}/status", json=patch_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FILED_WITH_FIU"
    assert data["assigned_analyst"] == "OFFICER-PMLA-01"

    # 2. Verify evicted from active ring
    assert "mule_target_STATUS_TEST@oksbi" not in sar_service._active_ring_index

    # 3. 404 for invalid ID
    resp_404 = test_client.patch(
        "/api/v1/sar/SAR-NONEXISTENT/status",
        json={"new_status": "DISMISSED", "analyst_id": "OFFICER-01"},
    )
    assert resp_404.status_code == 404


# ------------------------------------------------------------------------------
# 5. GET /api/v1/sar/{sar_id}/export (PDF & JSON)
# ------------------------------------------------------------------------------
def test_export_sar_dossier_pdf_and_json(test_client):
    """Verifies streaming PDF and FINnet 2.0 JSON export with proper headers."""
    sar_id = seed_test_case("EXPORT_TEST", 49800.0)

    # 1. PDF Export via format=pdf
    resp_pdf = test_client.get(f"/api/v1/sar/{sar_id}/export?format=pdf")
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert f'attachment; filename="{sar_id}.pdf"' in resp_pdf.headers["content-disposition"]
    assert resp_pdf.content.startswith(b"%PDF-")
    assert len(resp_pdf.content) > 2000

    # 2. JSON Export via format=json
    resp_json = test_client.get(f"/api/v1/sar/{sar_id}/export?format=json")
    assert resp_json.status_code == 200
    assert resp_json.headers["content-type"] == "application/json"
    assert f'attachment; filename="{sar_id}_FINNET2.json"' in resp_json.headers["content-disposition"]
    json_data = resp_json.json()
    assert json_data["batch_header"]["report_type"] == "STR"
    assert json_data["case_summary"]["sar_id"] == sar_id

    # 3. Invalid format -> 400
    resp_inv = test_client.get(f"/api/v1/sar/{sar_id}/export?format=xml")
    assert resp_inv.status_code in (400, 422)

    # 4. Non-existent case -> 404
    resp_404 = test_client.get("/api/v1/sar/SAR-NONEXISTENT/export?format=pdf")
    assert resp_404.status_code == 404
