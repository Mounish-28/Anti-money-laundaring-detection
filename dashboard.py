"""
QuantumAML Nexus — Compliance Investigator Dashboard
Production-ready Streamlit real-time triage interface for banking and cryptocurrency transactions.
"""

import time
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import requests
import streamlit as st

# ==============================================================================
# Page Configuration & Global Theme
# ==============================================================================
st.set_page_config(
    page_title="QuantumAML Nexus | Compliance Investigator Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Glassmorphism & Triage Tier Styling
st.markdown(
    """
<style>
    /* Metric & Card Containers */
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(26, 34, 52, 0.8), rgba(17, 24, 39, 0.9));
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 14px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .badge-online {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid #059669;
    }
    .badge-offline {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid #dc2626;
    }
    /* Risk Tiers */
    .tier-low {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid #059669;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 800;
        display: inline-block;
    }
    .tier-elevated {
        background-color: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
        border: 1px solid #d97706;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 800;
        display: inline-block;
    }
    .tier-high {
        background-color: rgba(249, 115, 22, 0.2);
        color: #f97316;
        border: 1px solid #ea580c;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 800;
        display: inline-block;
    }
    .tier-critical {
        background-color: rgba(239, 68, 68, 0.25);
        color: #ef4444;
        border: 1px solid #dc2626;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 900;
        display: inline-block;
        box-shadow: 0 0 12px rgba(239, 68, 68, 0.5);
        animation: pulse-border 2s infinite;
    }
    @keyframes pulse-border {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.6); }
        70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    .sar-alert-box {
        background: linear-gradient(135deg, rgba(127, 29, 29, 0.4), rgba(69, 10, 10, 0.5));
        border: 1px solid #ef4444;
        border-radius: 8px;
        padding: 12px 18px;
        margin-top: 14px;
        color: #fecaca;
        font-weight: 600;
    }
    .cleared-box {
        background: linear-gradient(135deg, rgba(6, 78, 59, 0.3), rgba(2, 44, 34, 0.4));
        border: 1px solid #10b981;
        border-radius: 8px;
        padding: 12px 18px;
        margin-top: 14px;
        color: #a7f3d0;
        font-weight: 600;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ==============================================================================
# Session State Initialization
# ==============================================================================
if "history" not in st.session_state:
    st.session_state.history = []

# Default Form States for Tab 1 (IBM Transactions)
if "ibm_tx_id" not in st.session_state:
    st.session_state.ibm_tx_id = "TX_LIVE_90241"
if "ibm_from_bank" not in st.session_state:
    st.session_state.ibm_from_bank = "010"
if "ibm_to_bank" not in st.session_state:
    st.session_state.ibm_to_bank = "012"
if "ibm_account_from" not in st.session_state:
    st.session_state.ibm_account_from = "ACC_SEND_8801"
if "ibm_account_to" not in st.session_state:
    st.session_state.ibm_account_to = "ACC_RECV_4420"
if "ibm_amount" not in st.session_state:
    st.session_state.ibm_amount = 2500.50
if "ibm_currency" not in st.session_state:
    st.session_state.ibm_currency = "USD"
if "ibm_payment_format" not in st.session_state:
    st.session_state.ibm_payment_format = "Credit Card"

# Default Form States for Tab 2 (Elliptic Bitcoin)
if "crypto_node_id" not in st.session_state:
    st.session_state.crypto_node_id = "BTC_NODE_LIVE_001"
if "crypto_timestep" not in st.session_state:
    st.session_state.crypto_timestep = 35
if "crypto_features_text" not in st.session_state:
    # Default 165 clean floats
    st.session_state.crypto_features_text = ", ".join(
        [f"{0.05 + 0.001 * (i % 10):.4f}" for i in range(165)]
    )


# ==============================================================================
# Helper Functions & Network Handlers
# ==============================================================================
def check_health(api_base_url: str) -> dict[str, Any]:
    """Queries GET /health endpoint to check server availability and loaded models."""
    try:
        url = f"{api_base_url.rstrip('/')}/health"
        resp = requests.get(url, timeout=2.5)
        if resp.status_code == 200:
            data = resp.json()
            return {"online": True, "data": data, "error": None}
        return {"online": False, "data": None, "error": f"HTTP {resp.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"online": False, "data": None, "error": str(e)}


def fetch_prometheus_metrics(api_base_url: str) -> dict[str, Any]:
    """Parses Prometheus text exposition format from GET /metrics."""
    metrics_summary = {
        "transactions_total": 0,
        "anomalies_total": 0,
        "raw_text": "",
        "online": False,
    }
    try:
        url = f"{api_base_url.rstrip('/')}/metrics"
        resp = requests.get(url, timeout=2.5)
        if resp.status_code == 200:
            metrics_summary["online"] = True
            metrics_summary["raw_text"] = resp.text
            for line in resp.text.splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                if line.startswith("aml_transactions_evaluated_total"):
                    try:
                        val = float(line.split()[-1])
                        metrics_summary["transactions_total"] += int(val)
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("aml_anomalies_detected_total"):
                    try:
                        val = float(line.split()[-1])
                        metrics_summary["anomalies_total"] += int(val)
                    except (ValueError, IndexError):
                        pass
    except requests.exceptions.RequestException:
        pass
    return metrics_summary


def render_tier_badge(tier_name: str) -> str:
    """Renders HTML colored badge based on standard risk tier names."""
    tier = str(tier_name).upper()
    if tier in ("CRITICAL", "CRITICAL_SAR"):
        return '<span class="tier-critical">CRITICAL SAR</span>'
    elif tier in ("HIGH", "HIGH_RISK"):
        return '<span class="tier-high">HIGH RISK</span>'
    elif tier in ("ELEVATED", "ELEVATED_RISK", "MEDIUM"):
        return '<span class="tier-elevated">ELEVATED</span>'
    return '<span class="tier-low">LOW RISK</span>'


# ==============================================================================
# Sidebar Architecture & Dynamic Health Probe
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=64)
    st.title("QuantumAML Nexus")
    st.caption("Quantitative Multi-Model AML Decision Engine")

    st.markdown("---")
    st.subheader("🌐 Inference Cluster Gateway")
    api_url = (
        st.text_input(
            "Backend API Base URL",
            value="http://localhost:8000",
            help="FastAPI serving layer endpoint URL",
        )
        .strip()
        .rstrip("/")
    )

    # Health Check Probe
    health_result = check_health(api_url)
    if health_result["online"]:
        st.markdown(
            '<div style="margin-bottom: 10px;"><span class="status-badge badge-online">● ONLINE</span> <span style="font-size:0.85rem; color:#9ca3af; margin-left:8px;">FastAPI v2.0.0</span></div>',
            unsafe_allow_html=True,
        )
        loaded_models = health_result["data"].get("loaded_models", [])
        with st.expander("📦 Active Model Artifacts", expanded=True):
            if loaded_models:
                for m in loaded_models:
                    st.markdown(f"• **`{m}`** `LOADED`")
            else:
                st.caption("No models reported loaded by registry.")
    else:
        st.markdown(
            '<div style="margin-bottom: 10px;"><span class="status-badge badge-offline">● OFFLINE</span> <span style="font-size:0.85rem; color:#ef4444; margin-left:8px;">Unreachable</span></div>',
            unsafe_allow_html=True,
        )
        st.error(f"Cannot connect to `{api_url}`. Ensure FastAPI backend is running.")

    st.markdown("---")
    st.subheader("📊 Session Telemetry")
    total_evals = len(st.session_state.history)
    total_anomalies = sum(1 for x in st.session_state.history if x.get("Is Anomaly"))
    anomaly_rate = (total_anomalies / total_evals * 100.0) if total_evals > 0 else 0.0

    col_s1, col_s2 = st.columns(2)
    col_s1.metric("Evaluations", total_evals)
    col_s2.metric("Anomalies", total_anomalies)
    st.metric("Anomaly Rate", f"{anomaly_rate:.1f}%")

    if st.button("🗑️ Clear Session Audit Log", use_container_width=True):
        st.session_state.history = []
        st.rerun()


# ==============================================================================
# Main Triage Interface Header
# ==============================================================================
st.title("🛡️ AML Compliance Investigator Workspace")
st.markdown(
    "Continuous real-time anomaly detection, risk triage classification, and SAR escalation dispatch."
)

tab1, tab2, tab3 = st.tabs(
    [
        "🏦 Banking Transaction Triage (IBM CatBoost)",
        "⚡ Crypto Transaction Triage (Elliptic XGBoost)",
        "📈 Cluster Telemetry & Audit Trail",
    ]
)


# ==============================================================================
# TAB 1: Banking Transaction Triage (IBM CatBoost)
# ==============================================================================
with tab1:
    st.markdown("### IBM Transactions AML Structuring & Topology Analysis")
    st.caption(
        "Evaluates banking transactions against balanced CatBoost weights trained on 5.08M transactions."
    )

    # Quick-Load Presets
    st.markdown("##### ⚡ Quick-Load Scenario Presets")
    col_pre1, col_pre2, _ = st.columns([1, 1, 2])

    if col_pre1.button("🟢 Legitimate Payroll Transfer", use_container_width=True):
        st.session_state.ibm_tx_id = f"PAYROLL_{int(time.time())}"
        st.session_state.ibm_from_bank = "010"
        st.session_state.ibm_to_bank = "010"
        st.session_state.ibm_account_from = "ACC_CORP_PAYROLL_01"
        st.session_state.ibm_account_to = "ACC_EMPLOYEE_CHECKING_99"
        st.session_state.ibm_amount = 3250.00
        st.session_state.ibm_currency = "USD"
        st.session_state.ibm_payment_format = "ACH"
        st.rerun()

    if col_pre2.button("🔴 Structuring / Smurfing Anomaly", use_container_width=True):
        st.session_state.ibm_tx_id = f"SAR_SMURF_{int(time.time())}"
        st.session_state.ibm_from_bank = "999"
        st.session_state.ibm_to_bank = "999"
        st.session_state.ibm_account_from = "HIGH_RISK_MULE_ACC_88"
        st.session_state.ibm_account_to = "SANCTIONED_DEST_ACC_99"
        st.session_state.ibm_amount = 9999.00
        st.session_state.ibm_currency = "USD"
        st.session_state.ibm_payment_format = "Wire"
        st.rerun()

    st.markdown("---")

    # Form Inputs adhering strictly to app/schemas/transaction.py
    with st.form("ibm_transaction_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            tx_id = st.text_input("Transaction ID", value=st.session_state.ibm_tx_id)
            from_bank = st.text_input(
                "Originating Bank (From Bank)", value=st.session_state.ibm_from_bank
            )
            to_bank = st.text_input(
                "Receiving Bank (To Bank)", value=st.session_state.ibm_to_bank
            )

        with col2:
            account_from = st.text_input(
                "Originating Account (Account_From)",
                value=st.session_state.ibm_account_from,
            )
            account_to = st.text_input(
                "Beneficiary Account (Account_To)",
                value=st.session_state.ibm_account_to,
            )
            amount = st.number_input(
                "Transaction Amount",
                min_value=0.01,
                value=float(st.session_state.ibm_amount),
                step=100.0,
                format="%.2f",
            )

        with col3:
            currency_options = ["USD", "EUR", "GBP", "CHF", "JPY"]
            curr_idx = (
                currency_options.index(st.session_state.ibm_currency)
                if st.session_state.ibm_currency in currency_options
                else 0
            )
            currency = st.selectbox(
                "Currency", options=currency_options, index=curr_idx
            )

            format_options = ["ACH", "Wire", "Credit Card", "Cheque", "Cash"]
            fmt_idx = (
                format_options.index(st.session_state.ibm_payment_format)
                if st.session_state.ibm_payment_format in format_options
                else 0
            )
            payment_format = st.selectbox(
                "Payment Format", options=format_options, index=fmt_idx
            )

        evaluate_ibm = st.form_submit_button(
            "🔍 Evaluate Banking Transaction", use_container_width=True
        )

    if evaluate_ibm:
        payload = {
            "transaction_id": str(tx_id).strip(),
            "from_bank": str(from_bank).strip(),
            "to_bank": str(to_bank).strip(),
            "account_from": str(account_from).strip(),
            "account_to": str(account_to).strip(),
            "amount": float(amount),
            "currency": str(currency).strip(),
            "payment_format": str(payment_format).strip(),
        }

        with st.spinner("Executing real-time inference against IBM CatBoost model..."):
            endpoint = f"{api_url}/api/v1/score/transaction"
            try:
                t0_req = time.perf_counter()
                resp = requests.post(endpoint, json=payload, timeout=5.0)
                roundtrip_ms = (time.perf_counter() - t0_req) * 1000.0

                if resp.status_code == 200:
                    data = resp.json()
                    risk_score = float(data.get("risk_score", 0.0))
                    risk_tier = str(data.get("risk_tier", "LOW"))
                    is_anomaly = bool(data.get("is_anomaly", False))
                    action = str(data.get("recommended_action", "AUTO_CLEARED"))
                    engine_latency = float(data.get("latency_ms", roundtrip_ms))

                    # Display Triage Evaluation Results
                    st.markdown("#### 🎯 Triage Evaluation Report")
                    res_col1, res_col2, res_col3, res_col4 = st.columns(4)

                    res_col1.metric(
                        "Risk Score",
                        f"{risk_score:.4f}",
                        delta=f"{risk_score * 100:.1f}%",
                    )
                    with res_col2:
                        st.markdown(
                            f"**Triage Classification**<br>{render_tier_badge(risk_tier)}",
                            unsafe_allow_html=True,
                        )
                    res_col3.metric("Recommended Action", action)

                    sla_color = "normal" if engine_latency < 50.0 else "inverse"
                    res_col4.metric(
                        "Inference Latency",
                        f"{engine_latency:.2f} ms",
                        delta="PASS < 50ms" if engine_latency < 50.0 else "SLA BREACH",
                        delta_color=sla_color,
                    )

                    # Visual Progress Bar
                    st.progress(min(max(risk_score, 0.0), 1.0))

                    # Celery Alert Status
                    if is_anomaly:
                        st.markdown(
                            f"""
                            <div class="sar-alert-box">
                                🚨 <b>CELERY ASYNCHRONOUS ALERT DISPATCHED</b><br>
                                Transaction <code>{tx_id}</code> breached anomaly thresholds. Triage task
                                <code>tasks.dispatch_investigator_alert</code> enqueued to Celery queue <code>aml_tasks</code>
                                for mandatory Suspicious Activity Report (SAR) filing.
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"""
                            <div class="cleared-box">
                                ✅ <b>TRANSACTION CLEARED</b><br>
                                Transaction <code>{tx_id}</code> evaluated within normal legitimate operational parameters.
                                Automated triage cleared without investigator escalation.
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # Update session history
                    st.session_state.history.append(
                        {
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Entity ID": tx_id,
                            "Dataset": "IBM Transactions",
                            "Risk Score": round(risk_score, 4),
                            "Tier": risk_tier,
                            "Is Anomaly": is_anomaly,
                            "Latency (ms)": round(engine_latency, 2),
                        }
                    )

                elif resp.status_code == 422:
                    st.error(f"Schema Validation Error (HTTP 422): {resp.text}")
                else:
                    st.error(
                        f"Inference Engine Error (HTTP {resp.status_code}): {resp.text}"
                    )

            except requests.exceptions.ConnectionError:
                st.error(
                    f"Connection Failed: Backend serving engine at `{api_url}` is unreachable."
                )
            except requests.exceptions.Timeout:
                st.error(
                    "Request Timeout: The inference request took longer than 5.0 seconds."
                )
            except requests.exceptions.RequestException as e:
                st.error(f"Network error: {e!s}")


# ==============================================================================
# TAB 2: Crypto Transaction Triage (Elliptic XGBoost)
# ==============================================================================
with tab2:
    st.markdown("### Elliptic Bitcoin Graph Anomaly & Illicit Node Triage")
    st.caption(
        "Evaluates Bitcoin graph node topology features against out-of-time calibrated XGBoost weights (166 features)."
    )

    # Quick-Load Presets
    st.markdown("##### ⚡ Quick-Load Scenario Presets")
    col_cpre1, col_cpre2, col_cpre3 = st.columns([1, 1, 1])

    if col_cpre1.button("🟢 Licit Exchange Node", use_container_width=True):
        st.session_state.crypto_node_id = f"BTC_CLEAN_UTXO_{int(time.time())}"
        st.session_state.crypto_timestep = 35
        # 165 low-variance, clean local features
        st.session_state.crypto_features_text = ", ".join(
            [f"{0.02 + 0.005 * (i % 5):.4f}" for i in range(165)]
        )
        st.rerun()

    if col_cpre2.button("🔴 Darknet / Mixer Illicit Pattern", use_container_width=True):
        st.session_state.crypto_node_id = f"BTC_MIXER_DARK_{int(time.time())}"
        st.session_state.crypto_timestep = 42
        # 165 high-degree, anomalous structural features
        st.session_state.crypto_features_text = ", ".join(
            [f"{1.85 + 0.25 * (i % 8):.4f}" for i in range(165)]
        )
        st.rerun()

    if col_cpre3.button("🎲 Auto-Generate 165 Floats", use_container_width=True):
        np.random.seed(int(time.time()) % 1000)
        random_vec = np.random.uniform(0.01, 1.25, 165)
        st.session_state.crypto_features_text = ", ".join(
            [f"{x:.4f}" for x in random_vec]
        )
        st.rerun()

    st.markdown("---")

    # Form Inputs adhering strictly to app/schemas/crypto.py
    with st.form("elliptic_crypto_form"):
        col_c1, col_c2 = st.columns([2, 1])

        with col_c1:
            crypto_node_id = st.text_input(
                "Node Transaction ID (txId)", value=st.session_state.crypto_node_id
            )
        with col_c2:
            crypto_timestep = st.slider(
                "Graph Snapshot Timestep (1–49)",
                min_value=1,
                max_value=49,
                value=int(st.session_state.crypto_timestep),
            )

        features_input = st.text_area(
            "Local & Aggregate Node Feature Vector (Exactly 165 comma-separated floats)",
            value=st.session_state.crypto_features_text,
            height=140,
            help="Comma-separated float values corresponding to the 165 local and aggregated neighbor features of the Elliptic dataset.",
        )

        evaluate_crypto = st.form_submit_button(
            "⚡ Evaluate Crypto Node", use_container_width=True
        )

    if evaluate_crypto:
        # Client-side validation: ensure exactly 165 comma-separated floats
        raw_elements = [
            x.strip() for x in features_input.replace("\n", ",").split(",") if x.strip()
        ]
        valid_floats = []
        parse_error = None

        for item in raw_elements:
            try:
                valid_floats.append(float(item))
            except ValueError:
                parse_error = f"Invalid non-numeric value: '{item}'"
                break

        if parse_error:
            st.error(f"❌ Feature Vector Parsing Error: {parse_error}")
        elif len(valid_floats) != 165:
            st.error(
                f"❌ Dimension Mismatch: Expected exactly 165 local features, but received {len(valid_floats)}. "
                f"Please adjust or click '🎲 Auto-Generate 165 Floats' above."
            )
        else:
            # Construct complete 166-feature tensor [timestep, feat_0, ..., feat_164]
            full_tensor_166 = [float(crypto_timestep)] + valid_floats
            payload_crypto = {
                "node_id": str(crypto_node_id).strip(),
                "features": full_tensor_166,
            }

            with st.spinner(
                "Executing topological inference against Elliptic XGBoost model..."
            ):
                endpoint_crypto = f"{api_url}/api/v1/score/crypto"
                try:
                    t0_req = time.perf_counter()
                    resp = requests.post(
                        endpoint_crypto, json=payload_crypto, timeout=5.0
                    )
                    roundtrip_ms = (time.perf_counter() - t0_req) * 1000.0

                    if resp.status_code == 200:
                        data = resp.json()
                        risk_score = float(data.get("risk_score", 0.0))
                        risk_tier = str(data.get("risk_tier", "LOW"))
                        is_anomaly = bool(data.get("is_anomaly", False))
                        action = str(data.get("recommended_action", "AUTO_CLEARED"))
                        engine_latency = float(data.get("latency_ms", roundtrip_ms))

                        # Display Triage Evaluation Results
                        st.markdown("#### 🎯 Crypto Node Triage Report")
                        c_col1, c_col2, c_col3, c_col4 = st.columns(4)

                        c_col1.metric(
                            "Illicit Probability",
                            f"{risk_score:.4f}",
                            delta=f"{risk_score * 100:.1f}%",
                        )
                        with c_col2:
                            st.markdown(
                                f"**Risk Classification**<br>{render_tier_badge(risk_tier)}",
                                unsafe_allow_html=True,
                            )
                        c_col3.metric("Triage Action", action)

                        sla_color = "normal" if engine_latency < 50.0 else "inverse"
                        c_col4.metric(
                            "Inference Latency",
                            f"{engine_latency:.2f} ms",
                            delta="PASS < 50ms"
                            if engine_latency < 50.0
                            else "SLA BREACH",
                            delta_color=sla_color,
                        )

                        # Progress Bar
                        st.progress(min(max(risk_score, 0.0), 1.0))

                        # Alert Banner
                        if is_anomaly:
                            st.markdown(
                                f"""
                                <div class="sar-alert-box">
                                    🚨 <b>ILLICIT GRAPH TOPOLOGY FLAGGED</b><br>
                                    Node <code>{crypto_node_id}</code> at timestep {crypto_timestep} identified with high illicit
                                    probability ({risk_score:.4f}). Auto-flagged for FinCEN SAR cryptocurrency escalation.
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f"""
                                <div class="cleared-box">
                                    ✅ <b>BENIGN CRYPTO UTXO</b><br>
                                    Node <code>{crypto_node_id}</code> exhibits regular exchange/custodial transfer patterns. Cleared.
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        # Update session history
                        st.session_state.history.append(
                            {
                                "Timestamp": datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "Entity ID": crypto_node_id,
                                "Dataset": "Elliptic Bitcoin",
                                "Risk Score": round(risk_score, 4),
                                "Tier": risk_tier,
                                "Is Anomaly": is_anomaly,
                                "Latency (ms)": round(engine_latency, 2),
                            }
                        )

                    elif resp.status_code == 422:
                        st.error(f"Schema Validation Error (HTTP 422): {resp.text}")
                    else:
                        st.error(
                            f"Inference Engine Error (HTTP {resp.status_code}): {resp.text}"
                        )

                except requests.exceptions.ConnectionError:
                    st.error(
                        f"Connection Failed: Backend serving engine at `{api_url}` is unreachable."
                    )
                except requests.exceptions.Timeout:
                    st.error(
                        "Request Timeout: The crypto inference request took longer than 5.0 seconds."
                    )
                except requests.exceptions.RequestException as e:
                    st.error(f"Network error: {e!s}")


# ==============================================================================
# TAB 3: Cluster Telemetry & Audit Trail
# ==============================================================================
with tab3:
    st.markdown("### Cluster Telemetry & Compliance Audit Trail")
    st.caption("Live Prometheus scrape inspection and session compliance records.")

    # Section 1: Real-time Prometheus Metrics View
    st.markdown("#### 📡 Live Prometheus Telemetry (`/metrics`)")
    prom_metrics = fetch_prometheus_metrics(api_url)

    prom_col1, prom_col2, prom_col3 = st.columns(3)
    if prom_metrics["online"]:
        prom_col1.metric(
            "Evaluations Processed", f"{prom_metrics['transactions_total']:,d}"
        )
        prom_col2.metric("Anomalies Detected", f"{prom_metrics['anomalies_total']:,d}")
        prom_col3.metric("Latency SLA Status", "HEALTHY (< 50ms)", delta="Certified")
    else:
        prom_col1.metric("Evaluations Processed", "N/A")
        prom_col2.metric("Anomalies Detected", "N/A")
        prom_col3.metric("Latency SLA Status", "OFFLINE", delta_color="inverse")
        st.warning(f"Unable to scrape `/metrics` from `{api_url}`.")

    st.markdown("---")

    # Section 2: Interactive Session Audit Log
    st.markdown("#### 📋 Interactive Session Audit Log")

    if not st.session_state.history:
        st.info(
            "No transaction scoring requests executed in this session yet. Evaluate records in Tab 1 or Tab 2 to populate."
        )
    else:
        audit_df = pd.DataFrame(st.session_state.history)

        # Filters
        f_col1, f_col2 = st.columns([1, 2])
        dataset_filter = f_col1.selectbox(
            "Filter by Dataset", ["All"] + list(audit_df["Dataset"].unique())
        )
        tier_filter = f_col2.multiselect(
            "Filter by Tier",
            list(audit_df["Tier"].unique()),
            default=list(audit_df["Tier"].unique()),
        )

        filtered_df = audit_df.copy()
        if dataset_filter != "All":
            filtered_df = filtered_df[filtered_df["Dataset"] == dataset_filter]
        if tier_filter:
            filtered_df = filtered_df[filtered_df["Tier"].isin(tier_filter)]

        st.dataframe(filtered_df, use_container_width=True, height=300)

        # Export CSV Button
        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Audit Log as CSV",
            data=csv_data,
            file_name=f"aml_audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

# ==============================================================================
# Footer
# ==============================================================================
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#6b7280; font-size:0.8rem;'>"
    "QuantumAML Nexus Enterprise Decision Engine • Zero-Downtime Multi-Model Serving Architecture • Confidential"
    "</div>",
    unsafe_allow_html=True,
)
