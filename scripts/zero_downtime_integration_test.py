"""
Zero-Downtime Local Integration & Deployment Verification Gate
Validates UnifiedInferenceEngine warmup, IBM 7-feature scoring, and Elliptic 166-feature scoring.
"""

import os
import sys
import time

# Ensure project root is in sys.path
_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _base_dir not in sys.path:
    sys.path.insert(0, _base_dir)

from app.services.inference_engine import UnifiedInferenceEngine


def run_integration_test():
    print("=" * 80)
    print(" QUANTUMAML NEXUS — ZERO-DOWNTIME LOCAL INTEGRATION & DEPLOYMENT TEST")
    print("=" * 80)
    sys.stdout.flush()

    verdict_items = {}

    # --------------------------------------------------------------------------
    # 1. Engine Warmup
    # --------------------------------------------------------------------------
    print("\n[STEP 1/3] Instantiating UnifiedInferenceEngine and executing warmup()...")
    t0_init = time.perf_counter()
    try:
        engine = UnifiedInferenceEngine()
        init_latency = (time.perf_counter() - t0_init) * 1000.0
        print(
            f"  [OK] Model registry initialized ({len(engine.models)} models loaded) in {init_latency:.2f}ms"
        )

        # Verify critical models exist
        assert "ibm_transactions" in engine.models, (
            "IBM Transactions model missing from engine."
        )
        assert "elliptic" in engine.models, (
            "Elliptic Bitcoin model missing from engine."
        )

        t0_warmup = time.perf_counter()
        engine.warmup()
        warmup_latency = (time.perf_counter() - t0_warmup) * 1000.0
        print(
            f"  [OK] engine.warmup() executed cleanly with zero errors in {warmup_latency:.2f}ms"
        )
        verdict_items["Warmup & Artifact Load"] = "PASS"
    except Exception as e:
        print(f"  [FAIL] Warmup encountered error: {e}")
        verdict_items["Warmup & Artifact Load"] = f"FAIL ({e})"
        print("\nDEPLOYMENT VERDICT: NO-GO")
        sys.exit(1)

    # --------------------------------------------------------------------------
    # 2. IBM Transactions Validation (7-feature schema)
    # --------------------------------------------------------------------------
    print("\n[STEP 2/3] Validating IBM Transactions continuous scoring (7 features)...")
    ibm_payload = {
        "transaction_id": "ibm_integration_tx_001",
        "from_bank": "10",
        "to_bank": "12",
        "account_from": "ACC_SEND_88",
        "account_to": "ACC_RECV_99",
        "amount": 2500.50,
        "currency": "US Dollar",
        "payment_format": "Credit Card",
    }

    try:
        t0_ibm = time.perf_counter()
        ibm_res = engine.score_transaction(ibm_payload)
        wall_latency_ibm = (time.perf_counter() - t0_ibm) * 1000.0

        print("  IBM Scoring Result:")
        print(f"    - Entity ID:          {ibm_res.get('entity_id')}")
        print(f"    - Dataset:            {ibm_res.get('dataset')}")
        print(f"    - Risk Score:         {ibm_res.get('risk_score')}")
        print(f"    - Risk Tier:          {ibm_res.get('risk_tier')}")
        print(f"    - Is Anomaly:         {ibm_res.get('is_anomaly')}")
        print(f"    - Engine Latency:     {ibm_res.get('latency_ms')} ms")
        print(f"    - Measured Latency:   {wall_latency_ibm:.3f} ms")

        # Assertions
        assert ibm_res.get("dataset") == "IBM Transactions", (
            "Invalid dataset identifier"
        )
        assert "risk_tier" in ibm_res and ibm_res["risk_tier"] in {
            "LOW",
            "ELEVATED",
            "HIGH",
            "CRITICAL_SAR",
        }, f"Invalid risk_tier: {ibm_res.get('risk_tier')}"
        assert ibm_res.get("latency_ms", 999) < 50.0, (
            f"IBM latency breached SLA (<50ms): {ibm_res.get('latency_ms')}ms"
        )
        assert wall_latency_ibm < 50.0, (
            f"IBM wall latency breached SLA (<50ms): {wall_latency_ibm}ms"
        )

        print("  [PASS] IBM scoring verified within SLA (< 50ms).")
        verdict_items["IBM Validation (7 features)"] = "PASS"
    except Exception as e:
        print(f"  [FAIL] IBM scoring validation failed: {e}")
        verdict_items["IBM Validation (7 features)"] = f"FAIL ({e})"

    # --------------------------------------------------------------------------
    # 3. Elliptic Bitcoin Validation (166-feature tensor)
    # --------------------------------------------------------------------------
    print(
        "\n[STEP 3/3] Validating Elliptic Bitcoin crypto node scoring (166-feature tensor)..."
    )
    mock_166_tensor = [0.05] * 166

    try:
        t0_crypto = time.perf_counter()
        crypto_res = engine.score_crypto(mock_166_tensor)
        wall_latency_crypto = (time.perf_counter() - t0_crypto) * 1000.0

        print("  Elliptic Scoring Result (Raw 166 Tensor):")
        print(f"    - Entity ID:          {crypto_res.get('entity_id')}")
        print(f"    - Dataset:            {crypto_res.get('dataset')}")
        print(f"    - Risk Score:         {crypto_res.get('risk_score')}")
        print(f"    - Risk Tier:          {crypto_res.get('risk_tier')}")
        print(f"    - Is Anomaly:         {crypto_res.get('is_anomaly')}")
        print(f"    - Engine Latency:     {crypto_res.get('latency_ms')} ms")
        print(f"    - Measured Latency:   {wall_latency_crypto:.3f} ms")

        # Assertions
        assert crypto_res.get("dataset") == "Elliptic Bitcoin", (
            "Invalid dataset identifier"
        )
        assert "risk_tier" in crypto_res and crypto_res["risk_tier"] in {
            "LOW",
            "ELEVATED",
            "HIGH",
            "CRITICAL_SAR",
        }, f"Invalid risk_tier: {crypto_res.get('risk_tier')}"
        assert crypto_res.get("latency_ms", 999) < 50.0, (
            f"Elliptic latency breached SLA (<50ms): {crypto_res.get('latency_ms')}ms"
        )
        assert wall_latency_crypto < 50.0, (
            f"Elliptic wall latency breached SLA (<50ms): {wall_latency_crypto}ms"
        )

        # Also test dict-formatted payload
        dict_payload = {"node_id": "btc_node_live_007", "features": mock_166_tensor}
        crypto_dict_res = engine.score_crypto(dict_payload)
        assert crypto_dict_res.get("entity_id") == "btc_node_live_007"
        assert crypto_dict_res.get("latency_ms", 999) < 50.0

        print("  [PASS] Elliptic 166-feature scoring verified within SLA (< 50ms).")
        verdict_items["Elliptic Validation (166 features)"] = "PASS"
    except Exception as e:
        print(f"  [FAIL] Elliptic crypto validation failed: {e}")
        verdict_items["Elliptic Validation (166 features)"] = f"FAIL ({e})"

    # --------------------------------------------------------------------------
    # 4. Final GO / NO-GO Deployment Verdict
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(" INTEGRATION VERIFICATION SUMMARY & GATE ASSESSMENT")
    print("=" * 80)
    all_passed = all(status == "PASS" for status in verdict_items.values())
    for name, status in verdict_items.items():
        print(f"  • {name:<35}: [{status}]")

    print("-" * 80)
    if all_passed:
        print(" FINAL DEPLOYMENT VERDICT: >>> GO <<< (Production Gate Certified)")
    else:
        print(" FINAL DEPLOYMENT VERDICT: >>> NO-GO <<< (Validation Failure Detected)")
    print("=" * 80 + "\n")
    sys.stdout.flush()

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_integration_test()
