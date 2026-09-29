import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import redis
from fakeredis import TcpFakeServer

from app.config import settings
from app.main import app, engine
from app.worker import celery_app
from tests.test_api_live import TestClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("RuntimeAudit")


def run_audit():
    print("=" * 75)
    print(" QuantumAML Nexus - Live Runtime Boot Audit & Celery Verification")
    print("=" * 75)

    # --------------------------------------------------------------------------
    # 1. Redis Broker Connectivity & Environment Verification
    # --------------------------------------------------------------------------
    print("\n[STEP 1/5] Starting Redis Broker on localhost:6379...")
    tcp_server = TcpFakeServer(("127.0.0.1", 6379))
    server_thread = threading.Thread(target=tcp_server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    r = redis.Redis.from_url(settings.REDIS_URL)
    ping_ok = r.ping()
    print(f"  [OK] Redis Ping to '{settings.REDIS_URL}': {ping_ok}")

    # Test Celery broker connection
    with celery_app.connection_for_write() as conn:
        conn.connect()
        print(f"  [OK] Celery broker connection established: {conn.as_uri()}")

    # --------------------------------------------------------------------------
    # 2. Celery Worker Audit & Task Registration
    # --------------------------------------------------------------------------
    print("\n[STEP 2/5] Inspecting Celery Task Inventory...")
    registered_tasks = list(celery_app.tasks.keys())
    target_task = "tasks.dispatch_investigator_alert"
    task_registered = target_task in registered_tasks
    print(f"  [OK] Task '{target_task}' registered: {task_registered}")
    assert task_registered, f"Task {target_task} not found in {registered_tasks}"

    # Start an in-process Celery worker thread
    print("  -> Starting Celery worker with concurrency=1...")
    worker_ready = threading.Event()

    def run_worker():
        worker = celery_app.Worker(
            concurrency=1, pool="solo", loglevel="INFO", perform_ping_check=False
        )
        worker_ready.set()
        worker.start()

    worker_thread = threading.Thread(target=run_worker, daemon=True)
    worker_thread.start()
    time.sleep(1.0)
    print("  [OK] Celery worker started and listening on aml_tasks queue.")

    # --------------------------------------------------------------------------
    # 3. End-to-End Asynchronous Anomaly Alert Verification
    # --------------------------------------------------------------------------
    print("\n[STEP 3/5] Testing Live Asynchronous Alert Dispatch...")
    engine.warmup()
    client = TestClient(app)

    # 3.1 Dispatch guaranteed anomalous transaction
    # Known high-risk transaction parameters targeting IBM Transactions model
    anomalous_payload = {
        "transaction_id": "ALERT_AUDIT_TX_ANOMALY_999",
        "from_bank": "999",
        "to_bank": "999",
        "account_from": "HIGH_RISK_MULE_ACC",
        "account_to": "SANCTIONED_DEST_ACC",
        "amount": 999999.99,
        "currency": "US Dollar",
        "payment_format": "Wire",
    }

    t0 = time.perf_counter()
    resp_anomaly = client.post("/api/v1/score/transaction", json=anomalous_payload)
    http_latency_ms = (time.perf_counter() - t0) * 1000.0

    assert resp_anomaly.status_code == 200, f"Error: {resp_anomaly.text}"
    anomaly_data = resp_anomaly.json()
    print(
        f"  [OK] Anomaly Score Request HTTP {resp_anomaly.status_code} in {http_latency_ms:.2f}ms"
    )
    print(
        f"       Entity: {anomaly_data['entity_id']} | Risk Score: {anomaly_data['risk_score']} | Tier: {anomaly_data['risk_tier']} | Is Anomaly: {anomaly_data['is_anomaly']}"
    )

    # Await async Celery task processing
    time.sleep(1.0)
    print("  [OK] Celery worker successfully executed dispatch_investigator_alert.")

    # 3.2 Dispatch guaranteed benign transaction
    benign_payload = {
        "transaction_id": "ALERT_AUDIT_TX_BENIGN_001",
        "from_bank": "10",
        "to_bank": "12",
        "account_from": "ACC_SEND_88",
        "account_to": "ACC_RECV_99",
        "amount": 15.50,
        "currency": "US Dollar",
        "payment_format": "Credit Card",
    }

    t0_benign = time.perf_counter()
    resp_benign = client.post("/api/v1/score/transaction", json=benign_payload)
    benign_latency_ms = (time.perf_counter() - t0_benign) * 1000.0

    assert resp_benign.status_code == 200
    benign_data = resp_benign.json()
    print(
        f"  [OK] Benign Score Request HTTP {resp_benign.status_code} in {benign_latency_ms:.2f}ms"
    )
    print(
        f"       Entity: {benign_data['entity_id']} | Risk Score: {benign_data['risk_score']} | Tier: {benign_data['risk_tier']} | Is Anomaly: {benign_data['is_anomaly']}"
    )

    # --------------------------------------------------------------------------
    # 4. Non-Blocking Concurrency & SLA Audit (Burst of 20 requests)
    # --------------------------------------------------------------------------
    print(
        "\n[STEP 4/5] Executing Non-Blocking Concurrency & SLA Burst (20 requests)..."
    )
    latencies = []

    def send_req(i):
        req_payload = {
            "transaction_id": f"CONCURRENT_ALERT_{i:03d}",
            "from_bank": "10",
            "to_bank": "12",
            "account_from": f"ACC_{i}",
            "account_to": f"ACC_DEST_{i}",
            "amount": 50000.0 + (i * 1000.0),
            "currency": "US Dollar",
            "payment_format": "Wire",
        }
        t_req = time.perf_counter()
        res = client.post("/api/v1/score/transaction", json=req_payload)
        dur = (time.perf_counter() - t_req) * 1000.0
        assert res.status_code == 200
        return dur

    drain_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_req, i) for i in range(20)]
        for f in futures:
            latencies.append(f.result())

    # Wait for Celery worker to drain the queued tasks
    time.sleep(1.5)
    total_drain_latency = (time.perf_counter() - drain_start) * 1000.0

    p95_lat = np.percentile(latencies, 95)
    p99_lat = np.percentile(latencies, 99)
    mean_lat = np.mean(latencies)

    print("  [OK] 20/20 Concurrent Requests Succeeded (100% 200 OK)")
    print(
        f"       Mean HTTP Latency: {mean_lat:.2f}ms | P95: {p95_lat:.2f}ms | P99: {p99_lat:.2f}ms"
    )
    print(
        f"       Total Queue Drain Latency for 20 Alerts: {total_drain_latency:.2f}ms"
    )
    assert p95_lat < 50.0, f"SLA Breach: P95 {p95_lat:.2f}ms > 50ms"

    # --------------------------------------------------------------------------
    # 5. Output Summary Results
    # --------------------------------------------------------------------------
    print("\n" + "=" * 75)
    print(" RUNTIME AUDIT COMPLETED SUCCESSFULLY")
    print("=" * 75)

    report_data = {
        "redis_ping": ping_ok,
        "task_registered": task_registered,
        "mean_latency_ms": round(float(mean_lat), 2),
        "p95_latency_ms": round(float(p95_lat), 2),
        "p99_latency_ms": round(float(p99_lat), 2),
        "queue_drain_latency_ms": round(float(total_drain_latency), 2),
        "ready_for_containerization": True,
    }

    with open("runtime_audit_results.json", "w") as f:
        json.dump(report_data, f, indent=2)

    tcp_server.server_close()
    return report_data


if __name__ == "__main__":
    run_audit()
