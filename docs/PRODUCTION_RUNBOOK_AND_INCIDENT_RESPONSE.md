# Production Operations Runbook & Security Incident Response Procedures

## 1. Incident Classification & Severity Matrix

| Severity | Incident Type | Trigger / Detection Mechanism | Response SLA | Target State |
| :--- | :--- | :--- | :--- | :--- |
| **SEV-1** | **Boundary Breach / Cross-Domain Attack** | Gateway Firewall catches `403_CROSS_DOMAIN_BREACH_ATTEMPT` or vector namespace override | **< 5 minutes** | Pod quarantined, token revoked, CISO notified |
| **SEV-1** | **Ledger State Tampering / Merkle Divergence** | Merkle auditor fails proof verification or hash-chain PoD flagged | **< 5 minutes** | Write pipeline halted, node isolated, WAL replayed |
| **SEV-2** | **KMS Key Compromise / HSM Failover** | Key expiration alert, unauthorized KMS decrypt anomaly | **< 30 minutes** | KEK rotated, DEKs re-wrapped, mTLS certs renewed |
| **SEV-3** | **Canary Deployment Rollback** | Prometheus alert: 5xx rate > 0.5% or p95 latency > 35ms | **< 15 minutes** | Canary aborted, stable traffic restored |

---

## 2. Procedure A: Cross-Domain Boundary Breach Handling (SEV-1)

### 2.1 Detection & Triage
1. **Trigger Alert**:
   - Prometheus metric `quantumaml_perimeter_breaches_total > 0`
   - Gateway audit log entry with code `403_CROSS_DOMAIN_BREACH_ATTEMPT`
2. **Identification of Attacker Context**:
   Inspect the gateway security log in the `mesh-gateway` namespace:
   ```bash
   kubectl logs -n mesh-gateway -l app=quantumaml-gateway --tail=100 | grep "CROSS_DOMAIN_BREACH"
   ```
   Extract:
   - Subject Token ID (`jti`)
   - Originator IP / Client Certificate Fingerprint
   - User Role (e.g. `INVESTIGATION_OFFICER`)
   - Attempted Target Namespace (e.g. `bank_aml_compliance_v1`)
   - Payload Injection Vectors (Base64, ROT13, NFKC variations)

### 2.2 Immediate Containment Protocol
1. **Revoke Offending Session**:
   Add the compromised `jti` to the distributed token blacklist:
   ```bash
   kubectl exec -n mesh-gateway deploy/quantumaml-gateway -- python3 -c "
   from app.services.auth_verifier import JWTAuthVerifier
   JWTAuthVerifier.revoke_token('<COMPROMISED_JTI>')
   "
   ```
2. **Isolate Compromised Pod via NetworkPolicy**:
   Label the originating pod with `quarantine: "true"`:
   ```bash
   kubectl label pod <POD_NAME> -n mesh-investigation quarantine=true
   ```
   *The NetworkPolicy immediately drops all egress and ingress for quarantined pods.*
3. **Trigger Boundary Rejection Card**:
   Verify that the connected dashboard UI displays the Phase 2 Boundary Rejection Card with cryptographic breach event hash and red security banner.

### 2.3 Evidence Preservation
- Export the immutable security breach log entry:
  ```bash
  python3 scripts/tamper_divergence_simulator.py --audit-dump
  ```
- Generate legal incident dossier for FinCEN/Internal Affairs submission.

---

## 3. Procedure B: Merkle Tree Divergence & Ledger Tampering Triage (SEV-1)

### 3.1 Detection
- Live supervisory console receives `PERIMETER_STATE_CORRUPTION_DETECTED` WebSocket alert.
- Independent auditor CLI fails root hash verification:
  ```bash
  node scripts/audit-verifier.mjs --block <BLOCK_FILE> --proof <PROOF_FILE>
  # Returns: [AUDIT STATUS: REJECTED]
  ```

### 3.2 Point-of-Divergence (PoD) Root-Cause Isolation
1. **Execute Forensic Divergence Engine**:
   Run the divergence isolation diagnostic tool against the affected cluster replica:
   ```bash
   python3 scripts/tamper_divergence_simulator.py
   ```
2. **Analyze Output Incident Ticket**:
   Identify:
   - `divergence_block_index`: Exact block height where mutation occurred ($i$).
   - `expected_parent_hash` vs. `actual_mutated_hash`.
   - `mutated_fields`: Specific JSON keys modified (e.g., `amount`, `status`, `authorized`).
   - `time_delta_ms`: Forensic timestamp discrepancy.

### 3.3 State Recovery & WAL Replay
1. **Halt Incoming Ledger Ingestion**:
   Drain traffic from affected ledger pod.
2. **Execute Automated Cold-Start WAL Replay**:
   ```bash
   python3 scripts/wal_failover_recovery.py
   ```
3. **Verify State Reconstruction**:
   - Assert zero state divergence against verified root.
   - Verify balance conservation across all accounts.
   - Confirm cold-start recovery time $\le 3.5\text{ seconds}$.
4. **Re-attach Node to Mesh**:
   Remove quarantine label and verify replica synchronization.

---

## 4. Procedure C: Cryptographic Key Rotation & Disaster Recovery (SEV-2)

### 4.1 Scheduled / Emergency KEK Rotation
1. **AWS KMS / Vault Master Key Rotation**:
   Trigger new Key Encryption Key (KEK) version creation in AWS KMS / Vault HSM:
   ```bash
   vault write -f transit/keys/quantumaml-master-kek/rotate
   ```
2. **Batch Re-Wrapping of Stored Evidence DEKs**:
   Invoke the background re-wrapping worker:
   ```bash
   python3 scripts/runtime_audit.py --re-wrap-keys
   ```
   *Note: Re-encrypts only the 32-byte DEK envelopes using `KMS.ReEncrypt()`; zero re-encryption of bulk document bytes required.*

### 4.2 Emergency Service Mesh Certificate Rotation
If mTLS certificate compromise is suspected:
```bash
# Force Istio CA to rotate short-lived certificates across all mesh namespaces
istioctl pc secret deploy/investigation-service -n mesh-investigation
kubectl rollout restart deployment -n mesh-gateway
kubectl rollout restart deployment -n mesh-investigation
kubectl rollout restart deployment -n mesh-bank
kubectl rollout restart deployment -n mesh-telemetry
```

---

## 5. Kubernetes Probe Calibration & Health SLA Guide

| Container | Probe Type | Endpoint / Method | Initial Delay | Period | Timeout | Failure Threshold | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Enclave** | Startup | `HTTP GET /health` | 2s | 2s | 2s | 15 (30s max) | Allows CatBoost/ML model loading into memory |
| **Backend Enclave** | Liveness | `HTTP GET /health` | 0s | 10s | 3s | 3 | Restarts container if deadlocked |
| **Backend Enclave** | Readiness | `HTTP GET /health` | 0s | 5s | 2s | 2 | Removes pod from service traffic if busy |
| **Gateway** | Startup | `HTTP GET /health` | 1s | 2s | 1s | 10 (20s max) | Fast startup check |
| **Gateway** | Liveness | `HTTP GET /health` | 0s | 5s | 2s | 3 | Immediate gateway health evaluation |
| **Gateway** | Readiness | `HTTP GET /health` | 0s | 3s | 1s | 2 | Zero dropped inbound connections |
