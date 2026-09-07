import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    BackgroundTasks,
    Body,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import REGISTRY, Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers.sar import router as sar_router
from app.schemas import (
    EllipticNodeInput,
    RiskEvaluationResponse,
    SAMLDInput,
    TimeSeriesInput,
    TransactionInput,
)
from app.schemas.sar import (
    SuspicionTypology,
)
from app.services.inference_engine import UnifiedInferenceEngine
from app.services.sar_service import sar_service
from app.worker import dispatch_investigator_alert

# Observability Configuration
logger = logging.getLogger("QuantumAML-API")
logging.basicConfig(level=logging.INFO)

# Global unified inference engine instance
engine: UnifiedInferenceEngine = UnifiedInferenceEngine()


# ------------------------------------------------------------------------------
# Prometheus Custom Metric Definitions & Registration
# ------------------------------------------------------------------------------
def _get_or_create_histogram(
    name: str, documentation: str, labelnames: list, buckets: list
) -> Histogram:
    try:
        return Histogram(name, documentation, labelnames=labelnames, buckets=buckets)
    except ValueError:
        return REGISTRY._names_to_collectors[name]


def _get_or_create_counter(name: str, documentation: str, labelnames: list) -> Counter:
    try:
        return Counter(name, documentation, labelnames=labelnames)
    except ValueError:
        return REGISTRY._names_to_collectors[name]


aml_inference_latency_seconds = _get_or_create_histogram(
    name="aml_inference_latency_seconds",
    documentation="Latency of AML model inference in seconds per dataset model",
    labelnames=["dataset_model"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
)

aml_transactions_evaluated_total = _get_or_create_counter(
    name="aml_transactions_evaluated_total",
    documentation="Total number of AML transactions evaluated by model and risk tier",
    labelnames=["dataset_model", "risk_tier"],
)

aml_anomalies_detected_total = _get_or_create_counter(
    name="aml_anomalies_detected_total",
    documentation="Total number of AML anomalies detected per dataset model",
    labelnames=["dataset_model"],
)


def _record_metrics(
    dataset_model: str, res: dict[str, Any], duration_seconds: float
) -> None:
    """Records latency observation, throughput by risk tier, and anomaly counters."""
    aml_inference_latency_seconds.labels(dataset_model=dataset_model).observe(
        duration_seconds
    )

    # Normalize risk tier to standard tiers: LOW, MEDIUM, HIGH, CRITICAL
    raw_tier = str(res.get("risk_tier", "LOW")).upper()
    if raw_tier in ("CRITICAL", "CRITICAL_SAR"):
        tier = "CRITICAL"
    elif raw_tier in ("HIGH",):
        tier = "HIGH"
    elif raw_tier in ("MEDIUM", "ELEVATED"):
        tier = "MEDIUM"
    else:
        tier = "LOW"

    aml_transactions_evaluated_total.labels(
        dataset_model=dataset_model, risk_tier=tier
    ).inc()

    if res.get("is_anomaly"):
        aml_anomalies_detected_total.labels(dataset_model=dataset_model).inc()


def queue_alert(res: dict):
    """Enqueues alert task to Celery broker with fallback to direct invocation."""
    try:
        dispatch_investigator_alert.delay(res)
    except Exception as e:
        logger.warning(
            "Failed to queue alert via Celery broker (%s), falling back to local dispatch.",
            e,
        )
        dispatch_investigator_alert(res)


# ------------------------------------------------------------------------------
# WebSocket Real-Time Broadcast Hub
# ------------------------------------------------------------------------------
class ConnectionManager:
    """Thread-safe asynchronous WebSocket connection manager for real-time inference streaming."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accepts the WebSocket handshake and registers the socket in the active pool."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(
            "WebSocket client connected. Active connections: %d",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket):
        """Safely removes the socket from active connections if present."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                "WebSocket client disconnected. Active connections: %d",
                len(self.active_connections),
            )

    async def broadcast(self, payload: dict):
        """
        Iterates through all active connections and transmits JSON payload.
        Catches closed/stale client sockets, collects dead connections, and
        purges them immediately without blocking or throwing unhandled exceptions.
        """
        if not self.active_connections:
            return

        async with self._lock:
            snapshot = list(self.active_connections)

        dead_connections: list[WebSocket] = []
        for connection in snapshot:
            try:
                await connection.send_json(payload)
            except Exception as e:
                logger.warning(
                    "Error sending WebSocket payload, scheduling socket cleanup: %s", e
                )
                dead_connections.append(connection)

        if dead_connections:
            async with self._lock:
                for dead_conn in dead_connections:
                    if dead_conn in self.active_connections:
                        self.active_connections.remove(dead_conn)
            logger.info(
                "Purged %d stale WebSocket connection(s). Remaining: %d",
                len(dead_connections),
                len(self.active_connections),
            )


manager = ConnectionManager()


# ------------------------------------------------------------------------------
# Asynchronous SAR Generation Pipeline & Typology Resolver
# ------------------------------------------------------------------------------
def _resolve_typology(
    engine_type: str,
    flags: list[str],
    payload: dict[str, Any],
) -> SuspicionTypology:
    """
    In-memory classification helper determining the appropriate FIU-IND SuspicionTypology.
    """
    if engine_type == "CRYPTO_FORENSICS":
        return SuspicionTypology.IN_TYP_VDA_MIX

    # FIAT_BANKING classification rules
    flags_set = set(flags) if flags else set()
    amount = float(payload.get("amount", 0.0) or 0.0)

    # 1. Structuring: PAN_STRUCTURING_EVASION flag or amount in [45000, 49999]
    if "PAN_STRUCTURING_EVASION" in flags_set or (45000.0 <= amount <= 49999.0):
        return SuspicionTypology.IN_TYP_STRUCT

    # 2. Hawala: HAWALA_WIRE flag or amount >= 25,00,000 (INR 2.5 million)
    if "HAWALA_WIRE" in flags_set or amount >= 2500000.0:
        return SuspicionTypology.IN_TYP_HAWALA

    # 3. Mule burst: MULE_BURST flag
    if "MULE_BURST" in flags_set:
        return SuspicionTypology.IN_TYP_MULE

    # Default fallback
    return SuspicionTypology.IN_TYP_STRUCT


async def process_sar_background(
    tx_payload: dict[str, Any],
    result_payload: dict[str, Any],
    typology: SuspicionTypology,
):
    """
    Asynchronously processes critical risk events in background without blocking
    inference latency, generating or aggregating SAR dossier records and broadcasting
    real-time regulatory alerts via WebSocket.
    """
    try:
        case = await sar_service.create_or_aggregate_sar(
            tx_payload=tx_payload,
            ml_result=result_payload,
            typology=typology,
        )
        logger.info(
            "SAR background processing complete: %s (Status: %s, Exposure: \u20b9%.2f, Typology: %s)",
            case.sar_id,
            case.status,
            case.total_exposure_inr,
            typology.value if hasattr(typology, "value") else typology,
        )

        # Broadcast real-time SAR alert packet to connected monitoring dashboards
        status_val = (
            case.status.value if hasattr(case.status, "value") else str(case.status)
        )
        sar_alert_packet = {
            "event": "SAR_DISPATCHED",
            "sar_id": case.sar_id,
            "exposure_inr": float(case.total_exposure_inr or 0.0),
            "exposure_btc": float(case.total_exposure_btc or 0.0),
            "status": status_val,
            "typology": typology.value if hasattr(typology, "value") else str(typology),
            "suspect": (
                (
                    getattr(case.suspect, "full_legal_name", None)
                    or getattr(case.suspect, "entity_name", None)
                )
                if case.suspect
                else (
                    tx_payload.get("account_from")
                    or tx_payload.get("node_id")
                    or "Unknown Suspect"
                )
            ),
            "triggering_tx_id": tx_payload.get("transaction_id")
            or tx_payload.get("node_id"),
            "timestamp": case.created_at.isoformat()
            if hasattr(case.created_at, "isoformat")
            else str(case.created_at),
        }
        await manager.broadcast(sar_alert_packet)
    except Exception as e:
        logger.error(
            "Failed to process SAR in background for payload %s: %s",
            tx_payload.get("transaction_id", "UNKNOWN"),
            str(e),
            exc_info=True,
        )


# ------------------------------------------------------------------------------
# 1. Lifespan & Startup Warmup
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    logger.info("Initializing QuantumAML Serving Layer...")
    if engine is None:
        engine = UnifiedInferenceEngine()
    engine.warmup()
    logger.info(
        "Engine warmup completed successfully. Loaded models: %s",
        list(engine.models.keys()),
    )
    yield
    logger.info("Shutting down QuantumAML Serving Layer...")


app = FastAPI(
    title="QuantumAML Nexus Serving Layer",
    version="2.0.0",
    description="Production continuous risk scoring and AML detection engine.",
    lifespan=lifespan,
)

# ------------------------------------------------------------------------------
# CORS Middleware Configuration (Resolves Preflight OPTIONS 405)
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# 2. Mount Prometheus FastAPI Instrumentator
# ------------------------------------------------------------------------------
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# ------------------------------------------------------------------------------
# 3. Health & Diagnostic Endpoints
# ------------------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "loaded_models": list(engine.models.keys()) if engine else [],
    }


# ------------------------------------------------------------------------------
# WebSocket Route (/ws/live)
# ------------------------------------------------------------------------------
@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Persistent WebSocket hub streaming live AML inference scoring events
    directly to connected frontend monitoring clients.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning("WebSocket client connection closed: %s", e)
        manager.disconnect(websocket)


# ------------------------------------------------------------------------------
# 4. Model Scoring Endpoints
# ------------------------------------------------------------------------------
@app.post("/api/v1/score/transaction", response_model=RiskEvaluationResponse)
async def score_transaction(
    payload: TransactionInput, background_tasks: BackgroundTasks
):
    try:
        t0 = time.perf_counter()
        res = engine.score_ibm_transaction(payload.model_dump())
        duration = time.perf_counter() - t0
        _record_metrics("ibm_transactions", res, duration)

        if res.get("is_anomaly"):
            background_tasks.add_task(queue_alert, res)

        # Construct normalized broadcast payload for FIAT banking
        flags = [res["recommended_action"]] if res.get("recommended_action") else []
        if res.get("is_anomaly") and "ANOMALY" not in flags:
            flags.insert(0, "ANOMALY")

        # Asynchronous SAR Generation / Ring Aggregation Pipeline
        raw_tier = str(res.get("risk_tier", "")).upper()
        score_val = float(res.get("risk_score", 0.0))
        is_structuring_candidate = (
            45000.0 <= float(payload.amount) <= 49999.0
            or "PAN_STRUCTURING_EVASION" in flags
            or "smurf" in str(payload.account_from).lower()
        )
        if (
            raw_tier in ("CRITICAL_SAR", "CRITICAL")
            or score_val >= 0.85
            or is_structuring_candidate
        ):
            txn_dict = payload.model_dump()
            typology = _resolve_typology("FIAT_BANKING", flags, txn_dict)
            background_tasks.add_task(
                process_sar_background,
                txn_dict,
                res,
                typology,
            )

        result_payload = {
            "engine": "FIAT_BANKING",
            "transaction_id": payload.transaction_id,
            "timestamp": payload.timestamp or datetime.now(timezone.utc).isoformat(),
            "rail": payload.payment_format,
            "from_entity": payload.account_from,
            "to_entity": payload.account_to,
            "amount": float(payload.amount),
            "currency": "INR",
            "risk_score": float(res.get("risk_score", 0.0)),
            "risk_tier": str(res.get("risk_tier", "LOW")),
            "latency_ms": float(res.get("latency_ms", round(duration * 1000, 2))),
            "flags": flags,
        }

        try:
            await manager.broadcast(result_payload)
        except Exception as ws_err:
            logger.warning("Failed to broadcast transaction score: %s", ws_err)

        return res
    except Exception as e:
        logger.error("Error evaluating IBM transaction: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/score/timeseries", response_model=RiskEvaluationResponse)
def score_timeseries(payload: TimeSeriesInput, background_tasks: BackgroundTasks):
    try:
        t0 = time.perf_counter()
        res = engine.score_timeseries(payload.model_dump())
        duration = time.perf_counter() - t0
        _record_metrics("timeseries", res, duration)

        if res.get("is_anomaly"):
            background_tasks.add_task(queue_alert, res)
        return res
    except Exception as e:
        logger.error("Error evaluating time-series event: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/score/crypto", response_model=RiskEvaluationResponse)
async def score_crypto(payload: EllipticNodeInput, background_tasks: BackgroundTasks):
    try:
        t0 = time.perf_counter()
        res = engine.score_elliptic(payload.model_dump())
        duration = time.perf_counter() - t0
        _record_metrics("elliptic", res, duration)

        if res.get("is_anomaly"):
            background_tasks.add_task(queue_alert, res)

        # Construct normalized crypto broadcast payload
        flags = [res["recommended_action"]] if res.get("recommended_action") else []
        if res.get("is_anomaly") and "ANOMALY" not in flags:
            flags.insert(0, "ANOMALY")

        # Asynchronous SAR Generation / Ring Aggregation Pipeline for Crypto
        raw_tier = str(res.get("risk_tier", "")).upper()
        score_val = float(res.get("risk_score", 0.0))
        if raw_tier in ("CRITICAL_SAR", "CRITICAL") or score_val >= 0.80:
            crypto_dict = payload.model_dump()
            background_tasks.add_task(
                process_sar_background,
                crypto_dict,
                res,
                SuspicionTypology.IN_TYP_VDA_MIX,
            )

        btc_amount = (
            round(abs(float(payload.btc_value)), 4)
            if payload.btc_value is not None
            else (
                round(abs(float(payload.features[0])), 4)
                if payload.features and abs(payload.features[0]) > 0
                else 1.0
            )
        )

        from_entity = payload.from_address or f"node_{payload.node_id}"
        to_entity = payload.to_address or f"cluster_{payload.node_id[:8]}"

        result_payload = {
            "engine": "CRYPTO_FORENSICS",
            "transaction_id": payload.tx_hash or payload.node_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rail": "BTC",
            "from_entity": from_entity,
            "to_entity": to_entity,
            "amount": float(btc_amount),
            "currency": "BTC",
            "risk_score": float(res.get("risk_score", 0.0)),
            "risk_tier": str(res.get("risk_tier", "LOW")),
            "latency_ms": float(res.get("latency_ms", round(duration * 1000, 2))),
            "flags": flags,
        }

        try:
            await manager.broadcast(result_payload)
        except Exception as ws_err:
            logger.warning("Failed to broadcast crypto score: %s", ws_err)

        return res
    except Exception as e:
        logger.error("Error evaluating crypto transaction: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/score/samld", response_model=RiskEvaluationResponse)
def score_samld(payload: SAMLDInput, background_tasks: BackgroundTasks):
    try:
        t0 = time.perf_counter()
        res = engine.score_samld(payload.model_dump())
        duration = time.perf_counter() - t0
        _record_metrics("samld", res, duration)

        if res.get("is_anomaly"):
            background_tasks.add_task(queue_alert, res)
        return res
    except Exception as e:
        logger.error("Error evaluating SAML-D transaction: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/score/amlsim", response_model=RiskEvaluationResponse)
def score_amlsim(payload: TransactionInput, background_tasks: BackgroundTasks):
    try:
        t0 = time.perf_counter()
        res = engine.score_amlsim(payload.model_dump())
        duration = time.perf_counter() - t0
        _record_metrics("amlsim", res, duration)

        if res.get("is_anomaly"):
            background_tasks.add_task(queue_alert, res)
        return res
    except Exception as e:
        logger.error("Error evaluating AMLSim transaction: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/score/batch")
def score_batch(
    items: list[dict[str, Any]] = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    dataset: str = Query(..., description="Target dataset for batch evaluation"),
):
    valid_datasets = [
        "ibm_transactions",
        "timeseries",
        "elliptic",
        "samld",
        "amlsim",
    ]
    if dataset not in valid_datasets:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid dataset '{dataset}'. Must be one of: {valid_datasets}",
        )

    scoring_methods = {
        "ibm_transactions": engine.score_ibm_transaction,
        "timeseries": engine.score_timeseries,
        "elliptic": engine.score_elliptic,
        "samld": engine.score_samld,
        "amlsim": engine.score_amlsim,
    }
    score_fn = scoring_methods[dataset]

    evaluations = []
    anomalies_detected = 0

    try:
        for item in items:
            t0 = time.perf_counter()
            res = score_fn(item)
            duration = time.perf_counter() - t0
            _record_metrics(dataset, res, duration)

            if res.get("is_anomaly"):
                anomalies_detected += 1
                if background_tasks is not None:
                    background_tasks.add_task(queue_alert, res)
            evaluations.append(res)

        return {
            "dataset": dataset,
            "total_evaluated": len(evaluations),
            "anomalies_detected": anomalies_detected,
            "evaluations": evaluations,
        }
    except Exception as e:
        logger.error(
            "Error during batch evaluation for %s: %s",
            dataset,
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# 5. Regulatory SAR Compliance & Reporting Router Mount
# ------------------------------------------------------------------------------
app.include_router(
    sar_router,
    prefix="/api/v1/sar",
    tags=["SAR Compliance & Reporting"],
)
