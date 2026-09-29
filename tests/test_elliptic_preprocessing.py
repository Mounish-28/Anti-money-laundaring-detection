"""
Test suite for Elliptic Bitcoin Step 2 Preprocessing & Graph Artifacts.
Validates:
1. Strict temporal partition integrity (t <= 34 vs t >= 35).
2. Zero forward-looking data leakage.
3. Zero label contamination (unlabeled nodes separated from supervision masks).
4. Feature tensor shape consistency (174 features across all 49 subgraphs).
5. Graph topology integrity (directed edge indices, node count alignment).
"""

import json
import os
import pytest
import torch
from torch_geometric.data import Data


@pytest.fixture(scope="module")
def preprocessed_artifacts():
    subgraphs_path = "data/elliptic/processed/elliptic_subgraphs_pyg.pt"
    unified_path = "data/elliptic/processed/elliptic_unified_pyg.pt"
    meta_path = "data/elliptic/processed/preprocessing_metadata.json"

    assert os.path.exists(subgraphs_path), f"Missing {subgraphs_path}"
    assert os.path.exists(unified_path), f"Missing {unified_path}"
    assert os.path.exists(meta_path), f"Missing {meta_path}"

    subgraphs = torch.load(subgraphs_path, weights_only=False)
    unified = torch.load(unified_path, weights_only=False)
    with open(meta_path, "r") as f:
        meta = json.load(f)

    return subgraphs, unified, meta


def test_subgraphs_count_and_types(preprocessed_artifacts):
    subgraphs, unified, meta = preprocessed_artifacts
    assert len(subgraphs) == 49, f"Expected 49 subgraphs, got {len(subgraphs)}"
    for idx, g in enumerate(subgraphs, start=1):
        assert isinstance(g, Data), f"Subgraph {idx} is not a PyG Data object"
        assert g.timestep == idx, f"Expected timestep {idx}, got {g.timestep}"
        assert g.x.dim() == 2, f"Subgraph {idx} x is not 2D"
        assert g.x.shape[1] == 174, f"Subgraph {idx} has {g.x.shape[1]} features, expected 174"
        assert g.edge_index.dim() == 2
        assert g.edge_index.shape[0] == 2


def test_total_nodes_and_edges_conservation(preprocessed_artifacts):
    subgraphs, unified, meta = preprocessed_artifacts
    total_subgraph_nodes = sum(g.num_nodes for g in subgraphs)
    total_subgraph_edges = sum(g.edge_index.shape[1] for g in subgraphs)

    assert total_subgraph_nodes == 203769, f"Total nodes {total_subgraph_nodes} != 203,769"
    assert total_subgraph_edges == 234355, f"Total edges {total_subgraph_edges} != 234,355"
    assert unified.num_nodes == 203769
    assert unified.edge_index.shape[1] == 234355


def test_temporal_split_integrity_and_masks(preprocessed_artifacts):
    subgraphs, unified, meta = preprocessed_artifacts

    # Unified masks
    train_mask = unified.train_mask
    test_mask = unified.test_mask
    labeled_mask = unified.labeled_mask
    unlabeled_mask = unified.unlabeled_mask
    timesteps = unified.timestep
    labels = unified.y

    # Check node counts
    assert train_mask.sum().item() == 29894, f"Train nodes {train_mask.sum().item()} != 29,894"
    assert test_mask.sum().item() == 16670, f"Test nodes {test_mask.sum().item()} != 16,670"
    assert labeled_mask.sum().item() == 46564, f"Labeled nodes {labeled_mask.sum().item()} != 46,564"
    assert unlabeled_mask.sum().item() == 157205, f"Unlabeled nodes {unlabeled_mask.sum().item()} != 157,205"

    # Zero overlap between train and test
    assert (train_mask & test_mask).sum().item() == 0, "Train and test masks overlap!"

    # Zero unlabeled nodes in train or test masks
    assert (train_mask & unlabeled_mask).sum().item() == 0, "Unlabeled nodes present in train_mask!"
    assert (test_mask & unlabeled_mask).sum().item() == 0, "Unlabeled nodes present in test_mask!"

    # Zero temporal forward leakage into train
    assert (timesteps[train_mask] > 34).sum().item() == 0, "Forward leakage: t > 34 in train_mask!"

    # Zero temporal backward leakage into test
    assert (timesteps[test_mask] <= 34).sum().item() == 0, "Backward leakage: t <= 34 in test_mask!"

    # Supervision labels validity
    assert set(labels[train_mask].tolist()).issubset({0, 1}), "Invalid labels in train split"
    assert set(labels[test_mask].tolist()).issubset({0, 1}), "Invalid labels in test split"
    assert (labels[unlabeled_mask] == -1).all(), "Unlabeled nodes do not have label -1"


def test_subgraph_per_timestep_masks(preprocessed_artifacts):
    subgraphs, unified, meta = preprocessed_artifacts

    for t, g in enumerate(subgraphs, start=1):
        if t <= 34:
            # Training timestep
            assert g.train_mask.sum().item() == g.labeled_mask.sum().item()
            assert g.test_mask.sum().item() == 0
        else:
            # Test timestep
            assert g.test_mask.sum().item() == g.labeled_mask.sum().item()
            assert g.train_mask.sum().item() == 0

        # Subgraph edges must reference nodes within [0, g.num_nodes - 1]
        if g.edge_index.shape[1] > 0:
            assert g.edge_index.min().item() >= 0
            assert g.edge_index.max().item() < g.num_nodes


def test_feature_matrix_validity_and_absence_of_nans(preprocessed_artifacts):
    subgraphs, unified, meta = preprocessed_artifacts
    assert not torch.isnan(unified.x).any(), "NaN found in unified feature tensor"
    assert not torch.isinf(unified.x).any(), "Inf found in unified feature tensor"
    assert unified.x.shape == (203769, 174)
