from typing import Any

from pydantic import BaseModel


class RiskEvaluationResponse(BaseModel):
    entity_id: str
    dataset: str
    risk_score: float
    risk_tier: str
    is_anomaly: bool
    recommended_action: str
    latency_ms: float
    metadata: dict[str, Any] | None = None
