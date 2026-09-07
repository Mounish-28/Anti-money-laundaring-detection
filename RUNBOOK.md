# QuantumAML Nexus — Production Operations Runbook

```
========================================================================================
 DOCUMENT CONTROL & OPERATIONAL METADATA
========================================================================================
 Document Title      : QuantumAML Nexus — Production Operations Runbook
 System Name         : QuantumAML Nexus Real-Time Quantitative AML Detection Engine
 Document Revision   : 2.0.0
 Classification      : Enterprise Operations & Site Reliability Engineering (SRE)
 Target Environment  : Production / Multi-Container Containerized & Host-Native Cluster
 Workspace Root      : E:\Anti money datasets
 Maintainer Group    : Platform Engineering, SecOps & SRE Core Team
 Last Verified Date  : 2026-09-05
 Production SLA Gate : P95 Latency < 50ms | Availability > 99.95% | 0% Unhandled Excs
========================================================================================
```

---

## 1. Executive Summary & SLA Baselines

The **QuantumAML Nexus Platform** is an enterprise-grade, distributed, high-throughput financial crime detection and anti-money laundering (AML) inference infrastructure. The system executes continuous risk scoring across five heterogeneous financial datasets (IBM Transactions, Time-Series AML, Elliptic Bitcoin graph topologies, SAML-D, and IBM AMLSim agent-based simulations) while maintaining strict real-time response guarantees.

### 1.1 Service Level Agreements (SLAs) & Objectives (SLOs)

| Metric Indicator | Operational Target (SLO) | Hard SLA Breach Limit | Measurement Window |
| :--- | :--- | :--- | :--- |
| **Inference Latency (P50)** | `< 10.0 ms` | `> 25.0 ms` | 1-minute rolling window |
| **Inference Latency (P95)** | `< 30.0 ms` | `> 50.0 ms` | 3-minute rolling window |
| **Inference Latency (P99)** | `< 45.0 ms` | `> 75.0 ms` | 5-minute rolling window |
| **Service Availability** | `99.99%` | `< 99.95%` | Monthly calendar period |
| **Ingestion Error Rate** | `0.00%` | `> 0.05%` | 5-minute sliding counter |
| **Background Triage Delay** | `< 2.0 sec` | `> 10.0 sec` | End-to-end Celery dispatch |

---

## 2. System Architecture & Inventory Matrix

### 2.1 End-to-End Traffic Flow Architecture

```
                                      [ Incoming Ingestion Request ]
                                                    │
                                                    ▼
                               ┌────────────────────────────────────────┐
                               │  Reverse Proxy / Ingress Load Balancer │
                               │            (Port 80 / 443)             │
                               └────────────────────┬───────────────────┘
                                                    │
                                                    ▼
                              ┌──────────────────────────────────────────┐
                              │  FastAPI Serving Engine (api:8000)       │
                              │  - 4 Uvicorn ASGI Workers                │
                              │  - Cold-Start Warmup on Lifespan         │
                              │  - Pydantic v2 Contract Validation       │
                              │  - GET /health & GET /metrics            │
                              └──────────────┬───────────────────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
       ┌───────────────────────────────┐             ┌─────────────────────────────┐
       │  Unified Inference Engine     │             │ Prometheus Scraper (:9090)  │
       │  - IBM CatBoost Model         │             │ - Scrapes /metrics (5s)     │
       │  - Elliptic GAT + XGBoost     │             │ - Histogram Buckets         │
       │  - SAML-D Tabular XGBoost     │             └──────────────┬──────────────┘
       │  - AMLSim LightGBM + GCN Head │                            │
       │  - Time-Series Dual Blend     │                            ▼
       └──────────────┬────────────────┘             ┌─────────────────────────────┐
                      │                              │ Grafana Dashboards (:3000)  │
                      │ (If is_anomaly == True)      │ - P95 Latency Gauge (<50ms) │
                      ▼                              │ - Endpoint Throughput (RPS) │
       ┌───────────────────────────────┐             │ - Risk Tier Bar Breakdown   │
       │  Redis In-Memory Broker       │             │ - Global Anomaly Rate Stat  │
       │  (redis:6379 / DB 0)          │             └─────────────────────────────┘
       │  - Task Queue: celery         │
       │  - Visibility Timeout: 3600s  │
       └──────────────┬────────────────┘
                      │
                      ▼
       ┌───────────────────────────────┐
       │  Celery Worker (celery_worker)│
       │  - tasks.dispatch_            │
       │    investigator_alert         │
       │  - High-Risk SAR Triage Audit │
       │  - Non-Blocking Background IO │
       └───────────────────────────────┘
```

### 2.2 Component Inventory Matrix

| Container / Service | Internal Port | Host Port | Base Image | Architectural Role | Health Check Probe Command / URL |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`quantumaml-api`** | `8000/TCP` | `8000` | `python:3.11-slim` | Multi-model quantitative inference serving engine | `curl -f http://localhost:8000/health` |
| **`quantumaml-redis`**| `6379/TCP` | `6379` | `redis:7-alpine` | High-throughput broker & ephemeral result backend | `redis-cli ping` |
| **`quantumaml-worker`**| N/A | N/A | `python:3.11-slim` | Distributed background triage alert worker daemon | `celery -A app.worker.celery_app inspect ping` |
| **`prometheus`** | `9090/TCP` | `9090` | `prom/prometheus:latest`| Time-series telemetry scraper & metric aggregator | `wget -q --tries=1 -O- http://localhost:9090/-/healthy` |
| **`grafana`** | `3000/TCP` | `3000` | `grafana/grafana:latest`| Visual telemetry, SLO dashboards, and alerts | `curl -f http://localhost:3000/api/health` |

---

## 3. Environment Variables & Secret Configuration

Production environments must define the configuration profile via an encrypted `.env` file situated strictly in the project root (`E:\Anti money datasets\.env`).

### 3.1 Environment Variable Reference

| Variable Name | Required | Default Value | Valid Options / Pattern | Operational Description |
| :--- | :---: | :--- | :--- | :--- |
| `ENVIRONMENT` | Yes | `production` | `development`, `staging`, `production` | Operational environment flag controlling log verbosity. |
| `PORT` | Yes | `8000` | Integer (`1024-65535`) | Internal TCP port exposed by FastAPI Uvicorn engine. |
| `REDIS_URL` | Yes | `redis://redis:6379/0` | `redis://[user:pass@]host:port/db` | Connection string for Celery broker and result storage. |
| `MODEL_DIR` | Yes | `/app/models` | Absolute or relative directory path | Storage mount containing the 5 model subsystem directories. |
| `UVICORN_WORKERS` | No | `4` | Integer (`1-32`) | Number of concurrent ASGI worker processes (CPU cores * 2). |
| `CELERY_CONCURRENCY`| No | `2` | Integer (`1-16`) | Number of concurrent Celery task processing processes. |
| `OMP_NUM_THREADS` | No | `2` | Integer (`1-8`) | CPU thread quota for OpenMP execution (XGBoost, CatBoost). |
| `GF_SECURITY_ADMIN_PASSWORD` | Yes | `admin` | Cryptographic string (`>= 16 chars`) | Root administrative password for Grafana instance. |
| `GF_USERS_ALLOW_SIGN_UP` | Yes | `false` | `true`, `false` | Disables public user account registration in Grafana. |

### 3.2 Security Protocols & File Permissions

```powershell
# 1. Enforce restrictive Access Control Lists (ACL) on the production .env file (Windows Host)
icacls .env /inheritance:d
icacls .env /grant:r "Administrators:F" "SYSTEM:F"

# 2. Verify that no raw credentials exist in version control
git status --ignored
# Confirm .env and models/ are explicitly listed in .gitignore
```

> [!CAUTION]
> Never hardcode `GF_SECURITY_ADMIN_PASSWORD` or production Redis credentials into `docker-compose.yml` or container images. Always inject secrets at runtime using environment files or external secret stores.

---

## 4. Operational Lifecycle & CLI Commands

### 4.1 Multi-Container Stack Boot (Docker Compose)

Execute the standard multi-container microservice lifecycle from a privileged PowerShell terminal within `E:\Anti money datasets`:

```powershell
# 1. Validate Docker Compose YAML syntax and volume mappings
docker compose config

# 2. Build images without cache and start services in detached mode
docker compose up -d --build

# 3. Inspect container lifecycle and health states
docker compose ps

# 4. Stream real-time logs across all services
docker compose logs -f

# 5. Filter logs for the API inference engine specifically
docker compose logs -f api

# 6. Stream background Celery triage worker alerts
docker compose logs -f celery_worker
```

### 4.2 Host-Native Local Execution (Windows Fallback)

In environments lacking the Docker daemon or during rapid local diagnostics, execute the stack directly on the Windows host:

```powershell
# 1. Activate Python 3.11 virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Execute the pre-commit and static analysis preflight gate
powershell -ExecutionPolicy Bypass -File .\run_preflight_checks.ps1

# 3. Verify Redis Broker Connectivity on Localhost:6379
Test-NetConnection -ComputerName 127.0.0.1 -Port 6379

# 4. Launch FastAPI Uvicorn Serving Layer (Production Configuration)
$env:MODEL_DIR = "models"
$env:REDIS_URL = "redis://localhost:6379/0"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 5. Launch Background Celery Worker (In a separate PowerShell session)
# Note: Windows requires --pool=solo to avoid multi-processing socket deadlocks
$env:MODEL_DIR = "models"
$env:REDIS_URL = "redis://localhost:6379/0"
celery -A app.worker.celery_app worker --loglevel=info --pool=solo --concurrency=2
```

### 4.3 Safe Teardown & Maintenance Operations

```powershell
# Standard graceful termination (preserves persistent volumes and Redis state)
docker compose down

# Emergency maintenance teardown (purges named volumes including redis_data and grafana_data)
docker compose down -v --remove-orphans
```

---

## 5. Zero-Downtime Model Artifact Hot-Swapping

The QuantumAML container architecture isolates machine learning model weights within the `./models` host volume mounted read-only (`:ro`) into the container at `/app/models`. This decouples code deployment from model lifecycle updates.

### 5.1 Step-by-Step Weight Hot-Swap Procedure

#### Phase 1: Local Candidate Model Verification
Validate model structure and metadata offline before promoting artifacts to production:
```powershell
python -c "
import joblib, catboost
# Example: Verify candidate SAML-D model
m = joblib.load('models/samld/candidate_model.joblib')
assert hasattr(m, 'predict_proba'), 'Invalid model artifact'
print('Model verification successful.')
"
```

#### Phase 2: Atomic File Swap on Host
Perform an atomic swap on the host filesystem to avoid mid-read corruption:
```powershell
# Navigate to target subsystem (e.g., SAML-D)
cd "E:\Anti money datasets\models\samld"

# Backup existing active weights
Copy-Item "xgboost_model.joblib" -Destination "xgboost_model.joblib.bak.$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Atomically overwrite active model with validated candidate
Move-Item -Force "candidate_model.joblib" "xgboost_model.joblib"
```

#### Phase 3: Rolling Container Process Reload
Execute a rolling restart of the API container. The host model mount immediately exposes the updated weights:
```powershell
# Trigger restart of the serving container
docker compose restart api
```

#### Phase 4: Verification of Engine Warmup & Health
Verify that the newly loaded model passes the cold-start warmup sequence:
```powershell
# 1. Probe the /health diagnostic endpoint
curl -s http://localhost:8000/health | jq .

# Expected output:
# {
#   "status": "HEALTHY",
#   "loaded_models": [
#     "ibm_transactions",
#     "samld",
#     "elliptic",
#     "amlsim_gcn",
#     "amlsim_lgbm",
#     "timeseries_xgb",
#     "timeseries_cb"
#   ]
# }

# 2. Confirm zero warmup errors in container logs
docker compose logs --tail=50 api | Select-String "Engine warmup completed successfully"
```

---

## 6. Observability, Telemetry & Metrics Harvesting

The serving layer mounts `prometheus-fastapi-instrumentator` and registers custom Prometheus collectors exposing metrics at `GET /metrics`.

### 6.1 Custom Prometheus Metric Inventory

| Metric Identifier | Metric Type | Labels | Buckets / Ranges | Operational Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`aml_inference_latency_seconds`** | `Histogram` | `dataset_model` | `0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5` | Measures execution time per model subsystem. Primary SLA tracking metric. |
| **`aml_transactions_evaluated_total`** | `Counter` | `dataset_model`, `risk_tier` | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | Aggregates request throughput broken down by risk classification. |
| **`aml_anomalies_detected_total`** | `Counter` | `dataset_model` | N/A | Tracks cumulative frequency of flagged high-risk anomalies (`is_anomaly=True`). |
| **`celery_queue_length`** | `Gauge` | `queue_name` | Integer | Monitors depth of pending alerts awaiting investigator dispatch. |

### 6.2 Prometheus Scrape Architecture

Prometheus is configured in [monitoring/prometheus.yml](file:///E:/Anti%20money%20datasets/monitoring/prometheus.yml) with a global **5-second scrape frequency**:

```yaml
global:
  scrape_interval: 5s
  evaluation_interval: 5s

scrape_configs:
  - job_name: "quantumaml-serving"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["api:8000"]
        labels:
          environment: "production"
          service: "quantumaml-nexus"
```

### 6.3 Core Grafana Dashboard Specification

The pre-provisioned Grafana dashboard (`monitoring/grafana_dashboard.json`, UID: `quantumaml-nexus-telemetry`) displays four primary operational panels:

1. **P95 Inference Latency Gauge (Panel 1)**:
   - *PromQL Query*: `histogram_quantile(0.95, sum(rate(aml_inference_latency_seconds_bucket[1m])) by (le, dataset_model)) * 1000`
   - *Unit*: Milliseconds (`ms`)
   - *Thresholds*: Green (`< 50ms`), Yellow (`50ms - 100ms`), Red (`> 100ms`).
2. **Request Throughput Timeseries (Panel 2)**:
   - *PromQL Query*: `sum(rate(aml_transactions_evaluated_total[1m])) by (dataset_model)`
   - *Unit*: Requests per second (`reqps`) with breakdown per model.
3. **Risk Tier Distribution Bar Chart (Panel 3)**:
   - *PromQL Query*: `sum(aml_transactions_evaluated_total) by (risk_tier)`
   - *Unit*: Short count displaying categorical volume across `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`.
4. **Anomaly Flagging Rate Stat Card (Panel 4)**:
   - *PromQL Query*: `clamp_max((sum(aml_anomalies_detected_total) / clamp_min(sum(aml_transactions_evaluated_total), 1)) * 100, 100)`
   - *Unit*: Percent (`%`) ratio of flagged anomalies to total evaluations.

---

## 7. Production Alerting & SLA Thresholds

```
=========================================================================================================
 SEVERITY MATRIX:
 P1 (Critical)   -> Immediate PagerDuty engagement; < 15 minute MTTR; executive escalation.
 P2 (High)       -> Slack alert to #secops-alerts; < 1 hour MTTR.
 P3 (Medium)     -> Daily triage log; next-business-day investigation.
=========================================================================================================
```

| Severity | Alert Identifier | Threshold Condition | Operational Impact | Target MTTR |
| :--- | :--- | :--- | :--- | :--- |
| **P1 - Critical** | `InferenceSLABreach` | `P95 Latency > 50ms for >= 3 minutes` | Degraded transaction throughput; downstream banking timeout risks. | `< 15 min` |
| **P1 - Critical** | `ServingEngineDown` | `probe_success{job="quantumaml-serving"} == 0 for > 30s` | Total outage of AML scoring layer; transactions unvetted. | `< 5 min` |
| **P2 - High** | `CeleryBacklogCritical` | `redis_queue_length{queue="celery"} > 500 for > 5 minutes` | Delays in SAR auto-flagging and investigator alerting. | `< 30 min` |
| **P2 - High** | `ModelMemoryExhaustion`| Container memory utilization `> 90%` | Threat of OOM-killer terminating ASGI workers. | `< 30 min` |
| **P3 - Medium** | `AnomalySpikeDetected`| `Anomaly Rate > 25% of throughput over 10 minutes` | Potential data drift, adversarial evasion attack, or batch glitch. | `< 4 hours`|

---

## 8. Capacity Management & Scaling Protocols

### 8.1 Horizontal Container Scaling

When traffic surges exceed single-instance capacity (sustained `> 1,200 RPS`), scale the API and worker pools via Docker Compose:

```powershell
# Scale FastAPI serving layer to 4 load-balanced container replicas
docker compose up -d --scale api=4 --no-recreate

# Scale Celery asynchronous triage workers to 4 consumers
docker compose up -d --scale celery_worker=4 --no-recreate

# Confirm all replicas are active and attached to aml-net
docker compose ps
```

### 8.2 Redis Broker Memory Hardening

Prevent Redis Out-Of-Memory (OOM) failures under burst triage alert volumes by enforcing eviction limits. Update or append to `docker-compose.yml`:

```yaml
redis:
  image: redis:7-alpine
  command: ["redis-server", "--maxmemory", "2gb", "--maxmemory-policy", "allkeys-lru", "--save", "900", "1"]
```

---

## 9. Incident Response Playbooks (Standard Operating Procedures)

### 9.1 Playbook 1: Inference Latency SLA Breach (`P95 > 50ms`)

```
Trigger: PagerDuty alert 'InferenceSLABreach' or Grafana P95 gauge entering red (> 50ms).
```

1. **Isolate the Offending Model**:
   Query Prometheus to pinpoint which specific model is breaching latency:
   ```promql
   histogram_quantile(0.95, sum(rate(aml_inference_latency_seconds_bucket[1m])) by (le, dataset_model)) * 1000
   ```
2. **Inspect Host CPU & Thread Saturation**:
   ```powershell
   Get-Process python | Select-Object Id, CPU, WorkingSet64
   docker stats --no-stream
   ```
   *Remediation*: If CPU is at 100%, verify OpenMP thread limits in container environments. Reduce `OMP_NUM_THREADS` to `2` to prevent CPU cache thrashing.
3. **Immediate Horizontal Scale-Out**:
   ```powershell
   docker compose up -d --scale api=4
   ```
4. **Log Analysis**:
   Inspect the most recent 100 lines for heavy payload evaluation or graph parsing issues:
   ```powershell
   docker compose logs --tail=100 api | Select-String "latency_ms"
   ```

### 9.2 Playbook 2: Redis Broker Failure or Task Backlog

```
Trigger: CeleryBacklogCritical alert or Redis connection errors in api logs.
```

1. **Verify Broker Network Connectivity**:
   ```powershell
   docker compose exec redis redis-cli ping
   # Expected response: PONG
   ```
2. **Inspect Backlog Depth**:
   ```powershell
   docker compose exec redis redis-cli llen celery
   ```
   *Threshold*: If length `> 500`, the worker pool is falling behind ingestion.
3. **Scale Background Workers**:
   ```powershell
   docker compose up -d --scale celery_worker=4
   ```
4. **Emergency Queue Drain (If Unrecoverable Deadlock Occurs)**:
   > [!CAUTION]
   > Draining the queue discards unhandled triage alerts. Export the backlog to disk before purging:
   ```powershell
   # Dump queue items to log file for post-mortem analysis
   docker compose exec redis redis-cli lrange celery 0 -1 > emergency_queue_dump.json
   # Flush the Celery queue
   docker compose exec redis redis-cli del celery
   ```

### 9.3 Playbook 3: Model Corruption or Cold-Start Initialization Failure

```
Trigger: Container crash loop on boot, or GET /health returning non-200.
```

1. **Inspect Lifespan Logs for Startup Failures**:
   ```powershell
   docker compose logs --tail=50 api
   ```
   Look for `RuntimeError`, `FileNotFoundError`, or `CatBoostError`.
2. **Verify File Integrity of Model Weights on Host**:
   ```powershell
   Get-ChildItem -Path ".\models" -Recurse -File | Select-Object FullName, Length, LastWriteTime
   ```
   Confirm all required model files exist:
   - `models/ibm_transactions/catboost_model.cbm`
   - `models/samld/xgboost_model.joblib`
   - `models/elliptic/xgboost_model.joblib`
   - `models/ibm_amlsim/gcn_backbone.pt` & `lgbm_head.joblib`
   - `models/timeseries/xgb_ts.joblib` & `cb_ts.cbm`
3. **Execute Emergency Rollback from Known-Good Backup**:
   ```powershell
   Copy-Item ".\models\backup\*" -Destination ".\models\" -Recurse -Force
   docker compose restart api
   ```
4. **Re-Validate System Health**:
   ```powershell
   curl -f http://localhost:8000/health
   ```

---

## 10. Routine Maintenance & Security Audits

### 10.1 Automated Docker Pruning & Log Maintenance

Run scheduled maintenance weekly to prevent storage exhaustion:

```powershell
# 1. Clean dangling container build cache and stopped containers
docker system prune -f --volumes

# 2. Truncate container JSON log files exceeding 100MB
Get-ChildItem "C:\ProgramData\Docker\containers\*\" -Filter "*-json.log" | Where-Object { $_.Length -gt 100MB } | ForEach-Object { Clear-Content $_.FullName }
```

### 10.2 Vulnerability Scanning via Trivy

Integrate regular security vulnerability auditing into deployment pipelines:

```powershell
# Scan production serving container image for HIGH and CRITICAL CVEs
trivy image --severity HIGH,CRITICAL quantumaml-api:latest

# Output results to security audit report
trivy image --format json --output trivy_security_report.json quantumaml-api:latest
```

### 10.3 Cryptographic Model Baseline Integrity Verification

Establish SHA-256 baseline hashes across all serialized model weights to detect tampering or silent bitrot:

```powershell
# Generate SHA-256 baseline checksum manifest
Get-ChildItem -Path ".\models" -Recurse -File | Get-FileHash -Algorithm SHA256 | Export-Csv -Path ".\models_sha256_manifest.csv" -NoTypeInformation

# Audit current files against recorded baseline
Import-Csv ".\models_sha256_manifest.csv" | ForEach-Object {
    $current = Get-FileHash -Path $_.Path -Algorithm SHA256
    if ($current.Hash -ne $_.Hash) {
        Write-Error "INTEGRITY FAULT: $($_.Path) has been modified! Expected: $($_.Hash) | Actual: $($current.Hash)"
    } else {
        Write-Host "VERIFIED: $($_.Path)" -ForegroundColor Green
    }
}
```

---

```
========================================================================================
 END OF OPERATIONS RUNBOOK — QUANTUMAML NEXUS PLATFORM v2.0.0
========================================================================================
```
