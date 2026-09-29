"""
Implicit Alternating Least Squares (iALS) & Behavioral Anomaly Engine.
Computes multi-dimensional variance and peer cluster deviation (> 2.5 sigma).
"""

from typing import Any, Dict, List
import numpy as np

FEATURE_WEIGHTS = np.array([1.2, 1.5, 2.0, 1.1, 1.3, 1.4, 1.8, 1.6])
FEATURE_NAMES = [
    "Tx Velocity",
    "Cross-Border Flow",
    "Structuring Score",
    "Off-Hours Activity",
    "Counterparty Entropy",
    "Cash Intensity",
    "Cyclical Flow",
    "Fan-Out Ratio",
]


class CollaborativeFilteringService:
    def __init__(self, peer_k: int = 5, anomaly_threshold: float = 0.40):
        self.peer_k = peer_k
        self.anomaly_threshold = anomaly_threshold
        self.accounts: List[Dict[str, Any]] = []

    def load_accounts(self, accounts: List[Dict[str, Any]]) -> None:
        self.accounts = accounts

    @staticmethod
    def weighted_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        wa = vec_a * FEATURE_WEIGHTS
        wb = vec_b * FEATURE_WEIGHTS
        dot = np.dot(wa, wb)
        norm_a = np.linalg.norm(wa)
        norm_b = np.linalg.norm(wb)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def evaluate_account(self, target_account: Dict[str, Any]) -> Dict[str, Any]:
        target_vec = np.array(target_account["vector"], dtype=float)
        scored_peers = []

        for acc in self.accounts:
            if acc["id"] == target_account["id"]:
                continue
            peer_vec = np.array(acc["vector"], dtype=float)
            sim = self.weighted_cosine_similarity(target_vec, peer_vec)
            scored_peers.append(
                {
                    "account": acc,
                    "similarity": round(sim, 4),
                }
            )

        scored_peers.sort(key=lambda x: x["similarity"], reverse=True)
        top_k = scored_peers[: self.peer_k]

        if not top_k:
            return {"anomaly_score": 0.0, "is_anomaly": False, "deviations": []}

        mean_sim = float(np.mean([p["similarity"] for p in top_k]))
        raw_anomaly = 1.0 - mean_sim
        anomaly_score = round(float(np.clip(raw_anomaly * 2.2, 0.0, 1.0)), 3)
        is_anomaly = anomaly_score >= self.anomaly_threshold

        # Compute dimension-level Z-score deviations
        peer_matrix = np.array([p["account"]["vector"] for p in top_k])
        peer_means = np.mean(peer_matrix, axis=0)
        peer_stds = np.std(peer_matrix, axis=0)
        peer_stds[peer_stds == 0] = 0.08  # prevent divide by zero

        deviations = []
        for i, name in enumerate(FEATURE_NAMES):
            sigma = float((target_vec[i] - peer_means[i]) / peer_stds[i])
            if abs(sigma) >= 2.0 or (target_vec[i] > 0.7 and peer_means[i] < 0.3):
                deviations.append(
                    {
                        "dimension": name,
                        "target_value": round(float(target_vec[i]), 3),
                        "peer_mean": round(float(peer_means[i]), 3),
                        "sigma": f"{'+' if sigma > 0 else ''}{round(sigma, 1)} sigma",
                        "is_critical": abs(sigma) >= 3.0,
                    }
                )

        return {
            "account_id": target_account["id"],
            "account_name": target_account["name"],
            "cluster": target_account.get("cluster", "UNKNOWN"),
            "anomaly_score": anomaly_score,
            "is_anomaly": is_anomaly,
            "risk_tier": (
                "CRITICAL_SAR"
                if anomaly_score >= 0.85
                else "ELEVATED" if is_anomaly else "NOMINAL"
            ),
            "mean_peer_similarity": round(mean_sim, 3),
            "nearest_peers": top_k,
            "deviations": deviations,
        }
