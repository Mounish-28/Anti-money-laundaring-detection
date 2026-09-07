#!/usr/bin/env python3
"""
QuantumAML Nexus - Comprehensive Diagnostic Health Check Script
================================================================

Systematically tests and validates all 4 core operational subsystems:
1. FastAPI REST Core Accessibility (GET /docs)
2. CatBoost Banking Inference Engine (POST /api/v1/score/transaction) - SLA < 50ms
3. XGBoost Crypto Threat Graph Engine (POST /api/v1/score/crypto) - SLA < 50ms
4. WebSocket Broadcast Hub Delivery (ws://localhost:8000/ws/live) - Delivery < 2.0s
5. Live Ingestion Streamer Sampling (streamer.py & live_crypto_feed.py autonomous traffic)

Usage:
    python health_check.py [--host HOST] [--port PORT] [--stream-timeout SECONDS] [--allow-idle-streamers]
"""

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import httpx
import websockets

# Enable ANSI escape sequence rendering on Windows PowerShell / Command Prompt
if os.name == "nt":
    os.system("")

# ANSI Color Codes
CLR_RESET = "\033[0m"
CLR_BOLD = "\033[1m"
CLR_DIM = "\033[2m"
CLR_RED = "\033[91m"
CLR_GREEN = "\033[92m"
CLR_YELLOW = "\033[93m"
CLR_BLUE = "\033[94m"
CLR_MAGENTA = "\033[95m"
CLR_CYAN = "\033[96m"
CLR_WHITE = "\033[97m"

SLA_LATENCY_MAX_MS = 50.0
WS_DELIVERY_TIMEOUT_S = 2.0


class DiagnosticResult:
    def __init__(
        self,
        name: str,
        endpoint: str,
        latency_ms: float,
        passed: bool,
        details: str = "",
        error_diagnostic: str | None = None,
        is_warning: bool = False,
    ):
        self.name = name
        self.endpoint = endpoint
        self.latency_ms = latency_ms
        self.passed = passed
        self.details = details
        self.error_diagnostic = error_diagnostic
        self.is_warning = is_warning


class HealthChecker:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        stream_timeout: float = 5.0,
        allow_idle_streamers: bool = False,
        no_color: bool = False,
    ):
        self.host = host
        self.port = port
        self.base_http_url = f"http://{host}:{port}"
        self.base_ws_url = f"ws://{host}:{port}/ws/live"
        self.stream_timeout = stream_timeout
        self.allow_idle_streamers = allow_idle_streamers
        self.use_color = not no_color and sys.stdout.isatty()
        self.results: list[DiagnosticResult] = []

    def _c(self, text: str, color_code: str) -> str:
        """Applies ANSI styling if color output is enabled."""
        if not self.use_color:
            return text
        return f"{color_code}{text}{CLR_RESET}"

    # --------------------------------------------------------------------------
    # Test 1: FastAPI REST Core Accessibility
    # --------------------------------------------------------------------------
    async def test_rest_accessibility(
        self, client: httpx.AsyncClient
    ) -> DiagnosticResult:
        endpoint = "/docs"
        url = f"{self.base_http_url}{endpoint}"
        t0 = time.perf_counter()
        try:
            resp = await client.get(url, timeout=5.0)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if resp.status_code == 200:
                return DiagnosticResult(
                    name="FastAPI REST Core",
                    endpoint=f"GET {endpoint}",
                    latency_ms=elapsed_ms,
                    passed=True,
                    details="HTTP 200 OK (OpenAPI Docs Active)",
                )
            else:
                return DiagnosticResult(
                    name="FastAPI REST Core",
                    endpoint=f"GET {endpoint}",
                    latency_ms=elapsed_ms,
                    passed=False,
                    details=f"Unexpected Status: {resp.status_code}",
                    error_diagnostic=(
                        f"Server returned HTTP {resp.status_code} on {url}. "
                        "Check FastAPI application configuration in app/main.py."
                    ),
                )
        except Exception as ex:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return DiagnosticResult(
                name="FastAPI REST Core",
                endpoint=f"GET {endpoint}",
                latency_ms=elapsed_ms,
                passed=False,
                details="Connection Refused / Timeout",
                error_diagnostic=(
                    f"FastAPI is unreachable at {url} ({type(ex).__name__}: {ex}). "
                    f"Ensure uvicorn is running: python -m uvicorn app.main:app --host 0.0.0.0 --port {self.port}"
                ),
            )

    # --------------------------------------------------------------------------
    # Test 2: CatBoost Banking Inference (< 50ms SLA)
    # --------------------------------------------------------------------------
    async def test_catboost_banking(
        self, client: httpx.AsyncClient
    ) -> DiagnosticResult:
        endpoint = "/api/v1/score/transaction"
        url = f"{self.base_http_url}{endpoint}"
        payload = {
            "transaction_id": f"HEALTH-UPI-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_bank": "State Bank of India (SBIN0001234)",
            "to_bank": "HDFC Bank (HDFC0000567)",
            "account_from": "audit.remitter@oksbi",
            "account_to": "audit.beneficiary@okhdfcbank",
            "amount": 49850.00,
            "currency": "INR",
            "payment_format": "UPI",
        }

        t0 = time.perf_counter()
        try:
            resp = await client.post(url, json=payload, timeout=5.0)
            network_elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if resp.status_code != 200:
                return DiagnosticResult(
                    name="CatBoost Banking Engine",
                    endpoint=f"POST {endpoint}",
                    latency_ms=network_elapsed_ms,
                    passed=False,
                    details=f"HTTP {resp.status_code}",
                    error_diagnostic=(
                        f"Inference route returned HTTP {resp.status_code}: {resp.text}. "
                        "Verify TransactionInput validation schema in app/schemas/transaction.py."
                    ),
                )

            data = resp.json()
            score = data.get("risk_score")
            tier = data.get("risk_tier")
            engine_latency = data.get("latency_ms", network_elapsed_ms)

            if score is None or tier is None:
                return DiagnosticResult(
                    name="CatBoost Banking Engine",
                    endpoint=f"POST {endpoint}",
                    latency_ms=engine_latency,
                    passed=False,
                    details="Missing risk_score or risk_tier",
                    error_diagnostic=(
                        "Response payload missing mandatory fields ('risk_score', 'risk_tier'). "
                        f"Received payload: {json.dumps(data)}"
                    ),
                )

            sla_passed = engine_latency < SLA_LATENCY_MAX_MS
            details = (
                f"SLA Met ({engine_latency:.1f}ms | Tier: {tier} | Score: {score:.4f})"
            )
            diagnostic = None
            if not sla_passed:
                details = (
                    f"SLA VIOLATION ({engine_latency:.1f}ms >= {SLA_LATENCY_MAX_MS}ms)"
                )
                diagnostic = (
                    f"CatBoost inference latency {engine_latency:.2f}ms exceeded sub-50ms SLA target. "
                    "Review model inference execution in app.services.inference_engine.score_ibm_transaction."
                )

            return DiagnosticResult(
                name="CatBoost Banking Engine",
                endpoint=f"POST {endpoint}",
                latency_ms=engine_latency,
                passed=sla_passed,
                details=details,
                error_diagnostic=diagnostic,
            )

        except Exception as ex:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return DiagnosticResult(
                name="CatBoost Banking Engine",
                endpoint=f"POST {endpoint}",
                latency_ms=elapsed_ms,
                passed=False,
                details=f"Request Failed ({type(ex).__name__})",
                error_diagnostic=(
                    f"Failed to query CatBoost endpoint at {url}: {ex}. "
                    "Verify uvicorn server status and model loading in UnifiedInferenceEngine."
                ),
            )

    # --------------------------------------------------------------------------
    # Test 3: XGBoost Crypto Graph Inference (< 50ms SLA)
    # --------------------------------------------------------------------------
    async def test_xgboost_crypto(self, client: httpx.AsyncClient) -> DiagnosticResult:
        endpoint = "/api/v1/score/crypto"
        url = f"{self.base_http_url}{endpoint}"
        test_tx_hash = f"btc_health_tx_{uuid.uuid4().hex[:12]}"

        # Construct synthetic 166-D feature vector expected by Elliptic XGBoost
        synthetic_features = [1.8542] + [0.02] * 165

        payload = {
            "node_id": test_tx_hash,
            "tx_hash": test_tx_hash,
            "timestep": 49,
            "features": synthetic_features,
            "btc_value": 1.8542,
            "from_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "to_address": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
        }

        t0 = time.perf_counter()
        try:
            resp = await client.post(url, json=payload, timeout=5.0)
            network_elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if resp.status_code != 200:
                return DiagnosticResult(
                    name="XGBoost Crypto Threat Engine",
                    endpoint=f"POST {endpoint}",
                    latency_ms=network_elapsed_ms,
                    passed=False,
                    details=f"HTTP {resp.status_code}",
                    error_diagnostic=(
                        f"Crypto scoring endpoint returned HTTP {resp.status_code}: {resp.text}. "
                        "Verify EllipticNodeInput schema and 166-feature array formatting."
                    ),
                )

            data = resp.json()
            score = data.get("risk_score")
            tier = data.get("risk_tier")
            engine_latency = data.get("latency_ms", network_elapsed_ms)

            if score is None or tier is None:
                return DiagnosticResult(
                    name="XGBoost Crypto Threat Engine",
                    endpoint=f"POST {endpoint}",
                    latency_ms=engine_latency,
                    passed=False,
                    details="Missing risk_score or risk_tier",
                    error_diagnostic=(
                        "Crypto response payload missing mandatory fields ('risk_score', 'risk_tier'). "
                        f"Received payload: {json.dumps(data)}"
                    ),
                )

            sla_passed = engine_latency < SLA_LATENCY_MAX_MS
            details = (
                f"SLA Met ({engine_latency:.1f}ms | Tier: {tier} | Score: {score:.4f})"
            )
            diagnostic = None
            if not sla_passed:
                details = (
                    f"SLA VIOLATION ({engine_latency:.1f}ms >= {SLA_LATENCY_MAX_MS}ms)"
                )
                diagnostic = (
                    f"XGBoost crypto inference latency {engine_latency:.2f}ms exceeded sub-50ms SLA target. "
                    "Review app.services.inference_engine.score_elliptic."
                )

            return DiagnosticResult(
                name="XGBoost Crypto Threat Engine",
                endpoint=f"POST {endpoint}",
                latency_ms=engine_latency,
                passed=sla_passed,
                details=details,
                error_diagnostic=diagnostic,
            )

        except Exception as ex:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return DiagnosticResult(
                name="XGBoost Crypto Threat Engine",
                endpoint=f"POST {endpoint}",
                latency_ms=elapsed_ms,
                passed=False,
                details=f"Request Failed ({type(ex).__name__})",
                error_diagnostic=(
                    f"Failed to query XGBoost crypto endpoint at {url}: {ex}. "
                    "Ensure models/elliptic_bitcoin/elliptic_xgboost_optimized.json is properly loaded."
                ),
            )

    # --------------------------------------------------------------------------
    # Test 4: WebSocket Broadcast Hub Delivery (< 2.0s timeout)
    # --------------------------------------------------------------------------
    async def test_websocket_broadcast(
        self, client: httpx.AsyncClient
    ) -> DiagnosticResult:
        target_endpoint = "/ws/live"
        post_endpoint = "/api/v1/score/transaction"
        test_tx_id = f"WS-VERIFY-TRIGGER-{uuid.uuid4().hex[:8]}"

        payload = {
            "transaction_id": test_tx_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_bank": "ICICI Bank (ICIC0000890)",
            "to_bank": "Axis Bank (UTIB0000321)",
            "account_from": "health.ws.sender@okicici",
            "account_to": "health.ws.receiver@okaxis",
            "amount": 12500.00,
            "currency": "INR",
            "payment_format": "IMPS",
        }

        t0 = time.perf_counter()
        try:
            # Connect to WebSocket hub
            async with websockets.connect(self.base_ws_url, close_timeout=2.0) as ws:
                # Trigger HTTP POST scoring while connected
                post_resp = await client.post(
                    f"{self.base_http_url}{post_endpoint}", json=payload, timeout=3.0
                )
                if post_resp.status_code != 200:
                    return DiagnosticResult(
                        name="WebSocket Broadcast Hub",
                        endpoint=f"WS {target_endpoint}",
                        latency_ms=(time.perf_counter() - t0) * 1000.0,
                        passed=False,
                        details="HTTP Trigger Failed",
                        error_diagnostic=(
                            f"HTTP trigger {post_endpoint} failed with HTTP {post_resp.status_code}. "
                            "Cannot evaluate WebSocket delivery."
                        ),
                    )

                # Listen for the broadcast message matching our transaction_id
                matched = False
                event_payload = {}
                deadline = time.perf_counter() + WS_DELIVERY_TIMEOUT_S

                while time.perf_counter() < deadline:
                    remaining_timeout = max(0.1, deadline - time.perf_counter())
                    try:
                        raw_msg = await asyncio.wait_for(
                            ws.recv(), timeout=remaining_timeout
                        )
                        msg_data = json.loads(raw_msg)
                        if msg_data.get("transaction_id") == test_tx_id:
                            matched = True
                            event_payload = msg_data
                            break
                    except asyncio.TimeoutError:
                        break
                    except Exception:
                        continue

                delivery_latency_ms = (time.perf_counter() - t0) * 1000.0

                if matched:
                    engine = event_payload.get("engine", "UNKNOWN")
                    tier = event_payload.get("risk_tier", "UNKNOWN")
                    return DiagnosticResult(
                        name="WebSocket Broadcast Hub",
                        endpoint=f"WS {target_endpoint}",
                        latency_ms=delivery_latency_ms,
                        passed=True,
                        details=f"Push Delivered (<2s | Engine: {engine} | Tier: {tier})",
                    )
                else:
                    return DiagnosticResult(
                        name="WebSocket Broadcast Hub",
                        endpoint=f"WS {target_endpoint}",
                        latency_ms=delivery_latency_ms,
                        passed=False,
                        details=f"Timeout (> {WS_DELIVERY_TIMEOUT_S}s Window)",
                        error_diagnostic=(
                            f"WebSocket client did not receive broadcast for transaction {test_tx_id} within {WS_DELIVERY_TIMEOUT_S}s. "
                            "Check ConnectionManager.broadcast() execution in app/main.py and websocket connection tracking."
                        ),
                    )

        except Exception as ex:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return DiagnosticResult(
                name="WebSocket Broadcast Hub",
                endpoint=f"WS {target_endpoint}",
                latency_ms=elapsed_ms,
                passed=False,
                details=f"Handshake Failed ({type(ex).__name__})",
                error_diagnostic=(
                    f"Failed to connect to WebSocket hub at {self.base_ws_url}: {ex}. "
                    "Ensure FastAPI is running and @app.websocket('/ws/live') endpoint is properly mounted."
                ),
            )

    # --------------------------------------------------------------------------
    # Test 5: Live Ingestion Streamer Verification (Stream Sampling)
    # --------------------------------------------------------------------------
    async def test_streamer_verification(self) -> DiagnosticResult:
        target_endpoint = f"/ws/live ({self.stream_timeout:.1f}s Sample)"
        t0 = time.perf_counter()

        fiat_count = 0
        crypto_count = 0
        total_observed = 0

        try:
            async with websockets.connect(self.base_ws_url, close_timeout=2.0) as ws:
                sampling_deadline = time.perf_counter() + self.stream_timeout

                while time.perf_counter() < sampling_deadline:
                    remaining = max(0.05, sampling_deadline - time.perf_counter())
                    try:
                        raw_msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
                        msg_data = json.loads(raw_msg)
                        engine = msg_data.get("engine", "")
                        rail = msg_data.get("rail", "")
                        currency = msg_data.get("currency", "")

                        if engine == "FIAT_BANKING" or currency == "INR":
                            fiat_count += 1
                        elif (
                            engine == "CRYPTO_FORENSICS"
                            or rail == "BTC"
                            or currency == "BTC"
                        ):
                            crypto_count += 1

                        total_observed += 1
                    except asyncio.TimeoutError:
                        break
                    except Exception:
                        continue

            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if total_observed > 0:
                return DiagnosticResult(
                    name="Live Ingestion Streamers",
                    endpoint=f"WS {target_endpoint}",
                    latency_ms=elapsed_ms,
                    passed=True,
                    details=f"{total_observed} Live Events ({fiat_count} Fiat Banking, {crypto_count} Crypto Mempool)",
                )
            else:
                # No messages observed during the sample window
                is_warning = self.allow_idle_streamers
                diag_msg = (
                    f"No autonomous streaming events observed during {self.stream_timeout:.1f}s sample window. "
                    "Ensure background streamer processes are active: "
                    "Run 'python streamer.py' for Indian Banking Switch traffic and/or 'python live_crypto_feed.py' for Bitcoin Mempool ingestion."
                )
                return DiagnosticResult(
                    name="Live Ingestion Streamers",
                    endpoint=f"WS {target_endpoint}",
                    latency_ms=elapsed_ms,
                    passed=is_warning,
                    is_warning=is_warning,
                    details=(
                        f"0 Events Captured in {self.stream_timeout:.1f}s (Streamers Idle)"
                        if is_warning
                        else f"0 Events Detected (Timeout {self.stream_timeout:.1f}s)"
                    ),
                    error_diagnostic=diag_msg,
                )

        except Exception as ex:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return DiagnosticResult(
                name="Live Ingestion Streamers",
                endpoint=f"WS {target_endpoint}",
                latency_ms=elapsed_ms,
                passed=False,
                details=f"WS Sampling Error ({type(ex).__name__})",
                error_diagnostic=(
                    f"Could not sample WebSocket stream: {ex}. "
                    f"Verify server is listening on {self.base_ws_url}."
                ),
            )

    # --------------------------------------------------------------------------
    # Master Execution & Reporting Pipeline
    # --------------------------------------------------------------------------
    async def run_all(self, skip_streamers: bool = False) -> int:
        print("\n" + self._c("=" * 106, CLR_CYAN))
        print(
            self._c(
                "              QUANTUMAML NEXUS - PRODUCTION SUITE DIAGNOSTIC HEALTH CHECK",
                CLR_BOLD + CLR_WHITE,
            )
        )
        print(self._c("=" * 106, CLR_CYAN))
        print(
            f"  Target Host: {self._c(self.base_http_url, CLR_CYAN)}  |  "
            f"WebSocket: {self._c(self.base_ws_url, CLR_CYAN)}  |  "
            f"Target SLA: {self._c(f'< {SLA_LATENCY_MAX_MS} ms', CLR_GREEN)}"
        )
        print(self._c("-" * 106, CLR_DIM))

        async with httpx.AsyncClient(timeout=10.0) as http_client:
            # 1. FastAPI REST Core
            res1 = await self.test_rest_accessibility(http_client)
            self.results.append(res1)

            # If REST core is completely down, skip subsequent HTTP/WS tests
            if not res1.passed:
                print(
                    self._c(
                        "  [!] FATAL: FastAPI REST Core is unreachable. Aborting downstream tests.",
                        CLR_RED,
                    )
                )
            else:
                # 2. CatBoost Banking Engine
                res2 = await self.test_catboost_banking(http_client)
                self.results.append(res2)

                # 3. XGBoost Crypto Threat Engine
                res3 = await self.test_xgboost_crypto(http_client)
                self.results.append(res3)

                # 4. WebSocket Broadcast Hub
                res4 = await self.test_websocket_broadcast(http_client)
                self.results.append(res4)

                # 5. Live Ingestion Streamer Verification
                if not skip_streamers:
                    res5 = await self.test_streamer_verification()
                    self.results.append(res5)

        # Print Formatted Results Table
        self.render_report_table()

        # Check Overall Success
        critical_failed = any(not r.passed and not r.is_warning for r in self.results)
        return 1 if critical_failed else 0

    def render_report_table(self):
        col_name_w = 30
        col_endp_w = 34
        col_lat_w = 12
        col_stat_w = 10
        col_det_w = 40

        header_line = (
            f"  {'COMPONENT / SERVICE NAME':<{col_name_w}}"
            f"{'TARGET ENDPOINT':<{col_endp_w}}"
            f"{'LATENCY':<{col_lat_w}}"
            f"{'STATUS':<{col_stat_w}}"
            f"{'DETAILS'}"
        )
        print("\n" + self._c(header_line, CLR_BOLD + CLR_WHITE))
        print(self._c("-" * 106, CLR_DIM))

        for res in self.results:
            lat_str = f"{res.latency_ms:.1f} ms"

            if res.passed:
                status_str = self._c("[PASS]", CLR_BOLD + CLR_GREEN)
            elif res.is_warning:
                status_str = self._c("[WARN]", CLR_BOLD + CLR_YELLOW)
            else:
                status_str = self._c("[FAIL]", CLR_BOLD + CLR_RED)

            line = (
                f"  {res.name:<{col_name_w}}"
                f"{res.endpoint:<{col_endp_w}}"
                f"{lat_str:<{col_lat_w}}"
                f"{status_str:<{col_stat_w + (len(status_str) - 6)}}"
                f"{res.details}"
            )
            print(line)

        print(self._c("-" * 106, CLR_DIM))

        # Actionable Diagnostics and Alerts
        failures = [r for r in self.results if not r.passed]
        warnings = [r for r in self.results if r.is_warning]

        if failures or warnings:
            print(
                "\n"
                + self._c(
                    "DIAGNOSTIC ALERTS & REMEDIATION ACTIONS:", CLR_BOLD + CLR_YELLOW
                )
            )
            print(self._c("-" * 106, CLR_DIM))

            for f in failures:
                print(
                    f"  {self._c('[FAIL]', CLR_BOLD + CLR_RED)} {self._c(f.name, CLR_BOLD)} ({f.endpoint}):"
                )
                print(f"         {f.error_diagnostic or f.details}\n")

            for w in warnings:
                print(
                    f"  {self._c('[WARN]', CLR_BOLD + CLR_YELLOW)} {self._c(w.name, CLR_BOLD)} ({w.endpoint}):"
                )
                print(f"         {w.error_diagnostic or w.details}\n")

            print(self._c("-" * 106, CLR_DIM))

        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)

        if not failures:
            summary_text = (
                f"  SUMMARY: {passed_count}/{total_count} Tests Passed | "
                "All Subsystems Operational & Sub-50ms SLA Compliant."
            )
            print(self._c(summary_text, CLR_BOLD + CLR_GREEN))
        else:
            summary_text = (
                f"  SUMMARY: {passed_count}/{total_count} Tests Passed | "
                f"{len(failures)} Service(s) Failed Operational / SLA Thresholds."
            )
            print(self._c(summary_text, CLR_BOLD + CLR_RED))

        print(self._c("=" * 106, CLR_CYAN) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="QuantumAML Nexus Comprehensive Service Health & SLA Diagnostic Suite"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="FastAPI host address (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="FastAPI server port (default: 8000)",
    )
    parser.add_argument(
        "--stream-timeout",
        type=float,
        default=5.0,
        help="Sampling window duration in seconds for live background streamers (default: 5.0)",
    )
    parser.add_argument(
        "--allow-idle-streamers",
        action="store_true",
        help="Treat 0 detected background streamer events as a warning instead of a hard failure",
    )
    parser.add_argument(
        "--skip-streamers",
        action="store_true",
        help="Skip Test 5 (streamer sampling verification)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI terminal colors",
    )

    args = parser.parse_args()

    checker = HealthChecker(
        host=args.host,
        port=args.port,
        stream_timeout=args.stream_timeout,
        allow_idle_streamers=args.allow_idle_streamers,
        no_color=args.no_color,
    )

    exit_code = asyncio.run(checker.run_all(skip_streamers=args.skip_streamers))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
