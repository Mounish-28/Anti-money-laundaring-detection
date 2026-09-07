"""
QuantumAML Nexus - Suspicious Activity Reporting (SAR) Router
==============================================================

Provides comprehensive RESTful endpoints for FIU-IND compliance workflows under
the Prevention of Money Laundering Act (PMLA) and FINnet 2.0 / FINGate specifications.

Endpoints:
- GET /api/v1/sar/list: Paginated, filtered case dossier query ledger.
- GET /api/v1/sar/{sar_id}: Detailed case retrieval by canonical identifier.
- POST /api/v1/sar/generate: Manual case creation and investigation escalation.
- PATCH /api/v1/sar/{sar_id}/status: State transitions with active ring eviction.
- GET /api/v1/sar/{sar_id}/export: Dynamic streaming download of forensic PDF or FINnet 2.0 JSON.
"""

import io
import logging
from typing import Any

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Path,
    Query,
    status,
)
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from app.schemas.sar import (
    CaseStatus,
    SARCaseRecord,
    SARCreateRequest,
    SARListResponse,
    SuspicionTypology,
)
from app.services.sar_exporter import sar_exporter
from app.services.sar_service import sar_service

logger = logging.getLogger("SARRouter")

router = APIRouter()


# ------------------------------------------------------------------------------
# Request Body Schemas
# ------------------------------------------------------------------------------
class SARStatusUpdateRequest(BaseModel):
    """Payload for updating SAR regulatory workflow state."""

    new_status: CaseStatus = Field(
        ...,
        description="Target case status transition (e.g. FILED_WITH_FIU, DISMISSED, ESCALATED)",
    )
    analyst_id: str = Field(
        ...,
        description="Unique identifier or badge number of the compliance investigator",
    )
    resolution_notes: str | None = Field(
        default=None,
        description="Investigator qualitative triage rationale or FINnet filing acknowledgement",
    )


# ------------------------------------------------------------------------------
# 1. List / Query SAR Cases
# ------------------------------------------------------------------------------
@router.get(
    "/list",
    response_model=SARListResponse,
    summary="List regulatory SAR cases",
    description=(
        "Retrieves a paginated list of suspicious activity report dossiers sorted newest first. "
        "Supports query filtering across case status, grounds of suspicion typology, and text search."
    ),
    responses={
        200: {"description": "Paginated list of matching SAR cases."},
    },
)
@router.get(
    "",
    response_model=SARListResponse,
    include_in_schema=False,
)
async def list_sars(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items returned per page"),
    status: CaseStatus | None = Query(None, description="Filter by case status"),
    typology: SuspicionTypology | None = Query(
        None, description="Filter by primary suspicion typology"
    ),
    search: str | None = Query(
        None, description="Search by SAR ID or entity identifier"
    ),
) -> SARListResponse:
    """Returns paginated metadata and matching SARCaseRecord items."""
    try:
        items, total_count = await sar_service.list_sars(
            page=page,
            page_size=page_size,
            status=status,
            typology=typology,
            search=search,
        )
        return SARListResponse(
            total_count=total_count,
            page=page,
            page_size=page_size,
            items=items,
        )
    except Exception as e:
        logger.error("Failed to list SAR cases: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing SAR cases: {e!s}",
        )


# ------------------------------------------------------------------------------
# 2. Retrieve SAR Case by ID
# ------------------------------------------------------------------------------
@router.get(
    "/{sar_id}",
    response_model=SARCaseRecord,
    summary="Retrieve single SAR case",
    description="Fetches a complete, canonical Suspicious Activity Report dossier by its SAR-IND ID.",
    responses={
        200: {"description": "Complete canonical SARCaseRecord dossier."},
        404: {"description": "SAR dossier not found."},
    },
)
async def get_sar_by_id(
    sar_id: str = Path(
        ..., description="Canonical SAR ID formatted as SAR-IND-YYYYMMDD-XXXXXX"
    ),
) -> SARCaseRecord:
    """Retrieves case record or raises 404 if missing."""
    case = await sar_service.get_sar_by_id(sar_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAR dossier not found",
        )
    return case


# ------------------------------------------------------------------------------
# 3. Manually Generate or Escalate a SAR Case
# ------------------------------------------------------------------------------
@router.post(
    "/generate",
    response_model=SARCaseRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Generate or escalate SAR case",
    description=(
        "Enables manual case initiation from frontend surveillance alert cards or ad-hoc audit workflows. "
        "Applies 5-minute rolling ring deduplication to consolidate multiple transactions if an active case exists."
    ),
    responses={
        201: {"description": "SAR case successfully initialized or aggregated."},
        400: {"description": "Invalid creation payload."},
    },
)
async def generate_sar(
    request: SARCreateRequest = Body(
        ..., description="Manual SAR initiation request payload"
    ),
) -> SARCaseRecord:
    """Manually creates or aggregates a SAR dossier from flagged transaction identifiers."""
    if not request.transaction_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one transaction_id must be provided.",
        )

    try:
        # Build initial payload from request attributes
        primary_tx_id = request.transaction_ids[0]
        suspect_id = request.suspect_identifier or f"MANUAL_SUSPECT_{primary_tx_id[:8]}"

        tx_payload: dict[str, Any] = {
            "transaction_id": primary_tx_id,
            "suspect_identifier": suspect_id,
            "amount": 49000.0,
            "currency": "INR",
            "payment_format": "UPI",
            "investigator_notes": request.investigator_notes,
        }
        ml_result: dict[str, Any] = {
            "risk_score": 0.95,
            "recommended_action": "MANUAL_INVESTIGATION_ESCALATION",
            "feature_importance": {"manual_escalation_flag": 1.0},
        }

        # Initial case creation / aggregation
        case = await sar_service.create_or_aggregate_sar(
            tx_payload=tx_payload,
            ml_result=ml_result,
            typology=request.primary_typology,
        )

        # Aggregate any subsequent transaction IDs provided in the request
        for secondary_tx_id in request.transaction_ids[1:]:
            subsequent_payload: dict[str, Any] = {
                "transaction_id": secondary_tx_id,
                "suspect_identifier": suspect_id,
                "amount": 48500.0,
                "currency": "INR",
                "payment_format": "UPI",
            }
            case = await sar_service.create_or_aggregate_sar(
                tx_payload=subsequent_payload,
                ml_result=ml_result,
                typology=request.primary_typology,
            )

        # Apply investigator and reporting entity metadata overrides
        if request.assigned_investigator:
            case.assigned_analyst = request.assigned_investigator
        if request.reporting_entity:
            case.reporting_entity = request.reporting_entity

        return case
    except Exception as e:
        logger.error("Failed to generate manual SAR case: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating SAR case: {e!s}",
        )


# ------------------------------------------------------------------------------
# 4. Update SAR Remediation Status & Evict Ring
# ------------------------------------------------------------------------------
@router.patch(
    "/{sar_id}/status",
    response_model=SARCaseRecord,
    summary="Update SAR case remediation status",
    description=(
        "Transitions case status (e.g., PENDING_REVIEW -> FILED_WITH_FIU or DISMISSED). "
        "If transitioned to a closed state (FILED_WITH_FIU or DISMISSED), the active ring key "
        "is immediately evicted from the 5-minute rolling deduplication index so future activity triggers fresh cases."
    ),
    responses={
        200: {"description": "SAR case record with updated status."},
        404: {"description": "SAR dossier not found."},
        422: {"description": "Validation error or missing status parameters."},
    },
)
async def update_sar_status(
    sar_id: str = Path(..., description="Canonical SAR ID"),
    payload: SARStatusUpdateRequest | None = Body(
        None, description="Status update body payload"
    ),
    new_status: CaseStatus | None = Query(
        None, description="Query parameter fallback for target status"
    ),
    analyst_id: str | None = Query(
        None, description="Query parameter fallback for analyst ID"
    ),
    resolution_notes: str | None = Query(
        None, description="Query parameter fallback for notes"
    ),
) -> SARCaseRecord:
    """Updates case status and evicts closed rings."""
    # Resolve target values from body or query params
    target_status = (payload.new_status if payload else None) or new_status
    target_analyst = (payload.analyst_id if payload else None) or analyst_id
    target_notes = (payload.resolution_notes if payload else None) or resolution_notes

    if not target_status:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field 'new_status' is required in request body or query parameters.",
        )
    if not target_analyst:
        target_analyst = "ANONYMOUS_INVESTIGATOR"

    case = await sar_service.update_sar_status(
        sar_id=sar_id,
        new_status=target_status,
        analyst_id=target_analyst,
        resolution_notes=target_notes,
    )
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAR dossier not found",
        )
    return case


# ------------------------------------------------------------------------------
# 5. Export SAR Dossier (PDF or FINnet 2.0 JSON)
# ------------------------------------------------------------------------------
@router.get(
    "/{sar_id}/export",
    summary="Export regulatory SAR dossier (PDF / JSON)",
    description=(
        "Streams a fully compiled regulatory document for the specified SAR ID. "
        "Use '?format=pdf' for a multi-page ReportLab forensic PDF dossier, "
        "or '?format=json' for an FIU-IND FINnet 2.0 electronic STR intake payload."
    ),
    responses={
        200: {
            "description": "Streamed file buffer (PDF or JSON).",
            "content": {
                "application/pdf": {},
                "application/json": {},
            },
        },
        404: {"description": "SAR dossier not found."},
        400: {"description": "Invalid format parameter."},
    },
)
async def export_sar_dossier(
    sar_id: str = Path(..., description="Canonical SAR ID"),
    format: str = Query(
        "pdf", pattern="^(pdf|json)$", description="Export format: 'pdf' or 'json'"
    ),
) -> Response:
    """Exports case as either PDF byte stream or FINnet 2.0 JSON."""
    case = await sar_service.get_sar_by_id(sar_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAR dossier not found",
        )

    fmt = format.strip().lower()

    if fmt == "pdf":
        try:
            pdf_bytes = sar_exporter.export_pdf(case)
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{sar_id}.pdf"',
                    "Content-Type": "application/pdf",
                },
            )
        except Exception as e:
            logger.error("Failed to generate PDF for %s: %s", sar_id, e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating PDF dossier: {e!s}",
            )

    elif fmt == "json":
        try:
            json_str = sar_exporter.export_json(case)
            return Response(
                content=json_str,
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{sar_id}_FINNET2.json"',
                    "Content-Type": "application/json",
                },
            )
        except Exception as e:
            logger.error(
                "Failed to serialize JSON for %s: %s", sar_id, e, exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error exporting FINnet 2.0 JSON: {e!s}",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Supported formats are 'pdf' or 'json'.",
        )


@router.get(
    "/{sar_id}/export/pdf",
    include_in_schema=False,
)
async def export_sar_pdf_alias(
    sar_id: str = Path(..., description="Canonical SAR ID"),
) -> Response:
    """Convenience alias for PDF export."""
    return await export_sar_dossier(sar_id=sar_id, format="pdf")


@router.get(
    "/{sar_id}/export/json",
    include_in_schema=False,
)
async def export_sar_json_alias(
    sar_id: str = Path(..., description="Canonical SAR ID"),
) -> Response:
    """Convenience alias for FINnet 2.0 JSON export."""
    return await export_sar_dossier(sar_id=sar_id, format="json")
