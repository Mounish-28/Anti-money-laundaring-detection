"""
api_server.py
=============================================================================
QuantumAML Nexus -- FastAPI Core AML AI Agent Server
=============================================================================
Author: Advanced AML AI Engineer
Purpose:
  1. Serves the AMLAgent engine via production-grade REST APIs.
  2. POST /api/v1/transactions/analyze: Single transaction real-time scoring.
  3. POST /api/v1/transactions/batch: Bulk asynchronous transaction evaluation.
  4. GET  /api/v1/investigate/{tx_id}/subgraph: 2-hop neighborhood network data
     in JSON format directly compatible with vis.js and Cytoscape.
  5. GET  /health: Health-check endpoint verifying model weights, pipeline
     status, and active graph telemetry.
  6. Pydantic validation schemas, structured error handling, and CORS middleware
     for http://localhost:3000 and http://localhost:8501.
=============================================================================
"""

from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import logging
import os
import sys
import time
from typing import Any, Dict, List, Literal, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

# Ensure root directory is in sys.path
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from agent_engine import AMLAgent, agent_engine

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AMLApiServer")

# Track server startup time for health telemetry
SERVER_START_TIME = time.time()


# =============================================================================
# 1. PYDANTIC DATA SCHEMAS
# =============================================================================

class TransactionPayload(BaseModel):
    """
    Polymorphic transaction payload supporting both fiat and crypto schemas.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # Identifiers
    tx_id: Optional[str] = Field(None, description="Unique transaction ID (Fiat)")
    tx_hash: Optional[str] = Field(None, description="Transaction hash (Crypto)")

    # Fiat rail fields
    account_from: Optional[str] = Field(None, description="Originator account number / IBAN")
    account_to: Optional[str] = Field(None, description="Beneficiary account number / IBAN")
    sender_id: Optional[str] = Field(None, description="Alternative sender ID")
    receiver_id: Optional[str] = Field(None, description="Alternative receiver ID")

    # Crypto rail fields
    from_wallet: Optional[str] = Field(None, description="Source crypto wallet address")
    to_wallet: Optional[str] = Field(None, description="Destination crypto wallet address")
    amount_btc: Optional[float] = Field(None, ge=0, description="Amount in Bitcoin")
    amount_eth: Optional[float] = Field(None, ge=0, description="Amount in Ethereum")
    mixer_risk: Optional[bool] = Field(False, description="Flag indicating tumbler / mixer interaction")

    # Common financial fields
    amount: Optional[float] = Field(None, ge=0, description="Nominal transaction amount")
    currency: Optional[str] = Field("USD", description="Currency ISO code or token ticker (USD, EUR, BTC, ETH)")
    timestamp: Optional[str] = Field(None, description="ISO 8601 transaction timestamp")
    is_cross_border: Optional[bool] = Field(False, description="Flag for cross-border international transfers")
    channel: Optional[str] = Field(None, description="Financial rail/channel (fiat, crypto, wire, ach)")
    memo: Optional[str] = Field("", description="Transaction remittance note or smart contract memo")


class EntityPair(BaseModel):
    source: str
    target: str


class AnalysisResponse(BaseModel):
    """
    Real-time transaction risk analysis result.
    """
    tx_id: str
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Composite AML risk score (0-100)")
    risk_level: Literal["Low", "Medium", "High", "Critical"] = Field(
        ..., description="Standardized AML risk tier"
    )
    alert_triggered: bool = Field(..., description="True if risk_score >= 75.0")
    fired_rules: List[str] = Field(default_factory=list, description="List of detected anomaly reason codes")
    severity_tier: str = Field(..., description="Operational tier (LOW_NOMINAL, HIGH_RISK, CRITICAL_SAR)")
    financial_rail: str = Field(..., description="'fiat' or 'crypto'")
    amount_usd: float = Field(..., description="Normalized transaction amount in USD")
    entities: EntityPair
    gnn_score: float = Field(..., description="Inductive GNN topological risk score")
    ensemble_score: float = Field(..., description="Temporal ensemble velocity risk score")
    inference_latency_ms: float = Field(..., description="End-to-end evaluation time in milliseconds")
    audit_hash: str = Field(..., description="Cryptographic SHA-256 tamper-evident hash")
    summary: str = Field(..., description="Human-readable decision summary")


class BatchTransactionPayload(BaseModel):
    """
    Batch transaction payload for bulk asynchronous scoring.
    """
    transactions: List[TransactionPayload] = Field(
        ..., min_length=1, max_length=1000, description="List of transaction payloads"
    )


class BatchAnalysisResponse(BaseModel):
    """
    Response schema for batch scoring operations.
    """
    batch_id: str
    total_processed: int
    alerts_triggered: int
    total_latency_ms: float
    results: List[AnalysisResponse]


class VisNode(BaseModel):
    id: str
    label: str
    group: str
    color: Dict[str, str]
    shape: str
    size: int
    title: str
    in_degree: int
    out_degree: int
    total_in_flow_usd: float
    total_out_flow_usd: float


class VisEdge(BaseModel):
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    label: str
    arrows: str = "to"
    color: Dict[str, str]
    width: int
    title: str
    tx_id: str
    amount_usd: float


class VisNetworkData(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class CytoscapeElement(BaseModel):
    data: Dict[str, Any]


class SubgraphResponse(BaseModel):
    """
    2-Hop neighborhood graph data compatible with vis.js and Cytoscape.
    """
    tx_id: str
    focal_entities: EntityPair
    aggregate_risk_score: float
    severity_tier: str
    reason_codes: List[str]
    structural_metrics: Dict[str, Any]
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    vis_network: VisNetworkData
    cytoscape_elements: List[Dict[str, Any]]
    investigator_summary: str
    audit_hash: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    uptime_seconds: float
    timestamp: str
    models: Dict[str, Any]
    graph_state: Dict[str, Any]


class ErrorDetail(BaseModel):
    code: str
    message: str
    timestamp: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


# =============================================================================
# 2. FASTAPI APPLICATION SETUP & MIDDLEWARE
# =============================================================================

app = FastAPI(
    title="QuantumAML Nexus Agent Server",
    description="High-Throughput Autonomous AML AI Agent Service with Inductive GNN and Temporal Ensembles",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configured for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8501",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# 3. STRUCTURED EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Structured handler for standard HTTP exceptions."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code=f"HTTP_{exc.status_code}",
                message=str(exc.detail),
                timestamp=now_iso,
            ),
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Structured handler for Pydantic schema validation failures."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request payload failed Pydantic schema validation.",
                timestamp=now_iso,
                details=exc.errors(),
            ),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Fallback handler for unhandled internal server exceptions."""
    now_iso = datetime.now(timezone.utc).isoformat()
    logger.exception(f"Unhandled server error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message=f"An unexpected error occurred: {str(exc)}",
                timestamp=now_iso,
            ),
        ).model_dump(),
    )


# =============================================================================
# 4. REST API ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System Health"])
async def health_check() -> HealthResponse:
    """
    Health-check endpoint verifying model weights, pipeline readiness,
    and active graph telemetry.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    uptime = time.time() - SERVER_START_TIME

    # Check GNN and Ensemble pipeline status
    gnn_ok = hasattr(agent_engine, "gnn_module") and agent_engine.gnn_module is not None
    ens_ok = hasattr(agent_engine, "ensemble_module") and agent_engine.ensemble_module is not None

    return HealthResponse(
        status="healthy" if (gnn_ok and ens_ok) else "degraded",
        service="QuantumAML Nexus Agent Server",
        version="3.0.0",
        uptime_seconds=round(uptime, 2),
        timestamp=now_iso,
        models={
            "gnn_module": {
                "status": "online" if gnn_ok else "offline",
                "framework": "PyTorch Geometric / PyTorch",
                "architecture": "Two-Layer Inductive GraphSAGE (SAGEConv)",
                "weights": "initialized_in_memory",
            },
            "temporal_ensemble": {
                "status": "online" if ens_ok else "offline",
                "framework": "LightGBM / XGBoost",
                "architecture": "Multi-Horizon EWMA Gradient Boosted Classifier",
                "weights": "initialized_in_memory",
            },
        },
        graph_state={
            "active_nodes_count": agent_engine.graph.number_of_nodes(),
            "active_edges_count": agent_engine.graph.number_of_edges(),
            "indexed_transactions_count": len(agent_engine.transactions),
            "total_alerts_count": len(agent_engine.alerts),
            "alert_threshold": agent_engine.alert_threshold,
        },
    )


@app.post(
    "/api/v1/transactions/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    tags=["Transaction Analysis"],
)
async def analyze_transaction(payload: TransactionPayload) -> AnalysisResponse:
    """
    Ingests a single transaction payload (handling both fiat and crypto fields),
    runs it through AMLAgent.evaluate(), and returns the risk score (0-100),
    risk level (Low/Medium/High/Critical), and fired alert rules.
    """
    try:
        raw_dict = payload.model_dump(exclude_none=True)
        # Execute AMLAgent.evaluate()
        result = agent_engine.evaluate(raw_dict)

        # Generate summary string
        level = result["risk_level"]
        score = result["risk_score"]
        rules = result["fired_rules"]
        rules_str = ", ".join(rules) if rules else "NOMINAL_CLEAR"
        summary = (
            f"[{level.upper()}] Risk: {score:.1f}/100. "
            f"Entities: {result['entities']['source']} -> {result['entities']['target']}. "
            f"Fired Rules: {rules_str}."
        )

        return AnalysisResponse(
            tx_id=result["tx_id"],
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            alert_triggered=result["alert_triggered"],
            fired_rules=result["fired_rules"],
            severity_tier=result["severity_tier"],
            financial_rail=result["financial_rail"],
            amount_usd=result["amount_usd"],
            entities=EntityPair(
                source=result["entities"]["source"],
                target=result["entities"]["target"],
            ),
            gnn_score=result["gnn_score"],
            ensemble_score=result["ensemble_score"],
            inference_latency_ms=result["inference_latency_ms"],
            audit_hash=result["audit_hash"],
            summary=summary,
        )
    except Exception as e:
        logger.error(f"Error evaluating transaction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference pipeline execution error: {str(e)}",
        )


@app.post(
    "/api/v1/transactions/batch",
    response_model=BatchAnalysisResponse,
    status_code=status.HTTP_200_OK,
    tags=["Transaction Analysis"],
)
async def analyze_batch_transactions(batch: BatchTransactionPayload) -> BatchAnalysisResponse:
    """
    Accepts a list of transactions for bulk asynchronous scoring.
    """
    t0 = time.perf_counter()
    batch_id = f"BATCH_{int(time.time()*1000)}"

    loop = asyncio.get_event_loop()
    results: List[AnalysisResponse] = []
    alerts_count = 0

    # Execute scoring in worker pool
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            loop.run_in_executor(
                executor,
                agent_engine.evaluate,
                tx.model_dump(exclude_none=True),
            )
            for tx in batch.transactions
        ]
        raw_evaluations = await asyncio.gather(*futures)

    for res in raw_evaluations:
        level = res["risk_level"]
        score = res["risk_score"]
        rules = res["fired_rules"]
        rules_str = ", ".join(rules) if rules else "NOMINAL_CLEAR"
        summary = (
            f"[{level.upper()}] Risk: {score:.1f}/100. "
            f"Entities: {res['entities']['source']} -> {res['entities']['target']}. "
            f"Fired Rules: {rules_str}."
        )

        if res["alert_triggered"]:
            alerts_count += 1

        results.append(
            AnalysisResponse(
                tx_id=res["tx_id"],
                risk_score=res["risk_score"],
                risk_level=res["risk_level"],
                alert_triggered=res["alert_triggered"],
                fired_rules=res["fired_rules"],
                severity_tier=res["severity_tier"],
                financial_rail=res["financial_rail"],
                amount_usd=res["amount_usd"],
                entities=EntityPair(
                    source=res["entities"]["source"],
                    target=res["entities"]["target"],
                ),
                gnn_score=res["gnn_score"],
                ensemble_score=res["ensemble_score"],
                inference_latency_ms=res["inference_latency_ms"],
                audit_hash=res["audit_hash"],
                summary=summary,
            )
        )

    total_latency = (time.perf_counter() - t0) * 1000.0

    return BatchAnalysisResponse(
        batch_id=batch_id,
        total_processed=len(results),
        alerts_triggered=alerts_count,
        total_latency_ms=round(total_latency, 2),
        results=results,
    )


@app.get(
    "/api/v1/investigate/{tx_id}/subgraph",
    response_model=SubgraphResponse,
    status_code=status.HTTP_200_OK,
    tags=["Forensic Investigation"],
)
async def get_transaction_subgraph(tx_id: str) -> SubgraphResponse:
    """
    Returns node and edge network data (JSON format compatible with vis.js
    and Cytoscape) for the 2-hop neighborhood of a flagged transaction.
    """
    if tx_id not in agent_engine.transactions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction ID '{tx_id}' not found in active agent memory.",
        )

    try:
        explanation = agent_engine.explain_decision(tx_id)
        focal_src = explanation["focal_entities"]["source"]
        focal_dst = explanation["focal_entities"]["target"]

        # 1. Transform Nodes into vis.js & Cytoscape specs
        vis_nodes = []
        cyto_elements = []

        for n in explanation["subgraph"]["nodes"]:
            nid = n["node_id"]
            is_focal = n["is_focal_entity"]
            entity_type = n.get("entity_type", "ACCOUNT")

            # Stylistic mapping
            if nid == focal_src:
                bg_color = "#f97316"  # Orange: Origin focal
                border_color = "#c2410c"
                group = "focal_source"
            elif nid == focal_dst:
                bg_color = "#ef4444"  # Red: Target focal
                border_color = "#b91c1c"
                group = "focal_target"
            else:
                bg_color = "#3b82f6"  # Blue: 2-hop neighbor
                border_color = "#1d4ed8"
                group = "neighbor"

            title_tooltip = (
                f"Node: {nid}\n"
                f"Type: {entity_type}\n"
                f"In-Degree: {n['in_degree']} | Out-Degree: {n['out_degree']}\n"
                f"Inflow: ${n['total_in_flow_usd']:,.2f} | Outflow: ${n['total_out_flow_usd']:,.2f}"
            )

            vis_nodes.append({
                "id": nid,
                "label": f"{nid}\n({entity_type})",
                "group": group,
                "color": {"background": bg_color, "border": border_color},
                "shape": "diamond" if entity_type == "WALLET" else "dot",
                "size": 30 if is_focal else 18,
                "title": title_tooltip,
                "in_degree": n["in_degree"],
                "out_degree": n["out_degree"],
                "total_in_flow_usd": n["total_in_flow_usd"],
                "total_out_flow_usd": n["total_out_flow_usd"],
            })

            cyto_elements.append({
                "data": {
                    "id": nid,
                    "label": nid,
                    "entity_type": entity_type,
                    "is_focal": is_focal,
                    "in_degree": n["in_degree"],
                    "out_degree": n["out_degree"],
                    "in_flow": n["total_in_flow_usd"],
                    "out_flow": n["total_out_flow_usd"],
                }
            })

        # 2. Transform Edges into vis.js & Cytoscape specs
        vis_edges = []
        for e in explanation["subgraph"]["edges"]:
            is_focal_tx = e["is_focal_transaction"]
            edge_color = "#ef4444" if is_focal_tx else "#94a3b8"
            edge_width = 3 if is_focal_tx else 1

            edge_label = f"${e['amount_usd']:,.0f}"

            vis_edges.append({
                "from": e["source"],
                "to": e["target"],
                "label": edge_label,
                "arrows": "to",
                "color": {"color": edge_color},
                "width": edge_width,
                "title": f"TX: {e['tx_id']}\nAmount: ${e['amount_usd']:,.2f} {e['currency']}\nTimestamp: {e['timestamp']}",
                "tx_id": e["tx_id"],
                "amount_usd": e["amount_usd"],
            })

            cyto_elements.append({
                "data": {
                    "id": f"e_{e['source']}_{e['target']}_{e['tx_id']}",
                    "source": e["source"],
                    "target": e["target"],
                    "label": edge_label,
                    "tx_id": e["tx_id"],
                    "amount_usd": e["amount_usd"],
                    "is_focal": is_focal_tx,
                }
            })

        return SubgraphResponse(
            tx_id=tx_id,
            focal_entities=EntityPair(source=focal_src, target=focal_dst),
            aggregate_risk_score=explanation["aggregate_risk_score"],
            severity_tier=explanation["severity_tier"],
            reason_codes=explanation["reason_codes"],
            structural_metrics=explanation["structural_metrics"],
            nodes=explanation["subgraph"]["nodes"],
            edges=explanation["subgraph"]["edges"],
            vis_network=VisNetworkData(nodes=vis_nodes, edges=vis_edges),
            cytoscape_elements=cyto_elements,
            investigator_summary=explanation["investigator_summary"],
            audit_hash=explanation["audit_hash"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting subgraph for {tx_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Subgraph extraction error: {str(e)}",
        )


# =============================================================================
# 5. CLI RUNNER
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    logger.info(f"Starting QuantumAML Nexus API Server on {host}:{port}")
    uvicorn.run("api_server:app", host=host, port=port, reload=False)
