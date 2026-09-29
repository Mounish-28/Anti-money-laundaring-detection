"""
Bank Operations Domain Router: Account Hash Lookups, iALS Collaborative Filtering & AML Surveillance.
"""

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from typing import List, Optional
from app.domains.bank.hash_lookup_service import RobinHoodHashTable
from app.domains.bank.collaborative_filter import CollaborativeFilteringService

router = APIRouter(prefix="/api/v1/bank", tags=["Bank Compliance Enclave"])

# Shared in-memory Robin Hood Hash Table preloaded with banking entities
_hash_table = RobinHoodHashTable(64)
_sample_accounts = [
    {
        "account_number": "ACC-021000021-994821",
        "entity_name": "Offshore Alpha LLC",
        "jurisdiction": "Cayman Islands",
        "kyc_risk_tier": "HIGH_RISK_EDD",
        "pep_status": False,
        "sanctions_match": False,
        "current_balance_usd": 1240500.00,
        "compliance_hold": True,
        "hold_reason": "Statutory Judicial Order Pending (Subpoena Served)",
    },
    {
        "account_number": "ACC-021000089-411082",
        "entity_name": "Apex Holdings Corp",
        "jurisdiction": "Delaware, USA",
        "kyc_risk_tier": "HIGH_RISK_EDD",
        "pep_status": False,
        "sanctions_match": False,
        "current_balance_usd": 45200.00,
        "compliance_hold": False,
        "hold_reason": None,
    },
    {
        "account_number": "ACC-559102938-771829",
        "entity_name": "Sovereign Petrochemical Trading Ltd",
        "jurisdiction": "Dubai, UAE",
        "kyc_risk_tier": "PROHIBITED_SANCTION_MATCH",
        "pep_status": True,
        "sanctions_match": True,
        "current_balance_usd": 14200900.00,
        "compliance_hold": True,
        "hold_reason": "OFAC SDN Blocked Entity Match - Immediate Freeze",
    },
]
for acc in _sample_accounts:
    _hash_table.insert(acc["account_number"], acc)

# Shared Collaborative Filtering Service
_cf_service = CollaborativeFilteringService(peer_k=2)
_cf_service.load_accounts(
    [
        {
            "id": "acc_01",
            "name": "Offshore Alpha LLC",
            "cluster": "Shell Companies",
            "vector": [0.95, 0.98, 0.92, 0.78, 0.91, 0.85, 0.88, 0.94],
        },
        {
            "id": "acc_02",
            "name": "Normal Peer A",
            "cluster": "Commercial B2B",
            "vector": [0.35, 0.40, 0.05, 0.12, 0.38, 0.08, 0.10, 0.25],
        },
        {
            "id": "acc_03",
            "name": "Normal Peer B",
            "cluster": "Commercial B2B",
            "vector": [0.38, 0.42, 0.04, 0.10, 0.35, 0.06, 0.08, 0.22],
        },
    ]
)


class AnomalyEvaluationRequest(BaseModel):
    account_id: str = Field(..., example="acc_01")
    vector: List[float] = Field(
        ..., example=[0.95, 0.98, 0.92, 0.78, 0.91, 0.85, 0.88, 0.94]
    )
    account_name: Optional[str] = "Evaluated Target"


@router.get("/accounts/{account_number}")
async def lookup_account(
    account_number: str = Path(..., examples=["ACC-021000021-994821"])
):
    """Constant-time O(1) account verification using Robin Hood hash index."""
    result = _hash_table.lookup(account_number.strip())
    if not result["found"]:
        raise HTTPException(
            status_code=404, detail="Account not found in active hash index"
        )
    return result


@router.post("/anomalies/evaluate")
async def evaluate_account_anomalies(payload: AnomalyEvaluationRequest):
    """Evaluate behavioral vector against peer cluster using iALS collaborative filtering."""
    target = {
        "id": payload.account_id,
        "name": payload.account_name,
        "vector": payload.vector,
    }
    return _cf_service.evaluate_account(target)


@router.get("/alerts")
async def get_aml_alerts():
    """Retrieve active AML surveillance alerts."""
    return {
        "alerts": [
            {
                "alert_id": "ALT-2026-9901",
                "account_number": "ACC-021000021-994821",
                "severity": "CRITICAL_SAR",
                "typology": "Structuring & Rapid Layering",
                "exposure_usd": 499500.0,
            }
        ]
    }
