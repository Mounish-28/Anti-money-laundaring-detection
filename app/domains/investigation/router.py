"""
Investigation Domain Router: Case Management, Subpoenas, BM25 Search & 3-Way QuickSort.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List
from app.domains.investigation.bm25_service import BM25SearchService
from app.domains.investigation.quicksort_service import QuickSortLedgerService

router = APIRouter(prefix="/api/v1/investigation", tags=["Investigation Enclave"])

# Shared in-memory BM25 instance initialized with sample evidence documents
_bm25_engine = BM25SearchService()
_sample_evidence = [
    {
        "id": "EVID-DOC-001",
        "case_id": "CASE-2026-NYSD-0982",
        "title": "Subpoena Return: JPMorgan Wire Ledger MT103",
        "category": "BANK_RECORD",
        "content": "JPMorgan Chase response to SUB-2026-8812. Wire transfer of $499,500.00 from Offshore Alpha LLC routing 021000021 to Apex Holdings LLC. Beneficiary routing 021000021. Payment reference specifies legal consulting. Sub-wire $495,000 sent to Orion Global Trust escrow.",
    },
    {
        "id": "EVID-DOC-002",
        "case_id": "CASE-2026-NYSD-0982",
        "title": "Seized Device Transcript: Encrypted Signal Chat #44",
        "category": "DIGITAL_FORENSICS",
        "content": "Forensic extraction of iPhone seized from target Marcus Vance. Conversation: Make sure the Cayman wire stays under 500k to avoid mandatory committee escalation. Route through Apex Holdings before sending to Orion Trust escrow. Delaware registered agent nominee director prepped.",
    },
    {
        "id": "EVID-DOC-003",
        "case_id": "CASE-2026-NYSD-0982",
        "title": "Forensic Accounting Memo: Layering Velocity & Structuring Analysis",
        "category": "FORENSIC_ANALYSIS",
        "content": "Cross-bank correlation reveals classic smurfing and rapid layering. 5 separate cash deposits of $9,800 to $9,950 structured at Manhattan retail branches within 48 hours, immediately aggregated and wired to Offshore Alpha LLC.",
    },
]
_bm25_engine.index_corpus(_sample_evidence)


class BM25SearchRequest(BaseModel):
    query: str = Field(..., example="shell company Cayman routing 021000021")
    k1: float = Field(default=1.25, ge=0.1, le=2.5)
    b: float = Field(default=0.75, ge=0.01, le=1.0)
    top_k: int = Field(default=20, ge=1, le=100)


class QuickSortRequest(BaseModel):
    records: List[Dict[str, Any]]
    sort_criteria: List[Dict[str, str]] = Field(
        default=[{"key": "amount", "direction": "desc"}]
    )


@router.get("/cases")
async def get_active_cases():
    """Retrieve active warrant-backed case dossiers."""
    return {
        "cases": [
            {
                "case_id": "CASE-2026-NYSD-0982",
                "title": "Operation Offshore Mirage",
                "court_docket": "1:26-cr-00982-KPF (S.D.N.Y.)",
                "status": "ACTIVE_INDICTMENT_PREP",
                "total_exposure_usd": 14850000.0,
                "clearance_level": "CJIS_LEVEL_4",
            }
        ]
    }


@router.post("/evidence/search")
async def search_evidence(payload: BM25SearchRequest):
    """Execute probabilistic BM25 search over evidence repository."""
    _bm25_engine.set_parameters(payload.k1, payload.b)
    return _bm25_engine.search(payload.query, top_k=payload.top_k)


@router.post("/trail/sort")
async def sort_transaction_trail(payload: QuickSortRequest):
    """Execute 3-way Dutch National Flag QuickSort on transaction ledger records."""
    return QuickSortLedgerService.sort(payload.records, payload.sort_criteria)


@router.get("/graph/{case_id}")
async def get_entity_graph(case_id: str):
    """Retrieve multi-hop directed relationship graph with betweenness centrality."""
    return {
        "case_id": case_id,
        "nodes": [
            {
                "id": "n1",
                "label": "Offshore Alpha LLC",
                "type": "SHELL_COMPANY",
                "centrality": 0.942,
            },
            {
                "id": "n2",
                "label": "Apex Holdings Corp",
                "type": "HOLDING_LLC",
                "centrality": 0.881,
            },
            {
                "id": "n3",
                "label": "Orion Global Trust",
                "type": "ESCROW_TRUST",
                "centrality": 0.765,
            },
            {
                "id": "n4",
                "label": "Marcus Vance",
                "type": "UBO_TARGET",
                "centrality": 0.991,
            },
        ],
        "edges": [
            {
                "from": "n1",
                "to": "n2",
                "amount": 499500.0,
                "label": "SWIFT Wire $499.5k",
            },
            {
                "from": "n2",
                "to": "n3",
                "amount": 495000.0,
                "label": "Fedwire Pass-Thru $495k",
            },
            {
                "from": "n4",
                "to": "n1",
                "amount": 0.0,
                "label": "Beneficial Control 100%",
            },
        ],
    }
