"""Unit tests for Elliptic Bitcoin Step 3 Graph Neural Network architecture,
residual blocks, masking mechanisms, and imbalance-aware loss functions.
"""

import json
import os
import pytest
import torch
from scripts.tune_elliptic_gnn import (
    ResidualSAGEBlock,
    EllipticGraphSAGE,
    BinaryFocalLoss,
    WeightedBCELoss,
)


def test_residual_sage_block_dimensions():
    """Verify that ResidualSAGEBlock handles same-dimension and dimension-changing projections."""
    num_nodes = 50
    edge_index = torch.randint(0, num_nodes, (2, 120), dtype=torch.long)

    # 1. Dimension change: in_channels=174 -> out_channels=128
    block_proj = ResidualSAGEBlock(in_channels=174, out_channels=128, dropout=0.2)
    x_in = torch.randn(num_nodes, 174)
    out_proj = block_proj(x_in, edge_index)
    assert out_proj.shape == (num_nodes, 128), f"Expected (50, 128), got {out_proj.shape}"

    # 2. Identity residual: in_channels=128 -> out_channels=128
    block_id = ResidualSAGEBlock(in_channels=128, out_channels=128, dropout=0.2)
    x_mid = torch.randn(num_nodes, 128)
    out_id = block_id(x_mid, edge_index)
    assert out_id.shape == (num_nodes, 128), f"Expected (50, 128), got {out_id.shape}"
    assert isinstance(block_id.res_proj, torch.nn.Identity)


def test_elliptic_graphsage_forward():
    """Verify end-to-end forward pass through the multi-layer GraphSAGE architecture."""
    num_nodes = 80
    in_channels = 174
    hidden_dim = 64
    num_layers = 3
    edge_index = torch.randint(0, num_nodes, (2, 200), dtype=torch.long)
    x = torch.randn(num_nodes, in_channels)

    model = EllipticGraphSAGE(in_channels=in_channels, hidden_dim=hidden_dim, num_layers=num_layers, dropout=0.25)
    logits = model(x, edge_index)

    assert logits.shape == (num_nodes,), f"Expected logits shape (80,), got {logits.shape}"
    assert not torch.isnan(logits).any(), "Model produced NaN logits"
    assert not torch.isinf(logits).any(), "Model produced Inf logits"


def test_binary_focal_loss_masking():
    """Verify Focal Loss correctly zeroes out unlabelled/masked nodes and computes valid gradients."""
    num_nodes = 20
    logits = torch.randn(num_nodes, requires_grad=True)
    targets = torch.randint(0, 2, (num_nodes,)).float()
    
    # Half of the nodes are unlabelled (-1 in dataset), mask has True only for labelled
    mask = torch.zeros(num_nodes, dtype=torch.bool)
    mask[:10] = True

    loss_fn = BinaryFocalLoss(alpha=0.80, gamma=2.0)
    loss = loss_fn(logits, targets, mask=mask)

    assert loss.item() > 0, "Loss must be strictly positive"
    loss.backward()
    assert logits.grad is not None
    # Masked nodes (index 10..19) should receive exactly zero gradient
    assert torch.all(logits.grad[10:] == 0.0), "Masked nodes must receive zero gradient"
    # Unmasked nodes should have non-zero gradients
    assert torch.any(logits.grad[:10] != 0.0), "Unmasked nodes must receive non-zero gradient"


def test_weighted_bce_loss_masking():
    """Verify Weighted BCE correctly applies pos_weight and masks unlabelled nodes."""
    num_nodes = 20
    logits = torch.randn(num_nodes, requires_grad=True)
    targets = torch.randint(0, 2, (num_nodes,)).float()
    
    mask = torch.zeros(num_nodes, dtype=torch.bool)
    mask[:10] = True

    loss_fn = WeightedBCELoss(pos_weight=7.63)
    loss = loss_fn(logits, targets, mask=mask)

    assert loss.item() > 0, "Loss must be strictly positive"
    loss.backward()
    assert torch.all(logits.grad[10:] == 0.0), "Masked nodes must receive zero gradient"


def test_saved_model_checkpoint_load():
    """Verify that the serialized best model checkpoint can be loaded and executed."""
    checkpoint_path = os.path.join("models", "elliptic", "best_elliptic_graphsage.pt")
    config_path = os.path.join("models", "elliptic", "optimal_hyperparameters.json")
    
    assert os.path.exists(checkpoint_path), f"Checkpoint missing at {checkpoint_path}"
    assert os.path.exists(config_path), f"Config missing at {config_path}"

    with open(config_path, "r") as f:
        config = json.load(f)

    state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)

    model = EllipticGraphSAGE(
        in_channels=174,
        hidden_dim=config["hidden_dim"],
        num_layers=config["num_layers"],
        dropout=config["dropout"]
    )
    model.load_state_dict(state_dict)
    model.eval()

    dummy_x = torch.randn(10, 174)
    dummy_edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 0]], dtype=torch.long)
    with torch.no_grad():
        out = model(dummy_x, dummy_edge_index)
    assert out.shape == (10,)
    probs = torch.sigmoid(out)
    assert (probs >= 0.0).all() and (probs <= 1.0).all()
