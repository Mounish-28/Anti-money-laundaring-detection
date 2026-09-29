# Anti-money-laundaring-detection

# QuantumAML Nexus — Real-Time Quantitative Anti-Money Laundering Detection Platform

An enterprise-grade, high-throughput financial crime detection and anti-money laundering (AML) inference infrastructure. The system executes continuous multi-tier risk scoring across heterogeneous financial transaction streams (including banking transactions, time-series AML patterns, and Elliptic Bitcoin graph topologies) with low-latency real-time response guarantees.

## Key Features

- **Multi-Dataset Detection Engines**: Support for IBM Transactions, Time-Series AML, Elliptic Bitcoin graph topologies, SAML-D, and agent-based simulations.
- **Real-Time Streaming & Inference**: High-throughput transaction streaming with sub-50ms P95 latency risk scoring.
- **Graph & ML Analytics**: Graph topological analysis combined with ensemble gradient boosting and neural risk classifiers.
- **REST APIs & Monitoring**: FastAPI microservices, Prometheus metrics, real-time alert triage, and operations runbook.
- **Modern Interactive Dashboard**: Full-featured frontend UI for analyst triage and system health inspection.

## Quick Start

### 1. Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Pre-flight Health Checks
```powershell
powershell -ExecutionPolicy Bypass -File .\run_preflight_checks.ps1
```

### 3. Run Pipeline Locally
```powershell
powershell -ExecutionPolicy Bypass -File .\run_pipeline_local.ps1
```

For complete deployment specifications, containerization, and production operating procedures, refer to [RUNBOOK.md](RUNBOOK.md).
