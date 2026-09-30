"""
app/surveillance/router.py
=============================================================================
QuantumAML Nexus -- Live Surveillance Platform Endpoints
Lead Infrastructure Engineer Component:
Modular FastAPI router providing decoupled REST and WebSocket ingestion
for live Indian UPI switch transactions and cryptocurrency mempool transfers.
Operates with cryptographic data isolation from all historical training sets.
=============================================================================
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app.surveillance.schemas import (
    CryptoNetwork,
    CryptoTransferPayload,
    SurveillanceEnvelope,
    SurveillanceIngestResponse,
    SurveillanceStatusResponse,
    SurveillanceStreamType,
    UPITransactionPayload,
)
from app.surveillance.connection_manager import surveillance_manager
from app.surveillance.generators import mock_crypto_generator, mock_upi_generator
from app.surveillance.isolation_guard import isolation_auditor

# Ensure agent_engine is available for real-time scoring
try:
    from agent_engine import agent_engine
except ImportError:
    agent_engine = None

logger = logging.getLogger("SurveillanceRouter")

router = APIRouter(tags=["Live Surveillance Platform"])

START_TIME = time.time()
SEQUENCE_TRACKER = 0


# =============================================================================
# 1. REST INGESTION ENDPOINTS (DECOUPLED BANKING & CRYPTO)
# =============================================================================

@router.post(
    "/api/v1/surveillance/banking/ingest",
    response_model=SurveillanceIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest Real-Time UPI Transaction Payload",
)
async def ingest_banking_transaction(
    payload: UPITransactionPayload,
    background_tasks: BackgroundTasks,
) -> SurveillanceIngestResponse:
    """
    Ingests an incoming UPI banking switch transaction.
    Verifies anti-cross-contamination isolation, evaluates real-time AML risk,
    and broadcasts to decoupled banking WebSocket subscribers.
    """
    global SEQUENCE_TRACKER
    t0 = time.perf_counter()
    SEQUENCE_TRACKER += 1

    # 1. Verify strict zero-reference isolation from historical training sets
    payload_dict = payload.model_dump()
    is_clean, proof, violations = isolation_auditor.verify_isolation(
        payload_dict, "UPI_BANKING"
    )
    if not is_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CROSS_CONTAMINATION_DETECTED",
                "message": "Incoming payload references historical training dataset signatures.",
                "violations": violations,
            },
        )

    # 2. Score via AMLAgent Engine (with graceful standalone fallback)
    risk_score = 35.0
    risk_level = "Low"
    alert_triggered = False
    indicators = list(payload.anomaly_flags)

    if payload.rbi_threshold_breach:
        risk_score = max(risk_score, 82.0)
        indicators.append("RBI_LARGE_P2P_BREACH")
    if "SUB_THRESHOLD_STRUCTURING" in payload.anomaly_flags:
        risk_score = max(risk_score, 88.0)
    if payload.mcc == "7995":
        risk_score = max(risk_score, 78.0)
        indicators.append("HIGH_RISK_MCC_GAMBLING")

    if agent_engine is not None:
        try:
            agent_payload = {
                "tx_id": payload.txn_id,
                "account_from": payload.payer_vpa,
                "account_to": payload.payee_vpa,
                "amount": payload.amount_usd,
                "currency": "USD",
                "channel": "upi",
                "is_cross_border": False,
                "velocity_1h": len(payload.anomaly_flags) * 3,
            }
            res = agent_engine.evaluate(agent_payload)
            risk_score = float(res.get("risk_score", risk_score))
            risk_level = str(res.get("risk_level", "Low"))
            alert_triggered = bool(res.get("alert_triggered", False))
            for rule in res.get("fired_rules", []):
                if rule not in indicators:
                    indicators.append(rule)
        except Exception as e:
            logger.warning(f"Engine scoring fallback: {e}")

    alert_triggered = risk_score >= 75.0
    if alert_triggered and risk_level in ("Low", "Medium"):
        risk_level = "High" if risk_score < 90.0 else "Critical"

    # 3. Encapsulate in Surveillance Envelope
    envelope = SurveillanceEnvelope(
        event_id=str(uuid4()),
        stream_type=SurveillanceStreamType.UPI_BANKING,
        sequence_number=SEQUENCE_TRACKER,
        timestamp=payload.timestamp,
        isolation_proof=proof,
        data=payload,
    )

    # 4. Asynchronously broadcast exclusively to banking and unified channels
    recipients = await surveillance_manager.broadcast_banking(envelope.model_dump())

    latency_ms = (time.perf_counter() - t0) * 1000.0

    return SurveillanceIngestResponse(
        status="ALERT_TRIGGERED" if alert_triggered else "ACCEPTED",
        event_id=envelope.event_id,
        stream_type=SurveillanceStreamType.UPI_BANKING,
        risk_score=round(risk_score, 1),
        risk_level=risk_level,
        alert_triggered=alert_triggered,
        fired_indicators=indicators,
        broadcast_recipients=recipients,
        processing_latency_ms=round(latency_ms, 2),
        isolation_verified=True,
    )


@router.post(
    "/api/v1/surveillance/crypto/ingest",
    response_model=SurveillanceIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest Live Cryptocurrency Transfer Payload",
)
async def ingest_crypto_transfer(
    payload: CryptoTransferPayload,
    background_tasks: BackgroundTasks,
) -> SurveillanceIngestResponse:
    """
    Ingests an incoming cryptocurrency mempool transfer.
    Verifies anti-cross-contamination isolation, evaluates mixer/peeling chain risk,
    and broadcasts to decoupled crypto WebSocket subscribers.
    """
    global SEQUENCE_TRACKER
    t0 = time.perf_counter()
    SEQUENCE_TRACKER += 1

    # 1. Verify strict zero-reference isolation from historical training sets
    payload_dict = payload.model_dump()
    is_clean, proof, violations = isolation_auditor.verify_isolation(
        payload_dict, "CRYPTO_TRANSFER"
    )
    if not is_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CROSS_CONTAMINATION_DETECTED",
                "message": "Incoming payload references historical training dataset signatures.",
                "violations": violations,
            },
        )

    # 2. Score via AMLAgent Engine
    risk_score = 25.0
    risk_level = "Low"
    alert_triggered = False
    indicators = list(payload.risk_tags)

    if payload.mixer_risk:
        risk_score = max(risk_score, 92.5)
        indicators.append("UNHOSTED_MIXER_PROXIMITY")
    if payload.peeling_chain:
        risk_score = max(risk_score, 88.0)
        indicators.append("MULTI_HOP_PEELING_CHAIN")
    if payload.hop_count >= 5:
        risk_score = max(risk_score, 84.0)

    if agent_engine is not None:
        try:
            agent_payload = {
                "tx_hash": payload.tx_hash,
                "from_wallet": payload.from_wallet,
                "to_wallet": payload.to_wallet,
                "amount_btc": payload.amount_crypto if payload.asset_symbol == "BTC" else None,
                "amount": payload.amount_usd,
                "currency": payload.asset_symbol,
                "channel": "crypto",
                "mixer_risk": payload.mixer_risk,
                "is_peeling_chain": payload.peeling_chain,
                "hop_count": payload.hop_count,
            }
            res = agent_engine.evaluate(agent_payload)
            risk_score = float(res.get("risk_score", risk_score))
            risk_level = str(res.get("risk_level", "Low"))
            alert_triggered = bool(res.get("alert_triggered", False))
            for rule in res.get("fired_rules", []):
                if rule not in indicators:
                    indicators.append(rule)
        except Exception as e:
            logger.warning(f"Engine scoring fallback: {e}")

    alert_triggered = risk_score >= 75.0
    if alert_triggered and risk_level in ("Low", "Medium"):
        risk_level = "Critical" if risk_score >= 90.0 else "High"

    # 3. Encapsulate in Surveillance Envelope
    envelope = SurveillanceEnvelope(
        event_id=str(uuid4()),
        stream_type=SurveillanceStreamType.CRYPTO_TRANSFER,
        sequence_number=SEQUENCE_TRACKER,
        timestamp=payload.timestamp,
        isolation_proof=proof,
        data=payload,
    )

    # 4. Asynchronously broadcast exclusively to crypto and unified channels
    recipients = await surveillance_manager.broadcast_crypto(envelope.model_dump())

    latency_ms = (time.perf_counter() - t0) * 1000.0

    return SurveillanceIngestResponse(
        status="ALERT_TRIGGERED" if alert_triggered else "ACCEPTED",
        event_id=envelope.event_id,
        stream_type=SurveillanceStreamType.CRYPTO_TRANSFER,
        risk_score=round(risk_score, 1),
        risk_level=risk_level,
        alert_triggered=alert_triggered,
        fired_indicators=indicators,
        broadcast_recipients=recipients,
        processing_latency_ms=round(latency_ms, 2),
        isolation_verified=True,
    )


# =============================================================================
# 2. PROCEDURAL SYNTHETIC STREAM SAMPLERS (ZERO DATASET REPLAY)
# =============================================================================

@router.get(
    "/api/v1/surveillance/banking/sample",
    response_model=UPITransactionPayload,
    status_code=status.HTTP_200_OK,
    summary="Generate Isolated Synthetic UPI Payload",
)
async def sample_banking_payload(
    anomaly_mode: Optional[str] = Query(
        None,
        description="Optional pattern: None (benign), 'STRUCTURING', 'GAMBLING_BURST', 'THRESHOLD_BREACH'",
    ),
    amount_inr: Optional[float] = Query(None, description="Force nominal transfer volume in INR"),
) -> UPITransactionPayload:
    """
    Procedurally synthesizes a real-time UPI transaction with 100% statistical isolation
    from historical training datasets.
    """
    return mock_upi_generator.generate_upi_payload(
        anomaly_mode=anomaly_mode,
        forced_amount_inr=amount_inr,
    )


@router.get(
    "/api/v1/surveillance/crypto/sample",
    response_model=CryptoTransferPayload,
    status_code=status.HTTP_200_OK,
    summary="Generate Isolated Synthetic Crypto Payload",
)
async def sample_crypto_payload(
    anomaly_mode: Optional[str] = Query(
        None,
        description="Optional pattern: None (benign), 'MIXER_TUMBLER', 'PEELING_CHAIN', 'LARGE_UNHOSTED'",
    ),
    network: CryptoNetwork = Query(CryptoNetwork.BITCOIN, description="Blockchain network"),
) -> CryptoTransferPayload:
    """
    Procedurally synthesizes a real-time cryptocurrency transfer with 100% statistical isolation
    from historical training datasets.
    """
    return mock_crypto_generator.generate_crypto_payload(
        anomaly_mode=anomaly_mode,
        network=network,
    )


# =============================================================================
# 3. PLATFORM TELEMETRY & ISOLATION AUDIT STATUS
# =============================================================================

@router.get(
    "/api/v1/surveillance/status",
    response_model=SurveillanceStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Surveillance Platform & Data Isolation Status",
)
async def get_surveillance_status() -> SurveillanceStatusResponse:
    """
    Returns operational health, subscriber pool counts, and cryptographic
    data isolation guarantees certifying zero cross-contamination.
    """
    uptime = time.time() - START_TIME
    subscribers = surveillance_manager.get_subscriber_counts()
    isolation_metrics = isolation_auditor.get_telemetry()

    return SurveillanceStatusResponse(
        platform="QuantumAML Nexus Live Surveillance Platform",
        version="3.1.0",
        status="HEALTHY",
        subscribers=subscribers,
        throughput_total=SEQUENCE_TRACKER,
        isolation_guarantee=isolation_metrics,
        uptime_seconds=round(uptime, 2),
    )


# =============================================================================
# 4. DECOUPLED WEBSOCKET STREAMING ENDPOINTS
# =============================================================================

@router.websocket("/ws/surveillance/banking")
async def websocket_banking_surveillance(websocket: WebSocket):
    """
    Dedicated decoupled WebSocket endpoint streaming live Indian UPI switch traffic.
    Excludes cryptocurrency transactions to prevent signal contamination.
    """
    await surveillance_manager.connect(websocket, channel="banking")
    try:
        # Send initial handshake message
        await websocket.send_json({
            "event": "CONNECTED",
            "channel": "banking",
            "message": "Connected to QuantumAML Nexus Banking Surveillance Stream (UPI/IMPS/NEFT).",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        while True:
            # Keep socket alive and receive client heartbeats/pings
            msg = await websocket.receive_text()
            if msg.lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await surveillance_manager.disconnect(websocket, channel="banking")
    except Exception as e:
        logger.error(f"Banking WebSocket error: {e}")
        await surveillance_manager.disconnect(websocket, channel="banking")


@router.websocket("/ws/surveillance/crypto")
async def websocket_crypto_surveillance(websocket: WebSocket):
    """
    Dedicated decoupled WebSocket endpoint streaming live cryptocurrency mempool transfers.
    Excludes fiat banking transactions for focused ledger surveillance.
    """
    await surveillance_manager.connect(websocket, channel="crypto")
    try:
        await websocket.send_json({
            "event": "CONNECTED",
            "channel": "crypto",
            "message": "Connected to QuantumAML Nexus Crypto Surveillance Stream (BTC/ETH/Mempool).",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        while True:
            msg = await websocket.receive_text()
            if msg.lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await surveillance_manager.disconnect(websocket, channel="crypto")
    except Exception as e:
        logger.error(f"Crypto WebSocket error: {e}")
        await surveillance_manager.disconnect(websocket, channel="crypto")


@router.websocket("/ws/surveillance/unified")
async def websocket_unified_surveillance(websocket: WebSocket):
    """
    Unified multi-rail WebSocket endpoint for joint financial crime war-rooms.
    Receives synchronized events across both banking and crypto channels.
    """
    await surveillance_manager.connect(websocket, channel="unified")
    try:
        await websocket.send_json({
            "event": "CONNECTED",
            "channel": "unified",
            "message": "Connected to QuantumAML Nexus Unified Multi-Rail Surveillance Stream.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        while True:
            msg = await websocket.receive_text()
            if msg.lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await surveillance_manager.disconnect(websocket, channel="unified")
    except Exception as e:
        logger.error(f"Unified WebSocket error: {e}")
        await surveillance_manager.disconnect(websocket, channel="unified")
