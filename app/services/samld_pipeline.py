"""
QuantumAML Nexus - SAML-D Feature Pipeline & Target Encoder
===========================================================
Location: app/services/samld_pipeline.py

Reusable, serializable feature transformation pipeline for SAML-D
transaction modeling and real-time inference with zero data leakage.
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import RobustScaler


class LaplaceTargetEncoder(BaseEstimator, TransformerMixin):
    """
    Bayesian Smoothed (Laplace / M-Estimate) Target Encoder.
    Formula: S_c = (sum(y_c) + m * y_global) / (count(c) + m)
    Guarantees zero data leakage by computing parameters strictly on training splits.
    """

    def __init__(self, m: float = 10.0):
        self.m = m
        self.global_mean: float = 0.0
        self.encodings: Dict[str, Dict[Any, float]] = {}

    def fit(self, X: pd.DataFrame, y: np.ndarray, cat_cols: Optional[List[str]] = None) -> "LaplaceTargetEncoder":
        if cat_cols is None:
            cat_cols = list(X.select_dtypes(include=["category", "object"]).columns)

        self.global_mean = float(np.mean(y))
        self.encodings = {}

        for col in cat_cols:
            series = X[col]
            categories = series.unique()
            col_map: Dict[Any, float] = {}

            counts = series.value_counts()
            positives = pd.Series(y, index=series.index).groupby(series, observed=False).sum()

            for cat in categories:
                n_c = float(counts.get(cat, 0))
                k_c = float(positives.get(cat, 0.0))
                smoothed = (k_c + self.m * self.global_mean) / (n_c + self.m)
                col_map[cat] = float(smoothed)

            self.encodings[col] = col_map
        return self

    def transform(self, X: pd.DataFrame, cat_cols: Optional[List[str]] = None) -> pd.DataFrame:
        if cat_cols is None:
            cat_cols = list(self.encodings.keys())

        out_df = pd.DataFrame(index=X.index)
        for col in cat_cols:
            col_map = self.encodings.get(col, {})
            mapped = X[col].map(col_map).fillna(self.global_mean).astype(np.float32)
            out_df[f"{col}_TE"] = mapped
        return out_df


class SamldFeaturePipeline(BaseEstimator, TransformerMixin):
    """
    Modular, scikit-learn compatible feature engineering and preprocessing
    pipeline for the SAML-D dataset with strict zero-leakage enforcement.
    """

    CATEGORICAL_COLS = [
        "Payment_type",
        "Sender_bank_location",
        "Receiver_bank_location",
        "Payment_currency",
        "Received_currency",
    ]

    NUMERICAL_SCALE_COLS = [
        "Amount",
        "Log_Amount",
        "Rolling_24h_Velocity",
        "Log_Velocity",
        "In_Degree",
        "Out_Degree",
        "Amount_to_Velocity_Ratio",
        "Degree_Ratio",
        "Degree_Difference",
        "Network_Activity",
        "Velocity_Per_Out_Degree",
        "Cash_Velocity_Risk",
        "Structuring_Proximity",
        "Payment_type_TE",
        "Sender_bank_location_TE",
        "Receiver_bank_location_TE",
        "Payment_currency_TE",
        "Received_currency_TE",
        "Location_Risk_Differential",
        "Currency_Risk_Differential",
    ]

    PASSTHROUGH_BINARY_COLS = [
        "Is_Cross_Border",
        "Is_Currency_Exchange",
        "Cross_Border_Currency_Mismatch",
        "Is_Cash",
        "Is_Structuring_Band",
        "Round_Amount_Flag",
    ]

    def __init__(self, target_encoding_m: float = 10.0):
        self.target_encoding_m = target_encoding_m
        self.target_encoder = LaplaceTargetEncoder(m=target_encoding_m)
        self.robust_scaler = RobustScaler(with_centering=True, with_scaling=True, quantile_range=(25.0, 75.0))
        self.is_fitted = False
        self.feature_names_: List[str] = []
        self.transformation_stats_: Dict[str, Any] = {}

    def _engineer_interactions(self, X: pd.DataFrame) -> pd.DataFrame:
        """Construct non-linear interaction and AML domain features."""
        df = pd.DataFrame(index=X.index)

        amount = X["Amount"].values.astype(np.float32)
        velocity = X["Rolling_24h_Velocity"].values.astype(np.float32)
        in_deg = X["In_Degree"].values.astype(np.float32)
        out_deg = X["Out_Degree"].values.astype(np.float32)

        # Raw continuous
        df["Amount"] = amount
        df["Rolling_24h_Velocity"] = velocity
        df["In_Degree"] = in_deg
        df["Out_Degree"] = out_deg

        # Log-transformed continuous to compress extreme skewness
        df["Log_Amount"] = np.log1p(np.maximum(0.0, amount)).astype(np.float32)
        df["Log_Velocity"] = np.log1p(np.maximum(0.0, velocity)).astype(np.float32)

        # 1. Burst spike: Amount to Velocity Ratio
        df["Amount_to_Velocity_Ratio"] = (amount / (velocity + 1.0)).astype(np.float32)

        # 2. Graph Asymmetry: Degree Ratio & Degree Difference
        df["Degree_Ratio"] = ((in_deg + 1.0) / (out_deg + 1.0)).astype(np.float32)
        df["Degree_Difference"] = (in_deg - out_deg).astype(np.float32)

        # 3. Network Product Connectivity (Hub / Smurfing Activity)
        df["Network_Activity"] = np.log1p(in_deg * out_deg).astype(np.float32)

        # 4. Collinearity Breaker: Velocity per Out-Degree (resolves r=0.9149 collinearity)
        df["Velocity_Per_Out_Degree"] = (velocity / (out_deg + 1.0)).astype(np.float32)

        # 5. Cross-border & Currency Exchange Invariants
        sender_loc = X["Sender_bank_location"].astype(str)
        receiver_loc = X["Receiver_bank_location"].astype(str)
        pay_curr = X["Payment_currency"].astype(str)
        rec_curr = X["Received_currency"].astype(str)

        is_cross_border = (sender_loc != receiver_loc).astype(np.float32)
        is_curr_exchange = (pay_curr != rec_curr).astype(np.float32)
        df["Is_Cross_Border"] = is_cross_border
        df["Is_Currency_Exchange"] = is_curr_exchange
        df["Cross_Border_Currency_Mismatch"] = (is_cross_border * is_curr_exchange).astype(np.float32)

        # 6. Cash Typology Interactions
        pay_type = X["Payment_type"].astype(str)
        is_cash = pay_type.isin(["Cash Deposit", "Cash Withdrawal"]).astype(np.float32)
        df["Is_Cash"] = is_cash
        df["Cash_Velocity_Risk"] = (is_cash * df["Log_Amount"]).astype(np.float32)

        # 7. Structuring Detection: Proximity to $10k Threshold (18.94% of SAML-D Laundering)
        df["Is_Structuring_Band"] = ((amount >= 8000.0) & (amount < 10000.0)).astype(np.float32)
        df["Structuring_Proximity"] = np.exp(-0.5 * ((amount - 9500.0) / 1500.0) ** 2).astype(np.float32)

        # 8. Round Amount Flag
        df["Round_Amount_Flag"] = ((amount >= 1000.0) & ((amount % 500.0) < 0.01)).astype(np.float32)

        return df

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "SamldFeaturePipeline":
        """Fit target encodings and robust scalers strictly on training data."""
        self.target_encoder.fit(X, y, self.CATEGORICAL_COLS)
        feat_df = self._engineer_interactions(X)
        te_df = self.target_encoder.transform(X, self.CATEGORICAL_COLS)

        for col in te_df.columns:
            feat_df[col] = te_df[col]

        feat_df["Location_Risk_Differential"] = (
            feat_df["Sender_bank_location_TE"] - feat_df["Receiver_bank_location_TE"]
        ).astype(np.float32)
        feat_df["Currency_Risk_Differential"] = (
            feat_df["Payment_currency_TE"] - feat_df["Received_currency_TE"]
        ).astype(np.float32)

        self.robust_scaler.fit(feat_df[self.NUMERICAL_SCALE_COLS])
        self.feature_names_ = self.NUMERICAL_SCALE_COLS + self.PASSTHROUGH_BINARY_COLS

        self.transformation_stats_ = {
            "n_input_features": len(X.columns),
            "n_output_features": len(self.feature_names_),
            "target_encoder_m": self.target_encoding_m,
            "global_target_mean": self.target_encoder.global_mean,
            "target_encodings_summary": {
                col: {
                    cat: round(val, 6)
                    for cat, val in list(self.target_encoder.encodings[col].items())[:10]
                }
                for col in self.CATEGORICAL_COLS
            },
            "robust_scaler_params": {
                col: {
                    "median": round(float(self.robust_scaler.center_[i]), 4),
                    "iqr": round(float(self.robust_scaler.scale_[i]), 4),
                }
                for i, col in enumerate(self.NUMERICAL_SCALE_COLS)
            },
        }

        self.is_fitted = True
        return self

    def transform_dict(self, data: Dict[str, Any]) -> np.ndarray:
        """
        Ultra-low-latency (<50us) vectorized scalar transformer for real-time
        single-row streaming inference without DataFrame fragmentation overhead.
        """
        amt = float(data.get("amount", data.get("Amount", 0.0)))
        vel = float(data.get("sender_velocity_24h", data.get("Rolling_24h_Velocity", 0.0)))
        in_deg = float(data.get("fan_in_count", data.get("In_Degree", 1.0)))
        out_deg = float(data.get("fan_out_count", data.get("Out_Degree", 1.0)))

        p_type = str(data.get("payment_type", data.get("Payment_type", "ACH")))
        s_loc = str(data.get("sender_bank_location", data.get("Sender_bank_location", "UK")))
        r_loc = str(data.get("receiver_bank_location", data.get("Receiver_bank_location", "UK")))
        p_curr = str(data.get("payment_currency", data.get("Payment_currency", "UK pounds")))
        r_curr = str(data.get("received_currency", data.get("Received_currency", "UK pounds")))

        log_amt = np.log1p(max(0.0, amt))
        log_vel = np.log1p(max(0.0, vel))
        amt_vel_ratio = amt / (vel + 1.0)
        deg_ratio = (in_deg + 1.0) / (out_deg + 1.0)
        deg_diff = in_deg - out_deg
        net_act = np.log1p(in_deg * out_deg)
        vel_out_deg = vel / (out_deg + 1.0)

        is_cash = 1.0 if p_type in ("Cash Deposit", "Cash Withdrawal") else 0.0
        cash_vel_risk = is_cash * log_amt
        struct_prox = np.exp(-0.5 * ((amt - 9500.0) / 1500.0) ** 2)

        gm = self.target_encoder.global_mean
        te_enc = self.target_encoder.encodings
        p_type_te = te_enc.get("Payment_type", {}).get(p_type, gm)
        s_loc_te = te_enc.get("Sender_bank_location", {}).get(s_loc, gm)
        r_loc_te = te_enc.get("Receiver_bank_location", {}).get(r_loc, gm)
        p_curr_te = te_enc.get("Payment_currency", {}).get(p_curr, gm)
        r_curr_te = te_enc.get("Received_currency", {}).get(r_curr, gm)

        loc_diff = s_loc_te - r_loc_te
        curr_diff = p_curr_te - r_curr_te

        raw_num = np.array([
            amt, log_amt, vel, log_vel, in_deg, out_deg,
            amt_vel_ratio, deg_ratio, deg_diff, net_act, vel_out_deg,
            cash_vel_risk, struct_prox,
            p_type_te, s_loc_te, r_loc_te, p_curr_te, r_curr_te,
            loc_diff, curr_diff
        ], dtype=np.float32)

        scaled_num = (raw_num - self.robust_scaler.center_) / self.robust_scaler.scale_

        is_cross_border = 1.0 if s_loc != r_loc else 0.0
        is_curr_ex = 1.0 if p_curr != r_curr else 0.0
        cb_curr_mismatch = is_cross_border * is_curr_ex
        is_struct_band = 1.0 if (8000.0 <= amt < 10000.0) else 0.0
        round_amt = 1.0 if (amt >= 1000.0 and (amt % 500.0) < 0.01) else 0.0

        binary_vals = np.array([
            is_cross_border, is_curr_ex, cb_curr_mismatch,
            is_cash, is_struct_band, round_amt
        ], dtype=np.float32)

        return np.concatenate([scaled_num, binary_vals]).astype(np.float32).reshape(1, -1)

    def transform(self, X: Any) -> np.ndarray:
        """Transform input features using fitted parameters with zero leakage."""
        if not self.is_fitted:
            raise RuntimeError("Pipeline must be fitted before calling transform().")

        if isinstance(X, dict):
            return self.transform_dict(X)

        if isinstance(X, pd.DataFrame) and len(X) == 1:
            return self.transform_dict(X.iloc[0].to_dict())

        feat_df = self._engineer_interactions(X)
        te_df = self.target_encoder.transform(X, self.CATEGORICAL_COLS)
        for col in te_df.columns:
            feat_df[col] = te_df[col]

        feat_df["Location_Risk_Differential"] = (
            feat_df["Sender_bank_location_TE"] - feat_df["Receiver_bank_location_TE"]
        ).astype(np.float32)
        feat_df["Currency_Risk_Differential"] = (
            feat_df["Payment_currency_TE"] - feat_df["Received_currency_TE"]
        ).astype(np.float32)

        scaled_vals = self.robust_scaler.transform(feat_df[self.NUMERICAL_SCALE_COLS]).astype(np.float32)
        binary_vals = feat_df[self.PASSTHROUGH_BINARY_COLS].values.astype(np.float32)

        return np.hstack([scaled_vals, binary_vals])

    def fit_transform(self, X: pd.DataFrame, y: np.ndarray) -> np.ndarray:
        return self.fit(X, y).transform(X)

