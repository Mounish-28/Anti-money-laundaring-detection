import json
import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()

TIERS_PATH = os.path.join(os.path.dirname(__file__), "../models/risk_tiers.json")
if os.path.exists(TIERS_PATH):
    with open(TIERS_PATH, "r") as f:
        CONFIG_DATA = json.load(f)
else:
    CONFIG_DATA = {
        "ibm_transactions": {"ELEVATED": 0.85, "HIGH": 0.95, "CRITICAL_SAR": 0.985},
        "elliptic": {"ELEVATED": 0.70, "HIGH": 0.88, "CRITICAL_SAR": 0.94},
        "thresholds": {"samld": 0.782, "amlsim": 0.597, "timeseries": 0.658},
    }
