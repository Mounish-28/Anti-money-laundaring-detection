"""
QuantumAML Nexus - Suspicious Activity / Transaction Reporting (SAR / STR) Schemas
===================================================================================

Defines strict, serializable Pydantic (v2 compatible) data contracts for regulatory
reporting aligned with Financial Intelligence Unit – India (FIU-IND) FINnet 2.0 /
FINGate specifications and Prevention of Money Laundering Act (PMLA) requirements.

Captures:
- Reporting entity credentials and suspect profiles
- Dual-rail transaction chronologies (Fiat UPI/IMPS/NEFT/RTGS and Crypto BTC/ETH)
- ML diagnostic telemetry and predictive drivers
- Standardized grounds of suspicion and typologies
- Automatic PMLA Rule 3 FIU deadline calculation (7 working days)
"""

import re
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ==============================================================================
# 1. Regulatory Enumerations
# ==============================================================================


class ReportingEntityType(str, Enum):
    """FIU-IND Reporting Entity Category Classifications."""

    SCHEDULED_COMMERCIAL_BANK = "SCHEDULED_COMMERCIAL_BANK"
    PAYMENT_AGGREGATOR = "PAYMENT_AGGREGATOR"
    VIRTUAL_DIGITAL_ASSET_SERVICE_PROVIDER = "VIRTUAL_DIGITAL_ASSET_SERVICE_PROVIDER"


class PaymentRail(str, Enum):
    """Payment Switch & Settlement Rails."""

    UPI = "UPI"
    IMPS = "IMPS"
    NEFT = "NEFT"
    RTGS = "RTGS"
    BTC = "BTC"
    ETH = "ETH"


class RiskTier(str, Enum):
    """Operational Risk Tiers for Surveillance & AML Scoring."""

    CRITICAL_SAR = "CRITICAL_SAR"
    HIGH = "HIGH"
    ELEVATED = "ELEVATED"
    LOW = "LOW"

    # Backward-compatible aliases for legacy codebase references
    HIGH_RISK = "HIGH"
    ELEVATED_RISK = "ELEVATED"
    LOW_RISK = "LOW"


class CaseStatus(str, Enum):
    """FIU-IND Regulatory Case Workflow Status."""

    PENDING_REVIEW = "PENDING_REVIEW"
    ESCALATED = "ESCALATED"
    FILED_WITH_FIU = "FILED_WITH_FIU"
    DISMISSED = "DISMISSED"


class SuspicionTypology(str, Enum):
    """
    Standardized Grounds of Suspicion Typologies under PMLA / FIU-IND Guidance.
    """

    IN_TYP_STRUCT = "IN_TYP_STRUCT"  # Structuring transactions below statutory ₹50,000 PAN threshold
    IN_TYP_HAWALA = "IN_TYP_HAWALA"  # High-value abnormal wire transfers lacking commercial rationale
    IN_TYP_MULE = (
        "IN_TYP_MULE"  # Multi-account smurfing and rapid draining through mule accounts
    )
    IN_TYP_VDA_MIX = "IN_TYP_VDA_MIX"  # High-velocity crypto peel chains, mixers, or unhosted illicit hops


# ==============================================================================
# Helper Functions: FIU Deadline & ID Generation
# ==============================================================================


def calculate_fiu_deadline(detection_date: datetime | None = None) -> datetime:
    """
    Calculates statutory FIU-IND filing deadline per PMLA Rule 3:
    Strictly 7 working days (excluding Saturdays and Sundays) from detection date.
    """
    if detection_date is None:
        detection_date = datetime.now(timezone.utc)

    current = detection_date
    working_days_added = 0
    while working_days_added < 7:
        current += timedelta(days=1)
        # Monday is 0, Sunday is 6. Skip Saturday (5) and Sunday (6)
        if current.weekday() < 5:
            working_days_added += 1

    return current


def generate_sar_id(prefix: str = "SAR-IND") -> str:
    """Generates standard regulatory identifier: SAR-IND-YYYYMMDD-XXXXXX."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_code = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{date_str}-{random_code}"


# ==============================================================================
# 2. Sub-Models
# ==============================================================================


class ReportingEntityInfo(BaseModel):
    """Details of the FIU-IND registered Reporting Entity (RE)."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    fiureid: str = Field(
        default="FIU-RE-COMM-2026-9081",
        description="FIU-IND assigned Reporting Entity Unique ID",
    )
    entity_name: str = Field(
        default="QuantumAML Nexus Surveillance Gateway",
        description="Legal name of reporting institution",
    )
    entity_category: ReportingEntityType = Field(
        default=ReportingEntityType.SCHEDULED_COMMERCIAL_BANK,
        description="Regulatory RE classification category",
    )
    principal_officer_id: str = Field(
        default="PO-REG-8819",
        description="Designated Principal Officer Registration ID",
    )


class SuspectEntityProfile(BaseModel):
    """Subject/Counterparty Entity Compliance Profile."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    entity_identifier: str = Field(
        ...,
        description="Unique identifier: Account Number, UPI VPA (user@bank), or Bitcoin Address",
    )
    entity_name: str | None = Field(
        default="ANONYMOUS_HOLDER",
        description="Legal name or account holder name",
    )
    entity_type: str = Field(
        default="INDIVIDUAL",
        description="Classification: 'INDIVIDUAL', 'CORPORATE', or 'UNHOSTED_WALLET'",
    )
    institution_code: str | None = Field(
        default=None,
        description="Branch IFSC code, bank institution name, or crypto cluster label",
    )
    kyc_risk_tier: RiskTier = Field(
        default=RiskTier.HIGH,
        description="Assigned AML risk tier rating",
    )
    is_pep: bool = Field(
        default=False,
        description="Politically Exposed Person (PEP) flag",
    )
    flags: list[str] = Field(
        default_factory=list,
        description="Automated risk indicators (e.g. 'PAN_MISSING', 'HIGH_RISK_IFSC')",
    )

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        valid_types = {"INDIVIDUAL", "CORPORATE", "UNHOSTED_WALLET", "MERCHANT"}
        if v.upper() not in valid_types:
            return "INDIVIDUAL"
        return v.upper()


class TransactionAuditRecord(BaseModel):
    """Individual transaction record forming the suspicious chronology."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    transaction_id: str = Field(
        ...,
        description="12-digit Indian Switch UTR or 64-char Bitcoin transaction hash",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Execution timestamp (UTC)",
    )
    rail: PaymentRail = Field(
        ...,
        description="Settlement rail (UPI, IMPS, NEFT, RTGS, BTC, ETH)",
    )
    amount: float = Field(
        ...,
        gt=0.0,
        description="Transaction principal value strictly greater than 0",
    )
    currency: str = Field(
        default="INR",
        description="Transaction currency denomination ('INR' or 'BTC')",
    )
    counterparty_from: str = Field(
        ...,
        description="Remitter account, VPA, or originating wallet address",
    )
    counterparty_to: str = Field(
        ...,
        description="Beneficiary account, VPA, or destination wallet address",
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="ML model inferred fraud probability score [0.0 - 1.0]",
    )
    detected_anomalies: list[str] = Field(
        default_factory=list,
        description="Specific anomaly tags triggered (e.g. 'PAN_STRUCTURING', 'HAWALA_VELOCITY')",
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        upper = v.upper()
        if upper not in {"INR", "BTC", "ETH", "USD"}:
            return "INR"
        return upper


class MLTelemetry(BaseModel):
    """Diagnostic audit trail of the machine learning inference decision."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    model_name: str = Field(
        default="CatBoost-Banking-v2.4",
        description="Name of the scoring engine (e.g., CatBoost-Banking-v2.4 or Elliptic-XGBoost-v1.2)",
    )
    model_version: str = Field(
        default="v2.4",
        description="Model artifact build version",
    )
    inference_latency_ms: float = Field(
        ...,
        ge=0.0,
        description="Latency recorded during model scoring (sub-50ms SLA target)",
    )
    feature_importance: dict[str, float] = Field(
        default_factory=dict,
        description="Top predictive feature attributions (e.g. 'amount_p99_ratio': 0.38)",
    )


class GroundsOfSuspicion(BaseModel):
    """Formal compliance justification for regulatory filing."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    primary_typology: SuspicionTypology = Field(
        ...,
        description="Primary FIU-IND criminal typology identified",
    )
    secondary_typologies: list[SuspicionTypology] = Field(
        default_factory=list,
        description="Secondary contributing financial crime patterns",
    )
    rule_triggers: list[str] = Field(
        default_factory=list,
        description="Specific statutory compliance rules breached (e.g., 'PMLA-SEC-12')",
    )
    narrative_summary: str = Field(
        ...,
        description="Legally structured audit narrative explaining grounds for suspicion",
    )


# ==============================================================================
# 3. Top-Level Request & Response Schemas
# ==============================================================================


class SARCreateRequest(BaseModel):
    """Payload dispatched to generate or escalate a Suspicious Activity Report."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    transaction_ids: list[str] = Field(
        ...,
        min_length=1,
        description="List of one or more transaction IDs (UTRs or BTC hashes) to attach",
    )
    primary_typology: SuspicionTypology = Field(
        default=SuspicionTypology.IN_TYP_STRUCT,
        description="Primary grounds of suspicion typology",
    )
    investigator_notes: str | None = Field(
        default=None,
        description="Analyst qualitative commentary or triage notes",
    )
    assigned_investigator: str | None = Field(
        default=None,
        description="Name or badge ID of assigned compliance officer",
    )
    suspect_identifier: str | None = Field(
        default=None,
        description="Primary suspect account or VPA if overriding transaction remitter",
    )
    reporting_entity: ReportingEntityInfo | None = Field(
        default=None,
        description="Custom reporting entity details (defaults to platform gateway if null)",
    )


class SARCaseRecord(BaseModel):
    """
    Full canonical Suspicious Transaction Report (STR / SAR) dossier model.
    Matches FIU-IND FINnet 2.0 / FINGate e-filing specifications.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_encoders={datetime: lambda dt: dt.isoformat()},
    )

    sar_id: str = Field(
        default_factory=generate_sar_id,
        description="Unique STR dossier ID formatted as SAR-IND-YYYYMMDD-XXXXXX",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp in UTC",
    )
    fiu_deadline: datetime = Field(
        default_factory=calculate_fiu_deadline,
        description="Statutory filing deadline (7 working days from detection per PMLA Rule 3)",
    )
    status: CaseStatus = Field(
        default=CaseStatus.PENDING_REVIEW,
        description="Current workflow state",
    )
    reporting_entity: ReportingEntityInfo = Field(
        default_factory=ReportingEntityInfo,
        description="Information about the filing institution",
    )
    suspect: SuspectEntityProfile = Field(
        ...,
        description="Primary suspect entity profile",
    )
    counterparty: SuspectEntityProfile | None = Field(
        default=None,
        description="Primary counterparty or beneficiary entity profile",
    )
    transactions: list[TransactionAuditRecord] = Field(
        default_factory=list,
        description="Chronological audit ledger of linked suspicious transactions",
    )
    total_exposure_inr: float = Field(
        default=0.0,
        ge=0.0,
        description="Aggregate suspicious volume exposure in Indian Rupees (INR)",
    )
    total_exposure_btc: float | None = Field(
        default=None,
        ge=0.0,
        description="Aggregate suspicious volume exposure in Bitcoin (BTC)",
    )
    ml_telemetry: MLTelemetry = Field(
        ...,
        description="Model inference diagnostics and feature attributions",
    )
    grounds_of_suspicion: GroundsOfSuspicion = Field(
        ...,
        description="Statutory typologies and compliance narrative",
    )
    assigned_analyst: str | None = Field(
        default=None,
        description="Assigned senior AML investigator or compliance officer",
    )

    @field_validator("sar_id")
    @classmethod
    def validate_sar_id_format(cls, v: str) -> str:
        pattern = r"^SAR-IND-\d{8}-[A-Z0-9]{4,12}$"
        if not re.match(pattern, v):
            # If invalid format, regenerate valid standard ID with original suffix
            return generate_sar_id()
        return v

    @model_validator(mode="after")
    def compute_exposures_and_defaults(self) -> "SARCaseRecord":
        """Auto-computes aggregate exposures from transaction items if not supplied."""
        if self.transactions:
            inr_sum = sum(
                tx.amount for tx in self.transactions if tx.currency.upper() == "INR"
            )
            btc_sum = sum(
                tx.amount for tx in self.transactions if tx.currency.upper() == "BTC"
            )

            if self.total_exposure_inr == 0.0 and inr_sum > 0:
                self.total_exposure_inr = round(inr_sum, 2)
            if self.total_exposure_btc is None and btc_sum > 0:
                self.total_exposure_btc = round(btc_sum, 6)

        return self


class SARListResponse(BaseModel):
    """Paginated regulatory SAR listing response envelope."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    total_count: int = Field(
        ..., ge=0, description="Total number of SAR cases matching query"
    )
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Items returned per page"
    )
    items: list[SARCaseRecord] = Field(
        default_factory=list, description="List of SAR case records"
    )
