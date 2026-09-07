from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from app.schemas import AlertRecord
from app.worker import query_alerts

router = APIRouter(prefix="/api/v1/alerts", tags=["Compliance Alerts Queue"])


@router.get("", response_model=List[AlertRecord])
async def get_alerts(
    tier: Optional[str] = Query(
        None, description="Filter by risk tier (HIGH_RISK or CRITICAL_SAR)"
    ),
    limit: int = Query(50, ge=1, le=500, description="Max number of alerts to return"),
):
    """
    Retrieves prioritized AML alert investigation queue from SQLite audit storage.
    """
    try:
        records = query_alerts(tier=tier, limit=limit)
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")
