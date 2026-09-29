"""
Domain-Isolated AI Copilot Router.
Enforces physical and logical isolation between LEO and Bank AI streams.
"""

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/api/v1/ai", tags=["Isolated AI Copilot"])


class AIChatRequest(BaseModel):
    prompt: str = Field(..., example="Summarize wire flow hops from Offshore Alpha")
    session_id: Optional[str] = "sess_default"
    active_case_id: Optional[str] = "CASE-2026-NYSD-0982"


@router.post("/investigation/chat")
async def investigation_ai_chat(
    payload: AIChatRequest, x_user_role: Optional[str] = Header(None)
):
    """
    Law Enforcement Forensic Copilot Endpoint.
    Strictly isolated to legally subpoenaed evidence and warrant dockets.
    """
    prompt_lower = payload.prompt.lower()

    # Domain Firewall Enforcement
    if "un-subpoenaed" in prompt_lower or "live bank ledger" in prompt_lower:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="REQUEST DENIED [SECURITY POLICY 403]: Law Enforcement Copilot cannot query un-subpoenaed private bank ledgers.",
        )

    if "wire flow" in prompt_lower or "hop" in prompt_lower:
        response_text = (
            "Forensic transaction hop summary for CASE-2026-NYSD-0982:\n"
            "1. Hop 0 (Smurfing): Structured branch cash deposits ($9.9k) into Offshore Alpha LLC.\n"
            "2. Hop 1 (Layering): SWIFT MT103 wire of $499,500.00 to Apex Holdings Corp (DE).\n"
            "3. Hop 2 (Pass-Thru): Fedwire of $495,000.00 to Orion Global Trust within 4 hours.\n"
            "4. Hop 3 (Integration): $490,000.00 settlement with Park Ave Title for penthouse acquisition."
        )
        citations = [
            "EVID-DOC-001: MT103",
            "SUB-2026-8812",
            "EVID-DOC-003: FinCEN Memo",
        ]
    else:
        response_text = "Analysis complete within authorized subpoena scope. All records verified against court dockets."
        citations = ["SUB-2026-8812"]

    return {
        "sender": "ai",
        "role": "LEO_AGENT",
        "domain": "INVESTIGATION_ENCLAVE",
        "response": response_text,
        "citations": citations,
        "canary_token": "CANARY_LEO_VALID_0x9f1a",
        "audit_hash": "0x8a91b42c19e8",
    }


@router.post("/bank/chat")
async def bank_ai_chat(
    payload: AIChatRequest, x_user_role: Optional[str] = Header(None)
):
    """
    Commercial Bank AML Copilot Endpoint.
    Strictly isolated to core bank ledgers under statutory anti-tipping off rules.
    """
    prompt_lower = payload.prompt.lower()

    # Anti-Tipping Off Guardrail Enforcement
    if (
        "fbi" in prompt_lower
        or "grand jury" in prompt_lower
        or "search warrant" in prompt_lower
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ANTI-TIPPING OFF HALT [31 U.S.C. § 5318(g)(2)]: Querying external criminal dockets is prohibited.",
        )

    if "structuring" in prompt_lower or "fastpay" in prompt_lower:
        response_text = (
            "AML Risk Evaluation for FastPay Retail Convenience:\n"
            "- Alert Trigger: Multiple cash deposits under $10,000 CTR threshold.\n"
            "- Peer Variance: +3.8 sigma deviation from grocery peer cluster mean.\n"
            "- Recommended Action: Escalate to FinCEN SAR Form 111 drafting queue."
        )
        recommended_action = "ESCALATE_SAR_FORM_111"
    else:
        response_text = "Surveillance check complete against core bank ledgers. Zero cross-domain data accessed."
        recommended_action = "NONE"

    return {
        "sender": "ai",
        "role": "BANK_AGENT",
        "domain": "BANK_OPERATIONS_ENCLAVE",
        "response": response_text,
        "recommended_action": recommended_action,
        "canary_token": "CANARY_BNK_VALID_0x3f12",
        "audit_hash": "0x3f12c98d014b",
    }
