import io
import time

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.schemas import BatchScoreItem, BatchScoreResponse, TransactionScoreRequest
from app.services.risk_engine import risk_engine

router = APIRouter(prefix="/api/v1/score", tags=["Batch Scoring"])


@router.post("/batch", response_model=BatchScoreResponse)
async def score_batch_json(
    requests: list[TransactionScoreRequest], background_tasks: BackgroundTasks
):
    """
    Asynchronous bulk evaluator for a batch of transaction JSON payloads.
    Returns summary statistics, risk tier breakdown, and individual triaged results.
    """
    t_start = time.perf_counter()
    if not requests:
        raise HTTPException(status_code=400, detail="Empty batch requests list")

    items: list[BatchScoreItem] = []
    tier_counts = {"LOW_RISK": 0, "ELEVATED_RISK": 0, "HIGH_RISK": 0, "CRITICAL_SAR": 0}
    scores_sum = 0.0

    for req in requests:
        res = risk_engine.score_transaction(req, background_tasks=background_tasks)
        tier_str = res.risk_tier.value
        tier_counts[tier_str] = tier_counts.get(tier_str, 0) + 1
        scores_sum += res.risk_score

        items.append(
            BatchScoreItem(
                transaction_id=res.transaction_id,
                risk_score=res.risk_score,
                percentile=res.percentile,
                risk_tier=res.risk_tier,
                action=res.action,
            )
        )

    total_ms = (time.perf_counter() - t_start) * 1000.0
    avg_score = scores_sum / len(requests)

    return BatchScoreResponse(
        total_processed=len(requests),
        tier_counts=tier_counts,
        avg_risk_score=round(avg_score, 4),
        total_latency_ms=round(total_ms, 2),
        flagged_sar_count=tier_counts.get("CRITICAL_SAR", 0),
        items=items,
    )


@router.post("/batch/csv", response_model=BatchScoreResponse)
async def score_batch_csv(
    file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Bulk evaluator processing an uploaded CSV file containing transactions.
    """
    t_start = time.perf_counter()
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {e}")

    items: list[BatchScoreItem] = []
    tier_counts = {"LOW_RISK": 0, "ELEVATED_RISK": 0, "HIGH_RISK": 0, "CRITICAL_SAR": 0}
    scores_sum = 0.0

    for i, row in df.iterrows():
        tx_id = str(row.get("transaction_id", row.get("transactionId", f"csv_tx_{i}")))
        req = TransactionScoreRequest(
            transaction_id=tx_id,
            from_bank=int(row.get("From Bank", row.get("from_bank", 10))),
            to_bank=int(row.get("To Bank", row.get("to_bank", 12))),
            account=str(row.get("Account", row.get("account", "acc_001"))),
            account_1=str(row.get("Account.1", row.get("account_1", "acc_002"))),
            amount=float(row.get("Amount Paid", row.get("amount", 1000.0))),
            amount_received=float(
                row.get("Amount Received", row.get("amount_received", 1000.0))
            ),
            receiving_currency=str(
                row.get(
                    "Receiving Currency", row.get("receiving_currency", "US Dollar")
                )
            ),
            payment_currency=str(
                row.get("Payment Currency", row.get("payment_currency", "US Dollar"))
            ),
            payment_format=str(
                row.get("Payment Format", row.get("payment_format", "Wire"))
            ),
            timestamp=str(
                row.get("Timestamp", row.get("timestamp", "2026/09/03 12:00"))
            ),
        )
        res = risk_engine.score_transaction(req, background_tasks=background_tasks)
        tier_str = res.risk_tier.value
        tier_counts[tier_str] = tier_counts.get(tier_str, 0) + 1
        scores_sum += res.risk_score

        items.append(
            BatchScoreItem(
                transaction_id=res.transaction_id,
                risk_score=res.risk_score,
                percentile=res.percentile,
                risk_tier=res.risk_tier,
                action=res.action,
            )
        )

    total_ms = (time.perf_counter() - t_start) * 1000.0
    avg_score = scores_sum / max(1, len(items))

    return BatchScoreResponse(
        total_processed=len(items),
        tier_counts=tier_counts,
        avg_risk_score=round(avg_score, 4),
        total_latency_ms=round(total_ms, 2),
        flagged_sar_count=tier_counts.get("CRITICAL_SAR", 0),
        items=items,
    )
