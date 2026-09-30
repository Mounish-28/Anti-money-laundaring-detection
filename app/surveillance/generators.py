"""
app/surveillance/generators.py
=============================================================================
QuantumAML Nexus -- Procedural Mock Stream Generators
Generates high-entropy, realistic real-time transaction payloads for:
  1. Indian UPI Banking Switch Traffic (UPI VPAs, NPCI References, MCC codes)
  2. Live Cryptocurrency Mempool Transfers (Bech32/ETH, Mixer Flags, Peeling Chains)

IMPORTANT INFRASTRUCTURE GUARANTEE:
These generators operate in complete statistical isolation from all five
historical training datasets (IBM, SAML-D, Elliptic, AMLSim, Time-Series AML).
All entities, accounts, wallets, and identifiers are synthesized procedurally
in-memory with zero disk reads or cross-contamination.
=============================================================================
"""

from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import random
import secrets
import string
import time
from typing import Any, Dict, List, Optional

from app.surveillance.schemas import (
    CryptoNetwork,
    CryptoTransferPayload,
    SurveillanceEnvelope,
    SurveillanceStreamType,
    UPIStatus,
    UPITransactionPayload,
)
from app.surveillance.isolation_guard import isolation_auditor


# =============================================================================
# PROCEDURAL UPI REGISTRIES (STRICTLY IN-MEMORY, ZERO DATASET REPLAY)
# =============================================================================

INDIAN_FIRST_NAMES = [
    "Rahul", "Priya", "Amit", "Sneha", "Vikram", "Ananya", "Rajesh",
    "Pooja", "Arjun", "Kavita", "Aditya", "Neha", "Deepak", "Ritu",
    "Sanjay", "Divya", "Suresh", "Meera", "Manoj", "Tanvi", "Alok",
    "Shreya", "Rohan", "Nisha", "Gaurav", "Swati", "Karan", "Aarti",
]

INDIAN_LAST_NAMES = [
    "Sharma", "Patel", "Verma", "Mehta", "Iyer", "Gupta", "Reddy",
    "Singh", "Nair", "Bose", "Joshi", "Kulkarni", "Rao", "Mishra",
    "Deshmukh", "Aggarwal", "Pillai", "Chopra", "Chatterjee", "Bhat",
]

UPI_PSP_HANDLES = [
    "okhdfcbank", "icici", "oksbi", "paytm", "ybl", "axisbank",
    "barodampay", "idfcbank", "kotak", "indus",
]

INDIAN_METROS = [
    "Mumbai, Maharashtra", "Bengaluru, Karnataka", "New Delhi, Delhi",
    "Hyderabad, Telangana", "Pune, Maharashtra", "Chennai, Tamil Nadu",
    "Kolkata, West Bengal", "Ahmedabad, Gujarat", "Jaipur, Rajasthan",
]

MERCHANT_CATEGORIES = [
    ("5411", "Grocery & Supermarkets"),
    ("5812", "Restaurants & Dining"),
    ("5311", "Department Stores"),
    ("4829", "Money Transfer / Quasi-Cash"),
    ("6011", "Financial Institutions / Automated Cash"),
    ("7995", "Betting, Casino & Gambling Services"),
    ("5944", "Jewelry, Watches & Precious Stones"),
]


class MockUPIGenerator:
    """
    Procedural generator for live Indian UPI transaction payloads.
    Guarantees zero coupling with historical AML training sets.
    """

    def __init__(self):
        self.seq_counter = 1000

    def generate_upi_payload(
        self,
        anomaly_mode: Optional[str] = None,
        forced_amount_inr: Optional[float] = None,
    ) -> UPITransactionPayload:
        """
        Synthesizes a realistic, high-entropy UPI transaction.
        anomaly_mode can be: None (benign), "STRUCTURING", "GAMBLING_BURST", "THRESHOLD_BREACH".
        """
        self.seq_counter += 1
        now_dt = datetime.now(timezone.utc)
        timestamp_str = now_dt.isoformat()
        date_prefix = now_dt.strftime("%Y%m%d")

        # Procedural names & VPAs
        p_first = random.choice(INDIAN_FIRST_NAMES)
        p_last = random.choice(INDIAN_LAST_NAMES)
        payer_name = f"{p_first} {p_last}"
        payer_handle = random.choice(UPI_PSP_HANDLES)
        payer_vpa = f"{p_first.lower()}.{p_last.lower()}{random.randint(10, 99)}@{payer_handle}"

        r_first = random.choice(INDIAN_FIRST_NAMES)
        r_last = random.choice(INDIAN_LAST_NAMES)
        payee_name = f"{r_first} {r_last}"
        payee_handle = random.choice(UPI_PSP_HANDLES)
        payee_vpa = f"{r_first.lower()}.{r_last.lower()}{random.randint(100, 999)}@{payee_handle}"

        # Synthesize NPCI 12-digit RRN
        rrn_digits = "".join(random.choices(string.digits, k=12))
        txn_id = f"UPI/{date_prefix}/{rrn_digits}"

        # Anomaly / Scenario synthesis
        anomaly_flags: List[str] = []
        rbi_breach = False
        mcc_code = "5411"

        if forced_amount_inr is not None:
            amt_inr = forced_amount_inr
        elif anomaly_mode == "STRUCTURING":
            # Just below regulatory reporting threshold of 100,000 INR
            amt_inr = float(random.choice([92000.0, 95000.0, 98500.0, 99200.0, 99500.0]))
            anomaly_flags.extend(["SUB_THRESHOLD_STRUCTURING", "ROUND_NUMBER_EVASION"])
        elif anomaly_mode == "THRESHOLD_BREACH":
            amt_inr = float(random.uniform(250000.0, 750000.0))
            rbi_breach = True
            anomaly_flags.append("RBI_P2P_THRESHOLD_BREACH")
        elif anomaly_mode == "GAMBLING_BURST":
            amt_inr = float(random.choice([49000.0, 75000.0, 89000.0]))
            mcc_code = "7995"  # High-risk gambling MCC
            anomaly_flags.extend(["HIGH_RISK_MCC_GAMBLING", "RAPID_VELOCITY_BURST"])
        else:
            # Standard daily retail / consumer UPI transfer
            amt_inr = round(float(random.expovariate(1 / 450.0) + 25.0), 2)
            mcc_code = random.choice(MERCHANT_CATEGORIES)[0]

        amt_inr = round(amt_inr, 2)
        amt_usd = round(amt_inr / 83.50, 2)

        # Device telemetry
        device_raw = f"DEV_PROC_{secrets.token_hex(8)}"
        device_fingerprint = hashlib.sha256(device_raw.encode()).hexdigest()
        mobile_raw = f"+9198{random.randint(10000000, 99999999)}"
        mobile_hash = hashlib.sha256(mobile_raw.encode()).hexdigest()

        return UPITransactionPayload(
            txn_id=txn_id,
            payer_vpa=payer_vpa,
            payee_vpa=payee_vpa,
            payer_name=payer_name,
            payee_name=payee_name,
            amount_inr=amt_inr,
            amount_usd=amt_usd,
            currency="INR",
            payer_mobile_hash=mobile_hash,
            device_fingerprint=device_fingerprint,
            ip_address=f"103.{random.randint(10, 250)}.{random.randint(1, 254)}.{random.randint(1, 254)}",
            location_city=random.choice(INDIAN_METROS),
            mcc=mcc_code,
            upi_status=UPIStatus.SUCCESS,
            rbi_threshold_breach=rbi_breach,
            anomaly_flags=anomaly_flags,
            timestamp=timestamp_str,
            channel="upi",
        )


# =============================================================================
# PROCEDURAL CRYPTO REGISTRIES (STRICTLY IN-MEMORY, ZERO DATASET REPLAY)
# =============================================================================

KNOWN_MIXER_NAMES = [
    "WasabiCoinJoinCoordinator", "TornadoVaultV2", "WhirlpoolPool_0.05",
    "ChipMixerClusterAlpha", "RailgunPrivacyRelayer",
]


class MockCryptoGenerator:
    """
    Procedural generator for live cryptocurrency mempool transfers.
    Guarantees zero coupling with historical Elliptic or Bitcoin training sets.
    """

    def __init__(self):
        self.seq_counter = 5000

    def _generate_wallet_address(self, network: CryptoNetwork) -> str:
        """Generates realistic cryptographic addresses."""
        if network == CryptoNetwork.BITCOIN:
            # Bech32 native SegWit address
            addr_hash = secrets.token_hex(16)
            return f"bc1q{addr_hash[:34]}"
        elif network in (CryptoNetwork.ETHEREUM, CryptoNetwork.POLYGON):
            # 0x-prefixed 40-hex address
            return f"0x{secrets.token_hex(20)}"
        elif network == CryptoNetwork.SOLANA:
            # Base58-style alphanumeric
            chars = string.ascii_letters + string.digits
            return "".join(secrets.choice(chars) for _ in range(44))
        else:
            return f"T{secrets.token_hex(17)}"

    def generate_crypto_payload(
        self,
        anomaly_mode: Optional[str] = None,
        network: CryptoNetwork = CryptoNetwork.BITCOIN,
    ) -> CryptoTransferPayload:
        """
        Synthesizes a realistic cryptocurrency mempool transaction.
        anomaly_mode can be: None (benign), "MIXER_TUMBLER", "PEELING_CHAIN", "LARGE_UNHOSTED".
        """
        self.seq_counter += 1
        now_dt = datetime.now(timezone.utc)
        timestamp_str = now_dt.isoformat()

        # 64-char hex transaction hash
        tx_hash = f"0x{secrets.token_hex(32)}"

        from_addr = self._generate_wallet_address(network)
        to_addr = self._generate_wallet_address(network)

        mixer_risk = False
        peeling_chain = False
        hop_count = 1
        risk_tags: List[str] = []

        if network == CryptoNetwork.BITCOIN:
            asset = "BTC"
            price = 65000.0
            gas_fee = round(random.uniform(2.5, 12.0), 2)
        elif network == CryptoNetwork.ETHEREUM:
            asset = "ETH"
            price = 3500.0
            gas_fee = round(random.uniform(4.0, 25.0), 2)
        else:
            asset = "USDT"
            price = 1.0
            gas_fee = 0.50

        if anomaly_mode == "MIXER_TUMBLER":
            mixer_risk = True
            to_addr = f"3Mixer{random.choice(KNOWN_MIXER_NAMES)[:18]}{secrets.token_hex(6)}"
            amt_crypto = round(random.uniform(3.5, 18.0), 4)
            risk_tags.extend(["UNHOSTED_MIXER_PROXIMITY", "OFAC_TUMBLER_INTERACTION"])
        elif anomaly_mode == "PEELING_CHAIN":
            peeling_chain = True
            hop_count = random.randint(4, 9)
            amt_crypto = round(random.uniform(8.0, 45.0), 4)
            risk_tags.extend(["MULTI_HOP_PEELING_CHAIN", "MICRO_CHANGE_SPLIT"])
        elif anomaly_mode == "LARGE_UNHOSTED":
            amt_crypto = round(random.uniform(25.0, 120.0), 4)
            risk_tags.append("LARGE_UNHOSTED_CAPITAL_FLIGHT")
        else:
            # Routine retail transfer
            amt_crypto = round(random.uniform(0.015, 0.45), 4)

        amt_usd = round(amt_crypto * price, 2)

        return CryptoTransferPayload(
            tx_hash=tx_hash,
            network=network,
            asset_symbol=asset,
            from_wallet=from_addr,
            to_wallet=to_addr,
            amount_crypto=amt_crypto,
            amount_usd=amt_usd,
            gas_fee_usd=gas_fee,
            block_height=None,  # Live in mempool
            is_mempool=True,
            mixer_risk=mixer_risk,
            peeling_chain=peeling_chain,
            hop_count=hop_count,
            unhosted_wallet=True,
            risk_tags=risk_tags,
            timestamp=timestamp_str,
            channel="crypto",
        )


# Global singleton generator instances
mock_upi_generator = MockUPIGenerator()
mock_crypto_generator = MockCryptoGenerator()
