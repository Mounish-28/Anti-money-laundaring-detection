# QuantumAML Nexus — Master Architecture Blueprint
## Phase 2: UI/UX Design, System Prototyping & Interface Architecture
**Classification:** RESTRICTED // FINANCIAL INTELLIGENCE & ENTERPRISE COMPLIANCE  
**Target Resolution:** 1920x1080 (Primary Command Center), 1440px (Desktop), 2560px (Ultra-Wide 4K)  
**Security Clearances:** LEO Investigation Enclave (Level 4) vs. Bank Compliance Enclave (Level 3)  
**Standards:** WCAG 2.1 AA/AAA Certified, Sub-50ms Interaction Ceilings, Strict Boundary Defense  

---

# TABLE OF CONTENTS

1. [STEP 2.1: Design Token System, Shell Architecture & Accessibility Contracts](#step-21-design-token-system-shell-architecture--accessibility-contracts)
   - 2.1.1 Enterprise Dark Theme Token System (CSS Custom Properties)
   - 2.1.2 Global Shell Structural ASCII Wireframes (1920x1080 Base)
   - 2.1.3 Global Header & BM25 Search Console Anatomy
   - 2.1.4 Layout Grid & Responsive Breakpoint Matrix
   - 2.1.5 Motion Choreography & Micro-Interactions
   - 2.1.6 WCAG 2.1 AA Accessibility & Keyboard Traversal Matrix
   - 2.1.7 Machine-Readable Design Token Schema (JSON / Tailwind)
   - 2.1.8 RBAC Lockout & Context-Locked Boundary Interaction Specs
2. [STEP 2.2: Investigation Dashboard UI & Forensic Workflows](#step-22-investigation-dashboard-ui--forensic-workflows)
   - 2.2.1 Case Dossier & Chain of Custody Timeline
   - 2.2.2 BM25 Evidence Deep Explorer
   - 2.2.3 Interactive Forensic Graph & Entity Canvas
   - 2.2.4 Subpoena Generation & Cryptographic Warrant Workflow
3. [STEP 2.3: Bank Dashboard UI & AML Workspaces](#step-23-bank-dashboard-ui--aml-workspaces)
   - 2.3.1 High-Density Financial Transaction Ledger
   - 2.3.2 Collaborative Filtering Anomaly Detector Workspace
   - 2.3.3 Suspicious Activity Report (SAR) Generation & FinCEN Workflow
   - 2.3.4 Real-Time Immutable Audit Stream Interface
4. [STEP 2.4: AI Copilot Boundary Defense & Prototype Handoff](#step-24-ai-copilot-boundary-defense--prototype-handoff)
   - 2.4.1 Context-Aware Dual-Persona AI Copilot Interaction Model
   - 2.4.2 Cross-Domain Perimeter Firewall & Breach Handling
   - 2.4.3 Split-Screen Dual-Domain Supervisory Inspection View
   - 2.4.4 Component Architecture Tree, TypeScript Contracts & State Machines

---

# STEP 2.1: Design Token System, Shell Architecture & Accessibility Contracts

### 2.1.1 Enterprise Dark Theme Token System (CSS Custom Properties)

```css
:root,
[data-theme="dark"] {
  color-scheme: dark;

  /* 1. Surface Layers (Obsidian Core) */
  --bg-canvas:                     #070a0f; /* Base root background (0dp) */
  --bg-surface:                    #0d121c; /* Default panel, card, table body (2dp) */
  --bg-surface-hover:              #121927; /* Interactive card/row hover */
  --bg-elevated:                   #151d2d; /* Sticky headers, modals, popovers (8dp) */
  --bg-elevated-hover:             #1c263b; /* Hover for elevated elements */
  --bg-sunken:                     #040609; /* Recessed terminal wells, code, hex dumps (-2dp) */
  --bg-dropdown:                   #172033; /* Autocomplete select overlays (12dp) */
  --bg-modal:                      #0f1624; /* Primary lightbox modal (16dp) */
  --bg-modal-scrim:                rgba(4, 6, 9, 0.85); /* Backdrop blur scrim */

  /* 2. Multi-Tier Borders */
  --border-subtle:                 #182232; /* Grid lines, micro-dividers */
  --border-default:                #223047; /* Standard card contours, inputs */
  --border-active:                 #34486b; /* Focused card borders, active tabs */
  --border-divider:                rgba(255, 255, 255, 0.08); /* Clean metric dividers */

  /* 3. Investigation Domain Accents (Forensic Cyan) */
  --investigation-primary:         #06b6d4; /* Cyan-500 */
  --investigation-hover:           #0891b2; /* Cyan-600 */
  --investigation-active:          #0e7490; /* Cyan-700 */
  --investigation-surface:         rgba(6, 182, 212, 0.12);
  --investigation-border:          rgba(6, 182, 212, 0.38);
  --investigation-ring:            rgba(56, 189, 248, 0.65);
  --investigation-glow:            0 0 20px -2px rgba(6, 182, 212, 0.40);

  /* 4. Bank Domain Accents (Financial Emerald) */
  --bank-primary:                  #10b981; /* Emerald-500 */
  --bank-hover:                    #059669; /* Emerald-600 */
  --bank-active:                   #047857; /* Emerald-700 */
  --bank-surface:                  rgba(16, 185, 129, 0.12);
  --bank-border:                   rgba(16, 185, 129, 0.38);
  --bank-ring:                     rgba(52, 211, 153, 0.65);
  --bank-glow:                     0 0 20px -2px rgba(16, 185, 129, 0.40);

  /* 5. Semantic & Security Alerts */
  --status-nominal:                #10b981;
  --status-nominal-bg:             rgba(16, 185, 129, 0.12);
  --status-warning:                #f59e0b;
  --status-warning-bg:             rgba(245, 158, 11, 0.12);
  --status-critical:               #ef4444;
  --status-critical-bg:            rgba(239, 68, 68, 0.16);
  --boundary-violation-alert:      #f43f5e;
  --boundary-violation-bg:         rgba(244, 63, 94, 0.22);
  --boundary-violation-border:     #fda4af;
  --boundary-violation-glow:       0 0 28px rgba(244, 63, 94, 0.55), inset 0 0 12px rgba(244, 63, 94, 0.3);

  /* 6. Typography & Monospace Rules */
  --font-sans:                     'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono:                     'JetBrains Mono', 'Roboto Mono', monospace;
  --font-mono-features:            "tnum" on, "lnum" on, "zero" on;

  --text-display:                  2.25rem;   /* 36px / 44px lh / 700 */
  --text-h1:                       1.75rem;   /* 28px / 36px lh / 700 */
  --text-h2:                       1.375rem;  /* 22px / 30px lh / 600 */
  --text-h3:                       1.125rem;  /* 18px / 26px lh / 600 */
  --text-body:                     0.875rem;  /* 14px / 22px lh / 400 */
  --text-small:                    0.75rem;   /* 12px / 18px lh / 400 */
  --text-micro:                    0.6875rem; /* 11px / 16px lh / 600 uppercase */
  --text-mono-body:                0.8125rem; /* 13px / 20px lh / 400 */

  /* Text Contrast Hierarchy (WCAG 2.1 AA Certified) */
  --text-primary:                  #f8fafc; /* 18.7:1 vs #070a0f */
  --text-secondary:                #94a3b8; /* 7.4:1 vs #0d121c */
  --text-muted:                    #64748b; /* 4.6:1 vs #0d121c */
  --text-inverse:                  #020617;
}
```

---

### 2.1.2 Global Shell Structural ASCII Wireframes (1920x1080 Base)

```
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| GLOBAL APPLICATION HEADER (64px H)                                                                                                                                |
| [LOGO] NEXUS ENTERPRISE | [DOMAIN: INVESTIGATION v] | [SEARCH: BM25 Query... (Ctrl+K)]                | [WS: 38ms] [IMMUTABLE LOG: OK] [HASH: 0x9f1a] | [AGENT: S.Chen] |
+-----------------------+-----------------------------------------------------------------------------------------------------------+-------------------------------+
| LEFT SIDEBAR (260px)  | MAIN CENTRAL VIEWPORT GRID (1300px Flexible Track)                                                       | DOCKED AI COPILOT (360px-520px|
+-----------------------+-----------------------------------------------------------------------------------------------------------+-------------------------------+
| [*] INVESTIGATION     | BREADCRUMBS: Investigations > Active Cases > CASE-IND-20260906-94A880 (SAR In Review)                     | [AI FORENSIC COPILOT] [<>]    |
|  [*] Case Queue   (14)|-----------------------------------------------------------------------------------------------------------| Isolation Enclave: ACTIVE     |
|  [ ] Entity Graph     | [SURVEILLANCE & TRIAGE LEDGER]                           [FILTERS: P1 Critical | Structuring | Today]     | Context: Case 94A880 Linked   |
|  [ ] BM25 Search      | +-------------------------------------------------------------------------------------------------------+ |-------------------------------|
|  [ ] Subpoena Vault   | | TX HASH            | SENDER ACC        | BENEFICIARY ACC   | AMOUNT (INR) | TIME (UTC) | ML RISK | DNF| | CONTEXTUAL EVIDENCE PILLS:    |
|  [ ] SAR Dossier  (3) | |--------------------+-------------------+-------------------+--------------+------------+---------+----| | [Case 94A880] [Alpha LLC]    |
|                       | | 0x8a92f0...31c     | ACC-021000021-99  | OFFSHORE-ALPHA-LLC|  499,500.00  | 14:22:01.0 | 0.985   | P1 | | [Subpoena SUB-8812]         |
| ALGORITHMIC SUITES    | | 0x41b89d...10a     | ACC-021000021-99  | CAYMAN-APEX-CORP  |  495,000.00  | 14:22:03.4 | 0.978   | P1 | |-------------------------------|
|  [ ] QuickSort (DNF)  | | 0x77c1e3...449     | ACC-021000021-99  | PANAMA-SETTLE-7   |  492,000.00  | 14:22:06.1 | 0.962   | P1 | | CHAT INTERACTION STREAM:      |
|  [ ] Collab Filtering | | 0xd389b2...881     | ACC-994100234-11  | MULE-ACCOUNT-8812 |    9,900.00  | 14:22:12.8 | 0.914   | P2 | |                               |
|  [ ] RobinHood Hash   | +-------------------------------------------------------------------------------------------------------+ | Analyst:                      |
|  [ ] Crypto Mempool   | QuickSort Ledger: 40 Records Sorted in 0.098ms (DNF Multi-Pivot Partitioning)                             | "Analyze structuring velocity |
|                       |-----------------------------------------------------------------------------------------------------------| across Cayman wires."         |
| RESTRICTED DOMAIN     | [COLLABORATIVE FILTERING ANOMALY SURFACE]                                                                 |                               |
|  [x] Bank Ledger [PAD]|   Target: OFFSHORE-ALPHA-LLC     Anomaly Score: 0.406 [EXCEEDS ANOMALY THRESHOLD 0.40]                    | AI Forensic Specialist:       |
|                       |   Peer Group: Corporate Offshore Wires (k=2) | Deviations: 8 anomalous features detected                  | "Flagged 3 transactions routed|
| SECURITY INTEGRITY    |   [Burstiness: +3.4σ] [Rapid Fan-Out: +4.1σ] [Off-Hours Velocity: +2.8σ]                                  | in 5.1s totaling INR 1.486M.  |
|  [o] Merkle Root Sync |-----------------------------------------------------------------------------------------------------------| Matches Smurf IN_TYP_STRUCT." |
|  [o] WebSocket 38ms   | [MULTI-HOP ENTITY LINK GRAPH CANVAS]                                                                      |                               |
|-----------------------|       [ACC-SEND-99] =====(INR 499.5k)=====> [OFFSHORE-ALPHA] =====(INR 1.48M)=====> [CAYMAN-APEX]         | [SUGGESTED ACTIONS]           |
| [<< Collapse Rail]    |                                                                                                           | [Freeze Entity] [Draft SAR]   |
| TLS 1.3 // SESSION OK |       Centrality Metric: Degree = 14 | Betweenness = 0.84 | Status: Critical Smurf Ring Flagged           |-------------------------------|
| HASH: 0x9f1a...7c4e   |                                                                                                           | [PROMPT INPUT DOCK]           |
+-----------------------+-----------------------------------------------------------------------------------------------------------+-------------------------------+
```

#### Left Sidebar State Variants:
```
EXPANDED STATE (260px)                      COLLAPSED RAIL (72px)
+------------------------------------+      +--------+
| [NX] QUANTUMAML NEXUS              |      |  [NX]  |
+------------------------------------+      +--------+
| ROLE: [*] INVESTIGATION ENCLAVE [v]|      |  [INV] | (Cyan Dot)
| FORENSIC WORKSPACE                 |      |--------|
|  [*] Case Triage Queue        (14) |      |  [Q]   | Tooltip: "Case Queue (14)"
|  [ ] Multi-Hop Link Graph          |      |  [G]   | Tooltip: "Entity Graph"
|  [ ] BM25 Subpoena Search          |      |  [S]   | Tooltip: "BM25 Search"
|  [ ] SAR Filing Dossiers       (3) |      |  [D]   | Tooltip: "SAR Dossiers"
| ALGORITHMIC SUITES                 |      |--------|
|  [ ] QuickSort 3-Way DNF           |      |  [QS]  | Tooltip: "QuickSort"
|  [ ] Collab Filtering Anomalies    |      |  [CF]  | Tooltip: "Collab Filtering"
|  [ ] RobinHood Hash Index (O(1))   |      |  [RH]  | Tooltip: "Hash Index"
|  [ ] Crypto Mempool Live           |      |  [BC]  | Tooltip: "Mempool Feed"
| RESTRICTED DOMAIN                  |      |--------|
|  [x] Bank Core Ledger         [PAD]|      |  [LCK] | Tooltip: "Bank Restricted"
| SYSTEM INTEGRITY                   |      |--------|
|  [o] Merkle Root Sync         [OK] |      |  [OK]  | Tooltip: "Merkle Root Valid"
|  [<<] Collapse Rail                |      |  [>>]  | Expand Trigger
+------------------------------------+      +--------+
```

---

### 2.1.3 Global Header & BM25 Search Console Anatomy

```
+---------------------------------------------------------------------------------------------------------------------------------+
| [MAGNIFIER] | [chip: case: *] [chip: tx: *] [chip: hash: *] [chip: subpoena: *] | Query: "Cayman wire routing under 500k" [X] | [Ctrl+K]
+---------------------------------------------------------------------------------------------------------------------------------+
| RESULTS AUTOCOMPLETE DROPDOWN (Overlay Z-Index: 1000):                                                                          |
| Search Telemetry: BM25 Ranked in 0.06ms | Indexed Corpus: 1,420 legal documents and wire notes                                   |
|---------------------------------------------------------------------------------------------------------------------------------|
| [SWIFT MT103]  DOC-994821: Alpha LLC Wire Routing 021000021 to Apex Holdings Cayman                         Score: 14.82 BM25   |
|   Matches: "...wire transfer routing **021000021** to Apex Holdings **Cayman** for $499,500.00 kept **under 500k**..."        |
|   Tags: [Bank Record]  [TAG: JURISDICTION_CAYMAN]  [TAG: STRUCTURING_RISK: P1]  [ROUTING: 021000021]            [38ms via BM25] |
|---------------------------------------------------------------------------------------------------------------------------------|
| [SIGNAL CHAT]  DOC-102488: Intercepted Communications Transcript (Marcus Vance)                             Score: 11.24 BM25   |
|   Matches: "...Keep **Cayman wire** transactions strictly **under 500k** to avoid automated escalation..."                      |
|   Tags: [Forensic Note]  [TAG: INTENT_SMURFING]  [SUSPECT: M.VANCE]  [EVIDENTIARY_SEAL: NYSD-0982]              [38ms via BM25] |
|---------------------------------------------------------------------------------------------------------------------------------|
| [SUBPOENA RETURN] DOC-55102: Apex Holdings Banking Mandate & Beneficial Ownership                           Score:  8.91 BM25   |
|   Matches: "...offshore wire authority granted to Marcus Vance for accounts receiving **routing** credits..."                   |
|   Tags: [Ledger Export]  [TAG: CORPORATE_MANDATE]  [BENEFICIAL_OWNER: M.VANCE]                                  [38ms via BM25] |
+---------------------------------------------------------------------------------------------------------------------------------+
```

---

### 2.1.4 Layout Grid & Responsive Breakpoint Matrix

```css
/* Layout Geometry Rules */
.nexus-shell-container {
  display: grid;
  grid-template-rows: 64px 1fr;
  grid-template-columns: 260px 1fr 360px;
  grid-template-areas:
    "header  header   header"
    "sidebar viewport copilot";
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background-color: var(--bg-canvas);
}

/* Z-Index Hierarchy */
:root {
  --z-canvas:                      0;
  --z-sticky-header:               100;
  --z-sidebar:                     200;
  --z-drawer:                      300;
  --z-modal-backdrop:              999;
  --z-modal:                       1000;
  --z-toast:                       2000;
  --z-boundary-violation:          2500;
}

/* 1440px Desktop: Auto-collapse drawer & sidebar */
@media (max-width: 1599px) {
  .nexus-shell-container {
    grid-template-columns: 72px 1fr 0px;
    grid-template-areas: "header header" "sidebar viewport";
  }
  .nexus-shell-copilot {
    position: fixed;
    top: 64px;
    right: 0;
    bottom: 0;
    width: 380px;
    transform: translateX(100%);
    box-shadow: -12px 0 36px rgba(0, 0, 0, 0.75);
  }
  .nexus-shell-copilot[data-open="true"] { transform: translateX(0); }
}

/* 2560px Ultra-Wide 4K: Multi-column ledger & dual canvas */
@media (min-width: 2048px) {
  .nexus-viewport-inner {
    display: grid;
    grid-template-columns: 1.3fr 1fr 1fr;
    gap: 1.5rem;
  }
}
```

---

### 2.1.5 Motion Choreography & Micro-Interactions
* **Sidebar Animation:** `transition: width 200ms cubic-bezier(0.16, 1, 0.3, 1);` with `contain: layout style;` preventing reflow thrashing.
* **AI Copilot Drawer Expansion:** `320ms cubic-bezier(0.16, 1, 0.3, 1)` expanding from $360\text{px}$ to $520\text{px}$.
* **Boundary Violation Visual Shock FX:**
```css
@keyframes boundaryPulse {
  0%, 100% { box-shadow: 0 0 20px -2px rgba(244, 63, 94, 0.65), inset 0 0 10px rgba(244, 63, 94, 0.35); border-color: #fda4af; }
  50% { box-shadow: 0 0 35px 2px rgba(244, 63, 94, 0.90), inset 0 0 18px rgba(244, 63, 94, 0.55); border-color: #f43f5e; }
}

@keyframes boundaryShake {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-4px); }
  40%, 80% { transform: translateX(4px); }
}
```

---

### 2.1.6 WCAG 2.1 AA Accessibility & Keyboard Traversal Matrix
* **ARIA Landmarks:** Header (`role="banner"`), Nav Rail (`role="navigation"`), Search Console (`role="search"`), Viewport (`role="main"`), AI Drawer (`role="complementary"`).
* **Live Regions:** `aria-live="polite"` for streaming LLM tokens and Merkle sync logs; `aria-live="assertive"` for security perimeter violations.
* **Global Hotkeys:** `Cmd/Ctrl + K` (Focus BM25 search), `Cmd/Ctrl + \` (Toggle AI Copilot), `Cmd/Ctrl + B` (Toggle Sidebar), `Esc` (Dismiss overlays).
* **Focus States:** High-contrast focus rings (`box-shadow: 0 0 0 2px var(--bg-surface), 0 0 0 4px #38bdf8`) certified $>4.8:1$ contrast against dark surfaces.

---

### 2.1.7 Machine-Readable Design Token Schema
Fully exported in [tokens.json](file:///e:/Anti%20money%20laundaring%20detection/nexus-frontend/src/tokens.json) with exact Hex/HSL properties, 4px spatial scale (`0.25rem` to `4.0rem`), and z-index declarations.

---

### 2.1.8 RBAC Lockout & Context-Locked Boundary Interaction
1. **Pointer Suppression:** `cursor: not-allowed !important;`, opacity reduced to 0.45.
2. **Rejection Shake:** Padlock icon rotates $\pm 10^\circ$ on unauthorized click with warning amber glow (`#F59E0B`).
3. **Security Tooltip:** Renders explicit legal citation: *"Restricted: Requires ROLE_BANK_COMPLIANCE_OFFICER under 31 U.S.C. 5318"*.
4. **Audit Dispatch:** Emits `RBAC_UNAUTHORIZED_PROBE` event with timestamp and user ID directly to the immutable Merkle audit ledger.

---

# STEP 2.2: Investigation Dashboard UI & Forensic Workflows

### 2.2.1 Case Dossier & Chain of Custody Timeline

```
+---------------------------------------------------------------------------------------------------------------------------------+
| CASE DOSSIER HEADER: CASE-IND-20260906-94A880                                                            STATUS: PENDING REVIEW |
| Title: Operation Alpha Smurf Ring // Target: Offshore Alpha LLC // Lead Agent: S.Chen // Jurisdiction: Federal SDNY            |
| Evidentiary Hash: 0x8f4c2e...771a (Tamper-Evident SHA-256 Validated) | Total Structuring Exposure: INR 1,486,500.00            |
+---------------------------------------------------------------------------------------------------------------------------------+
| CHAIN OF CUSTODY IMMUTABLE EVENT TIMELINE:                                                                                      |
|                                                                                                                                 |
| [14:22:01.0] [INTAKE] Transaction UTR-20260906-94745531 ingested from live banking stream.                                    |
|              Officer: System Agent DAEMON // Hash: 0x9a81...b201 // Integrity: VERIFIED                                         |
|                                                                                                                                 |
| [14:22:15.4] [CHECKOUT] Dossier assigned to Lead Investigator S.Chen for forensic evidentiary packaging.                      |
|              Officer: Supervisor M.Patel // Signature: SIG-ED25519-88190                                                        |
|                                                                                                                                 |
| [14:23:40.8] [EVIDENCE ATTACHED] BM25 match DOC-994821 (SWIFT MT103 Cayman routing) linked to case file.                       |
|              Integrity Seal: SHA-256 (0x77c1...884f) Match Validated                                                           |
+---------------------------------------------------------------------------------------------------------------------------------+
```

---

### 2.2.2 BM25 Evidence Deep Explorer

```
+---------------------------------------------------------------------------------------------------------------------------------+
| BM25 EVIDENCE DEEP EXPLORER                                                                                                     |
| [Filters: Subpoenas (X) | SWIFT MT103 (X) | Encrypted Chats (X)]   BM25 Tuning: [k1: 1.25 ----o-]  [b: 0.75 ---o--]             |
+---------------------------------------------------------------------------------------------------------------------------------+
| DOCUMENT SNIPPET INSPECTOR                                                    | EVIDENCE DOSSIER LINKING                        |
|-------------------------------------------------------------------------------+-------------------------------------------------|
| Document ID: DOC-994821 (SWIFT MT103 Wire Mandate)                            | Active Case: CASE-94A880                        |
| Classification: BANK_RECORD // Jurisdiction: Cayman Islands                   | Relevance Score: 14.82 BM25                     |
|                                                                               | Term Frequency (TF): 4 | IDF Weight: 3.71       |
| Text Corpus Excerpt:                                                          |                                                 |
| "...wire transfer routing 021000021 to Apex Holdings Cayman for amount        | Evidentiary Status:                             |
| $499,500.00 kept under 500k to avoid escalation Marcus Vance..."              | [o] Sealed Court Document                       |
|                                                                               | [o] Chain-of-Custody Verified                   |
| Matched Keywords: [wire transfer] [021000021] [Cayman] [under 500k]           |                                                 |
|                                                                               | [PIN TO ACTIVE DOSSIER]  [EXPORT SUBPOENA PDF]  |
+---------------------------------------------------------------------------------------------------------------------------------+
```

---

### 2.2.3 Interactive Forensic Graph & Entity Canvas

```
+---------------------------------------------------------------------------------------------------------------------------------+
| MULTI-HOP ENTITY LINK GRAPH CANVAS (Force-Directed Graph // Degree & Centrality Engine)                                        |
| [Layout: ForceAtlas2]  [Clustering: Louvain Community]  [Depth: 3 Hops]  [Threshold: Risk > 0.85]                               |
+---------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                 |
|        (ACC-SEND-99)                                                                                                            |
|              |                                                                                                                  |
|              | [Wire: INR 499.5k] (Timestamp: 14:22:01)                                                                         |
|              v                                                                                                                  |
|      [[ OFFSHORE ALPHA LLC ]] =======[Shared IP / Device ID: DEV-88102]=======> (( MARCUS VANCE ))                             |
|              |                                                                                |                                 |
|              | [Wire: INR 1.48M Total Aggregation]                                            | [Signal Chat: Intent]           |
|              v                                                                                v                                 |
|        (CAYMAN VAULT)                                                                  (( APEX HOLDINGS ))                      |
|                                                                                                                                 |
+---------------------------------------------------------------------------------------------------------------------------------+
| ENTITY INSPECTION FLYOUT (OFFSHORE ALPHA LLC):                                                                                  |
| Account: ACC-021000021-99 | Inflow: INR 1,486,500.00 | Outflow: INR 1,485,000.00 | Structuring Burst Delta: 5.1s                |
| Centrality: In-Degree = 14, Betweenness = 0.84 | Risk Tier: CRITICAL (0.985) | [DRAFT COURT SUBPOENA]  [FREEZE ACCOUNT ASSETS]  |
+---------------------------------------------------------------------------------------------------------------------------------+
```

---

### 2.2.4 Subpoena Generation & Cryptographic Warrant Workflow

```
+---------------------------------------------------------------------------------------------------------------------------------+
| COURT SUBPOENA & ASSET FREEZE WARRANT DRAFTING ENGINE                                                                           |
+---------------------------------------------------------------------------------------------------------------------------------+
| Jurisdiction: [ United States District Court - Southern District of New York (SDNY)                              [v] ]         |
| Target Entity / Account: [ OFFSHORE ALPHA LLC (ACC-021000021-99)                                                  ]             |
| Discovery Timeframe: [ 2026-09-01T00:00:00Z ] TO [ 2026-09-25T23:59:59Z ]                                                      |
| Compliance Justification: [ Probable cause established via 3 structured wire transfers executed under $500k threshold           |
|                             within 5.1 seconds in violation of 31 U.S.C. 5324 (Structuring to evade reporting).                 ] |
+---------------------------------------------------------------------------------------------------------------------------------+
| CRYPTOGRAPHIC WARRANT SIGNING CEREMONY:                                                                                         |
| Private Signing Key: [ HSM-ENCLAVE-ED25519-KEYSTORE // CARD PIN: **** ]                                                        |
| Generated Warrant Digest: SHA256: 0x3d7b92f...a108c4e (Immutable Legal Mandate)                                                |
|                                                                                                                                 |
| [ SIGN AND DISPATCH TO INSTITUTIONAL CLEARING HUB ]                    [ CANCEL & DISCARD DRAFT ]                               |
+---------------------------------------------------------------------------------------------------------------------------------+
```

---

# STEP 2.3: Bank Dashboard UI & AML Workspaces

### 2.3.1 High-Density Financial Transaction Ledger

```
+---------------------------------------------------------------------------------------------------------------------------------+
| SURVEILLANCE TRANSACTION LEDGER                                            [Mode: Ultra-Compact (X) | Standard Audit ( )]        |
| In-Memory QuickSort Telemetry: 40 Records Sorted in 0.098ms (DNF Multi-Pivot Partitioning on 'Amount DESC, Risk DESC')          |
+---------------------------------------------------------------------------------------------------------------------------------+
| TX HASH         | SENDER ACCOUNT   | BENEFICIARY ACC  | AMOUNT (INR) | TIME (UTC)   | RAIL  | ML RISK | DNF PIVOT | ACTION      |
|-----------------+------------------+------------------+--------------+--------------+-------+---------+-----------+-------------|
| 0x8a92f0...31c  | ACC-021000021-99 | OFFSHORE-ALPHA   |   499,500.00 | 14:22:01.042 | RTGS  | 0.985   | P1 (High) | [ESCALATE]  |
| 0x41b89d...10a  | ACC-021000021-99 | CAYMAN-APEX-CORP |   495,000.00 | 14:22:03.419 | RTGS  | 0.978   | P1 (High) | [ESCALATE]  |
| 0x77c1e3...449  | ACC-021000021-99 | PANAMA-SETTLE-7  |   492,000.00 | 14:22:06.182 | NEFT  | 0.962   | P1 (High) | [ESCALATE]  |
| 0xd389b2...881  | ACC-994100234-11 | MULE-ACCOUNT-88  |     9,900.00 | 14:22:12.809 | UPI   | 0.914   | P2 (Med)  | [ESCALATE]  |
| 0x1104e8...90a  | ACC-881902410-02 | RETAIL-VENDOR-14 |       450.00 | 14:22:14.218 | IMPS  | 0.012   | P3 (Low)  | [VERIFIED]  |
+---------------------------------------------------------------------------------------------------------------------------------+
```

---

### 2.3.2 Collaborative Filtering Anomaly Detector Workspace

```
+---------------------------------------------------------------------------------------------------------------------------------+
| COLLABORATIVE FILTERING BEHAVIORAL ANOMALY DETECTOR (Model: Cosine Nearest-Neighbors, k=2 Peer Clusters)                       |
+---------------------------------------------------------------------------------------------------------------------------------+
| ANOMALY ALERT CARD: OFFSHORE ALPHA LLC (ACC-021000021-99)                                                                       |
| Overall Anomaly Score: 0.406 [THRESHOLD: 0.40 EXCEEDED]  |  Peer Cluster: Institutional Wires (Normal Deviation: < 0.15)      |
|---------------------------------------------------------------------------------------------------------------------------------|
| BEHAVIORAL VECTOR DEVIATIONS:                                                                                                   |
| [1] Velocity Pass-Through:    [||||||||||||||||||||||||||||||||||||||] +4.8σ (99.8% drained in 60 seconds)                      |
| [2] Burstiness Index:          [||||||||||||||||||||||||||||||||||    ] +3.4σ (3 high-value wires in 5.1s)                       |
| [3] Off-Hours Execution:       [||||||||||||||||||||||||              ] +2.8σ (Executed 02:22 local bank time)                   |
| [4] Structuring Proximity:     [||||||||||||||||||||||||||||||||||||||] +5.1σ (Amounts clustered at 99.8% of $500k threshold)   |
|---------------------------------------------------------------------------------------------------------------------------------|
| DISPOSITION ACTIONS:                                                                                                            |
| [ESCALATE TO REGULATORY SAR]            [REQUEST ENHANCED DUE DILIGENCE (EDD)]            [MARK AS BENIGN / FALSE POSITIVE]     |
+---------------------------------------------------------------------------------------------------------------------------------+
```

---

### 2.3.3 Suspicious Activity Report (SAR) Generation & FinCEN Workflow

```
+---------------------------------------------------------------------------------------------------------------------------------+
| FINCEN SUSPICIOUS ACTIVITY REPORT (SAR) WORKFLOW BUILDER                                                                        |
+----------------------------------------------------------------+----------------------------------------------------------------+
| LEFT PANE: AUTO-POPULATED TRANSACTION TELEMETRY                | RIGHT PANE: FINCEN COMPLIANT NARRATIVE EDITOR                  |
|----------------------------------------------------------------+----------------------------------------------------------------|
| Dossier ID: SAR-IND-20260906-94A880                            | # SUSPICIOUS ACTIVITY REPORT NARRATIVE                         |
| Filing Deadline: 2026-10-06 (7 Working Days Remaining)         |                                                                |
| Subject: Offshore Alpha LLC (Tax ID: XX-XXX8812)               | During routine automated surveillance on 2026-09-06 at         |
| Suspected Typology: IN_TYP_STRUCT (Pan Structuring)            | 14:22:01 UTC, the automated monitoring engine detected a       |
| Total Exposure: INR 1,486,500.00                               | pattern of structured high-velocity wires originating from     |
| Related Transactions: 3 (UTR-94745531, UTR-51583722, ...)      | ACC-021000021-99 to multiple offshore counterparty accounts.   |
| Machine Learning Anomaly Score: 0.985                          |                                                                |
|                                                                | Specifically, three wires of INR 499,500.00, INR 495,000.00,  |
| [AUTO-FILL NARRATIVE CHIPS]                                    | and INR 492,000.00 were executed within 5.1 seconds,           |
| [Insert Velocity Metric] [Insert Typology Law] [Insert Hops]   | indicating deliberate smurfing below the INR 500,000 threshold |
+----------------------------------------------------------------+----------------------------------------------------------------+
| SUBMISSION STATE MACHINE:                                                                                                       |
|  [DRAFT] ===> [LEGAL COMPLIANCE REVIEW] ===> [OFFICER SIGN-OFF] ===> [FINCEN DISPATCH DISPATCHED]                              |
|                                                                                                                                 |
| [ SUBMIT FOR INTERNAL LEGAL REVIEW ]                                    [ EXPORT SAR DOSSIER PDF ]                              |
+---------------------------------------------------------------------------------------------------------------------------------+
```

---

### 2.3.4 Real-Time Immutable Audit Stream Interface

```
+---------------------------------------------------------------------------------------------------------------------------------+
| IMMUTABLE WRITE-AHEAD AUDIT LEDGER (RFC 6962 Merkle Tree Sync Hub)                                                             |
| Live Verification Status: [VERIFIED]  |  Current Merkle Root: 0x9f1a7c4e881023a9  |  Log Height: #882,410  |  Sync Latency: 0.04ms|
+---------------------------------------------------------------------------------------------------------------------------------+
| TIMESTAMP (UTC)      | EVENT TYPE               | PRINCIPAL ACTOR   | RECORD REFERENCE    | EVENT SHA-256 HASH                  |
|----------------------+--------------------------+-------------------+---------------------+-------------------------------------|
| 2026-09-25T14:22:01Z | STREAM_TX_INGESTED       | DAEMON_STREAMER   | UTR-20260906-947455 | 0x8a92f031ceb89104fa281c7e...       |
| 2026-09-25T14:22:15Z | SAR_DOSSIER_INITIALIZED  | SYSTEM_AML_ENGINE | SAR-94A880          | 0x3d7b92fa108c4e0981a29381...       |
| 2026-09-25T14:23:40Z | BM25_SEARCH_DISCOVERY    | AGENT_S_CHEN      | QUERY: CAYMAN_500K  | 0x77c1e3449b201a8f4c2e771a...       |
| 2026-09-25T14:24:02Z | RBAC_BOUNDARY_BLOCKED    | AGENT_S_CHEN      | RETAIL_LEDGER_PROBE | 0xf43f5e098112a9bc041289ac...       |
+---------------------------------------------------------------------------------------------------------------------------------+
```

---

# STEP 2.4: AI Copilot Boundary Defense & Prototype Handoff

### 2.4.1 Context-Aware Dual-Persona AI Copilot Interaction Model

```
INVESTIGATION COPILOT PERSONA                      BANK COMPLIANCE COPILOT PERSONA
+------------------------------------+             +------------------------------------+
| Model: Claude-3.5-Sonnet-Forensics |             | Model: Claude-3.5-Sonnet-FinCompliance|
| Clearance: Level 4 LEO Warrant     |             | Clearance: Level 3 Bank Compliance |
| Enclave: Evidentiary Subpoenas     |             | Enclave: Institutional Ledger / SAR|
| Scope: MT103, Signal Chats, Crypto |             | Scope: CTR, EDD, SAR Narratives    |
+------------------------------------+             +------------------------------------+
```

#### Dual-Mode Chat Interface Wireframe:
```
+-----------------------------------------------------------------------------------+
| [AI COPILOT: DUAL ENCLAVE DEFENDER]                                      [<>] [X] |
+-----------------------------------------------------------------------------------+
| Active Enclave: Investigation // Context Filter: SUBPOENA_EVIDENCE_ONLY           |
| Attached References: [Case 94A880] [Doc 994821] [Node: Offshore Alpha]           |
|-----------------------------------------------------------------------------------|
| Analyst: "Explain the legal grounds for asset freezing on Offshore Alpha."        |
|                                                                                   |
| Copilot:                                                                          |
| "Under 31 U.S.C. 5324(a)(3) and 18 U.S.C. 1956, sufficient evidence exists to     |
| issue a pre-indictment freezing order. Specifically:                              |
| 1. High-velocity structuring below the reporting threshold [1].                   |
| 2. Intercepted communications establishing deliberate avoidance intent [2].       |
|                                                                                   |
| Footnotes:                                                                        |
| [1] SWIFT MT103 Wire DOC-994821 (Amount: INR 499,500.00, 14:22:01 UTC)            |
| [2] Signal Chat Transcript DOC-102488 (Marcus Vance: 'Keep under 500k')           |
|-----------------------------------------------------------------------------------|
| Suggested Queries:                                                                |
| [Draft Asset Freeze Affidavit]  [Extract Offshore Routing Paths]  [Export Case]   |
+-----------------------------------------------------------------------------------+
| [ATTACH +] [Query Assistant within Active Legal Enclave...]                [SEND] |
+-----------------------------------------------------------------------------------+
```

---

### 2.4.2 Cross-Domain Perimeter Firewall & Breach Handling

When an Investigation user queries Bank customer PII (or vice versa), the security middleware intercepts the request before reaching the model:

```
+-----------------------------------------------------------------------------------+
| !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! |
| ! [SECURITY POLICY VIOLATION: CROSS-DOMAIN PERIMETER BREACH INTERCEPTED]         ! |
| ! CODE: ERR_SECURITY_BOUNDARY_VIOLATION_042                                      ! |
| !-------------------------------------------------------------------------------! |
| ! Attempted Action: Direct lookup of retail personal savings account balances.  ! |
| ! Active Clearance: Level 4 Lead Forensic Investigator (Warrant NYSD-0982).     ! |
| ! Restriction Policy: ISO 27001 / Bank Secrecy Act Customer Privacy Covenant.   ! |
| !                                                                               ! |
| ! Enclave Firewall Action: Prompt payload dropped. Connection sanitized.        ! |
| ! Cryptographic Audit Token: HASH-256 (0xf43f5e098112a9bc041289ac...) Logged.    ! |
| !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! |
+-----------------------------------------------------------------------------------+
```

---

### 2.4.3 Split-Screen Dual-Domain Supervisory Inspection View

For dual-credentialed Compliance Directors overseeing investigations alongside bank operations:

```
+---------------------------------------------------------------------------------------------------------------------------------+
| SUPERVISORY COMMAND VIEW: SYNCHRONIZED DUAL ENCLAVE OVERSIGHT                                            [DUAL CREDENTIAL VALID]|
+----------------------------------------------------------------+----------------------------------------------------------------+
| LEFT HALF: INVESTIGATION ENCLAVE (CYAN)                        | RIGHT HALF: BANK INSTITUTIONAL ENCLAVE (EMERALD)               |
| Border: 2px solid var(--investigation-primary)                 | Border: 2px solid var(--bank-primary)                          |
|----------------------------------------------------------------+----------------------------------------------------------------|
| CASE: CASE-IND-20260906-94A880                                 | SURVEILLANCE LEDGER: REAL-TIME INGEST                          |
| Target: Offshore Alpha LLC                                     | Account: ACC-021000021-99                                      |
| Status: Warrant NYSD-0982 Active                               | Status: Anomaly Score 0.406 [CRITICAL]                         |
|                                                                |                                                                |
| [EVIDENTIARY GRAPH CANVAS]                                     | [COLLABORATIVE FILTERING MATRIX]                               |
| (ACC-SEND-99) ===[499.5k]===> [OFFSHORE ALPHA]                 | Deviation: +4.8σ Pass-Through Velocity                         |
|                                                                |                                                                |
| [SUBPOENA DISCOVERY STATUS: 3 DOCS PENDING]                    | [SAR FILING STATUS: DRAFT IN REVIEW]                           |
+----------------------------------------------------------------+----------------------------------------------------------------+
| PHYSICAL ENCLAVE DIVIDER: Synchronized Timestamp 14:24:02 UTC // Cryptographic Air-Gap Active Between Enclave Contexts         |
+---------------------------------------------------------------------------------------------------------------------------------+
```

---

### 2.4.4 Component Architecture Tree, TypeScript Contracts & State Machines

#### 1. React Component Architecture Tree
```
nexus-frontend/src/
├── App.jsx [Root Global Shell State Machine Provider]
│   ├── components/header/
│   │   └── GlobalHeader.jsx [64px Header, Domain Switcher, BM25 Input, WS Beacon]
│   ├── components/sidebar/
│   │   └── EnterpriseSidebar.jsx [260px Expanded / 72px Collapsed Rail with RBAC Locks]
│   ├── components/investigation/
│   │   ├── CaseDossierView.jsx [Case Metadata, Timeline & Custody Seals]
│   │   ├── BM25EvidenceSearch.jsx [Probabilistic Search Console & Snippet Inspector]
│   │   ├── EntityLinkGraph.jsx [Force-Directed Graph & Centrality Node Flyout]
│   │   └── ForensicTrailLedger.jsx [QuickSort 3-Way DNF Partitioned Trail]
│   ├── components/banking/
│   │   ├── BankLedgerSurveillance.jsx [High-Density Ledger & Sort Controls]
│   │   ├── CollaborativeFilteringModule.jsx [Cluster Deviation & Anomaly Cards]
│   │   ├── HashLookupEngine.jsx [O(1) Robin Hood Hash Index Inspector]
│   │   └── RegulatorySarExporter.jsx [Split-Pane SAR Builder & FinCEN Markdown]
│   └── components/ai/
│       └── IsolatedAiCopilot.jsx [Context-Aware Copilot & Boundary Rejection Card]
```

#### 2. Strict TypeScript Data Contracts
```typescript
export interface DesignTokens {
  canvas: string;
  surface: string;
  elevated: string;
  sunken: string;
  investigationAccent: string;
  bankAccent: string;
  boundaryViolationAlert: string;
}

export interface LedgerRow {
  txHash: string;
  senderAccount: string;
  beneficiaryAccount: string;
  amount: number;
  currency: string;
  timestampUtc: string;
  paymentRail: 'RTGS' | 'NEFT' | 'UPI' | 'IMPS' | 'FEDWIRE';
  mlRiskScore: number;
  dnfPartitionTier: 'P1' | 'P2' | 'P3';
}

export interface AnomalyCard {
  entityId: string;
  entityName: string;
  anomalyScore: number;
  thresholdExceeded: boolean;
  peerClusterK: number;
  deviations: {
    dimension: string;
    sigmaDeviation: number;
    description: string;
  }[];
}

export interface BM25Result {
  docId: string;
  title: string;
  category: 'Bank Record' | 'Forensic Note' | 'Ledger Export' | 'Subpoena Return';
  relevanceScore: number;
  snippet: string;
  matchedTerms: string[];
  latencyMs: number;
}

export interface CopilotMessage {
  id: string;
  sender: 'user' | 'ai' | 'security_firewall';
  role: 'LEO_AGENT' | 'BANK_OFFICER' | 'FIREWALL_ALERT';
  text: string;
  timestamp: string;
  isBreachAlert?: boolean;
  citations?: {
    docId: string;
    title: string;
  }[];
}

export interface AuditLogEvent {
  logHeight: number;
  timestampUtc: string;
  eventType: 'STREAM_TX_INGESTED' | 'SAR_DOSSIER_INITIALIZED' | 'BM25_SEARCH_DISCOVERY' | 'RBAC_BOUNDARY_BLOCKED';
  principalActor: string;
  referenceId: string;
  sha256Hash: string;
  merkleVerified: boolean;
}
```

#### 3. State Machine Specification (RBAC & Boundary Transition)
```
          [UNAUTHENTICATED / BOOT]
                     │
                     ▼
          [ROLE RESOLUTION ENGINE]
          ├── LEO_INVESTIGATION ===> Active Enclave: Investigation (Cyan Theme)
          │                            • Bank modules locked with PADLOCK
          │                            • Cross-domain queries trigger BOUNDARY_REJECTION_CARD
          │
          └── BANK_OPERATIONS   ===> Active Enclave: Bank Institutional (Emerald Theme)
                                       • Subpoena vaults locked with PADLOCK
                                       • Evidentiary queries trigger BOUNDARY_REJECTION_CARD
```
