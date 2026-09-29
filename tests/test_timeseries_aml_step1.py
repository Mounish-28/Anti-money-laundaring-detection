"""
tests/test_timeseries_aml_step1.py
=============================================================================
Verification of Time-Series AML Step 1: Ingestion, Schema Standardization,
Temporal Window Profiling, Dynamic Network Construction & Leakage-Free Partitions.
=============================================================================
"""

import json
import os
import pytest


@pytest.fixture(scope="module")
def paths():
    return {
        "report": "experiments/TimeSeries-AML/step1_profiling_report.json",
        "splits": "data/timeseries_aml/processed/temporal_split_indices.json",
    }


def test_step1_artifacts_exist(paths):
    """Verify that report and partition files exist and are non-empty."""
    for name, path in paths.items():
        assert os.path.exists(path), f"File missing: {path}"
        assert os.path.getsize(path) > 0, f"File empty: {path}"


def test_schema_standardization_metrics(paths):
    """Verify schema standardization telemetry."""
    with open(paths["report"], "r") as f:
        data = json.load(f)

    assert data["dataset"] == "Time-Series of Transactions in AML"
    schema = data["schema_standardization"]
    assert schema["total_records_ingested"] >= 100000
    assert schema["unique_accounts"] > 100
    assert schema["inflows_count"] > 0
    assert schema["outflows_count"] > 0


def test_temporal_continuity_no_gaps(paths):
    """Verify that the temporal horizon is continuous with zero reporting gaps."""
    with open(paths["report"], "r") as f:
        data = json.load(f)

    temporal = data["temporal_window_profiling"]
    assert temporal["is_continuous"] is True
    assert temporal["missing_steps_count"] == 0
    assert temporal["total_timesteps"] > 200


def test_dynamic_network_snapshots(paths):
    """Verify that dynamic network snapshots were constructed across multiple days."""
    with open(paths["report"], "r") as f:
        data = json.load(f)

    net = data["dynamic_network_topology"]
    assert net["snapshots_evaluated"] >= 3
    assert len(net["snapshots"]) >= 3
    assert net["snapshots"][0]["active_nodes"] > 0
    assert net["snapshots"][0]["directed_edges"] > 0


def test_leakage_safe_partitioning(paths):
    """Verify strict chronological boundaries without backward overlap."""
    with open(paths["splits"], "r") as f:
        splits = json.load(f)

    train_bounds = splits["train_step_bounds"]
    val_bounds = splits["val_step_bounds"]
    test_bounds = splits["test_step_bounds"]

    # Strict forward progression
    assert train_bounds[1] < val_bounds[0], "Train overlaps with Val in time!"
    assert val_bounds[1] < test_bounds[0], "Val overlaps with Test in time!"
    assert splits["train_size"] > 0
    assert splits["val_size"] > 0
    assert splits["test_size"] > 0
