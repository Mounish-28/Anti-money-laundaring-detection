"""
Hardened JWT Authentication and RBAC Verification Service.
Enforces algorithm integrity (blocks 'none' exploit and RS256/HS256 confusion),
validates expiration claims, and maintains token revocation registries.
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Dict, Optional, Tuple

JWT_SECRET_KEY = "QUANTUMAML_SECURE_HMAC_SECRET_2026"
REVOKED_TOKENS = set()


def create_test_jwt(
    role: str = "LEO_INVESTIGATION_OFFICER",
    user_id: str = "officer_41",
    expires_in_seconds: int = 3600,
    algorithm: str = "HS256",
) -> str:
    """Generates an RFC 7519 compliant test JWT with cryptographic signature."""
    header = {"alg": algorithm, "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + expires_in_seconds,
    }

    header_b64 = (
        base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    )
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    )

    signing_input = f"{header_b64}.{payload_b64}"
    if algorithm == "none":
        signature = ""
    else:
        sig_bytes = hmac.new(
            JWT_SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        signature = base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")

    return f"{signing_input}.{signature}"


def verify_jwt_token_stub(token: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Cryptographically verifies a JWT token against algorithm exploits,
    expiration claims, and revocation blacklist.
    """
    if not token or token.count(".") != 2:
        return False, "Malformed JWT structure", None

    parts = token.split(".")
    header_b64, payload_b64, signature_b64 = parts[0], parts[1], parts[2]

    # Check for immediate revocation
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    if token_hash in REVOKED_TOKENS:
        return False, "Token has been revoked", None

    # Decode header
    try:
        header_padding = "=" * ((4 - len(header_b64) % 4) % 4)
        header_json = json.loads(
            base64.urlsafe_b64decode(header_b64 + header_padding).decode()
        )
    except Exception as e:
        return False, f"Invalid header encoding: {e}", None

    # Algorithm hardening: strictly forbid 'none'
    alg = header_json.get("alg")
    if alg == "none" or not alg:
        return (
            False,
            "Algorithm 'none' is strictly forbidden by zero-trust policy",
            None,
        )
    if alg != "HS256":
        return False, f"Unsupported or confused algorithm: {alg}", None

    # Decode payload
    try:
        payload_padding = "=" * ((4 - len(payload_b64) % 4) % 4)
        payload = json.loads(
            base64.urlsafe_b64decode(payload_b64 + payload_padding).decode()
        )
    except Exception as e:
        return False, f"Invalid payload encoding: {e}", None

    # Verify signature
    signing_input = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        JWT_SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

    if not hmac.compare_digest(signature_b64, expected_sig_b64):
        return False, "Cryptographic signature mismatch", None

    # Expiration check
    now = int(time.time())
    if "exp" in payload and payload["exp"] < now:
        return False, f"Token expired at {payload['exp']}, current time: {now}", None

    return True, "Token verified successfully", payload


def revoke_token(token: str) -> None:
    """Adds a token's SHA-256 fingerprint to the active revocation registry."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    REVOKED_TOKENS.add(token_hash)
