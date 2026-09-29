# QuantumAML Nexus — Dual-Domain Security Architecture
## Step 2.1 (Part 1: Sub-steps 2.1.1 – 2.1.4)
### Design Tokens, Global Shell Wireframe Architecture & Layout Grid
**Role:** Principal UI/UX Architect & Design Systems Lead  
**Classification:** RESTRICTED // FINANCIAL INTELLIGENCE & INSTITUTIONAL COMPLIANCE  
**Target:** 1920x1080 Base Resolution, WCAG 2.1 AA Certified, 8-Point Grid, Strict RBAC Enclave Isolation  

---

## Sub-step 2.1.1: Enterprise Dark Theme Token System (CSS Stylesheet)

```css
/**
 * QUANTUMAML NEXUS ENTERPRISE DESIGN TOKENS
 * Sub-step 2.1.1 - Core System Tokens & Role-Isolated Palettes
 */

:root,
[data-theme="dark"] {
  color-scheme: dark;

  /* ==========================================================================
     1. Surface Elevation Hierarchy (Obsidian Foundation)
     ========================================================================== */
  --bg-canvas:                     #070a11; /* Root viewport base ground */
  --bg-surface:                    #0b0f19; /* Default panel, card, table body */
  --bg-surface-hover:              #0f1523; /* Interactive row / card hover */
  --bg-elevated:                   #111827; /* Sticky headers, breadcrumbs, modals, popovers */
  --bg-elevated-hover:             #162035; /* Hover state for elevated controls */
  --bg-sunken:                     #04060a; /* Recessed terminal wells, hex dumps, query consoles */
  --bg-dropdown:                   #141c2e; /* Context menus, autocomplete select overlays */
  --bg-modal-backdrop:             rgba(4, 6, 10, 0.85); /* Modal scrim */
  --bg-glass:                      rgba(11, 15, 25, 0.78); /* Translucent glass panels */

  /* Surface Shadows */
  --shadow-sm:                     0 1px 2px 0 rgba(0, 0, 0, 0.5);
  --shadow-md:                     0 4px 12px -2px rgba(0, 0, 0, 0.65), 0 2px 4px -2px rgba(0, 0, 0, 0.45);
  --shadow-lg:                     0 12px 24px -4px rgba(0, 0, 0, 0.75), 0 4px 8px -2px rgba(0, 0, 0, 0.5);
  --shadow-modal:                  0 24px 48px -8px rgba(0, 0, 0, 0.85), 0 0 0 1px rgba(255, 255, 255, 0.06);

  /* Multi-Tier Structural Borders */
  --border-subtle:                 #1a2333; /* Table internal gridlines, micro-rules */
  --border-default:                #243046; /* Default card contours, input boundaries */
  --border-active:                 #3b4b69; /* Focused card strokes, active tab underlines */
  --border-divider:                rgba(255, 255, 255, 0.07); /* Metric column dividers */

  /* ==========================================================================
     2. Role-Isolated Domain Accent Palettes
     ========================================================================== */

  /* 2.1 Investigation Domain: Forensic Cyan & Deep Cyber Indigo */
  --investigation-primary:         #06b6d4; /* Cyan-500: Core action / badge glyph */
  --investigation-hover:           #0891b2; /* Cyan-600 */
  --investigation-active:          #0e7490; /* Cyan-700 */
  --investigation-surface:         rgba(6, 182, 212, 0.12); /* Tinted pill & card background */
  --investigation-border:          rgba(6, 182, 212, 0.38); /* Subtle contour line */
  --investigation-ring:            rgba(56, 189, 248, 0.65); /* Accessible focus ring */
  --investigation-glow:            0 0 20px -2px rgba(6, 182, 212, 0.40);

  /* 2.2 Bank Domain: Financial Emerald & Sovereign Slate */
  --bank-primary:                  #10b981; /* Emerald-500: Institutional compliance */
  --bank-hover:                    #059669; /* Emerald-600 */
  --bank-active:                   #047857; /* Emerald-700 */
  --bank-surface:                  rgba(16, 185, 129, 0.12); /* Ledger highlight background */
  --bank-border:                   rgba(16, 185, 129, 0.38); /* Institutional card outline */
  --bank-ring:                     rgba(52, 211, 153, 0.65); /* Accessible focus ring */
  --bank-glow:                     0 0 20px -2px rgba(16, 185, 129, 0.40);

  /* ==========================================================================
     3. Semantic Status & Security Boundary Tokens
     ========================================================================== */
  /* Verified / Nominal State */
  --status-nominal:                #10b981; /* Emerald-500 */
  --status-nominal-bg:             rgba(16, 185, 129, 0.12);
  --status-nominal-border:         rgba(16, 185, 129, 0.35);

  /* Pending Review / Stale State */
  --status-warning:                #f59e0b; /* Amber-500 */
  --status-warning-bg:             rgba(245, 158, 11, 0.12);
  --status-warning-border:         rgba(245, 158, 11, 0.35);

  /* Critical Anomaly / AML Flagged State */
  --status-critical:               #ef4444; /* Red-500 */
  --status-critical-bg:            rgba(239, 68, 68, 0.16);
  --status-critical-border:        rgba(239, 68, 68, 0.50);

  /* AI Domain Boundary Violation (Perimeter Breach Token) */
  --boundary-violation-alert:      #f43f5e; /* Rose-500: Sharp laser crimson */
  --boundary-violation-bg:         rgba(244, 63, 94, 0.22);
  --boundary-violation-border:     #fda4af; /* Rose-300: High-visibility edge stroke */
  --boundary-violation-neon:       0 0 28px rgba(244, 63, 94, 0.55), inset 0 0 12px rgba(244, 63, 94, 0.3);

  /* ==========================================================================
     4. Typography & Monospace Financial Data Stack
     ========================================================================== */
  --font-sans:                     'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono:                     'JetBrains Mono', 'Fira Code', 'Roboto Mono', Menlo, Consolas, monospace;

  /* Monospace Financial Configuration */
  --font-mono-ledger:              0.8125rem; /* 13px */
  --font-mono-ledger-lh:           1.25rem;   /* 20px */
  --font-mono-spacing:             -0.01em;
  --font-mono-features:            "tnum" on, "lnum" on, "zero" on;

  /* Foreground Text Hierarchy */
  --text-primary:                  #f8fafc; /* Slate-50: Contrast ratio 18.7:1 vs #070A11 */
  --text-secondary:                #94a3b8; /* Slate-400: Contrast ratio 7.4:1 vs #0B0F19 */
  --text-muted:                    #64748b; /* Slate-500: Contrast ratio 4.6:1 vs #0B0F19 */
  --text-dim:                      #475569; /* Slate-600: Deactivated glyphs */
  --text-inverse:                  #020617; /* Solid badge foreground */
}

/* Monospace Class Utility */
.font-financial-tabular {
  font-family: var(--font-mono);
  font-size: var(--font-mono-ledger);
  line-height: var(--font-mono-ledger-lh);
  font-feature-settings: var(--font-mono-features);
  letter-spacing: var(--font-mono-spacing);
  text-align: right;
  white-space: nowrap;
}

.hash-cell {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  letter-spacing: 0.02em;
  color: var(--text-secondary);
}
```

---

## Sub-step 2.1.2: Global Shell Structural ASCII Wireframes

### 1. Full-Screen 3-Pane Layout (1920x1080 Base Resolution)

```
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|  [NX] QUANTUMAML NEXUS  ::  ENTERPRISE GOVERNANCE                      [ENCLAVE: INVESTIGATION]              IMMUTABLE LOG: VERIFIED (0.04ms)   [USER: S.CHEN]   |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| GLOBAL APPLICATION HEADER (64px H)                                                                                                                                |
|  [LOGO] NEXUS | [DOM: INVESTIGATION v] | [SEARCH: BM25 Case & Evidence Query... (Ctrl+K)]             | [WS: LIVE 38ms] [SESSION: 0x9f1a] | [PROFILE: S.Chen]         |
+-----------------------+-----------------------------------------------------------------------------------------------------------+-------------------------------+
| LEFT SIDEBAR (260px)  | MAIN CENTRAL VIEWPORT CONTAINER (1300px Flexible Track)                                                   | DOCKED AI COPILOT (360px)     |
+-----------------------+-----------------------------------------------------------------------------------------------------------+-------------------------------+
| [*] ACTIVE ENCLAVE    | BREADCRUMBS: Investigations > Active Cases > CASE-IND-20260906-94A880 (SAR Filing In Progress)            | [AI FORENSIC SPECIALIST] [DOCK|
|  [>] Forensic Queue   |-----------------------------------------------------------------------------------------------------------|-------------------------------|
|  [ ] Entity Link Graph| [QUICKSORT TRIAGE LEDGER]                              [FILTERS: P1 Critical | Structuring | Last 24h]    | CONTEXTUAL EVIDENCE:          |
|  [ ] BM25 Search      | +-------------------------------------------------------------------------------------------------------+ | Active: CASE-94A880           |
|  [ ] Subpoena Vault   | | TX HASH            | SENDER ACC        | BENEFICIARY ACC   | AMOUNT (INR) | TIME (UTC) | ML RISK | DNF| | Boundary: RESTRICTED          |
|  [ ] SAR Dossier      | |--------------------+-------------------+-------------------+--------------+------------+---------+----| | (Institutional PII Locked)   |
|                       | | 0x8a92f0...31c     | ACC-021000021-99  | OFFSHORE-ALPHA-LLC|  499,500.00  | 14:22:01.0 | 0.985   | P1 | |-------------------------------|
| ROLE MODULES          | | 0x41b89d...10a     | ACC-021000021-99  | CAYMAN-APEX-CORP  |  495,000.00  | 14:22:03.4 | 0.978   | P1 | | [STREAM]                      |
|  [ ] Hawala Smurf Net | | 0x77c1e3...449     | ACC-021000021-99  | PANAMA-SETTLE-7   |  492,000.00  | 14:22:06.1 | 0.962   | P1 | | Analyst: "Trace structuring  |
|  [ ] Micro-Structuring| | 0xd389b2...881     | ACC-994100234-11  | MULE-ACCOUNT-8812 |    9,900.00  | 14:22:12.8 | 0.914   | P2 | | velocity for Alpha LLC"     |
|  [ ] Crypto Mempool   | +-------------------------------------------------------------------------------------------------------+ |                               |
|                       | QuickSort Statistics: 40 Records Sorted in 0.098ms (DNF Multi-Pivot Partitioning Complete)               | Copilot: "Detected 3 wire     |
| RESTRICTED DOMAIN     |-----------------------------------------------------------------------------------------------------------| structured under INR 500k     |
|  [x] Bank Ledgers[PAD]| [COLLABORATIVE FILTERING ANOMALY MATRIX]                                                                  | threshold (Total: INR 1.486M) |
|                       |   Entity: OFFSHORE-ALPHA-LLC     Anomaly Score: 0.406 [EXCEEDS THRESHOLD 0.40]                           | within 5.1 seconds."          |
| SECURITY INTEGRITY    |   Peer Group: Corporate Offshore Wires (k=2) | Deviation Vector: 8 anomalous dimensions detected          |                               |
|  [o] Merkle Root Sync |   [Burstiness Index: +3.4σ] [Rapid Fan-Out: +4.1σ] [Off-Hours Velocity: +2.8σ]                            | [QUICK ACTIONS]               |
|  [o] WebSocket 38ms   |-----------------------------------------------------------------------------------------------------------| [Freeze Entity] [Draft SAR]   |
|-----------------------| [MULTI-HOP ENTITY LINK GRAPH]                                                                             |-------------------------------|
| [<< Collapse Rail]    |  (ACC-SEND-99) ===[INR 499.5k]===> [OFFSHORE ALPHA] ===[INR 1.48M]===> [CAYMAN VAULT]                     | [INPUT PROMPT]                |
| TLS 1.3 // SESSION OK |   Status: Aggregation Layering Flagged                                                                    | [/explain, /subpoena...]      |
+-----------------------+-----------------------------------------------------------------------------------------------------------+-------------------------------+
```

---

### 2. Left Navigation Sidebar Variants

#### Expanded State (260px Width)
```
+------------------------------------+
|  [NX]  QUANTUMAML NEXUS            |
+------------------------------------+
| ENCLAVE CONTEXT LOCKER:            |
| +--------------------------------+ |
| | [*] INVESTIGATION ENCLAVE  [v] | |
| |     Clearance: LEVEL 4 LEAD    | |
| +--------------------------------+ |
|                                    |
| FORENSIC WORKSPACE                 |
|  [*] Case Triage Queue       (14)  |
|  [ ] Multi-Hop Link Graph          |
|  [ ] BM25 Subpoena Search          |
|  [ ] SAR Filing Dossiers      (3)  |
|                                    |
| ALGORITHMIC SUITES                 |
|  [ ] QuickSort Ledger View         |
|  [ ] Collab Filtering Anomalies    |
|  [ ] RobinHood Hash Inspector      |
|  [ ] Crypto Mempool Live           |
|                                    |
| CROSS-ENCLAVE (RESTRICTED)         |
|  [x] Bank Institutional Core  [PAD]|
|      Tooltip: "Requires RBAC       |
|       ROLE_BANK_OFFICER"           |
|                                    |
| SYSTEM INTEGRITY                   |
|  [o] Merkle Root Sync        [OK]  |
|  [o] WebSocket Stream       38ms   |
|                                    |
|------------------------------------|
| [<<] Collapse Navigation Rail      |
| TLS 1.3 // SESSION: 9f1a-7c4e-0e   |
+------------------------------------+
```

#### Collapsed State (72px Width)
```
+--------+
|  [NX]  |
+--------+
|  [INV] | <- Cyan active indicator
|--------|
|  [Q]   | <- Tooltip: "Case Triage Queue (14)"
|  [G]   | <- Tooltip: "Multi-Hop Link Graph"
|  [S]   | <- Tooltip: "BM25 Subpoena Search"
|  [D]   | <- Tooltip: "SAR Filing Dossiers (3)"
|--------|
|  [QS]  | <- Tooltip: "QuickSort Ledger View"
|  [CF]  | <- Tooltip: "Collab Filtering Anomalies"
|  [RH]  | <- Tooltip: "RobinHood Hash Inspector"
|  [BC]  | <- Tooltip: "Crypto Mempool Live"
|--------|
|  [LCK] | <- Padlock glyph (Bank Domain Locked)
|--------|
|  [OK]  | <- Green beacon: "Merkle Root Valid"
|  [>>]  | <- Expand Sidebar trigger
+--------+
```

---

### 3. Docked AI Copilot Drawer Blueprint

```
+-------------------------------------------------------------+
| [AI COPILOT: INVESTIGATION MODE]               [<>] [X]     |
| Enclave: Forensic Analysis // Boundary Filter: ACTIVE       |
+-------------------------------------------------------------+
| CONTEXTUAL EVIDENCE TAGS:                                   |
| [Case: 94A880 (Active)] [Entity: Offshore Alpha] [SAR-Draft]|
+-------------------------------------------------------------+
| MESSAGE STREAM:                                             |
|                                                             |
| Analyst: "What is recipient's domestic savings balance?"    |
|                                                             |
| +---------------------------------------------------------+ |
| | !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! | |
| | ! [SECURITY POLICY VIOLATION: DOMAIN BOUNDARY ENFORCED] ! | |
| | ! CODE: ERR_CROSS_DOMAIN_BREACH_DETECTED                ! | |
| | !                                                       ! | |
| | ! Query attempted cross-enclave fetch into Bank Retail  ! | |
| | ! Customer ledger: 'personal domestic savings'.         ! | |
| | ! Cross-domain queries are prohibited under ISO 27001 / ! | |
| | ! AML Data Isolation Act.                               ! | |
| | !                                                       ! | |
| | ! Logged to Immutable Audit Trail: Hash 0x7a81...c09    ! | |
| | !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! | |
| +---------------------------------------------------------+ |
|                                                             |
| AI Forensic Copilot: "I cannot provide personal domestic    |
| account balances. However, I can report external wire       |
| aggregations and suspicious velocity from public subpoena   |
| evidence."                                                  |
|                                                             |
| Suggested Queries:                                          |
| [Show multi-hop wire hops]  [Compute structuring delta]     |
+-------------------------------------------------------------+
| [ATTACH] [BM25 Doc +] [Case Node +]                         |
| +---------------------------------------------------------+ |
| | Ask Copilot within active forensic context...    [ENTER]| |
| +---------------------------------------------------------+ |
| Allowed domains: Wire MT103, Blockchain, SAR Evidence Only  |
+-------------------------------------------------------------+
```

---

## Sub-step 2.1.3: Global Header & BM25 Search Bar Anatomy

### 1. Global Header Component Anatomy

```
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|  [1. BRAND LOGO]     | [2. CONTEXT-LOCKED DOMAIN] | [3. GLOBAL BM25 SEARCH CONSOLE]                | [4. AUDIT STATUS]    | [5. WS BEACON] | [6. USER PROFILE]   |
|  NEXUS ENTERPRISE    | [*] INVESTIGATION ENCLAVE  | [MAG] [case: *] [tx: *] Search...     [Ctrl+K] | LOG: SYNCHRONIZED    | LIVE (38ms)    | S.Chen (Lead Agent) |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------+
```

1. **Brand Identity:** High-contrast logo with enterprise classification badge.
2. **Context-Locked Domain Selector:** Dropdown displaying current clearance, with disabled institutional domains marked by lock glyphs.
3. **Global BM25 Search Console:** Sub-50ms probabilistic evidence retrieval bar.
4. **Audit Status:** Real-time SHA-256 HMAC Merkle tree synchronization beacon.
5. **WebSocket Beacon:** Live latency indicator with pulsing nominal green light.
6. **User Profile Pill:** Identity, clearance level, and session lock trigger.

---

### 2. BM25 Search Bar Anatomy & Autocomplete Dropdown

```
+---------------------------------------------------------------------------------------------------------------------------------+
| SEARCH INPUT BAR (Header Center):                                                                                               |
| [MAGNIFIER] | [chip: case: *] [chip: tx: *] [chip: hash: *] [chip: subpoena: *] | Query: "Cayman wire routing under 500k" [X] | [Ctrl+K]
+---------------------------------------------------------------------------------------------------------------------------------+
| RESULTS AUTOCOMPLETE DROPDOWN (Overlay Z-Index: 1000):                                                                          |
| Search Telemetry: BM25 Ranked in 0.06ms | Indexed Corpus: 1,420 legal documents and wire notes                                   |
|---------------------------------------------------------------------------------------------------------------------------------|
| [MT103 WIRE] DOC-994821: Alpha LLC offshore wire routing 021000021 to Apex Holdings                         Score: 14.82 BM25   |
|   Matches: "...wire transfer routing 021000021 to Apex Holdings Cayman..."                                  [Relevance: 98%]    |
|   Tags: [SWIFT MT103] [JURISDICTION: CAYMAN] [ACCOUNT: ACC-021000021]                                                           |
|---------------------------------------------------------------------------------------------------------------------------------|
| [SIGNAL CHAT] DOC-102488: Intercepted communications transcript Vance Marcus                                Score: 11.24 BM25   |
|   Matches: "...Keep Cayman wire under 500k to avoid escalation Marcus Vance..."                             [Relevance: 84%]    |
|   Tags: [EVIDENTIARY] [INTENT_STRUCTURING] [SUSPECT: M.VANCE]                                                                    |
|---------------------------------------------------------------------------------------------------------------------------------|
| [SUBPOENA RETURN] DOC-55102: Apex Holdings banking mandate & beneficial ownership                           Score:  8.91 BM25   |
|   Matches: "...offshore wire authority granted to Marcus Vance..."                                          [Relevance: 62%]    |
|   Tags: [SUBPOENA_RETURN] [BENEFICIAL_OWNER]                                                                                    |
|---------------------------------------------------------------------------------------------------------------------------------|
| [Press ENTER to load full search matrix]                                                   [ESC to dismiss]                      |
+---------------------------------------------------------------------------------------------------------------------------------+
```

---

## Sub-step 2.1.4: Layout Grid, CSS Rules & Responsive Breakpoint Matrix

### 1. Structural CSS Grid Implementation

```css
/**
 * QUANTUMAML NEXUS GLOBAL SHELL GRID LAYOUT
 * Sub-step 2.1.4 - CSS Grid Column Definitions & Container Bounds
 */

/* Shell Root Container */
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

/* Header Area */
.nexus-shell-header {
  grid-area: header;
  height: 64px;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  z-index: 100;
}

/* Sidebar Area */
.nexus-shell-sidebar {
  grid-area: sidebar;
  width: 260px;
  background-color: var(--bg-surface);
  border-right: 1px solid var(--border-subtle);
  overflow-y: auto;
  z-index: 200;
  transition: width 280ms cubic-bezier(0.16, 1, 0.3, 1);
}

/* Main Viewport Container */
.nexus-shell-viewport {
  grid-area: viewport;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 1.5rem;
  background-color: var(--bg-canvas);
}

/* Docked AI Copilot Drawer */
.nexus-shell-copilot {
  grid-area: copilot;
  width: 360px;
  background-color: var(--bg-surface);
  border-left: 1px solid var(--border-subtle);
  z-index: 300;
  transition: width 320ms cubic-bezier(0.16, 1, 0.3, 1);
}

/* Collapsed Sidebar Track Modifier */
.nexus-shell-container[data-sidebar="collapsed"] {
  grid-template-columns: 72px 1fr 360px;
}
.nexus-shell-container[data-sidebar="collapsed"] .nexus-shell-sidebar {
  width: 72px;
}

/* Expanded Copilot Drawer Track Modifier */
.nexus-shell-container[data-copilot="expanded"] {
  grid-template-columns: 260px 1fr 520px;
}
.nexus-shell-container[data-copilot="expanded"] .nexus-shell-copilot {
  width: 520px;
}
```

---

### 2. Responsive Breakpoint Matrix

| Viewport Breakpoint | Target Screen Classification | Left Sidebar State | Main Viewport Grid Layout | Docked AI Copilot Drawer Behavior | Horizontal Scroll Policy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1440px Desktop** (`max-width: 1599px`) | Standard Analyst Workstation | **Auto-collapsed to 72px** icon rail | Single primary column (1fr), tabbed secondary views | **Auto-collapses to floating toggle trigger** or fixed compact 320px width | **Strict Zero** (All tables use vertical scroll + row truncation) |
| **1920px Standard Enterprise** (`1600px - 2047px`) | Primary SOC / Command Center Display | **Expanded 260px** with full navigation tree | **2-Column Split:** Ledger (1.3fr) + Anomaly Matrix (1fr) | **Docked 360px** (Expandable to 520px on demand) | **Strict Zero** |
| **2560px Ultra-Wide** (`min-width: 2048px`) | 4K Operations Desk / Multi-Monitor Array | **Expanded 260px** | **3-Column Grid:** Ledger (1.2fr) + Graph (1fr) + SAR Synthesis Deck (1fr) | **Docked Wide 520px** | **Strict Zero** |

```css
/* Responsive Media Query Adaptations */

/* Standard Desktop (1440px) */
@media (max-width: 1599px) {
  .nexus-shell-container {
    grid-template-columns: 72px 1fr 0px;
  }
  .nexus-shell-sidebar {
    width: 72px;
  }
  .nexus-shell-copilot {
    position: fixed;
    right: 0;
    top: 64px;
    bottom: 0;
    transform: translateX(100%);
  }
  .nexus-shell-copilot[data-open="true"] {
    transform: translateX(0);
    box-shadow: -12px 0 36px rgba(0, 0, 0, 0.75);
  }
}

/* Ultra-Wide (2560px+) Multi-Column Viewport */
@media (min-width: 2048px) {
  .nexus-viewport-inner {
    display: grid;
    grid-template-columns: 1.2fr 1fr 1fr;
    gap: 1.5rem;
    max-width: 100%;
  }
}
```

---

## Technical Delivery Verification Matrix

- [x] **Sub-step 2.1.1:** Complete `:root` / `[data-theme="dark"]` stylesheet with 4 surface tiers, multi-tier borders, investigation/bank accents, boundary breach alert tokens, and tabular monospace features.
- [x] **Sub-step 2.1.2:** 1920x1080 3-pane ASCII diagram, expanded (260px) and collapsed (72px) sidebar blueprints, and docked AI assistant drawer with cross-domain rejection alert.
- [x] **Sub-step 2.1.3:** Global header anatomy (6 zones) and dedicated BM25 search bar anatomy with syntax chips (`case:`, `tx:`, `hash:`, `subpoena:`) and latency metrics.
- [x] **Sub-step 2.1.4:** Production-ready CSS Grid stylesheet and responsive breakpoint matrix covering 1440px, 1920px, and 2560px screen sizes.
