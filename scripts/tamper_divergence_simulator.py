#!/usr/bin/env python3
"""
STEP 5.2.2: TAMPER-INJECTION SIMULATION & DIVERGENCE ROOT-CAUSE ENGINE
Simulates synthetic state corruption at arbitrary block heights in ledger records,
sequentially recalculates hash linkage (H_i = SHA256(0x02 || H_{i-1} || Event_i)),
isolates the Point-of-Divergence, diffs altered fields, and simulates WebSocket incident broadcast.
"""
import copy
import hashlib
import json
import logging
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DivergenceDiagnostics")

GENESIS_HASH = "0" * 64


def sha256_domain(domain_byte: int, payload: bytes) -> str:
    """Domain-separated SHA-256 hash."""
    hasher = hashlib.sha256()
    hasher.update(bytes([domain_byte]))
    hasher.update(payload)
    return hasher.hexdigest()


def compute_block_hash(prev_hash: str, block_index: int, timestamp: int, data: Dict[str, Any]) -> str:
    """Computes H_i = SHA256( 0x02 || H_{i-1} || Index || Timestamp || CanonicalJson )"""
    canonical_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
    raw = prev_hash.encode("utf-8") + str(block_index).encode("utf-8") + str(timestamp).encode("utf-8") + canonical_bytes
    return sha256_domain(0x02, raw)


class ForensicAuditLedger:
    def __init__(self):
        self.chain: List[Dict[str, Any]] = []

    def commit_block(self, data: Dict[str, Any], timestamp: Optional[int] = None) -> Dict[str, Any]:
        prev_hash = self.chain[-1]["block_hash"] if self.chain else GENESIS_HASH
        idx = len(self.chain)
        ts = timestamp if timestamp is not None else int(time.time() * 1000)

        block_hash = compute_block_hash(prev_hash, idx, ts, data)
        block = {
            "block_index": idx,
            "timestamp": ts,
            "previous_hash": prev_hash,
            "block_hash": block_hash,
            "data": copy.deepcopy(data)
        }
        self.chain.append(block)
        return block


class TamperDivergenceScanner:
    """Scans historical ledger chain and detects point of divergence with field-level diffing."""

    @staticmethod
    def audit_chain(
        ledger_chain: List[Dict[str, Any]],
        reference_chain: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        expected_prev = GENESIS_HASH

        for i, block in enumerate(ledger_chain):
            # 1. Verify previous hash pointer
            if block["previous_hash"] != expected_prev:
                return TamperDivergenceScanner._build_divergence_report(
                    diverged_index=i,
                    block=block,
                    reason="PREVIOUS_HASH_POINTER_BROKEN",
                    expected=expected_prev,
                    actual=block["previous_hash"],
                    reference_block=reference_chain[i] if reference_chain and i < len(reference_chain) else None
                )

            # 2. Recalculate block hash
            recomputed = compute_block_hash(
                expected_prev,
                block["block_index"],
                block["timestamp"],
                block["data"]
            )

            if recomputed != block["block_hash"]:
                return TamperDivergenceScanner._build_divergence_report(
                    diverged_index=i,
                    block=block,
                    reason="BLOCK_PAYLOAD_TAMPERED",
                    expected=block["block_hash"],
                    actual=recomputed,
                    reference_block=reference_chain[i] if reference_chain and i < len(reference_chain) else None
                )

            expected_prev = block["block_hash"]

        return {
            "status": "VERIFIED_SECURE",
            "total_blocks_scanned": len(ledger_chain),
            "divergence_detected": False,
            "incident_report": None
        }

    @staticmethod
    def _build_divergence_report(
        diverged_index: int,
        block: Dict[str, Any],
        reason: str,
        expected: str,
        actual: str,
        reference_block: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        tampered_fields: Dict[str, Any] = {}
        if reference_block:
            ref_data = reference_block.get("data", {})
            cur_data = block.get("data", {})
            for k in set(ref_data.keys()).union(cur_data.keys()):
                if ref_data.get(k) != cur_data.get(k):
                    tampered_fields[k] = {
                        "original_value": ref_data.get(k),
                        "mutated_value": cur_data.get(k)
                    }

        incident_id = f"INC-INTEGRITY-{int(time.time())}-BLK{diverged_index}"
        incident_report = {
            "incident_id": incident_id,
            "severity": "SEV-1_PERIMETER_INTEGRITY_BREACH",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "diverged_block_index": diverged_index,
            "diverged_block_hash": block.get("block_hash"),
            "expected_hash": expected,
            "recomputed_hash": actual,
            "divergence_reason": reason,
            "tampered_fields_diff": tampered_fields,
            "remediation": "QUARANTINE_NODE_AND_TRIGGER_DR_FAILOVER"
        }

        # Telemetry hook: Broadcast alert to supervisory console
        TamperDivergenceScanner.broadcast_websocket_security_alert(incident_report)

        return {
            "status": "TAMPERING_DETECTED",
            "total_blocks_scanned": diverged_index + 1,
            "divergence_detected": True,
            "incident_report": incident_report
        }

    @staticmethod
    def broadcast_websocket_security_alert(incident_report: Dict[str, Any]) -> None:
        """Simulates immediate WebSocket push of SEV-1 perimeter breach alert to active supervisors."""
        ws_frame = {
            "channel": "supervisory_integrity_alerts",
            "event_type": "PERIMETER_STATE_CORRUPTION_DETECTED",
            "payload": incident_report
        }
        logger.critical(
            f"[WS BROADCAST] {ws_frame['event_type']} -> Block #{incident_report['diverged_block_index']} "
            f"Mutated Fields: {list(incident_report['tampered_fields_diff'].keys())}"
        )


def run_divergence_simulation():
    print("================================================================")
    print("TAMPER INJECTION SIMULATION & DIVERGENCE DIAGNOSTICS")
    print("================================================================\n")

    ledger = ForensicAuditLedger()
    base_time = 1700000000000

    # Build reference chain of 10 blocks
    for i in range(10):
        ledger.commit_block({
            "tx_id": f"TX-LEDGER-{i:04d}",
            "amount": 10000.0 * (i + 1),
            "status": "SETTLED",
            "authorized_by": "COMPLIANCE_DIRECTOR_41"
        }, timestamp=base_time + (i * 1000))

    # Keep pristine copy as reference
    reference_chain = copy.deepcopy(ledger.chain)

    # 1. Audit pristine chain
    clean_result = TamperDivergenceScanner.audit_chain(ledger.chain, reference_chain)
    assert clean_result["status"] == "VERIFIED_SECURE"
    print(f"  [PASS] Pristine ledger of {len(ledger.chain)} blocks audited with 100% integrity.")

    # 2. Inject adversarial mutation at block height 4 (flip amount from 50000 to 500000)
    mutation_target = 4
    ledger.chain[mutation_target]["data"]["amount"] = 500000.00
    ledger.chain[mutation_target]["data"]["status"] = "UNAUTHORIZED_CREDIT"

    print(f"\n[INJECTING ADVERSARIAL TAMPERING] Mutating Block #{mutation_target} payload...")
    tampered_result = TamperDivergenceScanner.audit_chain(ledger.chain, reference_chain)

    assert tampered_result["status"] == "TAMPERING_DETECTED"
    assert tampered_result["divergence_detected"] is True
    report = tampered_result["incident_report"]
    assert report["diverged_block_index"] == mutation_target
    assert "amount" in report["tampered_fields_diff"]
    assert "status" in report["tampered_fields_diff"]
    assert report["severity"] == "SEV-1_PERIMETER_INTEGRITY_BREACH"

    print("\n--- FORENSIC INCIDENT REPORT GENERATED ---")
    print(f" - Incident ID:          {report['incident_id']}")
    print(f" - Severity:             {report['severity']}")
    print(f" - Mutated Block:        #{report['diverged_block_index']}")
    print(f" - Expected Hash:        {report['expected_hash']}")
    print(f" - Recomputed Hash:      {report['recomputed_hash']}")
    print(f" - Mutated Fields Diff:  {json.dumps(report['tampered_fields_diff'], indent=2)}")
    print("\n[SUCCESS] Tamper detection scanner pinpointed divergence with 100% accuracy.\n")


if __name__ == "__main__":
    run_divergence_simulation()
