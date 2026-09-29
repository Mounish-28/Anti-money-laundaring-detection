"""
QuantumAML Nexus - Production Drift Detection Service
=====================================================
Location: app/services/drift_detector.py

Provides production drift monitoring using Population Stability Index (PSI)
and Wasserstein Distance against initialized empirical baselines for SAML-D.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy import stats

logger = logging.getLogger("DriftDetector")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_BASELINE_PATH = os.path.join(BASE_DIR, "models", "samld", "drift_baselines.json")


class DriftDetector:
    """
    Evaluates covariate data drift and prediction probability drift against
    pre-computed reference distributions from the holdout validation split.
    """

    def __init__(self, baseline_path: str = DEFAULT_BASELINE_PATH):
        self.baseline_path = os.path.abspath(baseline_path)
        self.baselines: Dict[str, Any] = {}
        self._load_baselines()

    def _load_baselines(self) -> None:
        if os.path.exists(self.baseline_path):
            try:
                with open(self.baseline_path, "r", encoding="utf-8") as f:
                    self.baselines = json.load(f)
                logger.info(f"Loaded drift baselines from {self.baseline_path}")
            except Exception as e:
                logger.warning(f"Failed to load drift baselines: {e}")
                self.baselines = {}
        else:
            logger.warning(f"Drift baseline file not found: {self.baseline_path}")
            self.baselines = {}

    @property
    def is_initialized(self) -> bool:
        return bool(self.baselines and "features" in self.baselines)

    @staticmethod
    def calculate_psi(
        observed_vals: np.ndarray,
        bin_edges: List[float],
        ref_proportions: List[float],
        epsilon: float = 1e-6,
    ) -> float:
        """Calculates Population Stability Index between observed sample and baseline."""
        if len(observed_vals) == 0:
            return 0.0

        obs_counts, _ = np.histogram(observed_vals, bins=bin_edges)
        obs_pct = (obs_counts / max(1, len(observed_vals))) + epsilon
        ref_pct = np.array(ref_proportions) + epsilon

        obs_pct = obs_pct / np.sum(obs_pct)
        ref_pct = ref_pct / np.sum(ref_pct)

        psi = np.sum((obs_pct - ref_pct) * np.log(obs_pct / ref_pct))
        return float(psi)

    @staticmethod
    def classify_psi(psi_val: float) -> str:
        if psi_val < 0.10:
            return "STABLE_NO_DRIFT"
        elif psi_val < 0.25:
            return "MODERATE_DRIFT_WARNING"
        else:
            return "SIGNIFICANT_DRIFT_ALERT"

    def evaluate_feature_drift(self, feature_name: str, observed_vals: np.ndarray) -> Dict[str, Any]:
        if not self.is_initialized or feature_name not in self.baselines["features"]:
            return {"feature": feature_name, "status": "BASELINE_UNAVAILABLE"}

        feat_base = self.baselines["features"][feature_name]
        bin_edges = feat_base["psi_decile_edges"]
        ref_props = feat_base["reference_proportions"]
        ref_quantiles = np.array(feat_base["wasserstein_quantile_grid"])

        psi_val = self.calculate_psi(observed_vals, bin_edges, ref_props)
        psi_status = self.classify_psi(psi_val)

        # Wasserstein Distance against reference quantile grid
        w_dist = float(stats.wasserstein_distance(observed_vals, ref_quantiles))

        return {
            "feature": feature_name,
            "sample_size": len(observed_vals),
            "psi": round(psi_val, 5),
            "psi_status": psi_status,
            "wasserstein_distance": round(w_dist, 5),
            "observed_mean": round(float(np.mean(observed_vals)), 4),
            "observed_std": round(float(np.std(observed_vals)), 4),
            "baseline_mean": feat_base["summary_statistics"]["mean"],
            "baseline_std": feat_base["summary_statistics"]["std"],
        }

    def evaluate_prediction_drift(self, observed_scores: np.ndarray) -> Dict[str, Any]:
        if not self.is_initialized or "prediction_distribution" not in self.baselines:
            return {"status": "BASELINE_UNAVAILABLE"}

        pred_base = self.baselines["prediction_distribution"]
        bin_edges = pred_base["psi_decile_edges"]
        ref_props = pred_base["reference_proportions"]
        ref_quantiles = np.array(pred_base["wasserstein_quantile_grid"])

        psi_val = self.calculate_psi(observed_scores, bin_edges, ref_props)
        psi_status = self.classify_psi(psi_val)
        w_dist = float(stats.wasserstein_distance(observed_scores, ref_quantiles))

        return {
            "metric": "prediction_probability_risk_score",
            "sample_size": len(observed_scores),
            "psi": round(psi_val, 5),
            "psi_status": psi_status,
            "wasserstein_distance": round(w_dist, 5),
            "observed_mean_score": round(float(np.mean(observed_scores)), 6),
            "observed_max_score": round(float(np.max(observed_scores)), 6),
            "baseline_mean_score": pred_base["summary_statistics"]["mean"],
            "baseline_max_score": pred_base["summary_statistics"]["max"],
        }

    def evaluate_batch(
        self,
        features_matrix: np.ndarray,
        feature_names: List[str],
        scores: np.ndarray,
    ) -> Dict[str, Any]:
        """Evaluates full batch drift across all tracked features and model output scores."""
        feat_map = {name: i for i, name in enumerate(feature_names)}
        results: Dict[str, Any] = {
            "evaluated_features": {},
            "prediction_drift": self.evaluate_prediction_drift(scores),
            "overall_status": "STABLE_NO_DRIFT",
        }

        drift_flagged = False
        for feat_name in self.baselines.get("features", {}).keys():
            if feat_name in feat_map:
                col_idx = feat_map[feat_name]
                col_vals = features_matrix[:, col_idx]
                feat_res = self.evaluate_feature_drift(feat_name, col_vals)
                results["evaluated_features"][feat_name] = feat_res
                if feat_res["psi_status"] != "STABLE_NO_DRIFT":
                    drift_flagged = True

        if drift_flagged or results["prediction_drift"]["psi_status"] != "STABLE_NO_DRIFT":
            results["overall_status"] = "DRIFT_DETECTED"

        return results


# Global singleton drift detector instance
samld_drift_detector = DriftDetector()
