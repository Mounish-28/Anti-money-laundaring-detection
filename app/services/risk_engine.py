import time
from datetime import datetime

import numpy as np
import pandas as pd

from app.models_loader import registry
from app.schemas import (
    ActionType,
    CryptoScoreRequest,
    RiskTier,
    ScoreResponse,
    TransactionScoreRequest,
)
from app.worker import async_dispatch_alert


def resolve_percentile_and_tier(
    prob: float, dataset_key: str
) -> tuple[float, RiskTier, ActionType]:
    """
    Resolves calibrated probability to empirical percentile and operational risk tier.
    """
    config = registry.get_tier_config(dataset_key)
    cutoffs = config.get("cutoffs", {"P90": 0.05, "P97": 0.18, "P99_5": 0.65})

    p90 = cutoffs.get("P90", 0.05)
    p97 = cutoffs.get("P97", 0.18)
    p99_5 = cutoffs.get("P99_5", 0.65)

    # Calculate continuous percentile estimate via piecewise linear interpolation
    if prob <= p90:
        pct = (prob / (p90 + 1e-9)) * 90.0
        tier = RiskTier.LOW_RISK
        action = ActionType.AUTO_CLEAR
    elif prob < p97:
        pct = 90.0 + ((prob - p90) / (p97 - p90 + 1e-9)) * 7.0
        tier = RiskTier.ELEVATED_RISK
        action = ActionType.ROUTINE_MONITOR
    elif prob < p99_5:
        pct = 97.0 + ((prob - p97) / (p99_5 - p97 + 1e-9)) * 2.5
        tier = RiskTier.HIGH_RISK
        action = ActionType.SECONDARY_REVIEW
    else:
        pct = min(100.0, 99.5 + ((prob - p99_5) / (1.0 - p99_5 + 1e-9)) * 0.5)
        tier = RiskTier.CRITICAL_SAR
        action = ActionType.AUTO_FLAG_SAR

    return round(float(pct), 2), tier, action


class RiskEngine:
    def __init__(self):
        self.registry = registry
        self._cat_cols = [
            "From Bank",
            "To Bank",
            "Payment Format",
            "Receiving Currency",
            "Payment Currency",
        ]

    def score_transaction(
        self, req: TransactionScoreRequest, background_tasks=None
    ) -> ScoreResponse:
        t_start = time.perf_counter()

        # 1. Temporal feature extraction
        hour = 12
        dayofweek = 2
        if req.timestamp:
            try:
                ts_clean = req.timestamp.replace("-", "/").replace("T", " ")
                parts = ts_clean.split(" ")
                if len(parts) > 1 and ":" in parts[1]:
                    hour = int(parts[1].split(":")[0])
                if len(parts) > 0 and "/" in parts[0]:
                    dt_obj = datetime.strptime(parts[0], "%Y/%m/%d")
                    dayofweek = dt_obj.weekday()
            except Exception:
                hour = 12
                dayofweek = 2

        amt_paid = float(req.amount)
        amt_rcvd = (
            float(req.amount_received) if req.amount_received is not None else amt_paid
        )
        curr_exchange = int(req.receiving_currency != req.payment_currency)

        # Topology proxies
        sender_tx_count = 12
        receiver_tx_count = 8
        avg_sender_amount = 15000.0

        if amt_paid > 100000.0:
            amount_vs_sender_avg = amt_paid / 5000.0
        elif 9000.0 <= amt_paid <= 9999.0:
            amount_vs_sender_avg = 4.5
        else:
            amount_vs_sender_avg = amt_paid / avg_sender_amount

        # 2. DataFrame Construction
        row_dict = {
            "From Bank": int(req.from_bank),
            "To Bank": int(req.to_bank),
            "Amount Received": np.float32(amt_rcvd),
            "Receiving Currency": str(req.receiving_currency),
            "Amount Paid": np.float32(amt_paid),
            "Payment Currency": str(req.payment_currency),
            "Payment Format": str(req.payment_format),
            "hour": np.int8(hour),
            "dayofweek": np.int8(dayofweek),
            "Sender_Tx_Count": np.int32(sender_tx_count),
            "Receiver_Tx_Count": np.int32(receiver_tx_count),
            "Amount_vs_Sender_Avg": np.float32(amount_vs_sender_avg),
            "Currency_Exchange": np.int8(curr_exchange),
        }

        df_in = pd.DataFrame([row_dict])
        for c in self._cat_cols:
            df_in[c] = df_in[c].astype("category")

        # 3. Model Inference & Calibration
        raw_prob = 0.0001
        if self.registry.ibm_model is not None:
            try:
                raw_prob = float(self.registry.ibm_model.predict_proba(df_in)[:, 1][0])
            except Exception:
                pass

        cal_prob = raw_prob
        if self.registry.ibm_calibrator is not None:
            try:
                cal_prob = float(
                    self.registry.ibm_calibrator.predict_proba(np.array([raw_prob]))[0]
                )
            except Exception:
                cal_prob = raw_prob

        # High value or structuring rules enforcement
        if amt_paid >= 500000.0 or (curr_exchange and amt_paid > 200000.0):
            cal_prob = max(cal_prob, 0.88)
            primary_driver = "Extreme High-Value Cross-Currency Velocity"
        elif 9500.0 <= amt_paid <= 9999.0 and curr_exchange:
            cal_prob = max(cal_prob, 0.72)
            primary_driver = "Smurfing / Structuring Threshold Evasion"
        elif amount_vs_sender_avg > 15.0:
            cal_prob = max(cal_prob, 0.65)
            primary_driver = (
                f"Sudden Volume Spike ({amount_vs_sender_avg:.1f}x Historical Mean)"
            )
        elif cal_prob > 0.02:
            primary_driver = "High Anomaly CatBoost Tree Path"
        else:
            primary_driver = "Standard Transaction Baseline"

        # 4. Percentile & Risk Tier Mapping
        pct, tier, action = resolve_percentile_and_tier(cal_prob, "IBM_Transactions")

        latency = (time.perf_counter() - t_start) * 1000.0

        response = ScoreResponse(
            transaction_id=req.transaction_id,
            risk_score=round(float(cal_prob), 4),
            percentile=pct,
            risk_tier=tier,
            action=action,
            latency_ms=round(latency, 2),
            primary_driver=primary_driver,
        )

        # 5. Async Alert Dispatch for HIGH_RISK or CRITICAL_SAR
        if tier in [RiskTier.HIGH_RISK, RiskTier.CRITICAL_SAR]:
            alert_payload = {
                "transaction_id": req.transaction_id,
                "risk_score": float(cal_prob),
                "percentile": float(pct),
                "risk_tier": tier.value,
                "action": action.value,
                "primary_driver": primary_driver,
                "raw_payload": req.model_dump(),
                "timestamp": datetime.now().isoformat(),
            }
            async_dispatch_alert(alert_payload, background_tasks=background_tasks)

        return response

    def score_crypto(
        self, req: CryptoScoreRequest, background_tasks=None
    ) -> ScoreResponse:
        t_start = time.perf_counter()

        features = [float(req.timestep)] + [float(x) for x in req.features]
        if len(features) < 166:
            features = features + [0.0] * (166 - len(features))
        elif len(features) > 166:
            features = features[:166]

        prob = 0.05
        if self.registry.elliptic_model is not None:
            feat_cols = ["timestep"] + [f"feat_{i}" for i in range(165)]
            df_in = pd.DataFrame([features], columns=feat_cols)
            try:
                raw_p = float(
                    self.registry.elliptic_model.predict_proba(df_in)[:, 1][0]
                )
                if self.registry.elliptic_calibrator is not None:
                    prob = float(
                        self.registry.elliptic_calibrator.predict_proba(
                            np.array([raw_p])
                        )[0]
                    )
                else:
                    prob = raw_p
            except Exception:
                pass

        pct, tier, action = resolve_percentile_and_tier(prob, "Elliptic_Bitcoin")
        latency = (time.perf_counter() - t_start) * 1000.0

        primary_driver = (
            "Illicit Graph Topology / Darknet Mixer Cluster"
            if prob > 0.40
            else "Benign UTXO Node Pattern"
        )

        response = ScoreResponse(
            transaction_id=req.tx_id,
            risk_score=round(float(prob), 4),
            percentile=pct,
            risk_tier=tier,
            action=action,
            latency_ms=round(latency, 2),
            primary_driver=primary_driver,
        )

        if tier in [RiskTier.HIGH_RISK, RiskTier.CRITICAL_SAR]:
            alert_payload = {
                "transaction_id": req.tx_id,
                "risk_score": float(prob),
                "percentile": float(pct),
                "risk_tier": tier.value,
                "action": action.value,
                "primary_driver": primary_driver,
                "raw_payload": {"tx_id": req.tx_id, "timestep": req.timestep},
                "timestamp": datetime.now().isoformat(),
            }
            async_dispatch_alert(alert_payload, background_tasks=background_tasks)

        return response


risk_engine = RiskEngine()
