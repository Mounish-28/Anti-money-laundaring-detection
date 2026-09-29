"""
Linear Cryptographic Audit Hash Chain Engine.
Enforces monotonic timestamps, domain-separated sequential hashing,
and deterministic Point-of-Divergence detection.
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple

GENESIS_HASH = "0" * 64


def calculate_chain_hash(previous_hash: str, payload: Dict, timestamp: int) -> str:
    """Computes H_i = SHA256( 0x02 || H_{i-1} || timestamp || canonical_payload )"""
    canonical_json = json.dumps(payload, sort_keys=True)
    raw = (
        b"\x02"
        + previous_hash.encode("utf-8")
        + str(timestamp).encode("utf-8")
        + canonical_json.encode("utf-8")
    )
    return hashlib.sha256(raw).hexdigest()


def append_audit_event(
    previous_hash: str,
    payload: Dict,
    timestamp: Optional[int] = None,
    previous_timestamp: Optional[int] = None,
) -> Tuple[Dict, str]:
    """Appends an event with monotonic timestamp verification."""
    ts = timestamp if timestamp is not None else int(time.time() * 1000)

    if previous_timestamp is not None and ts < previous_timestamp:
        raise ValueError(f"Monotonic timestamp violation: {ts} < {previous_timestamp}")

    chain_hash = calculate_chain_hash(previous_hash, payload, ts)
    event = {
        "timestamp": ts,
        "payload": payload,
        "previous_hash": previous_hash,
        "chain_hash": chain_hash,
    }
    return event, chain_hash


def build_test_hash_chain(num_events: int = 5) -> List[Dict]:
    """Builds a verified linear hash chain for testing."""
    chain: List[Dict] = []
    prev_hash = GENESIS_HASH
    base_time = 1700000000000

    for i in range(num_events):
        ts = base_time + (i * 1000)
        payload = {
            "event_index": i,
            "action": f"FORENSIC_ACTION_{i}",
            "amount": 10000.0 * (i + 1),
            "status": "RECORDED",
        }
        event, chain_hash = append_audit_event(
            previous_hash=prev_hash,
            payload=payload,
            timestamp=ts,
            previous_timestamp=chain[-1]["timestamp"] if chain else None,
        )
        chain.append(event)
        prev_hash = chain_hash

    return chain


def verify_test_hash_chain(chain: List[Dict]) -> Tuple[bool, Optional[int]]:
    """
    Verifies a linear hash chain sequentially.
    Returns (True, None) if pristine, or (False, divergence_index) if tampered.
    """
    expected_prev = GENESIS_HASH

    for i, event in enumerate(chain):
        # 1. Verify link to previous hash
        if event["previous_hash"] != expected_prev:
            return False, i

        # 2. Recalculate hash
        recalculated = calculate_chain_hash(
            event["previous_hash"], event["payload"], event["timestamp"]
        )
        if recalculated != event["chain_hash"]:
            return False, i

        expected_prev = event["chain_hash"]

    return True, None
