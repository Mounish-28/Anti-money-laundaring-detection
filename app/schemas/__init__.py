from typing import Any

from app.schemas.crypto import EllipticNodeInput
from app.schemas.response import RiskEvaluationResponse
from app.schemas.samld import SAMLDInput
from app.schemas.sar import (
    CaseStatus,
    GroundsOfSuspicion,
    MLTelemetry,
    PaymentRail,
    ReportingEntityInfo,
    ReportingEntityType,
    RiskTier,
    SARCaseRecord,
    SARCreateRequest,
    SARListResponse,
    SuspectEntityProfile,
    SuspicionTypology,
    TransactionAuditRecord,
    calculate_fiu_deadline,
    generate_sar_id,
)
from app.schemas.timeseries import TimeSeriesInput
from app.schemas.transaction import AMLSimInput, TransactionInput

# Backward compatibility exports for legacy router references
TransactionScoreRequest = TransactionInput
CryptoScoreRequest = EllipticNodeInput
ScoreResponse = RiskEvaluationResponse
BatchScoreResponse = dict[str, Any]
BatchScoreItem = RiskEvaluationResponse
AlertRecord = RiskEvaluationResponse
ActionType = str

__all__ = [
    "TransactionInput",
    "AMLSimInput",
    "TimeSeriesInput",
    "EllipticNodeInput",
    "SAMLDInput",
    "RiskEvaluationResponse",
    "TransactionScoreRequest",
    "CryptoScoreRequest",
    "ScoreResponse",
    "BatchScoreResponse",
    "BatchScoreItem",
    "AlertRecord",
    "ActionType",
    # FIU-IND SAR / STR Models & Enums
    "ReportingEntityType",
    "PaymentRail",
    "RiskTier",
    "CaseStatus",
    "SuspicionTypology",
    "ReportingEntityInfo",
    "SuspectEntityProfile",
    "TransactionAuditRecord",
    "MLTelemetry",
    "GroundsOfSuspicion",
    "SARCreateRequest",
    "SARCaseRecord",
    "SARListResponse",
    "calculate_fiu_deadline",
    "generate_sar_id",
]
