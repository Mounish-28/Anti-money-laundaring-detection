"""
app.py
=============================================================================
QuantumAML Nexus -- 5-Dataset Benchmark Dashboard (Streamlit Host)
=============================================================================
Loads and parses five_dataset_new_evaluation_results.json across 5 financial crime datasets:
  1. IBM Transactions (CatBoost SymmetricTree + Balanced Class Weights)
  2. SAML-D (Regularized XGBoost)
  3. Elliptic Bitcoin (Optimized Topological XGBoost)
  4. IBM AMLSim (GCN + Graph Metrics + LightGBM Head)
  5. Time-Series AML (Dual-Engine XGBoost + CatBoost Lossguide)

Core Features:
  - Evaluation Metrics Extraction: Accuracy, Precision, Recall, F1-Score, ROC-AUC
  - Interactive Streamlit Comparison Table with sorting, formatting, and highlights
  - Side-by-Side Clustered Bar Charts (Plotly / Streamlit native fallback)
  - Detailed 4-Mandate Operational Framework Drilldown
=============================================================================
"""

from __future__ import annotations
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# Attempt Plotly import for enhanced interactive charts
try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Ensure repository root is in sys.path
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

BENCHMARK_RESULTS_PATH = os.path.join(ROOT_DIR, "five_dataset_new_evaluation_results.json")
REGISTRY_PATH = os.path.join(ROOT_DIR, "models", "registry.json")

# ==============================================================================
# Page Configuration & Modern Glassmorphism Styling
# ==============================================================================
st.set_page_config(
    page_title="QuantumAML Nexus | Comparative Benchmark Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .benchmark-card {
        background: linear-gradient(135deg, rgba(22, 30, 46, 0.8), rgba(15, 23, 42, 0.9));
        border: 1px solid rgba(59, 130, 246, 0.25);
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 16px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }
    .kpi-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .kpi-subtext {
        font-size: 0.75rem;
        color: #10b981;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# Data Ingestion & Parsing Engine
# ==============================================================================
@st.cache_data(ttl=300)
def load_and_parse_evaluation_results() -> Tuple[List[Dict[str, Any]], pd.DataFrame]:
    """
    Loads five_dataset_new_evaluation_results.json and parses the core evaluation
    metrics: Accuracy, Precision, Recall, F1-Score, and ROC-AUC for all 5 datasets.
    """
    if not os.path.exists(BENCHMARK_RESULTS_PATH):
        return [], pd.DataFrame()

    try:
        with open(BENCHMARK_RESULTS_PATH, "r", encoding="utf-8") as f:
            raw_json = json.load(f)
    except Exception as err:
        st.error(f"Failed to load `{BENCHMARK_RESULTS_PATH}`: {err}")
        return [], pd.DataFrame()

    parsed_rows = []
    for entry in raw_json:
        dataset_name = entry.get("Dataset", "Unknown Dataset")
        architecture = entry.get("Architecture", "Standard Classifier")
        financial_rail = entry.get("Financial_Rail", "N/A")
        primary_typology = entry.get("Primary_Typology", "N/A")

        legacy = entry.get("Legacy_Metrics", {})
        accuracy = float(legacy.get("Test_Accuracy", 0.0))
        precision = float(legacy.get("Precision", 0.0))
        recall = float(legacy.get("Recall", 0.0))
        f1_score = float(legacy.get("F1_Score", 0.0))
        roc_auc = float(legacy.get("ROC_AUC", 0.0))
        pr_auc = float(legacy.get("PR_AUC", 0.0))
        threshold = float(legacy.get("Best_Threshold", 0.5))

        parsed_rows.append({
            "Dataset": dataset_name,
            "Architecture": architecture,
            "Financial Rail": financial_rail,
            "Primary Typology": primary_typology,
            "Accuracy": accuracy,
            "Precision": precision,
            "Recall": recall,
            "F1-Score": f1_score,
            "ROC-AUC": roc_auc,
            "PR-AUC": pr_auc,
            "Operating Threshold": threshold,
        })

    df = pd.DataFrame(parsed_rows)
    return raw_json, df


raw_data, metrics_df = load_and_parse_evaluation_results()

# ==============================================================================
# Header & Navigation
# ==============================================================================
st.title("🛡️ QuantumAML Nexus | 5-Dataset Benchmark Dashboard")
st.markdown(
    "Comparative performance evaluation across 5 heterogeneous AML datasets and ensembles, "
    "tracking **Accuracy**, **Precision**, **Recall**, **F1-Score**, and **ROC-AUC**."
)

if metrics_df.empty:
    st.warning(
        f"Benchmark results file not found or empty at `{BENCHMARK_RESULTS_PATH}`. "
        "Please check the file path and rerun the evaluation scripts."
    )
    st.stop()

# ==============================================================================
# Top Metric Highlights (Best Performer Callouts)
# ==============================================================================
col_acc, col_prec, col_rec, col_f1, col_auc = st.columns(5)

best_acc_row = metrics_df.loc[metrics_df["Accuracy"].idxmax()]
best_prec_row = metrics_df.loc[metrics_df["Precision"].idxmax()]
best_rec_row = metrics_df.loc[metrics_df["Recall"].idxmax()]
best_f1_row = metrics_df.loc[metrics_df["F1-Score"].idxmax()]
best_auc_row = metrics_df.loc[metrics_df["ROC-AUC"].idxmax()]

with col_acc:
    st.markdown(
        f"""
        <div class="benchmark-card">
            <div class="kpi-title">Highest Accuracy</div>
            <div class="kpi-value">{best_acc_row['Accuracy']:.4f}</div>
            <div class="kpi-subtext">🏆 {best_acc_row['Dataset']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_prec:
    st.markdown(
        f"""
        <div class="benchmark-card">
            <div class="kpi-title">Highest Precision</div>
            <div class="kpi-value">{best_prec_row['Precision']:.4f}</div>
            <div class="kpi-subtext">🏆 {best_prec_row['Dataset']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_rec:
    st.markdown(
        f"""
        <div class="benchmark-card">
            <div class="kpi-title">Highest Recall</div>
            <div class="kpi-value">{best_rec_row['Recall']:.4f}</div>
            <div class="kpi-subtext">🏆 {best_rec_row['Dataset']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_f1:
    st.markdown(
        f"""
        <div class="benchmark-card">
            <div class="kpi-title">Highest F1-Score</div>
            <div class="kpi-value">{best_f1_row['F1-Score']:.4f}</div>
            <div class="kpi-subtext">🏆 {best_f1_row['Dataset']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_auc:
    st.markdown(
        f"""
        <div class="benchmark-card">
            <div class="kpi-title">Highest ROC-AUC</div>
            <div class="kpi-value">{best_auc_row['ROC-AUC']:.4f}</div>
            <div class="kpi-subtext">🏆 {best_auc_row['Dataset']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==============================================================================
# Interactive Sidebar Filters
# ==============================================================================
st.sidebar.header("⚙️ Dashboard Controls")

all_datasets = metrics_df["Dataset"].tolist()
selected_datasets = st.sidebar.multiselect(
    "Filter Datasets:",
    options=all_datasets,
    default=all_datasets,
)

available_metrics = ["Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC"]
selected_metrics = st.sidebar.multiselect(
    "Select Metrics for Side-by-Side Chart:",
    options=available_metrics,
    default=available_metrics,
)

chart_grouping = st.sidebar.radio(
    "Bar Chart Grouping Style:",
    options=["Group by Dataset (Side-by-Side Metrics)", "Group by Metric (Side-by-Side Datasets)"],
    index=0,
)

y_axis_scale = st.sidebar.selectbox(
    "Y-Axis Scaling:",
    options=["Dynamic Zoom (0.65 - 1.02)", "Full Scale (0.00 - 1.00)"],
    index=0,
)

filtered_df = metrics_df[metrics_df["Dataset"].isin(selected_datasets)]
if filtered_df.empty:
    st.warning("No datasets selected. Please select at least one dataset from the sidebar.")
    st.stop()

if not selected_metrics:
    selected_metrics = ["F1-Score", "ROC-AUC"]

# ==============================================================================
# SECTION 1: Interactive Streamlit Comparison Table
# ==============================================================================
st.subheader("📋 Interactive Model Performance Comparison Table")
st.markdown(
    "Interactive matrix displaying parsed evaluation metrics (**Accuracy**, **Precision**, **Recall**, "
    "**F1-Score**, and **ROC-AUC**) across all 5 benchmarked datasets. Click headers to sort."
)

table_display_df = filtered_df[[
    "Dataset",
    "Architecture",
    "Accuracy",
    "Precision",
    "Recall",
    "F1-Score",
    "ROC-AUC",
    "PR-AUC",
    "Operating Threshold",
    "Financial Rail",
]].copy()

st.dataframe(
    table_display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Dataset": st.column_config.TextColumn("Dataset", width="medium"),
        "Architecture": st.column_config.TextColumn("Production Architecture", width="large"),
        "Accuracy": st.column_config.ProgressColumn(
            "Accuracy",
            format="%.4f",
            min_value=0.0,
            max_value=1.0,
        ),
        "Precision": st.column_config.ProgressColumn(
            "Precision",
            format="%.4f",
            min_value=0.0,
            max_value=1.0,
        ),
        "Recall": st.column_config.ProgressColumn(
            "Recall",
            format="%.4f",
            min_value=0.0,
            max_value=1.0,
        ),
        "F1-Score": st.column_config.ProgressColumn(
            "F1-Score",
            format="%.4f",
            min_value=0.0,
            max_value=1.0,
        ),
        "ROC-AUC": st.column_config.ProgressColumn(
            "ROC-AUC",
            format="%.4f",
            min_value=0.0,
            max_value=1.0,
        ),
        "PR-AUC": st.column_config.NumberColumn("PR-AUC", format="%.4f"),
        "Operating Threshold": st.column_config.NumberColumn("Threshold", format="%.3f"),
        "Financial Rail": st.column_config.TextColumn("Financial Rail", width="medium"),
    },
)

# Export parsed metrics button
csv_data = table_display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Download Parsed Evaluation Metrics (CSV)",
    data=csv_data,
    file_name="five_dataset_evaluation_metrics.csv",
    mime="text/csv",
)

st.markdown("---")

# ==============================================================================
# SECTION 2: Side-by-Side Visualizations (Plotly / Streamlit)
# ==============================================================================
st.subheader("📊 Side-by-Side Performance Comparison Charts")
st.markdown(
    "Visualizing performance disparities across models with side-by-side grouped bars "
    "for direct cross-dataset benchmarking."
)

# Color Scheme for the 5 Metrics
COLOR_PALETTE = {
    "Accuracy": "#3b82f6",     # Vibrant Blue
    "Precision": "#10b981",    # Emerald Green
    "Recall": "#f59e0b",       # Amber Gold
    "F1-Score": "#8b5cf6",     # Amethyst Purple
    "ROC-AUC": "#ec4899",      # Vivid Magenta
}

y_min = 0.65 if "Dynamic Zoom" in y_axis_scale else 0.0
y_max = 1.02

if HAS_PLOTLY:
    if chart_grouping == "Group by Dataset (Side-by-Side Metrics)":
        # Grouped by Dataset on X-Axis, with side-by-side metric bars
        fig = go.Figure()
        for metric in selected_metrics:
            fig.add_trace(
                go.Bar(
                    x=filtered_df["Dataset"],
                    y=filtered_df[metric],
                    name=metric,
                    marker_color=COLOR_PALETTE.get(metric, "#64748b"),
                    text=[f"{val:.3f}" for val in filtered_df[metric]],
                    textposition="auto",
                    customdata=filtered_df[["Architecture", "Financial Rail"]].values,
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        + f"<b>{metric}:</b> %{{y:.4f}}<br>"
                        + "<b>Architecture:</b> %{customdata[0]}<br>"
                        + "<b>Financial Rail:</b> %{customdata[1]}<extra></extra>"
                    ),
                )
            )

        fig.update_layout(
            barmode="group",
            title="<b>Side-by-Side Metrics Comparison Grouped by Dataset</b>",
            xaxis_title="<b>Financial Crime Dataset / Subsystem</b>",
            yaxis_title="<b>Metric Score (0.0 - 1.0)</b>",
            yaxis=dict(range=[y_min, y_max], gridcolor="rgba(255,255,255,0.08)"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.4)",
            font=dict(color="#f1f5f9", family="sans-serif"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1.0,
                bgcolor="rgba(0,0,0,0.3)",
                bordercolor="rgba(255,255,255,0.1)",
                borderwidth=1,
            ),
            margin=dict(l=40, r=40, t=70, b=40),
            height=520,
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        # Grouped by Metric on X-Axis, with side-by-side dataset bars
        fig = go.Figure()
        dataset_colors = px.colors.qualitative.Plotly

        for i, (_, row) in enumerate(filtered_df.iterrows()):
            ds_name = row["Dataset"]
            metric_vals = [row[m] for m in selected_metrics]
            fig.add_trace(
                go.Bar(
                    x=selected_metrics,
                    y=metric_vals,
                    name=ds_name,
                    marker_color=dataset_colors[i % len(dataset_colors)],
                    text=[f"{v:.3f}" for v in metric_vals],
                    textposition="auto",
                    customdata=[row["Architecture"]] * len(selected_metrics),
                    hovertemplate=(
                        f"<b>{ds_name}</b><br>"
                        + "<b>Metric:</b> %{x}<br>"
                        + "<b>Score:</b> %{y:.4f}<br>"
                        + "<b>Architecture:</b> %{customdata}<extra></extra>"
                    ),
                )
            )

        fig.update_layout(
            barmode="group",
            title="<b>Side-by-Side Models Comparison Grouped by Metric</b>",
            xaxis_title="<b>Evaluation Metric</b>",
            yaxis_title="<b>Metric Score (0.0 - 1.0)</b>",
            yaxis=dict(range=[y_min, y_max], gridcolor="rgba(255,255,255,0.08)"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.4)",
            font=dict(color="#f1f5f9", family="sans-serif"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1.0,
                bgcolor="rgba(0,0,0,0.3)",
                bordercolor="rgba(255,255,255,0.1)",
                borderwidth=1,
            ),
            margin=dict(l=40, r=40, t=70, b=40),
            height=520,
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    # Streamlit Native Charts Fallback
    st.info("Rendering side-by-side comparison using native Streamlit charts.")
    if chart_grouping == "Group by Dataset (Side-by-Side Metrics)":
        native_chart_df = filtered_df.set_index("Dataset")[selected_metrics]
        st.bar_chart(native_chart_df, height=480)
    else:
        native_melted = filtered_df.melt(
            id_vars=["Dataset"],
            value_vars=selected_metrics,
            var_name="Metric",
            value_name="Score",
        )
        native_pivot = native_melted.pivot(index="Metric", columns="Dataset", values="Score")
        st.bar_chart(native_pivot, height=480)

# Dual-column faceted breakdowns
col_facet1, col_facet2 = st.columns(2)
with col_facet1:
    st.markdown("#### Precision vs. Recall Trade-Off")
    if HAS_PLOTLY:
        fig_pr = px.scatter(
            filtered_df,
            x="Recall",
            y="Precision",
            color="Dataset",
            size=[16] * len(filtered_df),
            text="Dataset",
            title="Precision vs. Recall Operational Frontier",
            range_x=[0.68, 1.02],
            range_y=[0.80, 1.02],
        )
        fig_pr.update_traces(textposition="top center")
        fig_pr.update_layout(
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.4)",
            font=dict(color="#f1f5f9"),
            height=380,
            margin=dict(l=30, r=30, t=50, b=30),
        )
        st.plotly_chart(fig_pr, use_container_width=True)
    else:
        st.bar_chart(filtered_df.set_index("Dataset")[["Precision", "Recall"]])

with col_facet2:
    st.markdown("#### F1-Score & ROC-AUC Discrimination Power")
    if HAS_PLOTLY:
        fig_f1_auc = go.Figure()
        fig_f1_auc.add_trace(go.Bar(
            x=filtered_df["Dataset"],
            y=filtered_df["F1-Score"],
            name="F1-Score",
            marker_color="#8b5cf6",
        ))
        fig_f1_auc.add_trace(go.Bar(
            x=filtered_df["Dataset"],
            y=filtered_df["ROC-AUC"],
            name="ROC-AUC",
            marker_color="#ec4899",
        ))
        fig_f1_auc.update_layout(
            barmode="group",
            yaxis=dict(range=[0.70, 1.02], gridcolor="rgba(255,255,255,0.08)"),
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.4)",
            font=dict(color="#f1f5f9"),
            height=380,
            margin=dict(l=30, r=30, t=50, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1.0, xanchor="right"),
        )
        st.plotly_chart(fig_f1_auc, use_container_width=True)
    else:
        st.bar_chart(filtered_df.set_index("Dataset")[["F1-Score", "ROC-AUC"]])

st.markdown("---")

# ==============================================================================
# SECTION 3: Deep-Dive 4-Mandate Analysis Accordion
# ==============================================================================
with st.expander("🏛️ Complete 4-Mandate Regulatory Analysis Deep-Dive", expanded=False):
    tab_m1, tab_m2, tab_m3, tab_m4 = st.tabs([
        "Mandate 1: Fixed Recall & Capacity",
        "Mandate 2: Rank Prioritization (P@K)",
        "Mandate 3: Financial Cost-Benefit",
        "Mandate 4: Calibration & Latency SLA",
    ])

    with tab_m1:
        st.markdown("##### Mandate 1: Operational Recall Thresholds & 20-FTE Daily Capacity")
        m1_list = []
        for entry in raw_data:
            m1 = entry.get("Mandate_1_Operational_Recall", {})
            r95 = m1.get("Target_Recall_95", {})
            r99 = m1.get("Target_Recall_99", {})
            m1_list.append({
                "Dataset": entry["Dataset"],
                "Operating Threshold (95%)": r95.get("Operating_Threshold", "N/A"),
                "Achieved Recall (95%)": f"{r95.get('Achieved_Recall', 0):.4f}",
                "FPR @ 95%": r95.get("FPR_Percentage", "N/A"),
                "Precision @ 95%": f"{r95.get('Precision_at_Recall', 0):.4f}",
                "Daily Capacity (95% / 20 FTE)": f"{r95.get('Daily_Sustainable_Tx_Capacity_20_FTE', 0):,}",
                "FPR @ 99%": r99.get("FPR_Percentage", "N/A"),
                "Daily Capacity (99% / 20 FTE)": f"{r99.get('Daily_Sustainable_Tx_Capacity_20_FTE', 0):,}",
            })
        st.dataframe(pd.DataFrame(m1_list), use_container_width=True, hide_index=True)

    with tab_m2:
        st.markdown("##### Mandate 2: Precision-at-K (P@K) & MAP@500 Top-Queue Purity")
        m2_list = []
        for entry in raw_data:
            m2 = entry.get("Mandate_2_Rank_Ordered_Prioritization", {})
            m2_list.append({
                "Dataset": entry["Dataset"],
                "P@10": f"{m2.get('P@10', 0):.4f}",
                "P@50": f"{m2.get('P@50', 0):.4f}",
                "P@100": f"{m2.get('P@100', 0):.4f}",
                "P@250": f"{m2.get('P@250', 0):.4f}",
                "P@500": f"{m2.get('P@500', 0):.4f}",
                "MAP@500": f"{m2.get('MAP@500', 0):.4f}",
                "NDCG@500": f"{m2.get('Financial_Severity_Weighted_NDCG@500', 0):.4f}",
            })
        st.dataframe(pd.DataFrame(m2_list), use_container_width=True, hide_index=True)

    with tab_m3:
        st.markdown("##### Mandate 3: Financial Cost-Benefit Optimization ($1,272.7 : 1 Cost Ratio)")
        m3_list = []
        for entry in raw_data:
            m3 = entry.get("Mandate_3_Financial_Cost_Benefit", {})
            m3_list.append({
                "Dataset": entry["Dataset"],
                "Default Loss / $1M": f"${m3.get('Default_Threshold_0_50_Loss_Per_1M_USD', 0):,.2f}",
                "Optimal Economic Threshold": f"{m3.get('Optimal_Economic_Threshold', 0):.3f}",
                "Optimized Loss / $1M": f"${m3.get('Economic_Threshold_Loss_Per_1M_USD', 0):,.2f}",
                "Net Dollar Savings": f"${m3.get('Net_Financial_Savings_Per_1M_USD', 0):,.2f}",
                "Cost Reduction (%)": m3.get("Cost_Reduction_Percentage", "N/A"),
                "FN:FP Cost Ratio": m3.get("Cost_Ratio_FN_to_FP", "1,272.7 : 1"),
            })
        st.dataframe(pd.DataFrame(m3_list), use_container_width=True, hide_index=True)

    with tab_m4:
        st.markdown("##### Mandate 4: Calibration, Stability (PSI) & Sub-50ms SLA Conformance")
        m4_list = []
        for entry in raw_data:
            m4 = entry.get("Mandate_4_Calibration_and_Stability", {})
            lat = m4.get("P95_Inference_Latency_MS", 999.0)
            m4_list.append({
                "Dataset": entry["Dataset"],
                "Pre-Calibration ECE": f"{m4.get('Pre_Calibration_ECE', 0):.4f}",
                "Post-Isotonic ECE": f"{m4.get('Post_Isotonic_ECE', 0):.4f}",
                "Brier Score": f"{m4.get('Brier_Score', 0):.4f}",
                "PSI (Drift)": f"{m4.get('Population_Stability_Index_PSI', 0):.4f}",
                "Drift Status": m4.get("Drift_Status", "NOMINAL_STABLE"),
                "P95 Latency": f"{lat:.2f} ms",
                "SLA Conformance (< 50ms)": "PASS ✅" if lat < 50.0 else "FAIL ❌",
            })
        st.dataframe(pd.DataFrame(m4_list), use_container_width=True, hide_index=True)

# Footer
st.caption(
    "QuantumAML Nexus v5.4.1 | Streamlit & Pandas Microservice | "
    "5-Dataset Benchmark Evaluation Engine"
)
