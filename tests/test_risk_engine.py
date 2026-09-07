# flake8: noqa
import time
import os
import sys
import asyncio
import numpy as np
import httpx

# Ensure root and src are on python path
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base not in sys.path:
    sys.path.insert(0, _base)
_src = os.path.join(_base, "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from app.main import app


async def run_benchmark():
    print(
        "================================================================================"
    )
    print("TEST & LOAD BENCHMARK: TIERED AML CONTINUOUS RISK ENGINE")
    print(
        "================================================================================"
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        # 1. Verify Health Endpoint
        print("\n[Step 1] Verifying /health endpoint...")
        res_health = await client.get("/health")
        assert res_health.status_code == 200, f"Health check failed: {res_health.text}"
        health_data = res_health.json()
        print(f"Health Status: {health_data['status']}")
        print(f"Models Loaded: {health_data['models_loaded']}")
        print(f"Risk Tiers Configured: {health_data['risk_tiers_configured']}")
        print(f"Worker Status: {health_data['worker_status']}")
        assert health_data["status"] == "healthy"
        assert health_data["risk_tiers_configured"] is True

        # 2. Test Crypto Endpoint
        print("\n[Step 2] Testing /api/v1/score/crypto endpoint...")
        crypto_payload = {
            "tx_id": "btc_test_node_001",
            "timestep": 35,
            "features": [0.12] * 165,
        }
        res_crypto = await client.post("/api/v1/score/crypto", json=crypto_payload)
        assert res_crypto.status_code == 200, (
            f"Crypto scoring failed: {res_crypto.text}"
        )
        crypto_data = res_crypto.json()
        print(
            f"Crypto Score: {crypto_data['risk_score']}, Percentile: {crypto_data['percentile']}%, Tier: {crypto_data['risk_tier']}, Latency: {crypto_data['latency_ms']}ms"
        )
        assert "risk_score" in crypto_data
        assert "percentile" in crypto_data
        assert "risk_tier" in crypto_data

        # 3. Test Batch Endpoint
        print("\n[Step 3] Testing /api/v1/score/batch endpoint...")
        batch_payload = [
            {
                "transaction_id": f"batch_tx_{i}",
                "from_bank": 10,
                "to_bank": 10,
                "amount": 100.0 * (i + 1),
                "receiving_currency": "US Dollar",
                "payment_currency": "US Dollar",
                "payment_format": "Credit Card",
                "timestamp": "2026/09/03 10:00",
            }
            for i in range(5)
        ]
        res_batch = await client.post("/api/v1/score/batch", json=batch_payload)
        assert res_batch.status_code == 200
        batch_data = res_batch.json()
        print(
            f"Batch Total Processed: {batch_data['total_processed']}, Avg Score: {batch_data['avg_risk_score']}, Total Latency: {batch_data['total_latency_ms']}ms"
        )
        assert batch_data["total_processed"] == 5

        # 4. 1,000 Mixed Transactions Simulation & Load Benchmark
        print(
            "\n[Step 4] Simulating 1,000 Mixed Transactions & Benchmarking Throughput..."
        )

        normal_tx_count = 900
        smurfing_tx_count = 50
        high_value_tx_count = 50
        total_tx = normal_tx_count + smurfing_tx_count + high_value_tx_count

        latencies = []
        tier_counts = {
            "LOW_RISK": 0,
            "ELEVATED_RISK": 0,
            "HIGH_RISK": 0,
            "CRITICAL_SAR": 0,
        }
        normal_tiers = {
            "LOW_RISK": 0,
            "ELEVATED_RISK": 0,
            "HIGH_RISK": 0,
            "CRITICAL_SAR": 0,
        }
        anomalous_tiers = {
            "LOW_RISK": 0,
            "ELEVATED_RISK": 0,
            "HIGH_RISK": 0,
            "CRITICAL_SAR": 0,
        }

        # Pre-generate 1,000 payloads
        normal_formats = ["Credit Card", "Cheque"]
        normal_banks = [1, 10, 12, 3208, 3209]

        payloads = []
        for i in range(normal_tx_count):
            b = normal_banks[i % len(normal_banks)]
            fmt = normal_formats[i % len(normal_formats)]
            payloads.append(
                (
                    "NORMAL",
                    {
                        "transaction_id": f"benign_tx_{i:04d}",
                        "from_bank": b,
                        "to_bank": b,
                        "amount": float(np.random.uniform(15.0, 500.0)),
                        "receiving_currency": "US Dollar",
                        "payment_currency": "US Dollar",
                        "payment_format": fmt,
                        "timestamp": "2026/09/03 14:30",
                    },
                )
            )

        for i in range(smurfing_tx_count):
            payloads.append(
                (
                    "SMURF",
                    {
                        "transaction_id": f"smurf_tx_{i:04d}",
                        "from_bank": 15,
                        "to_bank": 22,
                        "amount": float(np.random.uniform(9500.0, 9950.0)),
                        "receiving_currency": "Euro",
                        "payment_currency": "US Dollar",
                        "payment_format": "Wire",
                        "timestamp": "2026/09/03 03:15",
                    },
                )
            )

        for i in range(high_value_tx_count):
            payloads.append(
                (
                    "HIGH_VALUE",
                    {
                        "transaction_id": f"high_risk_tx_{i:04d}",
                        "from_bank": 99,
                        "to_bank": 105,
                        "amount": float(np.random.uniform(550000.0, 2500000.0)),
                        "receiving_currency": "Swiss Franc",
                        "payment_currency": "US Dollar",
                        "payment_format": "Wire",
                        "timestamp": "2026/09/03 02:45",
                    },
                )
            )

        # Warm-up request
        await client.post("/api/v1/score/transaction", json=payloads[0][1])

        t_benchmark_start = time.perf_counter()

        for category, p in payloads:
            t0 = time.perf_counter()
            res = await client.post("/api/v1/score/transaction", json=p)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)

            data = res.json()
            t = data["risk_tier"]
            tier_counts[t] += 1
            if category == "NORMAL":
                normal_tiers[t] += 1
            else:
                anomalous_tiers[t] += 1

        t_benchmark_end = time.perf_counter()
        total_duration_sec = t_benchmark_end - t_benchmark_start
        throughput = total_tx / total_duration_sec

        mean_latency = float(np.mean(latencies))
        p50_latency = float(np.percentile(latencies, 50.0))
        p95_latency = float(np.percentile(latencies, 95.0))
        p99_latency = float(np.percentile(latencies, 99.0))

        # Assertions
        normal_low_risk_pct = (normal_tiers["LOW_RISK"] / normal_tx_count) * 100.0
        anomalous_flagged_count = (
            anomalous_tiers["HIGH_RISK"] + anomalous_tiers["CRITICAL_SAR"]
        )
        anomalous_flagged_pct = (
            anomalous_flagged_count / (smurfing_tx_count + high_value_tx_count)
        ) * 100.0

        print(
            "\n================================================================================"
        )
        print("VERIFICATION MATRIX & LOAD BENCHMARK RESULTS")
        print(
            "================================================================================"
        )
        print(f"Total Transactions Tested:     {total_tx}")
        print(f"Total Wall Clock Duration:     {total_duration_sec:.2f} seconds")
        print(f"Throughput:                    {throughput:.1f} tx/sec")
        print(
            f"Mean Latency per Request:      {mean_latency:.2f} ms (Target: < 10.0 ms)"
        )
        print(f"Median (P50) Latency:          {p50_latency:.2f} ms")
        print(f"95th Percentile Latency (P95): {p95_latency:.2f} ms")
        print(f"99th Percentile Latency (P99): {p99_latency:.2f} ms")
        print(
            "--------------------------------------------------------------------------------"
        )
        print("TIER ROUTING BREAKDOWN:")
        print(
            f"  * LOW_RISK (Auto-cleared):       {tier_counts['LOW_RISK']} ({tier_counts['LOW_RISK'] / total_tx * 100:.1f}%)"
        )
        print(
            f"  * ELEVATED_RISK (Monitoring):    {tier_counts['ELEVATED_RISK']} ({tier_counts['ELEVATED_RISK'] / total_tx * 100:.1f}%)"
        )
        print(
            f"  * HIGH_RISK (Secondary Review):  {tier_counts['HIGH_RISK']} ({tier_counts['HIGH_RISK'] / total_tx * 100:.1f}%)"
        )
        print(
            f"  * CRITICAL_SAR (Immediate SAR):  {tier_counts['CRITICAL_SAR']} ({tier_counts['CRITICAL_SAR'] / total_tx * 100:.1f}%)"
        )
        print(
            "--------------------------------------------------------------------------------"
        )
        print("OBJECTIVE ASSERTION CHECKS:")
        print(
            f"  [Check 1] Benign Traffic Routed to LOW_RISK: {normal_low_risk_pct:.2f}% (Assertion: >= 90.0%) -> {'PASS' if normal_low_risk_pct >= 90.0 else 'FAIL'}"
        )
        print(
            f"  [Check 2] Anomalous Traffic Routed to HIGH/SAR: {anomalous_flagged_pct:.2f}% (Assertion: >= 95.0%) -> {'PASS' if anomalous_flagged_pct >= 95.0 else 'FAIL'}"
        )
        print(
            f"  [Check 3] Mean Latency Under 10ms: {mean_latency:.2f} ms (Assertion: < 10.0ms) -> {'PASS' if mean_latency < 10.0 else 'FAIL'}"
        )

        assert normal_low_risk_pct >= 90.0, (
            f"Normal traffic low-risk routing failed: {normal_low_risk_pct}% < 90%"
        )
        assert anomalous_flagged_pct >= 95.0, (
            f"Anomalous traffic detection failed: {anomalous_flagged_pct}% < 95%"
        )
        assert mean_latency < 10.0, f"Latency SLA breached: {mean_latency}ms >= 10ms"

        # 5. Check Audit Alerts Persistence
        print("\n[Step 5] Checking Alerts Audit Queue (alerts.db)...")
        res_alerts = await client.get("/api/v1/alerts?limit=10")
        assert res_alerts.status_code == 200
        alerts_list = res_alerts.json()
        print(f"Audit DB Records Successfully Retrieved: {len(alerts_list)}")
        if alerts_list:
            sample_alert = alerts_list[0]
            print(
                f"Sample Alert: TX={sample_alert['transaction_id']}, Score={sample_alert['risk_score']}, Tier={sample_alert['risk_tier']}, Action={sample_alert['action']}, Driver='{sample_alert['primary_driver']}'"
            )
            assert sample_alert["risk_tier"] in ["HIGH_RISK", "CRITICAL_SAR"]

        print("\nALL VERIFICATION TESTS & LOAD BENCHMARKS PASSED SUCCESSFULLY.\n")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
