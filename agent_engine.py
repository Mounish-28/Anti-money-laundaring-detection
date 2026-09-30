"""
agent_engine.py
=============================================================================
QuantumAML Nexus -- Core AML AI Agent Engine
=============================================================================
Author: Advanced AML AI Engineer
Purpose:
  1. Defines the AMLAgent class that ingests real-time transaction streams
     across both fiat (ISO 20022/ACH/Wire) and crypto (UTXO/EVM/VDA) schemas.
  2. Dynamically maps transactions into a real-time directed multigraph.
  3. Executes parallel inference using:
     - Inductive Graph Neural Network (PyG / PyTorch Geometric) module for
       topological anomaly and directed cycle detection.
     - Temporal Ensemble Classifier (LightGBM / XGBoost) for multi-horizon
       velocity spikes and threshold structuring anomalies.
  4. Computes an aggregate risk score normalized to 0–100 with non-linear fusion.
  5. Automatically triggers structured alert payloads with reason codes when
     risk exceeds threshold 75.
  6. Exposes explain_decision(tx_id) to extract the immediate 2-hop subgraph,
     compute topological invariants, and synthesize forensic investigator notes.
=============================================================================
"""

from __future__ import annotations
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from torch_geometric.nn import SAGEConv
    HAS_PYG = True
except ImportError:
    HAS_PYG = False

try:
    import lightgbm as lgb
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

logger = logging.getLogger("AMLAgentEngine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# =============================================================================
# 1. TRANSACTION NORMALIZATION & SCHEMAS
# =============================================================================

@dataclass
class NormalizedTransaction:
    tx_id: str
    source_node: str
    target_node: str
    amount: float
    amount_usd: float
    currency: str
    rail: str  # "fiat" or "crypto"
    timestamp: str
    timestamp_epoch: float
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    is_cross_border: bool = False
    mixer_risk: bool = False
    memo: str = ""


def normalize_transaction_payload(payload: Dict[str, Any]) -> NormalizedTransaction:
    """
    Polymorphic normalizer accepting both fiat (ISO 20022/ACH/Wire)
    and cryptocurrency (Bitcoin/Ethereum/VDA mempool) schemas.
    """
    now_epoch = time.time()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Determine rail type
    is_crypto = (
        bool(payload.get("tx_hash"))
        or bool(payload.get("from_wallet"))
        or bool(payload.get("to_wallet"))
        or bool(payload.get("mixer_risk"))
        or payload.get("channel") in ("crypto", "CRYPTO_SCREENING_FEED")
        or str(payload.get("currency", "")).upper() in ("BTC", "ETH", "USDT", "USDC", "SOL")
    )

    rail = "crypto" if is_crypto else "fiat"

    # Extract Transaction ID
    tx_id = (
        payload.get("tx_id")
        or payload.get("tx_hash")
        or payload.get("transaction_id")
        or f"TX_{rail.upper()}_{int(now_epoch * 1000)}"
    )

    # Extract Source & Target Entities
    if is_crypto:
        source = (
            payload.get("from_wallet")
            or payload.get("sender_address")
            or payload.get("from_address")
            or payload.get("sender")
            or "0xUNKNOWN_SENDER"
        )
        target = (
            payload.get("to_wallet")
            or payload.get("receiver_address")
            or payload.get("to_address")
            or payload.get("receiver")
            or "0xUNKNOWN_RECEIVER"
        )
        currency = str(payload.get("currency", "BTC")).upper()
        raw_amt = float(payload.get("amount_btc") or payload.get("amount_eth") or payload.get("amount") or 1.0)

        # Standard conversion approximation to USD
        conv_rates = {"BTC": 65000.0, "ETH": 3500.0, "USDT": 1.0, "USDC": 1.0, "SOL": 150.0}
        rate = conv_rates.get(currency, 1.0)
        amount_usd = raw_amt * rate
        mixer_flag = bool(
            payload.get("mixer_risk", False)
            or "MIXER" in target.upper()
            or "TORNADO" in target.upper()
            or "WASABI" in target.upper()
        )
        cross_border = True  # Crypto is inherently cross-border
    else:
        source = (
            payload.get("account_from")
            or payload.get("sender_id")
            or payload.get("sender_account")
            or payload.get("account_id")
            or payload.get("sender")
            or "ACC_UNKNOWN_SENDER"
        )
        target = (
            payload.get("account_to")
            or payload.get("receiver_id")
            or payload.get("receiver_account")
            or payload.get("beneficiary_id")
            or payload.get("receiver")
            or "ACC_UNKNOWN_RECEIVER"
        )
        currency = str(payload.get("currency", "USD")).upper()
        raw_amt = float(payload.get("amount") or 1000.0)
        # Currency rate
        fx_rates = {"USD": 1.0, "EUR": 1.08, "GBP": 1.28, "CHF": 1.12, "CAD": 0.74}
        rate = fx_rates.get(currency, 1.0)
        amount_usd = raw_amt * rate
        mixer_flag = False
        cross_border = bool(payload.get("is_cross_border", False) or payload.get("cross_border", False))

    ts_str = payload.get("timestamp") or now_iso
    return NormalizedTransaction(
        tx_id=str(tx_id),
        source_node=str(source),
        target_node=str(target),
        amount=raw_amt,
        amount_usd=round(amount_usd, 2),
        currency=currency,
        rail=rail,
        timestamp=ts_str,
        timestamp_epoch=now_epoch,
        raw_payload=payload,
        is_cross_border=cross_border,
        mixer_risk=mixer_flag,
        memo=str(payload.get("memo", "")),
    )


# =============================================================================
# 2. INDUCTIVE GRAPH NEURAL NETWORK (PyG) MODULE
# =============================================================================

class InductiveGNNNet(nn.Module):
    """
    Two-layer Inductive GraphSAGE architecture with LeakyReLU activations
    and residual skip projection for topological anomaly detection.
    """

    def __init__(self, in_features: int = 8, hidden_dim: int = 32, out_dim: int = 16):
        super().__init__()
        self.has_pyg = HAS_PYG
        if HAS_PYG:
            self.conv1 = SAGEConv(in_features, hidden_dim, aggr="mean")
            self.conv2 = SAGEConv(hidden_dim, out_dim, aggr="mean")
        else:
            self.fc1 = nn.Linear(in_features, hidden_dim)
            self.fc2 = nn.Linear(hidden_dim, out_dim)

        self.head = nn.Sequential(
            nn.Linear(out_dim * 2, 16),
            nn.LeakyReLU(0.2),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, src_idx: int, dst_idx: int) -> torch.Tensor:
        if self.has_pyg:
            h1 = F.leaky_relu(self.conv1(x, edge_index), 0.2)
            h2 = F.leaky_relu(self.conv2(h1, edge_index), 0.2)
        else:
            h1 = F.leaky_relu(self.fc1(x), 0.2)
            h2 = F.leaky_relu(self.fc2(h1), 0.2)

        src_emb = h2[src_idx]
        dst_emb = h2[dst_idx]
        edge_repr = torch.cat([src_emb, dst_emb], dim=-1)
        return self.head(edge_repr).squeeze(-1)


class InductiveGNNModule:
    """
    Wraps the Inductive GNN to perform neighborhood feature tensorization,
    directed cycle evaluation, and topological anomaly scoring.
    """

    def __init__(self):
        torch.manual_seed(42)
        self.model = InductiveGNNNet(in_features=8, hidden_dim=32, out_dim=16)
        self.model.eval()

    def _extract_local_features(
        self,
        graph: nx.DiGraph,
        node: str,
        rail: str,
        is_mixer: bool,
    ) -> List[float]:
        """Builds an 8-dimensional feature vector for a graph node."""
        in_deg = graph.in_degree(node) if graph.has_node(node) else 0
        out_deg = graph.out_degree(node) if graph.has_node(node) else 0

        in_vol = sum(d.get("amount_usd", 0.0) for _, _, d in graph.in_edges(node, data=True)) if graph.has_node(node) else 0.0
        out_vol = sum(d.get("amount_usd", 0.0) for _, _, d in graph.out_edges(node, data=True)) if graph.has_node(node) else 0.0

        # Pass-through flow equality ratio (0.0 to 1.0)
        tot = in_vol + out_vol + 1e-5
        pass_through = min(in_vol, out_vol) / (max(in_vol, out_vol) + 1e-5) if (in_vol > 0 and out_vol > 0) else 0.0

        norm_in = math.log1p(in_vol) / 15.0
        norm_out = math.log1p(out_vol) / 15.0

        return [
            min(1.0, norm_in),
            min(1.0, norm_out),
            min(1.0, in_deg / 20.0),
            min(1.0, out_deg / 20.0),
            float(pass_through),
            1.0 if rail == "crypto" else 0.0,
            1.0 if is_mixer else 0.0,
            1.0 if in_deg > 3 and out_deg <= 1 else 0.0,  # Smurfing aggregator indicator
        ]

    def predict_topology(
        self,
        graph: nx.DiGraph,
        tx: NormalizedTransaction,
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """
        Runs inductive GNN forward inference over the local 2-hop neighborhood.
        Returns: (topological_score_0_to_100, reason_codes, details_dict)
        """
        src = tx.source_node
        dst = tx.target_node
        reasons = []

        # 1. Topological Graph Cycle Detection
        # Check if adding this edge (src -> dst) completes a directed cycle back to src
        has_cycle = False
        cycle_nodes: List[str] = []
        if graph.has_node(dst) and graph.has_node(src):
            try:
                # If there is already a path from dst to src, then src -> dst forms a cycle!
                if nx.has_path(graph, dst, src):
                    cycle_path = nx.shortest_path(graph, dst, src)
                    has_cycle = True
                    cycle_nodes = cycle_path
                    reasons.append("CYCLE_CIRCULAR_LAYERING")
            except Exception:
                pass

        # 2. Structural Smurfing / Fan-In Aggregation Check
        in_degree_src = graph.in_degree(src) if graph.has_node(src) else 0
        in_degree_dst = graph.in_degree(dst) if graph.has_node(dst) else 0
        is_structuring_ring = (in_degree_dst >= 3) or (9000.0 <= tx.amount_usd <= 9999.0 and in_degree_dst >= 2)
        if is_structuring_ring:
            reasons.append("FAN_IN_STRUCTURING")

        # 3. Crypto Mixer / High-Risk Proximity
        if tx.mixer_risk:
            reasons.append("UNHOSTED_MIXER_PROXIMITY")

        # 4. Construct local node neighborhood tensor for GNN forward pass
        nodes_set = {src, dst}
        if graph.has_node(src):
            nodes_set.update(list(graph.predecessors(src))[:5])
            nodes_set.update(list(graph.successors(src))[:5])
        if graph.has_node(dst):
            nodes_set.update(list(graph.predecessors(dst))[:5])
            nodes_set.update(list(graph.successors(dst))[:5])

        node_list = list(nodes_set)
        node_to_idx = {n: i for i, n in enumerate(node_list)}
        x_features = [
            self._extract_local_features(graph, n, tx.rail, tx.mixer_risk if n in (src, dst) else False)
            for n in node_list
        ]
        x_tensor = torch.tensor(x_features, dtype=torch.float32)

        # Build local edge index
        edge_tuples = []
        for u in node_list:
            if graph.has_node(u):
                for v in graph.successors(u):
                    if v in node_to_idx:
                        edge_tuples.append((node_to_idx[u], node_to_idx[v]))
        # Add the active edge
        edge_tuples.append((node_to_idx[src], node_to_idx[dst]))

        if edge_tuples:
            src_edges, dst_edges = zip(*edge_tuples)
            edge_index = torch.tensor([list(src_edges), list(dst_edges)], dtype=torch.long)
        else:
            edge_index = torch.tensor([[node_to_idx[src]], [node_to_idx[dst]]], dtype=torch.long)

        # PyG / Neural Forward Pass
        with torch.no_grad():
            raw_gnn_out = float(self.model(x_tensor, edge_index, node_to_idx[src], node_to_idx[dst]).item())

        # Scale to 0-100 and escalate for critical topological patterns
        score = raw_gnn_out * 40.0  # Baseline GNN latent score

        if has_cycle:
            score = max(score, 94.5)
        if "FAN_IN_STRUCTURING" in reasons:
            score = max(score, 88.0)
        if tx.mixer_risk:
            score = max(score, 92.0)

        # Pass-through equality bonus
        if graph.has_node(src) and graph.has_node(dst):
            src_in = sum(d.get("amount_usd", 0.0) for _, _, d in graph.in_edges(src, data=True))
            if src_in > 0 and 0.85 <= (tx.amount_usd / src_in) <= 1.15:
                reasons.append("HIGH_PASS_THROUGH_EQUALITY")
                score = max(score, 85.0)

        score = float(np.clip(score, 0.0, 100.0))
        details = {
            "raw_gnn_activation": round(raw_gnn_out, 4),
            "cycle_detected": has_cycle,
            "cycle_nodes": cycle_nodes,
            "subgraph_nodes_evaluated": len(node_list),
            "subgraph_edges_evaluated": len(edge_tuples),
        }
        return round(score, 2), reasons, details


# =============================================================================
# 3. TEMPORAL ENSEMBLE CLASSIFIER (LightGBM / XGBoost)
# =============================================================================

class TemporalEnsembleClassifier:
    """
    Temporal Ensemble classifier monitoring multi-horizon EWMA velocity surges,
    inter-arrival time compression, and threshold evasion anomalies.
    """

    def __init__(self):
        self.node_history: Dict[str, deque] = {}
        self.model = None
        self._init_ensemble_model()

    def _init_ensemble_model(self):
        """Initializes and trains a lightweight synthetic gradient boosting classifier."""
        X_mock = np.array([
            # [amount_usd, ewma_1h, ewma_24h, surge_ratio, is_structuring, inter_arrival, is_cross_border]
            [500.0, 100.0, 500.0, 0.2, 0.0, 3600.0, 0.0],
            [1200.0, 200.0, 1000.0, 0.4, 0.0, 7200.0, 0.0],
            [9500.0, 9500.0, 1200.0, 3.8, 1.0, 120.0, 1.0],   # Structuring / Velocity Spike
            [25000.0, 22000.0, 3000.0, 4.5, 0.0, 45.0, 1.0],  # Major surge
            [300.0, 50.0, 400.0, 0.1, 0.0, 86400.0, 0.0],
            [9800.0, 9800.0, 2000.0, 3.2, 1.0, 300.0, 0.0],  # Structuring
            [75000.0, 75000.0, 5000.0, 6.0, 0.0, 60.0, 1.0], # Surge
        ])
        y_mock = np.array([0, 0, 1, 1, 0, 1, 1])

        if HAS_LGBM:
            self.model = lgb.LGBMClassifier(
                n_estimators=10,
                learning_rate=0.1,
                max_depth=3,
                verbose=-1,
                random_state=42,
            )
            self.model.fit(X_mock, y_mock)
        elif HAS_XGB:
            self.model = xgb.XGBClassifier(
                n_estimators=10,
                max_depth=3,
                eval_metric="logloss",
                random_state=42,
            )
            self.model.fit(X_mock, y_mock)

    def predict_velocity(
        self,
        tx: NormalizedTransaction,
        graph: nx.DiGraph,
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """
        Extracts temporal velocity features and scores event using Gradient Boosted Trees.
        Returns: (velocity_score_0_to_100, reason_codes, details_dict)
        """
        src = tx.source_node
        reasons = []

        history = self.node_history.setdefault(src, deque(maxlen=200))
        now = tx.timestamp_epoch

        # Calculate inter-arrival time
        inter_arrival = (now - history[-1]["epoch"]) if history else 86400.0
        history.append({"amount_usd": tx.amount_usd, "epoch": now})

        # Calculate multi-horizon sliding volumes
        vol_1h = sum(h["amount_usd"] for h in history if (now - h["epoch"]) <= 3600.0)
        vol_24h = sum(h["amount_usd"] for h in history if (now - h["epoch"]) <= 86400.0)
        count_1h = sum(1 for h in history if (now - h["epoch"]) <= 3600.0)

        # Baseline volume expectation
        baseline = max(100.0, vol_24h / 24.0)
        surge_ratio = vol_1h / baseline

        # Structuring check ($9,000 to $9,999 evasion)
        is_structuring = 1.0 if (9000.0 <= tx.amount_usd <= 9999.0) else 0.0

        if is_structuring > 0:
            reasons.append("SUB_THRESHOLD_STRUCTURING")

        if surge_ratio >= 3.0 or (count_1h >= 5 and vol_1h >= 15000.0):
            reasons.append("VELOCITY_SPIKE_24H")

        if inter_arrival < 180.0 and len(history) >= 2:
            reasons.append("RAPID_BURST_INTER_ARRIVAL")

        # Feature vector for GBDT
        feat = np.array([[
            tx.amount_usd,
            vol_1h,
            vol_24h,
            surge_ratio,
            is_structuring,
            inter_arrival,
            1.0 if tx.is_cross_border else 0.0,
        ]])

        if self.model is not None:
            proba = float(self.model.predict_proba(feat)[0, 1])
        else:
            # Deterministic empirical fallback
            proba = 0.10
            if is_structuring:
                proba += 0.45
            if surge_ratio > 3.0:
                proba += 0.40

        score = proba * 100.0

        # Hard minimums for critical velocity reason codes
        if "VELOCITY_SPIKE_24H" in reasons and "SUB_THRESHOLD_STRUCTURING" in reasons:
            score = max(score, 91.0)
        elif "VELOCITY_SPIKE_24H" in reasons:
            score = max(score, 82.0)
        elif "SUB_THRESHOLD_STRUCTURING" in reasons:
            score = max(score, 78.5)

        score = float(np.clip(score, 0.0, 100.0))
        details = {
            "vol_1h": round(vol_1h, 2),
            "vol_24h": round(vol_24h, 2),
            "surge_ratio": round(surge_ratio, 2),
            "tx_count_1h": count_1h,
            "inter_arrival_sec": round(inter_arrival, 2),
        }
        return round(score, 2), reasons, details


# =============================================================================
# 4. AML AGENT CORE ENGINE
# =============================================================================

@dataclass
class AlertPayload:
    alert_id: str
    tx_id: str
    timestamp: str
    risk_score: float
    severity_tier: str  # "CRITICAL_SAR" or "HIGH_RISK"
    reason_codes: List[str]
    entities_involved: Dict[str, str]
    financial_rail: str
    amount_usd: float
    summary: str
    audit_hash: str


class AMLAgent:
    """
    Enterprise-grade autonomous AML AI Agent. Ingests fiat/crypto streams,
    maintains real-time graph state, runs parallel GNN & Ensemble inference,
    triggers alerts at threshold 75, and explains decisions via 2-hop subgraphs.
    """

    def __init__(self, alert_threshold: float = 75.0):
        self.alert_threshold = alert_threshold
        self.graph = nx.DiGraph()
        self.transactions: Dict[str, Dict[str, Any]] = {}
        self.alerts: List[AlertPayload] = []

        # Sub-modules
        self.gnn_module = InductiveGNNModule()
        self.ensemble_module = TemporalEnsembleClassifier()
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="AMLAgentInfer")

        # Cryptographic tamper-evident hash chain
        self.audit_chain: List[str] = [
            hashlib.sha256(b"QUANTUMAML_NEXUS_AGENT_ENGINE_GENESIS").hexdigest()
        ]
        logger.info(f"AMLAgent initialized with Alert Threshold: {self.alert_threshold:.1f}")

    # -------------------------------------------------------------------------
    # PARALLEL INFERENCE PIPELINE
    # -------------------------------------------------------------------------

    def process_transaction(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accepts raw transaction payload (fiat or crypto), maps into graph,
        executes parallel inference, aggregates risk score (0-100), and fires alert if >= 75.
        """
        t0 = time.perf_counter()

        # 1. Normalize Transaction
        tx = normalize_transaction_payload(payload)

        # 2. Update Graph Structure (Pre-inference snapshot)
        src = tx.source_node
        dst = tx.target_node

        if not self.graph.has_node(src):
            self.graph.add_node(src, entity_type="WALLET" if tx.rail == "crypto" else "ACCOUNT", first_seen=tx.timestamp)
        if not self.graph.has_node(dst):
            self.graph.add_node(dst, entity_type="WALLET" if tx.rail == "crypto" else "ACCOUNT", first_seen=tx.timestamp)

        # 3. Parallel Inference Execution
        # Worker A: Inductive GNN for Topological Anomaly & Cycle Detection
        future_gnn = self.executor.submit(self.gnn_module.predict_topology, self.graph, tx)
        # Worker B: Temporal Ensemble for Velocity & Structuring Anomalies
        future_ens = self.executor.submit(self.ensemble_module.predict_velocity, tx, self.graph)

        gnn_score, gnn_reasons, gnn_details = future_gnn.result()
        ens_score, ens_reasons, ens_details = future_ens.result()

        # 4. Now commit edge to graph
        self.graph.add_edge(
            src,
            dst,
            tx_id=tx.tx_id,
            amount=tx.amount,
            amount_usd=tx.amount_usd,
            currency=tx.currency,
            rail=tx.rail,
            timestamp=tx.timestamp,
            mixer_risk=tx.mixer_risk,
        )

        # 5. Compute Aggregate Risk Score (0–100) with Non-Linear Fusion
        combined_reasons = sorted(list(set(gnn_reasons + ens_reasons)))

        # Soft envelope to prevent severe topological threats from dilution
        if gnn_reasons:
            aggregate_score = max(gnn_score, 0.60 * gnn_score + 0.40 * ens_score)
        elif ens_reasons:
            aggregate_score = max(ens_score, 0.40 * gnn_score + 0.60 * ens_score)
        else:
            aggregate_score = 0.50 * gnn_score + 0.50 * ens_score

        # Specific synergy boosts
        if "CYCLE_CIRCULAR_LAYERING" in combined_reasons:
            aggregate_score = max(aggregate_score, 95.0)
        if "UNHOSTED_MIXER_PROXIMITY" in combined_reasons:
            aggregate_score = max(aggregate_score, 92.5)
        if "FAN_IN_STRUCTURING" in combined_reasons and "VELOCITY_SPIKE_24H" in combined_reasons:
            aggregate_score = max(aggregate_score, 94.0)

        aggregate_score = round(float(np.clip(aggregate_score, 0.0, 100.0)), 2)

        # 6. Check Alert Trigger Threshold (>= 75)
        alert_triggered = aggregate_score >= self.alert_threshold
        alert_payload: Optional[AlertPayload] = None

        # 7. Cryptographic Audit Hashing
        parent_hash = self.audit_chain[-1]
        audit_str = f"{parent_hash}:{tx.tx_id}:{src}:{dst}:{tx.amount_usd}:{aggregate_score}:{alert_triggered}"
        current_audit_hash = hashlib.sha256(audit_str.encode()).hexdigest()
        self.audit_chain.append(current_audit_hash)

        if alert_triggered:
            tier = "CRITICAL_SAR" if aggregate_score >= 90.0 else "HIGH_RISK"
            summary_reasons = ", ".join(combined_reasons) if combined_reasons else "ELEVATED_STATISTICAL_RISK"
            summary = (
                f"[{tier}] Suspicious activity flagged (Risk: {aggregate_score:.1f}/100 >= {self.alert_threshold}). "
                f"Entities: {src} -> {dst}. Amount: ${tx.amount_usd:,.2f} USD. "
                f"Indicators: {summary_reasons}."
            )

            alert_payload = AlertPayload(
                alert_id=f"ALT_{int(time.time()*1000)}_{random.randint(100, 999)}",
                tx_id=tx.tx_id,
                timestamp=tx.timestamp,
                risk_score=aggregate_score,
                severity_tier=tier,
                reason_codes=combined_reasons,
                entities_involved={"source": src, "target": dst},
                financial_rail=tx.rail,
                amount_usd=tx.amount_usd,
                summary=summary,
                audit_hash=current_audit_hash,
            )
            self.alerts.append(alert_payload)
            logger.warning(f"[SUSPICIOUS ACTIVITY ALERT] {summary}")

        latency_ms = (time.perf_counter() - t0) * 1000.0

        decision_record = {
            "tx_id": tx.tx_id,
            "source_node": src,
            "target_node": dst,
            "amount": tx.amount,
            "amount_usd": tx.amount_usd,
            "currency": tx.currency,
            "rail": tx.rail,
            "timestamp": tx.timestamp,
            "aggregate_risk_score": aggregate_score,
            "alert_threshold": self.alert_threshold,
            "alert_triggered": alert_triggered,
            "severity_tier": "CRITICAL_SAR" if aggregate_score >= 90.0 else ("HIGH_RISK" if alert_triggered else "LOW_NOMINAL"),
            "reason_codes": combined_reasons,
            "gnn_score": gnn_score,
            "gnn_details": gnn_details,
            "ensemble_score": ens_score,
            "ensemble_details": ens_details,
            "alert_payload": asdict(alert_payload) if alert_payload else None,
            "triage_status": "OPEN",
            "triage_note": "",
            "audit_hash": current_audit_hash,
            "inference_latency_ms": round(latency_ms, 2),
        }

        self.transactions[tx.tx_id] = decision_record
        return decision_record

    def update_triage_status(self, tx_id: str, action: str, note: str = "") -> Dict[str, Any]:
        """
        Updates triage status for an alert/transaction.
        Actions:
          - 'APPROVE': Approves automated SAR filing.
          - 'ESCALATE': Escalates to Law Enforcement Strike Force.
          - 'DISMISS': Dismisses as benign / false positive.
        """
        record = self.transactions.get(tx_id)
        if not record:
            raise KeyError(f"Transaction ID '{tx_id}' not found in active agent memory.")

        act = action.upper()
        if "ESCALAT" in act:
            new_status = "ESCALATED_LEO"
        elif "APPROV" in act:
            new_status = "APPROVED_SAR"
        elif "DISMISS" in act or "CLEAR" in act:
            new_status = "CLEARED_FALSE_POSITIVE"
        else:
            new_status = action.upper()

        record["triage_status"] = new_status
        record["triage_note"] = note
        record["triage_updated_at"] = datetime.now(timezone.utc).isoformat()
        return record

    def evaluate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standard evaluation method for the AMLAgent engine.
        Ingests a transaction payload (handling both fiat and crypto fields),
        runs inference, and returns risk score, risk level (Low/Medium/High/Critical),
        and fired alert rules.
        """
        decision = self.process_transaction(payload)
        score = decision["aggregate_risk_score"]

        if score >= 85.0:
            level = "Critical"
        elif score >= 70.0:
            level = "High"
        elif score >= 40.0:
            level = "Medium"
        else:
            level = "Low"

        fired_rules = decision.get("reason_codes", [])

        return {
            "tx_id": decision["tx_id"],
            "risk_score": score,
            "risk_level": level,
            "alert_triggered": decision["alert_triggered"],
            "fired_rules": fired_rules,
            "reason_codes": fired_rules,
            "severity_tier": decision["severity_tier"],
            "financial_rail": decision["rail"],
            "amount_usd": decision["amount_usd"],
            "entities": {
                "source": decision["source_node"],
                "target": decision["target_node"],
            },
            "gnn_score": decision["gnn_score"],
            "ensemble_score": decision["ensemble_score"],
            "inference_latency_ms": decision["inference_latency_ms"],
            "audit_hash": decision["audit_hash"],
            "alert_payload": decision.get("alert_payload"),
        }

    # -------------------------------------------------------------------------
    # 5. INVESTIGATOR 2-HOP SUBGRAPH EXPLANATION
    # -------------------------------------------------------------------------

    def explain_decision(self, tx_id: str) -> Dict[str, Any]:
        """
        Extracts the immediate 2-hop neighborhood subgraph around the suspicious
        nodes for investigator inspection, computes topological invariants,
        and synthesizes a plain-English forensic explanation.
        """
        decision = self.transactions.get(tx_id)
        if not decision:
            raise KeyError(f"Transaction ID '{tx_id}' not found in active agent memory.")

        src = decision["source_node"]
        dst = decision["target_node"]

        # 1. Extract 2-Hop Neighborhood
        two_hop_nodes: Set[str] = {src, dst}

        for focal_node in (src, dst):
            if self.graph.has_node(focal_node):
                # 1-hop predecessors and successors
                hop1_pred = set(self.graph.predecessors(focal_node))
                hop1_succ = set(self.graph.successors(focal_node))
                two_hop_nodes.update(hop1_pred)
                two_hop_nodes.update(hop1_succ)

                # 2-hop neighbors
                for n1 in hop1_pred | hop1_succ:
                    two_hop_nodes.update(list(self.graph.predecessors(n1))[:10])
                    two_hop_nodes.update(list(self.graph.successors(n1))[:10])

        # Induce subgraph
        subgraph = self.graph.subgraph(two_hop_nodes)

        # 2. Serialize Nodes with Topological Metrics
        nodes_payload = []
        for node in subgraph.nodes():
            in_deg = subgraph.in_degree(node)
            out_deg = subgraph.out_degree(node)
            in_vol = sum(d.get("amount_usd", 0.0) for _, _, d in subgraph.in_edges(node, data=True))
            out_vol = sum(d.get("amount_usd", 0.0) for _, _, d in subgraph.out_edges(node, data=True))

            nodes_payload.append({
                "node_id": node,
                "is_focal_entity": node in (src, dst),
                "in_degree": in_deg,
                "out_degree": out_deg,
                "total_in_flow_usd": round(in_vol, 2),
                "total_out_flow_usd": round(out_vol, 2),
                "entity_type": self.graph.nodes[node].get("entity_type", "ACCOUNT"),
            })

        # 3. Serialize Edges
        edges_payload = []
        for u, v, d in subgraph.edges(data=True):
            is_active_tx = (d.get("tx_id") == tx_id)
            edges_payload.append({
                "source": u,
                "target": v,
                "tx_id": d.get("tx_id", "N/A"),
                "amount": d.get("amount", 0.0),
                "amount_usd": d.get("amount_usd", 0.0),
                "currency": d.get("currency", "USD"),
                "rail": d.get("rail", "fiat"),
                "timestamp": d.get("timestamp", ""),
                "is_focal_transaction": is_active_tx,
            })

        # 4. Topological Invariants & Cycles
        cycles = []
        try:
            raw_cycles = list(nx.simple_cycles(subgraph))
            # Filter cycles involving focal nodes
            for c in raw_cycles:
                if len(c) <= 6:
                    cycles.append(c)
        except Exception:
            pass

        # Calculate pass-through flow equality for focal target
        dst_in = sum(d.get("amount_usd", 0.0) for _, _, d in subgraph.in_edges(dst, data=True))
        dst_out = sum(d.get("amount_usd", 0.0) for _, _, d in subgraph.out_edges(dst, data=True))
        pass_through_ratio = (
            min(dst_in, dst_out) / (max(dst_in, dst_out) + 1e-5) if (dst_in > 0 and dst_out > 0) else 0.0
        )

        structural_metrics = {
            "subgraph_node_count": len(subgraph.nodes()),
            "subgraph_edge_count": len(subgraph.edges()),
            "detected_directed_cycles": cycles,
            "cycle_count": len(cycles),
            "target_pass_through_equality": round(pass_through_ratio, 3),
            "source_out_degree": subgraph.out_degree(src) if subgraph.has_node(src) else 0,
            "target_in_degree": subgraph.in_degree(dst) if subgraph.has_node(dst) else 0,
        }

        # 5. Synthesize Plain-English Forensic Explanation
        reasons = decision.get("reason_codes", [])
        score = decision.get("aggregate_risk_score", 0.0)

        narrative_parts = [
            f"FORENSIC INVESTIGATION DOSSIER FOR TX: {tx_id}",
            f"Aggregate Risk Score: {score:.1f}/100 | Severity: {decision.get('severity_tier')} | Rail: {decision.get('rail').upper()}",
            f"Transaction Amount: ${decision.get('amount_usd'):,.2f} USD ({decision.get('amount')} {decision.get('currency')})",
            f"Focal Route: {src} ---> {dst}",
            "",
            "KEY FINDINGS & TOPOLOGICAL ANOMALIES:",
        ]

        if "CYCLE_CIRCULAR_LAYERING" in reasons or cycles:
            narrative_parts.append(
                f"• DIRECTED CYCLE DETECTED: Funds cycle through {len(cycles)} closed topological loop(s). "
                f"Cycle topology: {' -> '.join(cycles[0]) if cycles else 'Circular path observed'}."
            )
        if "FAN_IN_STRUCTURING" in reasons:
            narrative_parts.append(
                f"• FAN-IN STRUCTURING: Destination node '{dst}' exhibits an elevated in-degree of "
                f"{structural_metrics['target_in_degree']} incoming hops, consistent with smurfing/mule collection."
            )
        if "SUB_THRESHOLD_STRUCTURING" in reasons:
            narrative_parts.append(
                f"• CTR THRESHOLD EVASION: Transfer amount (${decision.get('amount_usd'):,.2f}) "
                f"falls directly within the $9,000–$9,999 smurfing bracket designed to evade mandatory Bank Secrecy Act CTR filing."
            )
        if "VELOCITY_SPIKE_24H" in reasons:
            narrative_parts.append(
                f"• VELOCITY SURGE: Origin node '{src}' exhibits an anomalous 24h burst exceeding 3.0x historical baseline."
            )
        if "UNHOSTED_MIXER_PROXIMITY" in reasons:
            narrative_parts.append(
                f"• CRYPTO MIXER INTERACTION: Counterparty '{dst}' connects to high-risk cryptocurrency tumbling infrastructure."
            )

        narrative_parts.extend([
            "",
            "RECOMMENDED INVESTIGATIVE ACTION:",
            "1. Initiate immediate review under FinCEN 31 CFR § 1020.320 for SAR Form 111 electronic filing.",
            "2. Freeze target beneficiary account / flag unhosted wallet address across inter-bank sanctions registry.",
            f"3. Cryptographic Audit Signature: {decision.get('audit_hash')}",
        ])

        investigator_summary = "\n".join(narrative_parts)

        return {
            "tx_id": tx_id,
            "focal_entities": {"source": src, "target": dst},
            "aggregate_risk_score": score,
            "alert_triggered": decision.get("alert_triggered", False),
            "severity_tier": decision.get("severity_tier"),
            "reason_codes": reasons,
            "structural_metrics": structural_metrics,
            "subgraph": {
                "nodes": nodes_payload,
                "edges": edges_payload,
            },
            "investigator_summary": investigator_summary,
            "audit_hash": decision.get("audit_hash"),
        }


# Global singleton instance
agent_engine = AMLAgent(alert_threshold=75.0)


# =============================================================================
# CLI DEMO & VERIFICATION HARNESS
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("[INIT] QuantumAML Nexus: AMLAgent Engine Self-Test")
    print("=" * 70)

    agent = AMLAgent(alert_threshold=75.0)

    # 1. Normal Fiat Transaction
    fiat_normal = {
        "tx_id": "TX_NORM_001",
        "account_from": "ACC_ALICE",
        "account_to": "ACC_BOB",
        "amount": 250.0,
        "currency": "USD",
    }
    r1 = agent.process_transaction(fiat_normal)
    print(f"\n[1] Normal Fiat: Risk={r1['aggregate_risk_score']}/100, Alert={r1['alert_triggered']}")

    # 2. Structuring + Velocity Surge Fiat Transaction (Smurfing)
    fiat_smurf = {
        "tx_id": "TX_SMURF_999",
        "account_from": "ACC_MULE_01",
        "account_to": "ACC_BOSS_RING",
        "amount": 9500.0,
        "currency": "USD",
        "is_cross_border": True,
    }
    # Pre-seed ring in-degree
    for i in range(4):
        agent.process_transaction({
            "tx_id": f"TX_FEED_{i}",
            "account_from": f"ACC_MULE_{i:02d}",
            "account_to": "ACC_BOSS_RING",
            "amount": 9400.0,
        })
    r2 = agent.process_transaction(fiat_smurf)
    print(f"[2] Smurfing Ring: Risk={r2['aggregate_risk_score']}/100, Alert={r2['alert_triggered']}, Reasons={r2['reason_codes']}")

    # 3. Circular Layering Cycle: A -> B -> C -> A
    print("\nSimulating Directed Cycle A -> B -> C -> A...")
    agent.process_transaction({"tx_id": "TX_CYC_1", "account_from": "ACC_CYCLE_A", "account_to": "ACC_CYCLE_B", "amount": 50000.0})
    agent.process_transaction({"tx_id": "TX_CYC_2", "account_from": "ACC_CYCLE_B", "account_to": "ACC_CYCLE_C", "amount": 49000.0})
    r3 = agent.process_transaction({"tx_id": "TX_CYC_3", "account_from": "ACC_CYCLE_C", "account_to": "ACC_CYCLE_A", "amount": 48500.0})
    print(f"[3] Cycle Completion: Risk={r3['aggregate_risk_score']}/100, Alert={r3['alert_triggered']}, Reasons={r3['reason_codes']}")

    # 4. Crypto Mixer Transaction
    crypto_mixer = {
        "tx_hash": "0x7a3f81e01bc",
        "from_wallet": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "to_wallet": "3MixerTumblerService99",
        "amount": 8.5,
        "currency": "BTC",
        "mixer_risk": True,
    }
    r4 = agent.process_transaction(crypto_mixer)
    print(f"[4] Crypto Mixer: Risk={r4['aggregate_risk_score']}/100, Alert={r4['alert_triggered']}, Reasons={r4['reason_codes']}")

    # 5. Explain Decision (2-Hop Subgraph Extraction)
    print("\n" + "-" * 70)
    print("[EXPLAIN] Calling explain_decision('TX_CYC_3')...")
    print("-" * 70)
    explanation = agent.explain_decision("TX_CYC_3")
    print(explanation["investigator_summary"])
    print(f"\nSubgraph Extracted: {explanation['structural_metrics']['subgraph_node_count']} nodes, {explanation['structural_metrics']['subgraph_edge_count']} edges.")
    print("=" * 70 + "\n")
