# Cryptographic Envelope Encryption & Secret Management Architecture

## 1. Executive Summary & Security Objectives
The QuantumAML Nexus platform processes classified law enforcement evidence, bank subpoena returns, and FinCEN Suspicious Activity Reports (SAR). This architecture specifies a cryptographic envelope encryption hierarchy combining hardware security modules (AWS KMS / HashiCorp Vault Transit Engine) with ephemeral, localized Data Encryption Keys (DEKs).

---

## 2. Cryptographic Key Hierarchy

```
+------------------------------------------------------------------------+
|             Level 1: Key Encryption Key (KEK) - Master Key             |
|  - Stored in FIPS 140-2 Level 3 HSM (AWS KMS / Vault Transit Engine)   |
|  - 256-bit AES-GCM / Ed25519; never leaves secure hardware boundary    |
+------------------------------------+-----------------------------------+
                                     |
               KMS:GenerateDataKey() | Encrypted DEK returned
                                     v
+------------------------------------------------------------------------+
|             Level 2: Data Encryption Key (DEK) - Ephemeral Key         |
|  - Generated uniquely per Evidence Dossier, Subpoena PDF, or Block     |
|  - Plaintext DEK resides in volatile memory (tmpfs) only during write  |
|  - Sanitized from RAM via explicit byte zeroization after operation    |
+------------------------------------+-----------------------------------+
                                     |
                 Local AES-256-GCM   | Ciphertext Payload + Tag
                                     v
+------------------------------------------------------------------------+
|             Level 3: Encrypted Evidence & Ledger Storage               |
|  Envelope Header:                                                      |
|    - KEK Key ARN / Version ID                                          |
|    - Encrypted DEK (E_KEK(DEK))                                        |
|    - 96-bit Initialization Vector (IV)                                 |
|    - 128-bit Authentication Tag                                        |
|  Body:                                                                 |
|    - AES-256-GCM Encrypted Document Payload                            |
+------------------------------------------------------------------------+
```

---

## 3. Mathematical Encryption & Decryption Workflows

### 3.1 Encryption Workflow (Per Evidence File / Block)
1. **DEK Generation**:
   The enclave service requests a dynamic DEK from the KMS:
   $$\text{Plaintext DEK}, \text{Encrypted DEK} \leftarrow \text{KMS.GenerateDataKey}(\text{KeyId}=\text{KEK\_ID}, \text{KeySpec}=\text{"AES\_256"})$$
2. **Local Payload Encryption**:
   A cryptographically secure 96-bit random IV is generated:
   $$\text{IV} \leftarrow \text{CSPRNG}(12 \text{ bytes})$$
   $$\text{Ciphertext}, \text{Tag} \leftarrow \text{AES-256-GCM-Encrypt}(\text{Key}=\text{Plaintext DEK}, \text{IV}=\text{IV}, \text{Plaintext}=\text{DocumentPayload}, \text{AAD}=\text{RecordMetadata})$$
3. **RAM Zeroization**:
   The `Plaintext DEK` buffer is immediately overwritten with `0x00` bytes across memory before heap garbage collection.
4. **Persisted Envelope Structure**:
   $$\text{Envelope} = \text{KEK\_ID} \parallel \text{Length}(\text{Encrypted DEK}) \parallel \text{Encrypted DEK} \parallel \text{IV} \parallel \text{Tag} \parallel \text{Ciphertext}$$

### 3.2 Decryption Workflow
1. The enclave extracts `KEK_ID`, `Encrypted DEK`, `IV`, `Tag`, and `Ciphertext`.
2. The enclave calls `KMS.Decrypt(CiphertextBlob=Encrypted DEK)`.
3. KMS verifies authorization via IAM role and returns `Plaintext DEK`.
4. Enclave decrypts and verifies authenticity tag in memory:
   $$\text{DocumentPayload} \leftarrow \text{AES-256-GCM-Decrypt}(\text{Key}=\text{Plaintext DEK}, \text{IV}=\text{IV}, \text{Ciphertext}=\text{Ciphertext}, \text{Tag}=\text{Tag}, \text{AAD}=\text{RecordMetadata})$$
5. `Plaintext DEK` buffer is zeroed immediately.

---

## 4. Secret Management & Memory-Backed (tmpfs) Injection

1. **Zero Plaintext Disk Persistence**:
   - Microservices execute with `readOnlyRootFilesystem: true`.
   - Kubernetes secrets and external tokens are projected strictly into `tmpfs` mounts (`medium: Memory`).
   - If a pod crashes or node storage is compromised, no cryptographic keys or plaintext tokens exist on non-volatile physical disk.
2. **External Secrets Operator (ESO)**:
   - Polls Vault / AWS KMS every 1 hour to detect key rotation.
   - Synchronizes rotated secret objects directly into in-memory secret buffers.
   - Service accounts use Kubernetes Projected Service Account Tokens (bound tokens with 10-minute expiry).

---

## 5. Key Rotation & Re-wrapping Policy
- **Master KEK Rotation**: Automatic annual rotation in AWS KMS. When a KEK rotates, the backing key material updates, but existing `Encrypted DEK` blobs remain decryptable by KMS through key version indexing.
- **Envelope Re-Wrapping**: An automated background batch job re-encrypts old `Encrypted DEK` blobs with the new KEK version (`KMS.ReEncrypt()`) without ever decrypting or transmitting the underlying gigabytes of evidence files.
