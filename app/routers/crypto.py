from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.schemas import CryptoScoreRequest, ScoreResponse
from app.services.risk_engine import risk_engine

router = APIRouter(prefix="/api/v1/score", tags=["Scoring"])


@router.post("/crypto", response_model=ScoreResponse)
async def score_crypto(request: CryptoScoreRequest, background_tasks: BackgroundTasks):
    """
    Real-time illicit activity scoring for cryptocurrency transactions / Elliptic Bitcoin node features.
    """
    try:
        response = risk_engine.score_crypto(request, background_tasks=background_tasks)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crypto scoring error: {str(e)}")
