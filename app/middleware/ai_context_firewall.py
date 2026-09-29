"""
ASGI AI Context Firewall & Zero-Trust Perimeter Gateway Middleware.
Enforces strict physical and logical domain isolation between LEO and Bank AI endpoints.
Detects vector namespace jailbreaks, encoded prompt injection (Base64/ROT13/NFKC),
and issues immediate SHA-256 audit log commitments with HTTP 403 Boundary Rejection Cards.
"""

import base64
import codecs
import hashlib
import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("AI-ContextFirewall")

# In-memory append-only audit trail for perimeter breach attempts
PERIMETER_BREACH_AUDIT_LOG: List[Dict] = []

CROSS_DOMAIN_RESTRICTIONS = {
    "/api/v1/ai/investigation/chat": {
        "required_role": "LEO_INVESTIGATION_OFFICER",
        "forbidden_namespaces": [
            "bank_aml_compliance_v1",
            "bank_core_ledger_v2",
            "commercial_banking_v1",
        ],
        "forbidden_terms": [
            "live bank ledger",
            "un-subpoenaed",
            "internal bank hr",
            "employee notes",
            "bank_aml_compliance_v1",
            "raw bank customer pii",
            "customer ssn",
            "unredacted balance",
        ],
        "jailbreak_patterns": [
            r"ignore\s+(all\s+)?previous\s+instructions",
            r"system\s+prompt\s+extraction",
            r"reveal\s+(your\s+)?system\s+prompt",
            r"you\s+are\s+now\s+in\s+unrestricted\s+mode",
            r"override\s+namespace",
            r"bypass\s+firewall",
        ],
        "error_msg": "REQUEST DENIED [SECURITY POLICY 403]: Law Enforcement Copilot cannot query un-subpoenaed private bank ledgers.",
    },
    "/api/v1/ai/bank/chat": {
        "required_role": "BANK_COMPLIANCE_OFFICER",
        "forbidden_namespaces": [
            "investigation_dossiers_v1",
            "grand_jury_warrants_v1",
            "leo_surveillance_v1",
        ],
        "forbidden_terms": [
            "fbi case",
            "grand jury",
            "search warrant",
            "wiretap",
            "confidential informant",
            "investigation_dossiers_v1",
            "sealed indictment",
            "fiu case docket",
        ],
        "jailbreak_patterns": [
            r"ignore\s+(all\s+)?previous\s+instructions",
            r"system\s+prompt\s+extraction",
            r"reveal\s+(your\s+)?system\s+prompt",
            r"anti-tipping\s+off\s+bypass",
        ],
        "error_msg": "ANTI-TIPPING OFF HALT [31 U.S.C. § 5318(g)(2)]: Querying external criminal dockets is prohibited by federal statute.",
    },
}


def decode_potential_payloads(raw_text: str) -> List[str]:
    """Extracts and decodes raw, NFKC-normalized, Base64, and ROT13 variants from request payload."""
    candidates = [raw_text]

    # 1. Unicode normalization (NFKC)
    nfkc_text = unicodedata.normalize("NFKC", raw_text)
    if nfkc_text != raw_text:
        candidates.append(nfkc_text)

    # 2. Extract and decode Base64 strings (>= 12 alphanumeric characters with padding)
    b64_matches = re.findall(r"[A-Za-z0-9+/]{12,}={0,2}", raw_text)
    for b64 in b64_matches:
        try:
            decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
            if len(decoded.strip()) > 3:
                candidates.append(decoded)
        except Exception:
            pass

    # 3. ROT13 variant
    try:
        rot13_text = codecs.decode(raw_text, "rot_13")
        candidates.append(rot13_text)
    except Exception:
        pass

    return candidates


def generate_breach_audit_entry(
    client_ip: str,
    path: str,
    user_role: Optional[str],
    violation_type: str,
    detail: str,
    payload_sample: str,
) -> Dict:
    """Generates an immutable SHA-256 audit entry committed to the perimeter event log."""
    timestamp = datetime.now(timezone.utc).isoformat()
    raw_material = f"{timestamp}|{client_ip}|{path}|{user_role}|{violation_type}|{payload_sample[:128]}"
    audit_hash = hashlib.sha256(raw_material.encode("utf-8")).hexdigest()

    entry = {
        "event_id": f"BREACH-{audit_hash[:12]}",
        "timestamp": timestamp,
        "client_ip": client_ip,
        "endpoint": path,
        "user_role": user_role or "ANONYMOUS",
        "violation_type": violation_type,
        "detail": detail,
        "audit_hash": audit_hash,
        "mitigation": "HTTP_403_PERIMETER_INTERCEPTION",
    }
    PERIMETER_BREACH_AUDIT_LOG.append(entry)
    logger.critical(
        f"PERIMETER BREACH INTERCEPTED: {entry['event_id']} - {violation_type} - {audit_hash}"
    )
    return entry


class AIContextFirewallMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if path in CROSS_DOMAIN_RESTRICTIONS:
            rule = CROSS_DOMAIN_RESTRICTIONS[path]
            client_ip = request.client.host if request.client else "127.0.0.1"

            # 1. Validate Clearance Role Header / Claim
            user_role = getattr(
                request.state, "user_role", None
            ) or request.headers.get("X-User-Role")
            if user_role and user_role != rule["required_role"]:
                logger.warning(
                    f"Domain clearance mismatch: role '{user_role}' targeted '{path}'"
                )
                audit_entry = generate_breach_audit_entry(
                    client_ip=client_ip,
                    path=path,
                    user_role=user_role,
                    violation_type="RBAC_CLEARANCE_MISMATCH",
                    detail=f"Role '{user_role}' lacks required clearance '{rule['required_role']}'",
                    payload_sample="ROLE_HEADER_MISMATCH",
                )
                return Response(
                    content=json.dumps(
                        {
                            "error": "CROSS_DOMAIN_BREACH_ATTEMPT",
                            "status_code": status.HTTP_403_FORBIDDEN,
                            "error_code": "403_CROSS_DOMAIN_BREACH_ATTEMPT",
                            "detail": "Cross-domain clearance mismatch. Access denied.",
                            "audit_hash": audit_entry["audit_hash"],
                            "timestamp": audit_entry["timestamp"],
                            "boundary_rejection_card": {
                                "violation_type": "RBAC_CLEARANCE_MISMATCH",
                                "severity": "CRITICAL",
                                "enclave_isolated": True,
                                "required_role": rule["required_role"],
                                "presented_role": user_role,
                            },
                        }
                    ),
                    status_code=status.HTTP_403_FORBIDDEN,
                    media_type="application/json",
                )

            # 2. Inspect Request Body for Vector Namespace Injection & Attacks
            body_bytes = await request.body()
            body_text = body_bytes.decode("utf-8", errors="ignore")

            # Check JSON structure for direct namespace override attacks
            try:
                parsed_json = json.loads(body_text)
                if isinstance(parsed_json, dict):
                    injected_namespace = parsed_json.get(
                        "namespace"
                    ) or parsed_json.get("vector_namespace")
                    if injected_namespace in rule.get("forbidden_namespaces", []):
                        audit_entry = generate_breach_audit_entry(
                            client_ip=client_ip,
                            path=path,
                            user_role=user_role,
                            violation_type="VECTOR_NAMESPACE_JAILBREAK",
                            detail=f"Unauthorized vector namespace injection: {injected_namespace}",
                            payload_sample=body_text[:128],
                        )
                        return Response(
                            content=json.dumps(
                                {
                                    "error": "CROSS_DOMAIN_BREACH_ATTEMPT",
                                    "status_code": status.HTTP_403_FORBIDDEN,
                                    "error_code": "403_CROSS_DOMAIN_BREACH_ATTEMPT",
                                    "detail": f"Unauthorized vector namespace injection: '{injected_namespace}' is quarantined.",
                                    "audit_hash": audit_entry["audit_hash"],
                                    "timestamp": audit_entry["timestamp"],
                                    "boundary_rejection_card": {
                                        "violation_type": "VECTOR_NAMESPACE_JAILBREAK",
                                        "severity": "CRITICAL",
                                        "enclave_isolated": True,
                                        "quarantined_namespace": injected_namespace,
                                    },
                                }
                            ),
                            status_code=status.HTTP_403_FORBIDDEN,
                            media_type="application/json",
                        )
            except Exception:
                pass

            # 3. Decode & scan for Prompt Injections, ROT13, Base64, and System Leakage
            payload_variants = decode_potential_payloads(body_text)
            for variant in payload_variants:
                var_lower = variant.lower()

                # Forbidden Domain Terms
                for term in rule["forbidden_terms"]:
                    if term in var_lower:
                        audit_entry = generate_breach_audit_entry(
                            client_ip=client_ip,
                            path=path,
                            user_role=user_role,
                            violation_type="STATUTORY_BOUNDARY_VIOLATION",
                            detail=f"Query contained forbidden cross-domain term '{term}'",
                            payload_sample=variant[:128],
                        )
                        return Response(
                            content=json.dumps(
                                {
                                    "error": "CROSS_DOMAIN_BREACH_ATTEMPT",
                                    "status_code": status.HTTP_403_FORBIDDEN,
                                    "error_code": "403_CROSS_DOMAIN_BREACH_ATTEMPT",
                                    "detail": rule["error_msg"],
                                    "audit_hash": audit_entry["audit_hash"],
                                    "timestamp": audit_entry["timestamp"],
                                    "boundary_rejection_card": {
                                        "violation_type": "STATUTORY_BOUNDARY_VIOLATION",
                                        "severity": "CRITICAL",
                                        "enclave_isolated": True,
                                        "intercepted_term": term,
                                    },
                                }
                            ),
                            status_code=status.HTTP_403_FORBIDDEN,
                            media_type="application/json",
                        )

                # Jailbreak and Prompt Injection Regex Patterns
                for pattern in rule.get("jailbreak_patterns", []):
                    if re.search(pattern, var_lower):
                        audit_entry = generate_breach_audit_entry(
                            client_ip=client_ip,
                            path=path,
                            user_role=user_role,
                            violation_type="PROMPT_INJECTION_ATTEMPT",
                            detail=f"Jailbreak pattern matched: {pattern}",
                            payload_sample=variant[:128],
                        )
                        return Response(
                            content=json.dumps(
                                {
                                    "error": "CROSS_DOMAIN_BREACH_ATTEMPT",
                                    "status_code": status.HTTP_403_FORBIDDEN,
                                    "error_code": "403_CROSS_DOMAIN_BREACH_ATTEMPT",
                                    "detail": "Adversarial prompt injection pattern intercepted by AI Context Firewall.",
                                    "audit_hash": audit_entry["audit_hash"],
                                    "timestamp": audit_entry["timestamp"],
                                    "boundary_rejection_card": {
                                        "violation_type": "PROMPT_INJECTION_ATTEMPT",
                                        "severity": "CRITICAL",
                                        "enclave_isolated": True,
                                    },
                                }
                            ),
                            status_code=status.HTTP_403_FORBIDDEN,
                            media_type="application/json",
                        )

        return await call_next(request)
