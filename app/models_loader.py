import json
import os
import sys

import joblib

# Ensure src is in sys.path so calibrators and utils unpickle seamlessly
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_base_dir, "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


class ModelRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.base_dir = _base_dir
        self.models_dir = os.path.join(self.base_dir, "models")

        self.ibm_model = None
        self.ibm_calibrator = None
        self.elliptic_model = None
        self.elliptic_calibrator = None
        self.timeseries_bundle = None
        self.samld_model = None

        self.risk_tiers = {}
        self.load_artifacts()
        self._initialized = True

    def load_artifacts(self):
        # 1. Risk Tiers
        tier_path = os.path.join(self.models_dir, "risk_tiers.json")
        if os.path.exists(tier_path):
            try:
                with open(tier_path, "r") as f:
                    self.risk_tiers = json.load(f)
            except Exception as e:
                print(f"Warning loading risk tiers: {e}")

        # 2. IBM Transactions CatBoost + Calibrator
        ibm_model_path = os.path.join(self.models_dir, "IBM-AML", "model_v5.joblib")
        ibm_cal_path = os.path.join(self.models_dir, "IBM-AML", "calibrator_v5.joblib")
        if os.path.exists(ibm_model_path):
            try:
                self.ibm_model = joblib.load(ibm_model_path)
            except Exception as e:
                print(f"Warning loading IBM model: {e}")
        if os.path.exists(ibm_cal_path):
            try:
                self.ibm_calibrator = joblib.load(ibm_cal_path)
            except Exception as e:
                print(f"Warning loading IBM calibrator: {e}")

        # 3. Elliptic XGBoost + Calibrator
        ell_model_path = os.path.join(self.models_dir, "Elliptic", "model_v5.joblib")
        ell_cal_path = os.path.join(self.models_dir, "Elliptic", "calibrator_v5.joblib")
        if os.path.exists(ell_model_path):
            try:
                self.elliptic_model = joblib.load(ell_model_path)
            except Exception as e:
                print(f"Warning loading Elliptic model: {e}")
        if os.path.exists(ell_cal_path):
            try:
                self.elliptic_calibrator = joblib.load(ell_cal_path)
            except Exception as e:
                print(f"Warning loading Elliptic calibrator: {e}")

        # 4. SAML-D XGBoost
        samld_path = os.path.join(self.models_dir, "SAML-D", "model_v5.joblib")
        if os.path.exists(samld_path):
            try:
                self.samld_model = joblib.load(samld_path)
            except Exception as e:
                print(f"Warning loading SAML-D model: {e}")

        # 5. Time-Series AML Ensemble
        ts_path = os.path.join(self.models_dir, "TimeSeries-AML", "model_v5.joblib")
        if os.path.exists(ts_path):
            try:
                self.timeseries_bundle = joblib.load(ts_path)
            except Exception as e:
                print(f"Warning loading Time-Series bundle: {e}")

    def get_tier_config(self, dataset_key: str):
        default_config = {"cutoffs": {"P90": 0.05, "P97": 0.18, "P99_5": 0.65}}
        if not self.risk_tiers or "datasets" not in self.risk_tiers:
            tier_path = os.path.join(self.models_dir, "risk_tiers.json")
            if os.path.exists(tier_path):
                with open(tier_path, "r") as f:
                    self.risk_tiers = json.load(f)

        return self.risk_tiers.get("datasets", {}).get(dataset_key, default_config)


registry = ModelRegistry()
