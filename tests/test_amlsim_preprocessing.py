"""
tests/test_amlsim_preprocessing.py
=============================================================================
Verification & Integrity Tests for AMLSim Graph Preprocessing,
Sparse Tensor Serialization, and Zero-Leakage Protocols.
=============================================================================
"""

import json
import os
import pytest
import torch
from torch_geometric.data import Data
import joblib


@pytest.fixture(scope="module")
def paths():
    return {
        "pyg": "data/ibm_amlsim/processed/amlsim_pyg_data.pt",
        "sparse": "data/ibm_amlsim/processed/amlsim_sparse_tensors.pt",
        "scaler": "data/ibm_amlsim/processed/amlsim_node_scaler.joblib",
        "report": "experiments/AMLSim/preprocessing_report.json",
    }


def test_files_exist_and_non_empty(paths):
    """Verify that all packaged artifacts and reports were generated and are non-empty."""
    for name, path in paths.items():
        assert os.path.exists(path), f"Artifact missing: {path}"
        assert os.path.getsize(path) > 0, f"Artifact empty: {path}"


def test_pyg_tensor_integrity(paths):
    """Verify the structural integrity, shapes, and types of PyG Data."""
    data = torch.load(paths["pyg"], weights_only=False)
    assert isinstance(data, Data), "Loaded object is not a PyG Data instance"

    # Node count and feature dimension
    assert data.num_nodes == 10000, f"Expected 10,000 nodes, got {data.num_nodes}"
    assert data.x.shape == (10000, 15), f"Expected shape (10000, 15), got {data.x.shape}"
    assert not torch.isnan(data.x).any(), "NaN values found in node feature tensor"
    assert not torch.isinf(data.x).any(), "Inf values found in node feature tensor"

    # Edge index and attributes
    assert data.edge_index.shape[0] == 2, "Edge index must have shape [2, E]"
    assert data.edge_index.shape[1] == 1323234, f"Expected 1,323,234 edges, got {data.edge_index.shape[1]}"
    assert data.edge_attr.shape == (1323234, 2), f"Expected edge_attr (1323234, 2), got {data.edge_attr.shape}"
    assert data.edge_time.shape == (1323234,), f"Expected edge_time (1323234,), got {data.edge_time.shape}"

    # Labels
    assert data.y.shape == (10000,), f"Expected y shape (10000,), got {data.y.shape}"
    assert set(data.y.unique().tolist()).issubset({0, 1}), "y labels must be binary {0, 1}"
    assert data.y_edge.shape == (1323234,), f"Expected y_edge shape (1323234,), got {data.y_edge.shape}"


def test_zero_node_label_leakage(paths):
    """Verify that train, validation, and test node masks are strictly disjoint and sum to N."""
    data = torch.load(paths["pyg"], weights_only=False)
    train_m = data.train_mask
    val_m = data.val_mask
    test_m = data.test_mask

    # Disjointness checks
    assert not (train_m & val_m).any(), "Overlap detected between train_mask and val_mask!"
    assert not (train_m & test_m).any(), "Overlap detected between train_mask and test_mask!"
    assert not (val_m & test_m).any(), "Overlap detected between val_mask and test_mask!"

    # Completeness check
    total_masked = (train_m | val_m | test_m).sum().item()
    assert total_masked == 10000, f"Expected 10,000 masked nodes, got {total_masked}"
    assert train_m.sum().item() == 7000
    assert val_m.sum().item() == 1500
    assert test_m.sum().item() == 1500


def test_chronological_edge_masking(paths):
    """Verify edge masks strictly follow timestamp partitions (Train <= 139, Val <= 169, Test >= 170)."""
    data = torch.load(paths["pyg"], weights_only=False)
    edge_time = data.edge_time
    e_train = data.edge_train_mask
    e_val = data.edge_val_mask
    e_test = data.edge_test_mask

    # Time boundaries
    assert (edge_time[e_train] <= 139).all(), "Train edge mask contains future edges (>139)!"
    assert (edge_time[e_val] >= 140).all() and (edge_time[e_val] <= 169).all(), "Val edges violate boundary!"
    assert (edge_time[e_test] >= 170).all(), "Test edges contain historical edges (<170)!"

    # Total edge partition completeness
    assert (e_train.sum() + e_val.sum() + e_test.sum()).item() == 1323234


def test_sparse_tensor_formats(paths):
    """Verify sparse COO and CSR adjacency tensor constructions."""
    pkg = torch.load(paths["sparse"], weights_only=False)
    assert "adj_sparse_coo" in pkg
    assert "adj_sparse_csr" in pkg
    assert "train_adj_sparse_coo" in pkg
    assert "train_adj_sparse_csr" in pkg

    adj_coo = pkg["adj_sparse_coo"]
    assert adj_coo.is_sparse
    assert adj_coo.shape == (10000, 10000)

    train_adj = pkg["train_adj_sparse_coo"]
    assert train_adj.is_sparse
    assert train_adj.shape == (10000, 10000)
    assert train_adj._nnz() <= adj_coo._nnz(), "Train adjacency cannot have more non-zeros than full graph!"


def test_report_metrics_validity(paths):
    """Verify preprocessing JSON report content and values."""
    with open(paths["report"], "r") as f:
        rep = json.load(f)

    assert rep["dataset"] == "IBM AMLSim"
    assert rep["stage_1_profiling"]["accounts"]["total_count"] == 10000
    assert rep["stage_1_profiling"]["transactions"]["total_count"] == 1323234
    assert rep["stage_2_topology"]["nodes"] == 10000
    assert rep["stage_2_topology"]["directed_edges"] == 68947
    assert rep["stage_3_anomalies"]["active_fraud_nodes"] == 1639
    assert rep["stage_4_packaging"]["anti_leakage_guarantees"]["chronological_split"] is True
