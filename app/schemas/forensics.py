"""
QuantumAML Nexus - Forensic Investigation Workbench Schemas
=============================================================

Pydantic validation schemas supporting the standalone forensic investigation
workbench in 'quantumaml-investigation':
- CaseSummary: Priority triage queue alerts with risk metrics and SLA deadlines.
- GraphNode, GraphEdge, GraphResponse: Multi-hop transaction link topologies for Cytoscape.js.
- FeatureAttribution, ExplainabilityResponse: CatBoost/XGBoost TreeSHAP model attribution.
- SuspectProfileResponse: KYC compliance profile and entity freeze state.
- StatusUpdateRequest: Case workflow state transitions.
- SarGenerateRequest: Regulatory SAR dossier generation payload.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CaseSummary(BaseModel):
    """Priority triage queue case summary schema."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(..., description="Canonical case identifier (e.g. ESC-90812)")
    rail: str = Field(..., description="Payment rail: UPI, IMPS, or BTC")
    amount: float = Field(..., description="Transaction or cluster exposure volume")
    currency: str = Field(default="INR", description="Fiat or crypto currency code")
    risk_score: float = Field(..., description="ML anomaly probability (0.0 - 1.0)")
    risk_tier: str = Field(..., description="AML risk tier: CRITICAL, HIGH, MEDIUM, LOW")
    typology: str = Field(..., description="Primary detected laundering typology")
    suspect_entity: str = Field(..., description="Identified suspect handle, account, or VPA")
    sla_deadline: str = Field(..., description="FIU statutory compliance countdown ISO deadline")
    status: str = Field(default="OPEN", description="Investigation status: OPEN, UNDER_REVIEW, ESCALATED, FILED_WITH_FIU")
    created_at: str = Field(..., description="Alert detection ISO timestamp")

    @model_validator(mode="before")
    @classmethod
    def sync_case_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize to snake_case
            if "risk_score" not in data and "riskScore" in data:
                data["risk_score"] = data["riskScore"]
            if "risk_tier" not in data and "riskTier" in data:
                data["risk_tier"] = data["riskTier"]
            if "suspect_entity" not in data and "suspectEntity" in data:
                data["suspect_entity"] = data["suspectEntity"]
            if "sla_deadline" not in data and "slaDeadline" in data:
                data["sla_deadline"] = data["slaDeadline"]
            if "created_at" not in data and "createdAt" in data:
                data["created_at"] = data["createdAt"]

            # Populate dual camelCase keys for seamless JS frontend interop
            data.setdefault("riskScore", data.get("risk_score"))
            data.setdefault("riskTier", data.get("risk_tier"))
            data.setdefault("suspectEntity", data.get("suspect_entity"))
            data.setdefault("slaDeadline", data.get("sla_deadline"))
            data.setdefault("createdAt", data.get("created_at"))
        return data


class GraphNode(BaseModel):
    """Directed link graph node representing an entity, mule, mixer, or transit hub."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Descriptive display label")
    type: str = Field(..., description="Entity role: ORIGIN, SUSPECT, MULE, INTERMEDIARY, DESTINATION")
    risk_tier: str = Field(..., description="Node risk category: CRITICAL, HIGH, MEDIUM, LOW")
    balance: str | float = Field(..., description="Account balance or remaining volume")
    degree: int = Field(default=1, description="Graph network connectivity degree")

    @model_validator(mode="before")
    @classmethod
    def sync_node_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "risk_tier" not in data and "riskTier" in data:
                data["risk_tier"] = data["riskTier"]
            data.setdefault("riskTier", data.get("risk_tier"))
        return data


class GraphEdge(BaseModel):
    """Directed transaction hop between entities."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    amount: float = Field(..., description="Transaction quantum")
    currency: str = Field(default="INR", description="Currency identifier")
    formatted_amount: str = Field(..., description="Localized currency representation")
    timestamp: str = Field(..., description="Hop execution ISO timestamp")
    latency_seconds: int | float = Field(..., description="Inter-hop transfer velocity in seconds")
    rail: str = Field(default="UPI", description="Underlying rail: UPI, IMPS, BTC")

    @model_validator(mode="before")
    @classmethod
    def sync_edge_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "formatted_amount" not in data and "formattedAmount" in data:
                data["formatted_amount"] = data["formattedAmount"]
            if "latency_seconds" not in data and "latencySeconds" in data:
                data["latency_seconds"] = data["latencySeconds"]
            data.setdefault("formattedAmount", data.get("formatted_amount"))
            data.setdefault("latencySeconds", data.get("latency_seconds"))
        return data


class GraphResponse(BaseModel):
    """Complete multi-hop topology response formatted for Cytoscape.js."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    nodes: list[GraphNode] = Field(default_factory=list, description="Topological entity nodes")
    edges: list[GraphEdge] = Field(default_factory=list, description="Direct transactional links")
    elements: list[dict[str, Any]] | None = Field(default=None, description="Pre-synthesized Cytoscape elements")
    summary: dict[str, Any] | None = Field(default=None, description="Network summary metrics")


class FeatureAttribution(BaseModel):
    """TreeSHAP feature importance metric item."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    feature: str = Field(..., description="Feature name or risk factor")
    weight: float | int = Field(..., description="Attribution weight or percentage (0 - 100)")
    impact: str = Field(default="HIGH", description="Relative risk contribution: HIGH, MEDIUM, LOW")


class ExplainabilityResponse(BaseModel):
    """ML model explainability breakdown for regulatory transparency."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    model_name: str = Field(default="CatBoost + XGBoost Ensemble v4", description="Model identifier")
    anomaly_confidence: float = Field(default=0.942, description="Model inference confidence (0.0 - 1.0)")
    features: list[FeatureAttribution] = Field(default_factory=list, description="Ranked feature attributions")

    @model_validator(mode="before")
    @classmethod
    def sync_explainability_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "model_name" not in data and "engineName" in data:
                data["model_name"] = data["engineName"]
            if "anomaly_confidence" not in data and "modelConfidence" in data:
                data["anomaly_confidence"] = data["modelConfidence"]
            if "features" not in data and "featureImportance" in data:
                data["features"] = data["featureImportance"]

            data.setdefault("engineName", data.get("model_name"))
            data.setdefault("modelConfidence", data.get("anomaly_confidence"))
            data.setdefault("featureImportance", data.get("features"))
        return data


class SuspectProfileResponse(BaseModel):
    """KYC and regulatory identity profile for suspect or inspected graph node."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    entity_id: str = Field(..., description="Entity or node identifier")
    vpa_or_wallet: str = Field(..., description="VPA, bank account, or wallet address")
    kyc_status: str = Field(..., description="KYC status: VERIFIED, PARTIAL, FAILED")
    account_age_days: int = Field(..., description="Age of account in days")
    linked_phone_masked: str = Field(..., description="Masked phone number")
    pan_or_tax_id_masked: str = Field(..., description="Masked PAN, Tax ID, or VASP registration")
    risk_tier: str = Field(..., description="Entity risk tier: CRITICAL, HIGH, MEDIUM, LOW")
    is_frozen: bool = Field(default=False, description="Debit freeze flag under PMLA § 12")

    @model_validator(mode="before")
    @classmethod
    def sync_suspect_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "entity_id" not in data and "entityId" in data:
                data["entity_id"] = data["entityId"]
            if "vpa_or_wallet" not in data and "vpaOrWallet" in data:
                data["vpa_or_wallet"] = data["vpaOrWallet"]
            if "kyc_status" not in data and "kycStatus" in data:
                data["kyc_status"] = data["kycStatus"]
            if "account_age_days" not in data and "accountAgeDays" in data:
                data["account_age_days"] = data["accountAgeDays"]
            if "linked_phone_masked" not in data and "linkedPhoneMasked" in data:
                data["linked_phone_masked"] = data["linkedPhoneMasked"]
            if "pan_or_tax_id_masked" not in data and "panOrTaxIdMasked" in data:
                data["pan_or_tax_id_masked"] = data["panOrTaxIdMasked"]
            if "risk_tier" not in data and "riskTier" in data:
                data["risk_tier"] = data["riskTier"]
            if "is_frozen" not in data and "frozenStatus" in data:
                data["is_frozen"] = data["frozenStatus"]

            data.setdefault("entityId", data.get("entity_id"))
            data.setdefault("vpaOrWallet", data.get("vpa_or_wallet"))
            data.setdefault("kycStatus", data.get("kyc_status"))
            data.setdefault("accountAgeDays", data.get("account_age_days"))
            data.setdefault("linkedPhoneMasked", data.get("linked_phone_masked"))
            data.setdefault("panOrTaxIdMasked", data.get("pan_or_tax_id_masked"))
            data.setdefault("riskTier", data.get("risk_tier"))
            data.setdefault("frozenStatus", data.get("is_frozen"))
        return data


class StatusUpdateRequest(BaseModel):
    """Case workflow status update request."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    status: str = Field(..., description="Target status: OPEN, UNDER_REVIEW, ESCALATED, FILED_WITH_FIU")
    notes: str | None = Field(default=None, description="Investigator notes or audit rationale")
    updated_by: str = Field(default="OP-441", description="Investigator badge or ID")


class SarGenerateRequest(BaseModel):
    """Regulatory SAR dossier generation request."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    case_id: str | None = Field(default=None, description="Case identifier")
    narrative: str = Field(default="", description="Formal statutory SAR narrative")
    notes: str = Field(default="", description="Internal audit remarks")
    operator_id: str = Field(default="OP-441", description="Investigator badge ID")
