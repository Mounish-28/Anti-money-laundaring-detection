from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas import ScoreResponse, TransactionScoreRequest
from app.services.risk_engine import risk_engine

router = APIRouter(prefix="/api/v1/score", tags=["Scoring"])


@router.post("/transaction", response_model=ScoreResponse)
async def score_transaction(
    request: TransactionScoreRequest, background_tasks: BackgroundTasks
):
    """
    Real-time continuous AML risk scoring for banking transactions (IBM AML / SAML-D schema).
    Maps transaction features to calibrated probability, empirical percentile, and operational triage tier.
    """
    try:
        response = risk_engine.score_transaction(
            request, background_tasks=background_tasks
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {e!s}")
