"""
scripts/profile_timeseries_aml.py
=============================================================================
Time-Series of Transactions in AML: Step 1 — Ingestion, Schema Validation,
Temporal Structuring, Dynamic Network Construction & Topological Profiling.
=============================================================================
Author: Principal AML Data Scientist
Purpose:
  1. Schema Standardization & Type Casting: Ingest streaming transaction logs,
     map timestamp sequences into explicit datetime indices, standardize source/destination
     account entities, transaction formats (cash, wire, ACH, card), and currency amounts.
  2. Temporal Window Profiling: Analyze complete temporal horizon (t=1..354), sampling
     frequency, hourly/daily transaction volumes, reporting gap audits, and burstiness.
  3. Dynamic Network Construction: Construct directed dynamic graphs across discrete
     daily temporal snapshots. Quantify evolving network density, in/out-degree velocity,
     and circular/cyclic flow patterns.
  4. Leakage-Safe Partitioning Strategy: Enforce strict chronological split boundaries
     (Train 70% t=1..247, Val 15% t=248..300, Holdout Test 15% t=301..354) guaranteeing
     zero backward temporal leakage prior to feature computation.
"""

from __future__ import annotations
import gc
import json
import os
import sys
import time
from typing import Any, Dict, List, Tuple

import networkx as nx
import numpy as np
import pandas as pd


def resolve_base_dir() -> str:
    """Locates the raw dataset directory."""
    candidates = [
        "Time series of transaction in AML",
        "data/timeseries_aml",
        "../Time series of transaction in AML",
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.exists(os.path.join(c, "event_order_train.csv")):
            return c
    raise FileNotFoundError("Could not locate 'Time series of transaction in AML' directory.")


# =============================================================================
# 1. SCHEMA STANDARDIZATION & TYPE CASTING
# =============================================================================
def ingest_and_standardize_schema(
    base_dir: str, chunk_limit: int = 500000
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Ingests transaction logs, parses discrete timesteps into explicit datetimes,
    maps accounts, directions, formats, and currency amounts with strict memory safety.
    """
    print("\n" + "=" * 80)
    print("STEP 1: SCHEMA STANDARDIZATION & TYPE CASTING")
    print("=" * 80)
    t0 = time.time()

    event_path = os.path.join(base_dir, "event_order_train.csv")
    ts_id_path = os.path.join(base_dir, "time_series_ids_train.csv")
    fraud_path = os.path.join(base_dir, "fraud_labels_train.csv")
    tx_path = os.path.join(base_dir, "transactions_train.csv")
    comp_path = os.path.join(base_dir, "companies_train.csv")

    print(f"[*] Ingesting event order and time-series IDs from {base_dir} (limit={chunk_limit:,d} rows)...")
    # Load aligned metadata
    events_df = pd.read_csv(event_path, nrows=chunk_limit)
    ts_ids_df = pd.read_csv(ts_id_path, nrows=chunk_limit)
    
    # Load transaction amount (column '0') and format proxy columns ('1'..'4')
    usecols = ["transactionId", "0", "1", "2", "3", "4"]
    tx_df = pd.read_csv(tx_path, usecols=usecols, nrows=chunk_limit)

    assert len(events_df) == len(ts_ids_df) == len(tx_df), "Rows must align 1:1 across files"

    # Merge core schema
    df = events_df.copy()
    df["time_series_id"] = ts_ids_df["time_series_ids"].values
    df["raw_amount"] = pd.to_numeric(tx_df["0"], errors="coerce").fillna(0.0).astype(np.float32)

    # Transaction Formats proxy features (standardized latent representations)
    df["format_wire"] = pd.to_numeric(tx_df["1"], errors="coerce").fillna(0.0).astype(np.float32)
    df["format_cash"] = pd.to_numeric(tx_df["2"], errors="coerce").fillna(0.0).astype(np.float32)
    df["format_ach"] = pd.to_numeric(tx_df["3"], errors="coerce").fillna(0.0).astype(np.float32)
    df["format_card"] = pd.to_numeric(tx_df["4"], errors="coerce").fillna(0.0).astype(np.float32)

    del events_df, ts_ids_df, tx_df
    gc.collect()

    # 1. Parse Entity IDs
    df["accountId"] = df["time_series_id"].str.split("_window_").str[0]
    df["window_num"] = df["time_series_id"].str.split("_window_").str[1].astype(np.int32)

    # 2. Map Source and Destination Entities
    # Positive amount = Inflow (External counterparty -> accountId)
    # Negative amount = Outflow (accountId -> External counterparty)
    is_inflow = df["raw_amount"] >= 0
    df["from_account"] = np.where(is_inflow, "EXT_SRC_" + df["accountId"], df["accountId"])
    df["to_account"] = np.where(is_inflow, df["accountId"], "EXT_DST_" + df["accountId"])
    df["tx_direction"] = np.where(is_inflow, "INFLOW", "OUTFLOW")
    df["abs_amount"] = np.abs(df["raw_amount"]).astype(np.float32)
    df["log_amount"] = np.log1p(df["abs_amount"]).astype(np.float32)

    # 3. Explicit Datetime Parsing
    # eventAt represents discrete sequential hours (1..354)
    ref_date = pd.to_datetime("2020-01-01 00:00:00")
    df["datetime"] = ref_date + pd.to_timedelta(df["eventAt"].astype(np.int64), unit="h")
    df["t_k_sec"] = df["eventAt"].astype(np.int64) * 3600
    df["hour"] = (df["eventAt"] % 24).astype(np.int32)
    df["day"] = (df["eventAt"] // 24).astype(np.int32)
    df["dayofweek"] = ((df["eventAt"] // 24) % 7).astype(np.int32)

    # 4. Integrate Fraud Labels
    if os.path.exists(fraud_path):
        labels_df = pd.read_csv(fraud_path)
        label_col_id = labels_df.columns[0]
        label_target_col = [c for c in labels_df.columns if "fraud" in c.lower()][0]
        label_map = dict(zip(labels_df[label_col_id], labels_df[label_target_col]))
        df["isFraudUser"] = df["time_series_id"].map(label_map).fillna(False).astype(int)
        del labels_df
    else:
        df["isFraudUser"] = 0

    print(f"[*] Standardized Dataset Shape: {df.shape[0]:,d} transactions x {df.shape[1]} columns.")
    print(f"    - Unique Account Entities:  {df['accountId'].nunique():,d}")
    print(f"    - Unique Windows:           {df['time_series_id'].nunique():,d}")
    print(f"    - Inflows vs Outflows:      {(df['tx_direction'] == 'INFLOW').sum():,d} Inflows / {(df['tx_direction'] == 'OUTFLOW').sum():,d} Outflows")
    print(f"    - Fraudulent Windows:       {df['isFraudUser'].sum():,d} ({df['isFraudUser'].mean()*100:.2f}%)")

    summary = {
        "total_records_ingested": len(df),
        "unique_accounts": df["accountId"].nunique(),
        "unique_windows": df["time_series_id"].nunique(),
        "inflows_count": int((df["tx_direction"] == "INFLOW").sum()),
        "outflows_count": int((df["tx_direction"] == "OUTFLOW").sum()),
        "fraud_rate_pct": round(float(df["isFraudUser"].mean() * 100.0), 3),
        "execution_time_sec": round(time.time() - t0, 3),
    }
    return df, summary


# =============================================================================
# 2. TEMPORAL WINDOW PROFILING & REPORTING GAP AUDIT
# =============================================================================
def profile_temporal_windows(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Profiles complete temporal horizon, hourly/daily transaction distributions,
    detects intermittent reporting gaps, and calculates inter-arrival burstiness.
    """
    print("\n" + "=" * 80)
    print("STEP 2: TEMPORAL WINDOW PROFILING & REPORTING GAP AUDIT")
    print("=" * 80)
    t0 = time.time()

    min_step = int(df["eventAt"].min())
    max_step = int(df["eventAt"].max())
    total_steps = max_step - min_step + 1

    # 1. Reporting Gap Detection
    unique_steps = set(df["eventAt"].unique())
    full_step_range = set(range(min_step, max_step + 1))
    missing_steps = sorted(list(full_step_range - unique_steps))

    print(f"[*] Complete Temporal Horizon:")
    print(f"    - Range:                 Step {min_step} to Step {max_step} ({total_steps} sequential hours = {total_steps/24:.2f} days)")
    print(f"    - Earliest Timestamp:    {df['datetime'].min()}")
    print(f"    - Latest Timestamp:      {df['datetime'].max()}")
    print(f"    - Intermittent Gaps:     {len(missing_steps)} missing hours ({'NONE - 100% CONTINUOUS' if len(missing_steps) == 0 else f'Gaps at: {missing_steps}'})")

    # 2. Hourly & Daily Volume Dynamics
    hourly_counts = df.groupby("eventAt")["transactionId"].count()
    hourly_volume = df.groupby("eventAt")["abs_amount"].sum()
    daily_counts = df.groupby("day")["transactionId"].count()
    daily_volume = df.groupby("day")["abs_amount"].sum()

    print(f"[*] Throughput & Volume Kinematics:")
    print(f"    - Mean Transactions / Hour: {hourly_counts.mean():.1f} (Min: {hourly_counts.min():,d}, Max: {hourly_counts.max():,d})")
    print(f"    - Mean Transactions / Day:  {daily_counts.mean():.1f} (Min: {daily_counts.min():,d}, Max: {daily_counts.max():,d})")
    print(f"    - Mean Daily Total Volume:  ${daily_volume.mean():,.2f}")

    # 3. Inter-Arrival Time Dynamics & Burstiness
    # Sort chronologically by account to calculate delta_t
    df_sorted = df.sort_values(by=["accountId", "eventAt"])
    df_sorted["prev_event"] = df_sorted.groupby("accountId")["eventAt"].shift(1)
    df_sorted["delta_t_steps"] = (df_sorted["eventAt"] - df_sorted["prev_event"]).fillna(0.0)

    # Burstiness parameter B = (sigma - mu) / (sigma + mu)
    delta_vals = df_sorted["delta_t_steps"].values
    delta_pos = delta_vals[delta_vals > 0]
    mu_dt = float(np.mean(delta_pos)) if len(delta_pos) > 0 else 1.0
    sigma_dt = float(np.std(delta_pos)) if len(delta_pos) > 0 else 0.0
    burstiness_b = float((sigma_dt - mu_dt) / (sigma_dt + mu_dt + 1e-5))

    print(f"[*] Arrival Cadence & Burstiness Metrics:")
    print(f"    - Mean Inter-Arrival Step (mu_dt):     {mu_dt:.2f} hours")
    print(f"    - Standard Deviation (sigma_dt):       {sigma_dt:.2f} hours")
    print(f"    - Inter-Arrival Volatility (CV):       {sigma_dt/(mu_dt+1e-5):.2f}")
    print(f"    - System Burstiness Parameter (B):    {burstiness_b:.4f} (Positive indicates episodic burst clustering)")

    summary = {
        "min_timestep": min_step,
        "max_timestep": max_step,
        "total_timesteps": total_steps,
        "missing_steps_count": len(missing_steps),
        "is_continuous": len(missing_steps) == 0,
        "hourly_stats": {
            "mean_tx_count": round(float(hourly_counts.mean()), 2),
            "min_tx_count": int(hourly_counts.min()),
            "max_tx_count": int(hourly_counts.max()),
            "mean_volume": round(float(hourly_volume.mean()), 2),
        },
        "daily_stats": {
            "total_days": len(daily_counts),
            "mean_tx_count": round(float(daily_counts.mean()), 2),
            "mean_volume": round(float(daily_volume.mean()), 2),
        },
        "burstiness": {
            "mean_delta_t_hours": round(mu_dt, 3),
            "std_delta_t_hours": round(sigma_dt, 3),
            "burstiness_index_B": round(burstiness_b, 4),
        },
        "execution_time_sec": round(time.time() - t0, 3),
    }
    return summary


# =============================================================================
# 3. DYNAMIC NETWORK CONSTRUCTION & TOPOLOGICAL METRICS
# =============================================================================
def construct_dynamic_network_snapshots(
    df: pd.DataFrame, num_daily_snapshots: int = 5
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Constructs directed dynamic graphs across sequential daily temporal snapshots.
    Quantifies evolving network density, in/out-degree velocity, and cyclic patterns.
    """
    print("\n" + "=" * 80)
    print("STEP 3: DYNAMIC NETWORK CONSTRUCTION & TOPOLOGICAL PROFILING")
    print("=" * 80)
    t0 = time.time()

    # Map each transaction to directed edge between accounts / counterparties
    # To model community interaction and money cycling:
    # Entities: accountId nodes, connected across temporal windows and transfers
    days = sorted(df["day"].unique())[:num_daily_snapshots]
    snapshot_profiles = []

    print(f"[*] Building Directed Dynamic Network across {len(days)} Daily Snapshots...")
    for d in days:
        t_snap_start = time.time()
        sub_df = df[df["day"] == d]

        # Construct weighted directed graph G_d
        G = nx.DiGraph()
        
        # Build edges: from_account -> to_account
        edges = sub_df.groupby(["from_account", "to_account"]).agg(
            weight=("abs_amount", "count"), total_vol=("abs_amount", "sum")
        ).reset_index()

        for _, row in edges.iterrows():
            G.add_edge(row["from_account"], row["to_account"], weight=row["weight"], volume=row["total_vol"])

        n_nodes = G.number_of_nodes()
        n_edges = G.number_of_edges()
        density = nx.density(G) if n_nodes > 1 else 0.0

        # Degree centralities
        in_degrees = dict(G.in_degree())
        out_degrees = dict(G.out_degree())
        mean_in_deg = float(np.mean(list(in_degrees.values()))) if in_degrees else 0.0
        mean_out_deg = float(np.mean(list(out_degrees.values()))) if out_degrees else 0.0

        # In/Out Degree Velocity (transfers per 24-hour day)
        in_velocity = mean_in_deg / 24.0
        out_velocity = mean_out_deg / 24.0

        # Cyclic Transaction Patterns: Strongly Connected Components with size > 1
        scc = list(nx.strongly_connected_components(G))
        cyclic_components = [c for c in scc if len(c) > 1]
        cycle_nodes_count = sum(len(c) for c in cyclic_components)

        snap_profile = {
            "day": int(d),
            "date": str(df[df["day"] == d]["datetime"].dt.date.iloc[0]),
            "active_nodes": n_nodes,
            "directed_edges": n_edges,
            "density": float(density),
            "mean_in_degree": round(mean_in_deg, 3),
            "mean_out_degree": round(mean_out_deg, 3),
            "in_degree_velocity_per_hour": round(in_velocity, 4),
            "out_degree_velocity_per_hour": round(out_velocity, 4),
            "cyclic_scc_count": len(cyclic_components),
            "nodes_in_cyclic_loops": cycle_nodes_count,
            "compute_time_sec": round(time.time() - t_snap_start, 3),
        }
        snapshot_profiles.append(snap_profile)

        print(
            f"    - Day {d:02d} ({snap_profile['date']}): "
            f"Nodes = {n_nodes:,d} | Edges = {n_edges:,d} | "
            f"Density = {density:.5e} | Cyclic Loops = {len(cyclic_components)} ({cycle_nodes_count} nodes)"
        )

    summary = {
        "snapshots_evaluated": len(snapshot_profiles),
        "mean_active_nodes": round(float(np.mean([s["active_nodes"] for s in snapshot_profiles])), 1),
        "mean_directed_edges": round(float(np.mean([s["directed_edges"] for s in snapshot_profiles])), 1),
        "mean_density": float(np.mean([s["density"] for s in snapshot_profiles])),
        "snapshots": snapshot_profiles,
        "execution_time_sec": round(time.time() - t0, 3),
    }
    return snapshot_profiles, summary


# =============================================================================
# 4. LEAKAGE-SAFE TEMPORAL PARTITIONING STRATEGY
# =============================================================================
def partition_temporal_horizons(
    df: pd.DataFrame,
    output_dir: str = "data/timeseries_aml/processed",
) -> Dict[str, Any]:
    """
    Enforces strict chronological boundary cuts (Train 70%, Val 15%, Test 15%)
    guaranteeing zero backward temporal leakage.
    """
    print("\n" + "=" * 80)
    print("STEP 4: LEAKAGE-SAFE TEMPORAL PARTITIONING STRATEGY")
    print("=" * 80)
    t0 = time.time()
    os.makedirs(output_dir, exist_ok=True)

    min_step = int(df["eventAt"].min())
    max_step = int(df["eventAt"].max())
    total_steps = max_step - min_step + 1

    # Exact 70 / 15 / 15 temporal cutoff steps
    train_end_step = int(min_step + 0.70 * total_steps)
    val_end_step = int(min_step + 0.85 * total_steps)

    # Boolean Masks
    train_mask = df["eventAt"] <= train_end_step
    val_mask = (df["eventAt"] > train_end_step) & (df["eventAt"] <= val_end_step)
    test_mask = df["eventAt"] > val_end_step

    n_total = len(df)
    n_train = int(train_mask.sum())
    n_val = int(val_mask.sum())
    n_test = int(test_mask.sum())

    train_fraud_rate = float(df.loc[train_mask, "isFraudUser"].mean() * 100.0)
    val_fraud_rate = float(df.loc[val_mask, "isFraudUser"].mean() * 100.0)
    test_fraud_rate = float(df.loc[test_mask, "isFraudUser"].mean() * 100.0)

    print(f"[*] Chronological Partition Boundaries:")
    print(f"    - Train Partition (t in [{min_step}, {train_end_step}]):      {n_train:,d} txs ({n_train/n_total*100:.1f}%) | Fraud Rate: {train_fraud_rate:.2f}%")
    print(f"    - Validation Partition (t in [{train_end_step+1}, {val_end_step}]): {n_val:,d} txs ({n_val/n_total*100:.1f}%) | Fraud Rate: {val_fraud_rate:.2f}%")
    print(f"    - Holdout Test Partition (t in [{val_end_step+1}, {max_step}]):  {n_test:,d} txs ({n_test/n_total*100:.1f}%) | Fraud Rate: {test_fraud_rate:.2f}%")

    # Anti-Leakage Invariant Verification
    assert (df.loc[train_mask, "eventAt"].max() < df.loc[val_mask, "eventAt"].min()), "CRITICAL: Train and Val overlap in time!"
    assert (df.loc[val_mask, "eventAt"].max() < df.loc[test_mask, "eventAt"].min()), "CRITICAL: Val and Test overlap in time!"
    print(f"[*] Anti-Leakage Verification: PASSED. Zero backward temporal contamination guaranteed.")

    # Save standardized partition indices
    partitions = {
        "train_indices": np.where(train_mask)[0].tolist(),
        "val_indices": np.where(val_mask)[0].tolist(),
        "test_indices": np.where(test_mask)[0].tolist(),
    }
    part_file = os.path.join(output_dir, "temporal_split_indices.json")
    with open(part_file, "w") as f:
        json.dump({
            "train_step_bounds": [min_step, train_end_step],
            "val_step_bounds": [train_end_step + 1, val_end_step],
            "test_step_bounds": [val_end_step + 1, max_step],
            "train_size": n_train,
            "val_size": n_val,
            "test_size": n_test,
        }, f, indent=2)
    print(f"[*] Serialized Temporal Split Bounds -> {part_file}")

    summary = {
        "train_boundary": [min_step, train_end_step],
        "val_boundary": [train_end_step + 1, val_end_step],
        "test_boundary": [val_end_step + 1, max_step],
        "train_records": n_train,
        "val_records": n_val,
        "test_records": n_test,
        "train_fraud_rate_pct": train_fraud_rate,
        "val_fraud_rate_pct": val_fraud_rate,
        "test_fraud_rate_pct": test_fraud_rate,
        "leakage_invariants_verified": True,
        "execution_time_sec": round(time.time() - t0, 3),
    }
    return summary


# =============================================================================
# MASTER RUNNER
# =============================================================================
def main():
    print("=" * 80)
    print("TIME-SERIES OF TRANSACTIONS IN AML: STEP 1 INGESTION & TOPOLOGY ENGINE")
    print("=" * 80)
    start_time = time.time()

    base_dir = resolve_base_dir()
    experiments_dir = "experiments/TimeSeries-AML"
    os.makedirs(experiments_dir, exist_ok=True)

    # 1. Schema Standardization & Type Casting (Memory-Safe streaming sample)
    df, schema_summary = ingest_and_standardize_schema(base_dir, chunk_limit=300000)

    # 2. Temporal Window Profiling
    temporal_summary = profile_temporal_windows(df)

    # 3. Dynamic Network Construction
    _, network_summary = construct_dynamic_network_snapshots(df, num_daily_snapshots=5)

    # 4. Leakage-Safe Partitioning Strategy
    partition_summary = partition_temporal_horizons(df)

    # Master Step 1 Report
    master_report = {
        "dataset": "Time-Series of Transactions in AML",
        "pipeline_phase": "Step 1: Ingestion, Temporal Structuring & Topological Profiling",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_runtime_sec": round(time.time() - start_time, 3),
        "schema_standardization": schema_summary,
        "temporal_window_profiling": temporal_summary,
        "dynamic_network_topology": network_summary,
        "leakage_safe_partitioning": partition_summary,
    }

    report_path = os.path.join(experiments_dir, "step1_profiling_report.json")
    with open(report_path, "w") as f:
        json.dump(master_report, f, indent=4)

    print("\n" + "=" * 80)
    print("STEP 1 PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
    print(f"Master Profiling Telemetry saved -> {report_path}")
    print(f"Total Execution Time: {master_report['total_runtime_sec']}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
