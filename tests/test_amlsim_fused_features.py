"""
tests/test_amlsim_fused_features.py
=============================================================================
Verification of Feature Fusion, Inductive GCN Topo Embeddings, Cleansing,
and Leakage-Free Sparse Tensors for IBM AMLSim.
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
        "pyg": "data/ibm_amlsim/processed/amlsim_fused_pyg_data.pt",
        "sparse": "data/ibm_amlsim/processed/amlsim_fused_sparse_tensors.pt",
        "imputer": "data/ibm_amlsim/processed/amlsim_feature_imputer.joblib",
        "scaler": "data/ibm_amlsim/processed/amlsim_robust_scaler.joblib",
        "report": "experiments/AMLSim/fused_feature_spec_report.json",
    }


def test_artifacts_exist_and_non_empty(paths):
    """Verify all fused pipeline artifacts exist and have non-zero file size."""
    for name, path in paths.items():
        assert os.path.exists(path), f"Artifact missing: {path}"
        assert os.path.getsize(path) > 0, f"Artifact empty: {path}"


def test_fused_feature_dimensions(paths):
    """Verify the fused node feature matrix has 56 dimensions (24 tabular + 32 GCN topo)."""
    data = torch.load(paths["pyg"], weights_only=False)
    assert isinstance(data, Data)
    assert data.x.shape == (10000, 56), f"Expected shape (10000, 56), got {data.x.shape}"
    assert not torch.isnan(data.x).any(), "NaN values found in fused feature matrix"
    assert not torch.isinf(data.x).any(), "Inf values found in fused feature matrix"


def test_sparse_tensor_package(paths):
    """Verify sparse COO and CSR tensors in the fused package."""
    pkg = torch.load(paths["sparse"], weights_only=False)
    assert pkg["x"].shape == (10000, 56)
    assert pkg["adj_sparse_coo"].is_sparse
    assert pkg["adj_sparse_coo"].shape == (10000, 10000)
    assert pkg["adj_sparse_csr"].is_sparse_csr
    assert pkg["train_adj_sparse_coo"].is_sparse
    assert pkg["train_adj_sparse_csr"].is_sparse_csr


def test_imputer_and_scaler_validity(paths):
    """Verify imputer and scaler were fitted on 24 tabular features."""
    imputer = joblib.load(paths["imputer"])
    scaler = joblib.load(paths["scaler"])
    assert imputer.statistics_.shape == (24,)
    assert scaler.center_.shape == (24,)
    assert scaler.scale_.shape == (24,)


def test_zero_leakage_and_mask_purity(paths):
    """Verify that node masks are disjoint and edge masks preserve temporal ordering."""
    data = torch.load(paths["pyg"], weights_only=False)
    tm, vm, testm = data.train_mask, data.val_mask, data.test_mask

    # Disjointness
    assert not (tm & vm).any()
    assert not (tm & testm).any()
    assert not (vm & testm).any()
    assert (tm | vm | testm).sum().item() == 10000

    # Temporal bounds
    assert (data.edge_time[data.edge_train_mask] <= 139).all()
    assert (data.edge_time[data.edge_val_mask] >= 140).all() and (data.edge_time[data.edge_val_mask] <= 169).all()
    assert (data.edge_time[data.edge_test_mask] >= 170).all()
