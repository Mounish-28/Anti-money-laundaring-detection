#!/usr/bin/env python3
"""
QuantumAML Nexus - Standalone Indian Banking Transaction Streamer
Procedurally generates realistic continuous Indian banking switch traffic (UPI, IMPS, NEFT, RTGS)
and streams scored events to the QuantumAML FastAPI serving layer.
"""

import argparse
import logging
import random
import sys
import time
from datetime import datetime, timezone
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None

try:
    import requests
except ImportError:
    requests = None

# Ensure UTF-8 output across Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TransactionStreamer")

# ANSI terminal colors
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
DIM = "\033[2m"

# ------------------------------------------------------------------------------
# Static Procedural Entity Registries (Zero Dataset Replay)
# ------------------------------------------------------------------------------
INDIAN_FIRST_NAMES = [
    "Amit",
    "Priya",
    "Rajesh",
    "Sunil",
    "Ananya",
    "Rohit",
    "Sneha",
    "Vikram",
    "Neha",
    "Arjun",
    "Pooja",
    "Deepak",
    "Kavita",
    "Suresh",
    "Meera",
    "Aditya",
    "Ritu",
    "Manoj",
    "Divya",
    "Sanjay",
    "Tanvi",
    "Alok",
    "Shreya",
    "Rohan",
    "Nisha",
    "Gaurav",
    "Swati",
    "Karan",
    "Aarti",
    "Varun",
    "Rahul",
    "Naveen",
    "Pallavi",
    "Vivek",
    "Preeti",
    "Kunal",
    "Harish",
    "Smita",
    "Dev",
    "Isha",
]

INDIAN_LAST_NAMES = [
    "Sharma",
    "Patel",
    "Verma",
    "Mehta",
    "Iyer",
    "Gupta",
    "Reddy",
    "Singh",
    "Nair",
    "Choudhury",
    "Bose",
    "Joshi",
    "Kulkarni",
    "Rao",
    "Mishra",
    "Deshmukh",
    "Aggarwal",
    "Pillai",
    "Bhat",
    "Saxena",
    "Mukherjee",
    "Kapoor",
    "Chopra",
    "Das",
    "Menon",
    "Bhattacharya",
    "Trivedi",
    "Banerjee",
    "Ghosh",
]

COMMERCIAL_ENTITIES = [
    "Apex Logistics Pvt Ltd",
    "CloudNine Tech Solutions",
    "Bharat Mart Retail",
    "Zenith Infotech Ltd",
    "Kaveri Enterprises",
    "Mahalaxmi Trading Co",
    "BlueDart Express Partner",
    "Narmada Agro Mills",
    "Tata Telemedia Hub",
    "Swiggy Merchant Ops",
    "Zomato Partner Hub",
    "Flipkart Seller 99",
    "UrbanClap Services Pvt Ltd",
    "Reliance Retail Branch 40",
    "Paytm Payments Merchant",
    "Infosys BPM Services",
    "Hindalco Ancillary Works",
    "Godrej Agrovet Agency",
    "Adani Bunkering Corp",
    "L&T Electrical Systems",
]

HAWALA_SHELL_ENTITIES = [
    "Golden Bullion International FZE",
    "SilkRoute Global Logistics Ltd",
    "Offshore Apex Holdings Corp",
    "Pacific Diamond Trading LLP",
    "Eurasian Commodities DMCC",
    "Royal Falcon Precious Metals Ltd",
    "Maritime Horizon Shipping Corp",
    "TransAsia Exchange House Pvt Ltd",
]

MERCHANT_HANDLES = [
    "merchant.swiggy@okhdfcbank",
    "paytm.merchant.grocery@paytm",
    "zomato.order@okicici",
    "reliance.fresh@oksbi",
    "flipkart.pay@okaxis",
    "amazon.in@ybl",
    "uber.trip@okhdfcbank",
    "ola.cabs@okaxis",
    "apollo.pharmacy@okicici",
    "bigbasket.sales@oksbi",
]

VPA_HANDLES = ["@oksbi", "@okhdfcbank", "@okicici", "@okaxis", "@paytm", "@ybl"]

BANKS_AND_IFSC_MAP = [
    ("State Bank of India", "SBIN"),
    ("HDFC Bank", "HDFC"),
    ("ICICI Bank", "ICIC"),
    ("Axis Bank", "UTIB"),
    ("Punjab National Bank", "PUNB"),
    ("Bank of Baroda", "BARB"),
    ("Kotak Mahindra Bank", "KKBK"),
    ("IndusInd Bank", "INDB"),
]

HIGH_RISK_HAWALA_IFSC = [
    ("State Bank of India", "SBIN0061299"),  # Border / Free Trade Hub
    ("HDFC Bank", "HDFC0009941"),  # Offshore Bullion Clearing
    ("Axis Bank", "UTIB0004812"),  # Free Trade Zone
    ("ICICI Bank", "ICIC0007781"),  # Special Economic Zone
    ("Bank of Baroda", "BARB0098231"),  # Bullion Exchange Branch
]


class EntityGenerator:
    """Procedural generator for authentic Indian banking identities and credentials."""

    @staticmethod
    def generate_person_name() -> str:
        first = random.choice(INDIAN_FIRST_NAMES)
        last = random.choice(INDIAN_LAST_NAMES)
        return f"{first} {last}"

    @staticmethod
    def generate_vpa(name: str | None = None) -> str:
        if name is None:
            name = EntityGenerator.generate_person_name()
        clean = name.lower().replace(" ", ".")
        handle = random.choice(VPA_HANDLES)
        suffix = random.choice(
            ["", str(random.randint(10, 99)), str(random.randint(100, 999))]
        )
        return f"{clean}{suffix}{handle}"

    @staticmethod
    def generate_bank(high_risk: bool = False) -> tuple[str, str]:
        """Returns tuple of (Bank Name, Formatted Bank String with IFSC)."""
        if high_risk:
            bank_name, ifsc = random.choice(HIGH_RISK_HAWALA_IFSC)
        else:
            bank_name, prefix = random.choice(BANKS_AND_IFSC_MAP)
            branch_num = random.randint(1000, 999999)
            ifsc = f"{prefix}{branch_num:07d}"
        return bank_name, f"{bank_name} ({ifsc})"

    @staticmethod
    def generate_account_number() -> str:
        """Generates standard 12-16 digit Indian bank account number."""
        return f"ACC{random.randint(100000000000, 999999999999)}"

    @staticmethod
    def generate_utr() -> str:
        """Generates authentic 12-digit Indian banking switch UTR reference."""
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_suffix = random.randint(10000000, 99999999)
        return f"UTR-{today_str}-{random_suffix}"

    @staticmethod
    def get_iso_timestamp() -> str:
        """Generates current UTC timestamp in ISO-8601 format."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ------------------------------------------------------------------------------
# Baseline Spending Distribution Generator (85% of Traffic)
# ------------------------------------------------------------------------------
def generate_baseline_transaction() -> tuple[dict[str, Any], str]:
    """
    Generates a legitimate baseline transaction weighted across payment rails:
    - 60% UPI
    - 25% IMPS
    - 10% NEFT
    - 5% RTGS
    """
    rail = random.choices(["UPI", "IMPS", "NEFT", "RTGS"], weights=[60, 25, 10, 5])[0]

    from_bank_name, from_bank = EntityGenerator.generate_bank()
    to_bank_name, to_bank = EntityGenerator.generate_bank()

    # Log-normal baseline amounts by rail
    if rail == "UPI":
        # Micro-transfers (₹50 - ₹4,500) or standard bills (₹5,000 - ₹35,000)
        if random.random() < 0.85:
            # Micro-transfer
            amount = round(random.uniform(50.0, 4500.0), 2)
            remitter = EntityGenerator.generate_vpa()
            beneficiary = (
                random.choice(MERCHANT_HANDLES)
                if random.random() < 0.50
                else EntityGenerator.generate_vpa()
            )
        else:
            # P2M bill payment
            amount = round(random.uniform(5000.0, 35000.0), 2)
            remitter = EntityGenerator.generate_vpa()
            beneficiary = random.choice(MERCHANT_HANDLES)

        account_from = remitter
        account_to = beneficiary

    elif rail == "IMPS":
        # Micro P2P or vendor payout (₹200 to ₹35,000)
        if random.random() < 0.65:
            amount = round(random.uniform(200.0, 4500.0), 2)
        else:
            amount = round(random.uniform(5000.0, 35000.0), 2)

        account_from = (
            EntityGenerator.generate_vpa()
            if random.random() < 0.40
            else EntityGenerator.generate_account_number()
        )
        account_to = EntityGenerator.generate_account_number()

    elif rail == "NEFT":
        # Vendor invoice / corporate clearing (₹15,000 to ₹3,00,000)
        if random.random() < 0.60:
            amount = round(random.uniform(15000.0, 85000.0), 2)
        else:
            amount = round(random.uniform(100000.0, 300000.0), 2)

        account_from = f"{random.choice(COMMERCIAL_ENTITIES)} ({EntityGenerator.generate_account_number()})"
        account_to = f"{random.choice(COMMERCIAL_ENTITIES)} ({EntityGenerator.generate_account_number()})"

    else:  # RTGS
        # High-value legitimate commercial settlement (₹2,00,000 to ₹5,00,000)
        amount = round(random.uniform(200000.0, 500000.0), 2)
        account_from = f"{random.choice(COMMERCIAL_ENTITIES)} ({EntityGenerator.generate_account_number()})"
        account_to = f"{random.choice(COMMERCIAL_ENTITIES)} ({EntityGenerator.generate_account_number()})"

    payload = {
        "transaction_id": EntityGenerator.generate_utr(),
        "timestamp": EntityGenerator.get_iso_timestamp(),
        "from_bank": from_bank,
        "to_bank": to_bank,
        "account_from": account_from,
        "account_to": account_to,
        "amount": amount,
        "currency": "INR",
        "payment_format": rail,
    }

    return payload, "BASELINE_LEGITIMATE"


# ------------------------------------------------------------------------------
# Algorithmic Anomaly Synthesizers (15% of Traffic)
# ------------------------------------------------------------------------------
def generate_typology_a_structuring() -> list[tuple[dict[str, Any], str]]:
    """
    Typology A: PAN Structuring / Smurfing.
    A rapid sequence of 4 to 8 distinct synthetic mule VPAs each sending amounts
    strictly between ₹48,000.00 and ₹49,950.00 to a single aggregator VPA
    within 15 seconds to simulate evading the Indian ₹50,000 PAN reporting threshold.
    """
    aggregator_vpa = f"aggregator.{random.choice(INDIAN_LAST_NAMES).lower()}{random.randint(10, 99)}@paytm"
    _, to_bank = EntityGenerator.generate_bank()

    count = random.randint(4, 8)
    sequence = []

    for i in range(count):
        mule_name = EntityGenerator.generate_person_name()
        mule_vpa = EntityGenerator.generate_vpa(mule_name)
        _, from_bank = EntityGenerator.generate_bank()
        # Strictly below ₹50,000 threshold
        amount = round(random.uniform(48000.0, 49950.0), 2)

        tx = {
            "transaction_id": EntityGenerator.generate_utr(),
            "timestamp": EntityGenerator.get_iso_timestamp(),
            "from_bank": from_bank,
            "to_bank": to_bank,
            "account_from": mule_vpa,
            "account_to": aggregator_vpa,
            "amount": amount,
            "currency": "INR",
            "payment_format": "UPI",
        }
        tag = f"PAN_STRUCTURING_SMURFING [Mule {i + 1}/{count} -> {aggregator_vpa}]"
        sequence.append((tx, tag))

    return sequence


def generate_typology_b_hawala_rtgs() -> list[tuple[dict[str, Any], str]]:
    """
    Typology B: High-Value Hawala RTGS.
    Sudden out-of-band transfers of ₹25,00,000 to ₹1,20,00,000 between newly
    created corporate accounts domiciled at high-risk branch IFSCs.
    """
    _, from_bank = EntityGenerator.generate_bank(high_risk=True)
    _, to_bank = EntityGenerator.generate_bank(high_risk=True)

    from_corp = f"{random.choice(HAWALA_SHELL_ENTITIES)} ({EntityGenerator.generate_account_number()})"
    to_corp = f"{random.choice(HAWALA_SHELL_ENTITIES)} ({EntityGenerator.generate_account_number()})"

    # ₹25 Lakhs to ₹1.2 Crores
    amount = round(random.uniform(2500000.0, 12000000.0), 2)

    tx = {
        "transaction_id": EntityGenerator.generate_utr(),
        "timestamp": EntityGenerator.get_iso_timestamp(),
        "from_bank": from_bank,
        "to_bank": to_bank,
        "account_from": from_corp,
        "account_to": to_corp,
        "amount": amount,
        "currency": "INR",
        "payment_format": "RTGS",
    }
    tag = f"HIGH_VALUE_HAWALA_RTGS [₹{amount:,.2f}]"
    return [(tx, tag)]


def generate_typology_c_velocity_draining() -> list[tuple[dict[str, Any], str]]:
    """
    Typology C: Velocity / Mule Draining.
    A single consumer account suddenly firing 6 to 10 rapid IMPS transfers
    (₹10,000 to ₹25,000 each) to different beneficiary accounts in under 10 seconds.
    """
    victim_name = EntityGenerator.generate_person_name()
    victim_account = f"{victim_name} ({EntityGenerator.generate_account_number()})"
    _, from_bank = EntityGenerator.generate_bank()

    count = random.randint(6, 10)
    sequence = []

    for i in range(count):
        beneficiary_name = EntityGenerator.generate_person_name()
        beneficiary_acc = (
            f"{beneficiary_name} ({EntityGenerator.generate_account_number()})"
        )
        _, to_bank = EntityGenerator.generate_bank()
        amount = round(random.uniform(10000.0, 25000.0), 2)

        tx = {
            "transaction_id": EntityGenerator.generate_utr(),
            "timestamp": EntityGenerator.get_iso_timestamp(),
            "from_bank": from_bank,
            "to_bank": to_bank,
            "account_from": victim_account,
            "account_to": beneficiary_acc,
            "amount": amount,
            "currency": "INR",
            "payment_format": "IMPS",
        }
        tag = f"VELOCITY_MULE_DRAINING [Drain {i + 1}/{count} from {victim_name}]"
        sequence.append((tx, tag))

    return sequence


# ------------------------------------------------------------------------------
# HTTP Network Client & Dispatcher
# ------------------------------------------------------------------------------
class ResilientDispatcher:
    """Dispatches transaction payloads with resilient retry and graceful backoff."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self._httpx_client: Any | None = None
        if httpx is not None:
            self._httpx_client = httpx.Client(timeout=10.0)

    def dispatch(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any] | None, str]:
        """Transmits JSON payload and returns (success, response_dict, error_message)."""
        if self._httpx_client is not None:
            try:
                resp = self._httpx_client.post(self.endpoint, json=payload)
                if resp.status_code == 200:
                    return True, resp.json(), ""
                return False, None, f"HTTP {resp.status_code}: {resp.text[:120]}"
            except Exception as e:
                return False, None, str(e)
        elif requests is not None:
            try:
                resp = requests.post(self.endpoint, json=payload, timeout=10.0)
                if resp.status_code == 200:
                    return True, resp.json(), ""
                return False, None, f"HTTP {resp.status_code}: {resp.text[:120]}"
            except Exception as e:
                return False, None, str(e)
        else:
            return False, None, "Neither httpx nor requests library is installed."

    def close(self):
        if self._httpx_client is not None:
            try:
                self._httpx_client.close()
            except Exception:
                pass


# ------------------------------------------------------------------------------
# Formatted Terminal Logger
# ------------------------------------------------------------------------------
def format_log_line(
    payload: dict[str, Any],
    tag: str,
    resp: dict[str, Any] | None,
    err: str,
) -> str:
    """Formats terminal output for high readability and operational monitoring."""
    ts = payload.get("timestamp", "UNKNOWN_TIME")
    rail = payload.get("payment_format", "UPI").ljust(4)
    amount_str = f"₹{payload.get('amount', 0.0):>13,.2f}"

    # Truncate entity handles for scannable columns
    from_e = str(payload.get("account_from", ""))[:28].ljust(28)
    to_e = str(payload.get("account_to", ""))[:28].ljust(28)

    is_anomaly = "ANOMALY" in tag or tag != "BASELINE_LEGITIMATE"

    if err:
        status_color = RED
        status_text = f"ERR: {err[:35]}"
    elif resp:
        tier = resp.get("risk_tier", "LOW")
        score = resp.get("risk_score", 0.0)
        lat = resp.get("latency_ms", 0.0)

        if tier in ("CRITICAL_SAR", "CRITICAL"):
            tier_color = RED + BOLD
        elif tier == "HIGH":
            tier_color = YELLOW + BOLD
        elif tier in ("ELEVATED", "MEDIUM"):
            tier_color = CYAN
        else:
            tier_color = GREEN

        status_text = f"HTTP 200 [{tier_color}{tier}{RESET} p={score:.3f} {lat:.1f}ms]"
    else:
        status_text = "SENT"

    if is_anomaly:
        tag_badge = f"{RED}{BOLD}[{tag}]{RESET}"
    else:
        tag_badge = f"{DIM}[NORMAL]{RESET}"

    return (
        f"{DIM}{ts}{RESET} | {BOLD}{rail}{RESET} | {CYAN}{amount_str}{RESET} | "
        f"{from_e} -> {to_e} | {tag_badge} | {status_text}"
    )


# ------------------------------------------------------------------------------
# Main Continuous Streaming Loop
# ------------------------------------------------------------------------------
def run_streamer(
    endpoint: str,
    base_interval: float,
    anomaly_rate: float,
    max_count: int,
):
    """Executes continuous infinite transaction generation and transmission."""
    print("=" * 105)
    print(
        f"{BOLD}{CYAN} QuantumAML Nexus - Live Indian Banking Switch Streamer {RESET}"
    )
    print(f" Target Endpoint : {BOLD}{endpoint}{RESET}")
    print(f" Stream Cadence  : {base_interval:.2f}s (jitter: 1.0s - 2.0s)")
    print(f" Anomaly Rate    : {anomaly_rate * 100:.1f}%")
    print(
        f" Total Count     : {'Infinite (Ctrl+C to stop)' if max_count <= 0 else max_count}"
    )
    print("=" * 105)

    dispatcher = ResilientDispatcher(endpoint)
    sent_count = 0
    anomaly_count = 0
    consecutive_errors = 0

    pending_queue: list[tuple[dict[str, Any], str, float]] = []

    try:
        while True:
            if max_count > 0 and sent_count >= max_count:
                print(
                    f"\n{GREEN}Reached requested count of {max_count} transactions. Shutting down.{RESET}"
                )
                break

            # If anomaly burst has pending items, drain them with rapid inter-transaction delays
            if pending_queue:
                tx_payload, tag, delay = pending_queue.pop(0)
                time.sleep(delay)
            else:
                # Decide whether to inject an anomaly burst
                if random.random() < anomaly_rate:
                    typology = random.choice(["A", "B", "C"])
                    if typology == "A":
                        burst = generate_typology_a_structuring()
                        # Inter-transaction delay ~0.4s to 0.9s (under 15s total for 4-8 txs)
                        for item in burst:
                            pending_queue.append(
                                (item[0], item[1], random.uniform(0.4, 0.9))
                            )
                    elif typology == "B":
                        burst = generate_typology_b_hawala_rtgs()
                        for item in burst:
                            pending_queue.append(
                                (item[0], item[1], random.uniform(1.0, 1.8))
                            )
                    else:
                        burst = generate_typology_c_velocity_draining()
                        # Rapid draining ~0.2s to 0.6s (under 10s total for 6-10 txs)
                        for item in burst:
                            pending_queue.append(
                                (item[0], item[1], random.uniform(0.2, 0.6))
                            )

                    tx_payload, tag, _ = pending_queue.pop(0)
                else:
                    # Baseline legitimate traffic
                    tx_payload, tag = generate_baseline_transaction()

            # Transmit to FastAPI endpoint
            success, resp, err = dispatcher.dispatch(tx_payload)

            if success:
                consecutive_errors = 0
            else:
                consecutive_errors += 1
                if consecutive_errors in (1, 5, 10) or consecutive_errors % 20 == 0:
                    logger.warning(
                        "FastAPI endpoint unreachable at %s (%s). Retrying without terminating...",
                        endpoint,
                        err,
                    )
                # Exponential backoff on server outage (up to 5s)
                time.sleep(min(5.0, 0.5 * (2 ** min(consecutive_errors, 4))))

            sent_count += 1
            if "ANOMALY" in tag or tag != "BASELINE_LEGITIMATE":
                anomaly_count += 1

            # Print readable terminal log line
            print(format_log_line(tx_payload, tag, resp, err))

            # Continuous cadence pause for baseline transactions (1.0 to 2.0s)
            if not pending_queue:
                jittered_pause = max(
                    0.2, random.uniform(base_interval * 0.8, base_interval * 1.3)
                )
                time.sleep(jittered_pause)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Streamer terminated by user (Ctrl+C).{RESET}")
    finally:
        dispatcher.close()
        print(
            f"\nSummary: Sent {sent_count} transactions ({anomaly_count} anomalies injected)."
        )


# ------------------------------------------------------------------------------
# CLI Argument Parser
# ------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="QuantumAML Nexus - Continuous Indian Banking Transaction Streamer"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://localhost:8000/api/v1/score/transaction",
        help="FastAPI scoring endpoint URL (default: http://localhost:8000/api/v1/score/transaction)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.5,
        help="Target streaming interval in seconds (default: 1.5)",
    )
    parser.add_argument(
        "--anomaly-rate",
        type=float,
        default=0.15,
        help="Fraction of transactions triggering crime typologies (default: 0.15)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Number of transactions to send before exiting (default: 0 for infinite)",
    )

    args = parser.parse_args()
    run_streamer(
        endpoint=args.endpoint,
        base_interval=args.interval,
        anomaly_rate=args.anomaly_rate,
        max_count=args.count,
    )


if __name__ == "__main__":
    main()
