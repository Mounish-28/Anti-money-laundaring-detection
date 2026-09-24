"""
Test Suite for Forensic Investigation Workbench API Router
=============================================================
Location: tests/test_forensics_api.py

Validates all endpoints required by the standalone forensic investigation workbench:
1. GET /api/v1/health
2. GET /api/v1/cases
3. GET /api/v1/cases/{case_id}
4. PATCH /api/v1/cases/{case_id}/status
5. GET /api/v1/cases/{case_id}/graph
6. GET /api/v1/cases/{case_id}/explainability
7. GET /api/v1/cases/{case_id}/suspect
8. POST /api/v1/cases/{case_id}/entities/{entity_id}/freeze
9. POST /api/v1/sar/cases/{case_id}/generate
10. GET /api/v1/sar/export/{case_id}?format=pdf
"""

import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_check(client):
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    assert data["service"] == "QuantumAML-Core"
    assert data["port"] == 8000


@pytest.mark.asyncio
async def test_get_cases_queue(client):
    res = await client.get("/api/v1/cases?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 5

    c0 = data[0]
    assert "id" in c0
    assert "risk_score" in c0
    assert "risk_tier" in c0
    assert "sla_deadline" in c0
    assert "typology" in c0
    assert "suspect_entity" in c0


@pytest.mark.asyncio
async def test_get_case_by_id(client):
    res = await client.get("/api/v1/cases/ESC-90812")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "ESC-90812"
    assert data["rail"] == "UPI"
    assert "Smurfing" in data["typology"]


@pytest.mark.asyncio
async def test_get_case_not_found(client):
    res = await client.get("/api/v1/cases/UNKNOWN-CASE-999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_case_status(client):
    payload = {
        "status": "UNDER_REVIEW",
        "notes": "Escalated for senior compliance review",
        "updated_by": "OP-441",
    }
    res = await client.patch("/api/v1/cases/ESC-90812/status", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "ESC-90812"
    assert data["status"] == "UNDER_REVIEW"
    assert data["updated_by"] == "OP-441"


@pytest.mark.asyncio
async def test_get_case_graph(client):
    res = await client.get("/api/v1/cases/ESC-90812/graph")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) >= 5
    assert len(data["edges"]) >= 4

    # Verify nodes structure
    n0 = data["nodes"][0]
    assert "id" in n0
    assert "label" in n0
    assert "type" in n0
    assert "risk_tier" in n0

    # Verify edges structure
    e0 = data["edges"][0]
    assert "source" in e0
    assert "target" in e0
    assert "amount" in e0


@pytest.mark.asyncio
async def test_get_explainability(client):
    res = await client.get("/api/v1/cases/ESC-90812/explainability")
    assert res.status_code == 200
    data = res.json()
    assert "model_name" in data
    assert "anomaly_confidence" in data
    assert "features" in data
    assert len(data["features"]) >= 5
    f0 = data["features"][0]
    assert "feature" in f0
    assert "weight" in f0
    assert "impact" in f0


@pytest.mark.asyncio
async def test_get_suspect_profile(client):
    # Primary suspect
    res = await client.get("/api/v1/cases/ESC-90812/suspect")
    assert res.status_code == 200
    data = res.json()
    assert data["entity_id"] == "ESC-90812"
    assert "vpa_or_wallet" in data
    assert "kyc_status" in data
    assert "pan_or_tax_id_masked" in data

    # Clicked graph node
    res_node = await client.get("/api/v1/cases/ESC-90812/suspect?node_id=node-mule-1")
    assert res_node.status_code == 200
    node_data = res_node.json()
    assert node_data["entity_id"] == "node-mule-1"
    assert node_data["vpa_or_wallet"] == "mule4@okaxis"


@pytest.mark.asyncio
async def test_freeze_entity(client):
    res = await client.post("/api/v1/cases/ESC-90812/entities/mule4@okaxis/freeze", json={"frozen": True})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["frozen_entity"] == "mule4@okaxis"


@pytest.mark.asyncio
async def test_generate_sar_dossier(client):
    payload = {
        "case_id": "ESC-90812",
        "narrative": "Statutory grounds under Section 12 PMLA for structuring funneling.",
        "notes": "Verified against Hawala aggregator ring.",
        "operator_id": "OP-441",
    }
    res = await client.post("/api/v1/sar/cases/ESC-90812/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["sar_id"] == "SAR-2026-90812"
    assert data["status"] == "FILED"
    assert "filing_timestamp" in data


@pytest.mark.asyncio
async def test_export_sar_pdf(client):
    res = await client.get("/api/v1/sar/export/ESC-90812?format=pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=SAR_ESC-90812_DOSSIER.pdf" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) > 1000  # Valid binary PDF size
