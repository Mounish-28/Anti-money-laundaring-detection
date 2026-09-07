"""
Hermetic Integration & Regression Test Suite for SAR Router Endpoints
======================================================================
Location: tests/test_sar_endpoints.py

Validates all endpoints and edge cases of the SAR router (/api/v1/sar):
- POST /api/v1/sar/generate (Manual generation & validation errors)
- GET /api/v1/sar/list (Listing, pagination, typology & search filtering)
- GET /api/v1/sar/{sar_id} (Dossier retrieval & 404 handling)
- PATCH /api/v1/sar/{sar_id}/status (Status transitions & active ring eviction)
- GET /api/v1/sar/{sar_id}/export (Streaming PDF and FINnet 2.0 JSON)
- Zero state bleed between test runs via autouse cleanup fixtures.
"""

from datetime import datetime, timezone
import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport

from app.main import app
from app.schemas.sar import (
    CaseStatus,
    ReportingEntityInfo,
    SuspicionTypology,
    calculate_fiu_deadline,
)
from app.services.sar_service import sar_service


# ------------------------------------------------------------------------------
# 1. Fixtures & Hermetic State Isolation
# ------------------------------------------------------------------------------
@pytest_asyncio.fixture
async def async_client():
    """Asynchronous test client using httpx.ASGITransport targeting base_url='http://test'."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def clean_sar_state():
    """Clears all in-memory indexes of sar_service before and after each test."""
    sar_service._cases.clear()
    sar_service._active_ring_index.clear()
    sar_service._ring_last_active.clear()
    yield
    sar_service._cases.clear()
    sar_service._active_ring_index.clear()
    sar_service._ring_last_active.clear()


@pytest.fixture
def sample_sar_payload():
    """Returns an authentic, valid SARCreateRequest dictionary."""
    return {
        "transaction_ids": ["UTR-PMLA-908123456789"],
        "primary_typology": "IN_TYP_STRUCT",
        "investigator_notes": "Structuring evasion detected below ₹50,000 statutory PAN threshold.",
        "assigned_investigator": "INV-PMLA-42",
        "suspect_identifier": "mule.smurf99@okhdfcbank",
        "reporting_entity": {
            "fiureid": "FIU-RE-COMM-2026-9081",
            "entity_name": "QuantumAML Nexus Surveillance Gateway",
            "category": "SCHEDULED_COMMERCIAL_BANK",
            "principal_officer_id": "PO-REG-8819",
        },
    }


async def seed_sar_case(
    tx_id: str,
    suspect_id: str,
    typology: SuspicionTypology = SuspicionTypology.IN_TYP_STRUCT,
    amount: float = 49850.0,
    entity_name: str = "Anonymous Holder",
) -> str:
    """Helper to seed an active SAR dossier directly into sar_service."""
    tx_payload = {
        "transaction_id": tx_id,
        "suspect_identifier": suspect_id,
        "entity_name": entity_name,
        "account_from": f"smurf_{tx_id[:6]}@okicici",
        "account_to": suspect_id,
        "amount": amount,
        "currency": "INR",
        "payment_format": "UPI",
    }
    ml_result = {"risk_score": 0.94, "latency_ms": 7.5}
    case = await sar_service.create_or_aggregate_sar(
        tx_payload=tx_payload,
        ml_result=ml_result,
        typology=typology,
    )
    return case.sar_id


# ------------------------------------------------------------------------------
# 2. Test 1: Manual SAR Generation (POST /api/v1/sar/generate)
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_manual_sar_generation(async_client, sample_sar_payload):
    """Verifies that POST /api/v1/sar/generate creates a valid compliant SARCaseRecord."""
    response = await async_client.post("/api/v1/sar/generate", json=sample_sar_payload)

    assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}: {response.text}"
    data = response.json()

    # Schema adherence assertions
    assert data["sar_id"].startswith("SAR-IND-"), f"Invalid SAR ID format: {data.get('sar_id')}"
    assert data["status"] == "PENDING_REVIEW", f"Expected PENDING_REVIEW, got {data.get('status')}"
    assert data["suspect"]["entity_identifier"] == "mule.smurf99@okhdfcbank"
    assert data["assigned_analyst"] == "INV-PMLA-42"

    # Deadline validation (~7 working days in the future)
    deadline_dt = datetime.fromisoformat(data["fiu_deadline"])
    created_dt = datetime.fromisoformat(data["created_at"])
    diff_days = (deadline_dt - created_dt).days
    assert 6 <= diff_days <= 12, f"Statutory deadline should be roughly 7-11 calendar days out, got {diff_days}"


# ------------------------------------------------------------------------------
# 3. Test 2: Validation Handling on Generation
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_validation_handling_on_generation(async_client):
    """Verifies that invalid payloads are rejected with 422 Unprocessable Entity."""
    # Empty body
    res_empty = await async_client.post("/api/v1/sar/generate", json={})
    assert res_empty.status_code == 422, f"Expected 422 for empty payload, got {res_empty.status_code}"

    # Invalid typology string
    res_bad_typo = await async_client.post(
        "/api/v1/sar/generate",
        json={
            "transaction_ids": ["UTR-999"],
            "primary_typology": "INVALID_TYPOLOGY_CODE",
        },
    )
    assert res_bad_typo.status_code == 422, f"Expected 422 for invalid typology, got {res_bad_typo.status_code}"


# ------------------------------------------------------------------------------
# 4. Test 3: List & Filter SARs (GET /api/v1/sar/list)
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_and_filter_sars(async_client):
    """Verifies list pagination, typology filtering, and keyword search."""
    # Seed 3 distinct cases: two IN_TYP_STRUCT, one IN_TYP_HAWALA
    id1 = await seed_sar_case("UTR-STRUCT-01", "mule_alpha@oksbi", SuspicionTypology.IN_TYP_STRUCT, 48000.0, "Alpha Traders")
    id2 = await seed_sar_case("UTR-STRUCT-02", "mule_beta@oksbi", SuspicionTypology.IN_TYP_STRUCT, 49000.0, "Beta Enterprises")
    id3 = await seed_sar_case("UTR-HAWALA-01", "hawala_corp@swift", SuspicionTypology.IN_TYP_HAWALA, 2500000.0, "Golden Bullion Global")

    # 1. Default listing
    resp_all = await async_client.get("/api/v1/sar/list")
    assert resp_all.status_code == 200
    all_data = resp_all.json()
    assert all_data["total_count"] == 3, f"Expected 3 cases, got {all_data['total_count']}"
    assert all_data["page"] == 1
    assert all_data["page_size"] == 20
    assert len(all_data["items"]) == 3

    # 2. Typology filter
    resp_hawala = await async_client.get("/api/v1/sar/list?typology=IN_TYP_HAWALA")
    assert resp_hawala.status_code == 200
    hawala_data = resp_hawala.json()
    assert hawala_data["total_count"] == 1, f"Expected 1 Hawala case, got {hawala_data['total_count']}"
    assert hawala_data["items"][0]["sar_id"] == id3

    # 3. Search filter by partial entity name
    resp_search = await async_client.get("/api/v1/sar/list?search=Golden+Bullion")
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert search_data["total_count"] == 1
    assert search_data["items"][0]["sar_id"] == id3

    # 4. Search filter by partial VPA
    resp_search_vpa = await async_client.get("/api/v1/sar/list?search=mule_alpha")
    assert resp_search_vpa.status_code == 200
    assert resp_search_vpa.json()["total_count"] == 1
    assert resp_search_vpa.json()["items"][0]["sar_id"] == id1


# ------------------------------------------------------------------------------
# 5. Test 4: Retrieve Specific SAR by ID (GET /api/v1/sar/{sar_id})
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retrieve_sar_by_id(async_client):
    """Verifies fetching an existing SAR returns 200, and non-existent returns 404."""
    sar_id = await seed_sar_case("UTR-FETCH-01", "target_account@paytm", SuspicionTypology.IN_TYP_STRUCT, 49500.0)

    # 1. Existing ID -> 200 OK
    resp_ok = await async_client.get(f"/api/v1/sar/{sar_id}")
    assert resp_ok.status_code == 200, f"Expected 200, got {resp_ok.status_code}"
    data = resp_ok.json()
    assert data["sar_id"] == sar_id
    assert data["total_exposure_inr"] == 49500.0
    assert data["suspect"]["entity_identifier"] == "target_account@paytm"

    # 2. Non-existent ID -> 404 Not Found
    resp_404 = await async_client.get("/api/v1/sar/SAR-IND-00000000-000000")
    assert resp_404.status_code == 404, f"Expected 404, got {resp_404.status_code}"
    assert "not found" in resp_404.json()["detail"].lower()


# ------------------------------------------------------------------------------
# 6. Test 5: Status State Transitions & Eviction (PATCH /api/v1/sar/{sar_id}/status)
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_status_transitions_and_eviction(async_client):
    """Verifies status transitions to FILED_WITH_FIU and active ring index eviction."""
    suspect_entity = "active_ring_suspect@oksbi"
    sar_id = await seed_sar_case("UTR-RING-01", suspect_entity, SuspicionTypology.IN_TYP_STRUCT, 48000.0)

    # Confirm suspect is registered in active ring index
    assert suspect_entity in sar_service._active_ring_index

    # 1. Transition case to FILED_WITH_FIU
    patch_payload = {
        "new_status": "FILED_WITH_FIU",
        "analyst_id": "ANALYST-42",
        "resolution_notes": "Filed electronic STR report to FIU-IND FINnet gateway.",
    }
    patch_resp = await async_client.patch(f"/api/v1/sar/{sar_id}/status", json=patch_payload)
    assert patch_resp.status_code == 200, f"Expected 200, got {patch_resp.status_code}"
    data = patch_resp.json()
    assert data["status"] == "FILED_WITH_FIU"
    assert data["assigned_analyst"] == "ANALYST-42"

    # 2. Verify that the suspect was evicted from _active_ring_index
    assert suspect_entity not in sar_service._active_ring_index, "Closed case suspect must be evicted from active ring index"

    # 3. Subsequent transaction from the same suspect must create a NEW case instead of aggregating
    new_sar_id = await seed_sar_case("UTR-RING-02", suspect_entity, SuspicionTypology.IN_TYP_STRUCT, 47000.0)
    assert new_sar_id != sar_id, f"Expected fresh SAR ID after eviction, got duplicate {new_sar_id}"

    # 4. Attempt to update non-existent SAR ID -> 404 Not Found
    resp_404 = await async_client.patch(
        "/api/v1/sar/SAR-IND-00000000-000000/status",
        json={"new_status": "DISMISSED", "analyst_id": "ANALYST-42"},
    )
    assert resp_404.status_code == 404, f"Expected 404 for missing SAR ID, got {resp_404.status_code}"


# ------------------------------------------------------------------------------
# 7. Test 6: Machine-Readable JSON Export (GET /api/v1/sar/{sar_id}/export?format=json)
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_json_export_endpoint(async_client):
    """Verifies FINnet 2.0 JSON export with proper headers and hierarchy."""
    sar_id = await seed_sar_case("UTR-EXP-JSON", "export_target@upi", SuspicionTypology.IN_TYP_STRUCT, 48900.0)

    resp = await async_client.get(f"/api/v1/sar/{sar_id}/export?format=json")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    # Headers
    content_type = resp.headers.get("content-type", "")
    assert "application/json" in content_type, f"Expected application/json, got {content_type}"
    content_disp = resp.headers.get("content-disposition", "")
    assert f'attachment; filename="{sar_id}_FINNET2.json"' in content_disp, f"Missing attachment header: {content_disp}"

    # JSON structure verification
    data = resp.json()
    assert "batch_header" in data
    assert data["batch_header"]["report_type"] == "STR"
    assert "reporting_entity" in data
    assert "case_summary" in data
    assert data["case_summary"]["sar_id"] == sar_id
    assert "grounds_of_suspicion" in data
    assert data["grounds_of_suspicion"]["primary_typology"] == "IN_TYP_STRUCT"


# ------------------------------------------------------------------------------
# 8. Test 7: Forensic PDF Dossier Export (GET /api/v1/sar/{sar_id}/export?format=pdf)
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pdf_export_endpoint(async_client):
    """Verifies streaming forensic PDF dossier export with standard PDF headers and magic bytes."""
    sar_id = await seed_sar_case("UTR-EXP-PDF", "export_pdf_target@upi", SuspicionTypology.IN_TYP_STRUCT, 49200.0)

    resp = await async_client.get(f"/api/v1/sar/{sar_id}/export?format=pdf")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    # Headers
    content_type = resp.headers.get("content-type", "")
    assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
    content_disp = resp.headers.get("content-disposition", "")
    assert f'attachment; filename="{sar_id}.pdf"' in content_disp, f"Missing attachment header: {content_disp}"

    # PDF Binary signature
    assert len(resp.content) > 1000, "PDF content must be non-empty"
    assert resp.content.startswith(b"%PDF-"), "Response content must start with PDF magic bytes %PDF-"


# ------------------------------------------------------------------------------
# 9. Test 8: Invalid Export Format Validation
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_invalid_export_format(async_client):
    """Verifies that an unsupported export format query param returns 422 Unprocessable Entity."""
    sar_id = await seed_sar_case("UTR-EXP-ERR", "export_err@upi")

    resp = await async_client.get(f"/api/v1/sar/{sar_id}/export?format=docx")
    assert resp.status_code == 422, f"Expected 422 Unprocessable Entity for format=docx, got {resp.status_code}"
