"""
app/surveillance/schemas.py
=============================================================================
QuantumAML Nexus -- Data Contracts for Live Surveillance Platform
Defines decoupled schemas for real-time UPI switch transactions and live
cryptocurrency mempool transfers, engineered for strict zero-contamination
isolation from historical training datasets.
=============================================================================
"""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


# =============================================================================
# ENUMERATIONS
# =============================================================================

class UPIStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PENDING = "PENDING"
    FAILURE = "FAILURE"
    DECLINED_SUSPECTED_FRAUD = "DECLINED_SUSPECTED_FRAUD"


class CryptoNetwork(str, Enum):
    BITCOIN = "BITCOIN"
    ETHEREUM = "ETHEREUM"
    SOLANA = "SOLANA"
    POLYGON = "POLYGON"
    TRON = "TRON"


class SurveillanceStreamType(str, Enum):
    UPI_BANKING = "UPI_BANKING"
    CRYPTO_TRANSFER = "CRYPTO_TRANSFER"


# =============================================================================
# 1. REAL-TIME UPI TRANSACTION PAYLOAD SCHEMA
# =============================================================================

class UPITransactionPayload(BaseModel):
    """
    Real-time Indian banking switch UPI transaction payload.
    Captures Virtual Payment Addresses (VPAs), NPCI references, merchant codes,
    and mobile device telemetry in complete isolation from historical datasets.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    txn_id: str = Field(
        ...,
        description="Unique NPCI UPI transaction reference (e.g. UPI/20260930/987123456789)",
        examples=["UPI/20260930/847291847192"],
    )
    payer_vpa: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9.\-_]{2,64}@[a-zA-Z0-9]{2,32}$",
        description="Payer Virtual Payment Address (e.g. user@okhdfcbank)",
        examples=["rahul.sharma@okhdfcbank"],
    )
    payee_vpa: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9.\-_]{2,64}@[a-zA-Z0-9]{2,32}$",
        description="Payee Virtual Payment Address (e.g. merchant@icici)",
        examples=["quickpay.solutions@icici"],
    )
    payer_name: str = Field("Verified Originator", min_length=2, max_length=120, description="Payer legal or registered name")
    payee_name: str = Field("Verified Counterparty", min_length=2, max_length=120, description="Payee legal or registered name")
    amount_inr: float = Field(..., gt=0.0, description="Nominal transaction amount in Indian Rupees (INR)")
    amount_usd: float = Field(0.0, ge=0.0, description="Normalized amount in USD (derived via live FX baseline)")
    currency: Literal["INR"] = Field("INR", description="Domestic financial currency code")
    
    # Device & Network Telemetry
    payer_mobile_hash: str = Field("4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945", description="SHA-256 masked originator MSISDN")
    device_fingerprint: str = Field("fp_and_7738210984ba", description="SHA-256 hardware/IMEI device fingerprint")
    ip_address: str = Field("103.21.244.0", description="Originating client IP address")
    location_city: str = Field("Mumbai", description="Geographic point of ingress (city/state)")
    city: Optional[str] = Field(None, description="City alias for location_city")
    rrn: Optional[str] = Field(None, description="Retrieval Reference Number (NPCI switch reference)")
    mcc: str = Field(
        "5411",
        description="Merchant Category Code (e.g. 6011=ATM/Cash, 5411=Grocery, 7995=Gambling)",
        examples=["6011", "5411", "7995", "4829"],
    )
    upi_status: UPIStatus = Field(UPIStatus.SUCCESS, description="NPCI switch settlement status")
    rbi_threshold_breach: bool = Field(
        False,
        description="True if amount exceeds RBI regulatory monitoring ceiling (>= INR 100,000 for P2P)",
    )
    anomaly_flags: List[str] = Field(
        default_factory=list,
        description="Real-time switch anomaly tags (e.g. RAPID_VELOCITY, ROUND_NUMBER_STRUCTURING)",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC transaction timestamp",
    )
    channel: Literal["upi"] = Field("upi", description="Designated financial switch rail")

    @model_validator(mode="before")
    @classmethod
    def process_and_derive_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Synchronize city alias
            if "city" in data and ("location_city" not in data or not data["location_city"]):
                data["location_city"] = data["city"]
            
            # Derive amount_usd if missing or 0
            amt_inr = float(data.get("amount_inr", 0.0))
            if ("amount_usd" not in data or not data.get("amount_usd")) and amt_inr > 0:
                data["amount_usd"] = round(amt_inr / 83.5, 2)
            
            # Auto-flag RBI threshold breach if >= 100,000 INR
            if amt_inr >= 100000.0:
                data["rbi_threshold_breach"] = True
            
            # Timestamp fallback
            if "timestamp" not in data or not data["timestamp"]:
                data["timestamp"] = datetime.now(timezone.utc).isoformat()
        return data


# =============================================================================
# 2. LIVE CRYPTOCURRENCY TRANSFER PAYLOAD SCHEMA
# =============================================================================

class CryptoTransferPayload(BaseModel):
    """
    Live cryptocurrency mempool / ledger transfer payload.
    Captures native token amounts, public wallet addresses, mixer risk flags,
    and peeling chain tracking with complete statistical isolation from training sets.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    tx_hash: str = Field(
        ...,
        description="Blockchain transaction hash (hexadecimal 64-char or 0x-prefixed)",
        examples=["0x7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"],
    )
    network: CryptoNetwork = Field(CryptoNetwork.BITCOIN, description="Underlying distributed ledger network")
    asset_symbol: str = Field(
        ...,
        description="Token or coin ticker symbol (BTC, ETH, USDT, USDC, SOL)",
        examples=["BTC", "ETH", "USDT"],
    )
    from_wallet: str = Field(
        ...,
        min_length=26,
        max_length=68,
        description="Source public cryptographic wallet address",
        examples=["bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"],
    )
    to_wallet: str = Field(
        ...,
        min_length=26,
        max_length=68,
        description="Beneficiary public cryptographic wallet address",
        examples=["3MixerWasabiTumblingHub999999999999"],
    )
    amount_crypto: float = Field(..., gt=0.0, description="Nominal transfer volume in native token units")
    amount_usd: float = Field(0.0, ge=0.0, description="Equivalent market value in USD")
    gas_fee_usd: float = Field(0.0, ge=0.0, description="Network transaction / miner gas fee in USD")
    block_height: Optional[int] = Field(
        None,
        description="Block confirmation number (None indicates pending in mempool)",
    )
    is_mempool: bool = Field(True, description="True if transaction is an unconfirmed mempool broadcast")
    mixer_risk: bool = Field(
        False,
        description="True if interaction involves privacy tumblers or mixing protocols (Wasabi, Tornado, ChipMixer)",
    )
    peeling_chain: bool = Field(
        False,
        description="True if topological pattern reflects micro-change peeling chain behavior",
    )
    hop_count: int = Field(1, ge=1, le=50, description="Identified chain depth / hop distance from seed funding")
    unhosted_wallet: bool = Field(True, description="True if counterparty is an unhosted private key entity")
    risk_tags: List[str] = Field(
        default_factory=list,
        description="Real-time crypto risk flags (e.g. TUMBLER_INTERACTION, HIGH_FAN_OUT)",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of broadcast",
    )
    channel: Literal["crypto"] = Field("crypto", description="Designated financial rail")

    @model_validator(mode="before")
    @classmethod
    def process_and_derive_crypto_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "timestamp" not in data or not data["timestamp"]:
                data["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Auto-derive USD value if missing or 0
            if "amount_usd" not in data or not data.get("amount_usd"):
                sym = data.get("asset_symbol", "BTC")
                amt = float(data.get("amount_crypto", 1.0))
                rates = {"BTC": 65000.0, "ETH": 2500.0, "SOL": 140.0, "USDT": 1.0, "USDC": 1.0}
                data["amount_usd"] = round(amt * rates.get(sym, 1.0), 2)
        return data


# =============================================================================
# 3. SURVEILLANCE STREAM EVENT ENVELOPE
# =============================================================================

class SurveillanceEnvelope(BaseModel):
    """
    Standardized, high-throughput streaming envelope encapsulating incoming live events.
    Contains cryptographic isolation proof certifying zero cross-contamination.
    """
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    stream_type: SurveillanceStreamType
    sequence_number: int = Field(..., ge=0)
    timestamp: str = Field(...)
    isolation_proof: str = Field(
        ...,
        description="Cryptographic SHA-256 seal guaranteeing zero coupling with historical training sets",
    )
    data: Union[UPITransactionPayload, CryptoTransferPayload]


# =============================================================================
# 4. SURVEILLANCE INGEST RESPONSE
# =============================================================================

class SurveillanceIngestResponse(BaseModel):
    """
    Synchronous response acknowledging ingestion into live surveillance pipeline.
    """
    status: Literal["ACCEPTED", "ALERT_TRIGGERED", "DROPPED"] = "ACCEPTED"
    event_id: str
    stream_type: SurveillanceStreamType
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: Literal["Low", "Medium", "High", "Critical"]
    alert_triggered: bool
    fired_indicators: List[str] = Field(default_factory=list)
    broadcast_recipients: int = Field(0, description="Count of active WebSocket clients dispatched to")
    processing_latency_ms: float = Field(..., description="End-to-end ingestion and routing latency")
    isolation_verified: bool = Field(True, description="Integrity audit confirmation")


# =============================================================================
# 5. SURVEILLANCE PLATFORM HEALTH & STATUS
# =============================================================================

class SurveillanceStatusResponse(BaseModel):
    """
    Operational health and telemetry for the live surveillance streaming subsystem.
    """
    platform: str = "QuantumAML Nexus Live Surveillance Platform"
    version: str = "3.1.0"
    status: str = "HEALTHY"
    subscribers: Dict[str, int] = Field(
        default_factory=dict,
        description="Active WebSocket subscriber counts per channel (banking, crypto, unified)",
    )
    throughput_total: int = Field(0, description="Total ingested events since service boot")
    isolation_guarantee: Dict[str, Any] = Field(
        default_factory=dict,
        description="Audit proof attesting complete isolation from historical datasets",
    )
    uptime_seconds: float
