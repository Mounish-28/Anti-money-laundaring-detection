#!/usr/bin/env python3
"""
QuantumAML Nexus - Unified Multi-Process Orchestration Runner
==============================================================

Coordinates, launches, streams logs, and manages graceful shutdown for all 4 runtime services:
1. FastAPI Backend Core (uvicorn app.main:app --port 8000 --reload)
2. Indian Banking Switch Streamer (streamer.py --interval 1.5)
3. Live Bitcoin Mempool Ingestion Feed (live_crypto_feed.py --rate-limit 1.0)
4. Vite React Frontend (npm run dev in nexus-frontend/)

Features:
- Health check polling on http://localhost:8000/docs (0.5s cadence, 20s timeout) before launching streamers & frontend.
- Line-by-line multiplexed terminal logging with color-coded ANSI service tags.
- Robust SIGINT / Ctrl+C interception and Windows taskkill process tree mitigation (no zombie ports 8000 / 5173).
- CLI customization: --backend-port, --no-crypto, --no-frontend, --streamer-interval, --crypto-rate-limit.

Usage:
    python runner.py [--backend-port PORT] [--no-crypto] [--no-frontend] [--no-color]
"""

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from typing import Dict, List, Optional

# Enable ANSI escape sequence rendering on Windows consoles
if os.name == "nt":
    os.system("")

# ANSI Styling Tokens
CLR_RESET = "\033[0m"
CLR_BOLD = "\033[1m"
CLR_DIM = "\033[2m"
CLR_CYAN = "\033[96m"              # [BACKEND] (Cyan)
CLR_GREEN = "\033[92m"             # [BANKING] (Green)
CLR_YELLOW = "\033[93m"            # [CRYPTO] (Yellow)
CLR_MAGENTA = "\033[95m"           # [FRONTEND] (Magenta)
CLR_WHITE = "\033[1m\033[97m"      # [ORCHESTRATOR] (Bold White)
CLR_RED = "\033[91m"

SERVICE_CONFIGS = [
    {
        "id": "backend",
        "name": "BACKEND",
        "color": CLR_CYAN,
        "is_primary": True,
    },
    {
        "id": "banking",
        "name": "BANKING",
        "color": CLR_GREEN,
        "is_primary": False,
    },
    {
        "id": "crypto",
        "name": "CRYPTO",
        "color": CLR_YELLOW,
        "is_primary": False,
    },
    {
        "id": "frontend",
        "name": "FRONTEND",
        "color": CLR_MAGENTA,
        "is_primary": False,
    },
]


def resolve_python_path() -> str:
    """Finds the best Python executable (preferring repo virtualenv)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, ".venv", "Scripts", "python.exe"),  # Windows venv
        os.path.join(base_dir, ".venv", "bin", "python"),          # POSIX venv
        sys.executable,
    ]
    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return sys.executable


def resolve_npm_path() -> str:
    """Resolves the npm executable across Windows and POSIX systems."""
    if sys.platform == "win32":
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            npm_cmd = os.path.join(path_dir, "npm.cmd")
            if os.path.isfile(npm_cmd):
                return npm_cmd
        return "npm.cmd"
    return "npm"


class ServiceProcess:
    """Manages a single child process with real-time, non-blocking stream demultiplexing."""

    def __init__(self, service_id: str, name: str, color: str, cmd: List[str], cwd: str):
        self.service_id = service_id
        self.name = name
        self.color = color
        self.cmd = cmd
        self.cwd = cwd
        self.proc: Optional[subprocess.Popen] = None
        self.reader_thread: Optional[threading.Thread] = None

    def start(self, log_callback):
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        self.proc = subprocess.Popen(
            self.cmd,
            cwd=self.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )

        self.reader_thread = threading.Thread(
            target=self._read_stream,
            args=(log_callback,),
            daemon=True,
        )
        self.reader_thread.start()

    def _read_stream(self, log_callback):
        if not self.proc or not self.proc.stdout:
            return
        try:
            for raw_line in iter(self.proc.stdout.readline, ""):
                line = raw_line.rstrip("\r\n")
                if line:
                    log_callback(self.name, self.color, line)
        except Exception:
            pass

    def terminate_tree(self):
        """Forcefully terminates the entire process tree on Windows or POSIX."""
        if not self.proc:
            return

        pid = self.proc.pid
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            except Exception:
                pass
        else:
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except Exception:
                try:
                    self.proc.terminate()
                except Exception:
                    pass

        try:
            self.proc.wait(timeout=2.0)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


class Orchestrator:
    """Coordinates lifecycle, health-checked boot staging, logging, and fail-safe teardown."""

    def __init__(
        self,
        port: int = 8000,
        streamer_interval: float = 1.5,
        crypto_rate_limit: float = 1.0,
        no_crypto: bool = False,
        no_frontend: bool = False,
        no_color: bool = False,
        backend_port: Optional[int] = None,
    ):
        self.port = backend_port if backend_port is not None else port
        self.streamer_interval = streamer_interval
        self.crypto_rate_limit = crypto_rate_limit
        self.no_crypto = no_crypto
        self.no_frontend = no_frontend
        self.use_color = not no_color and sys.stdout.isatty()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.frontend_dir = os.path.join(self.base_dir, "nexus-frontend")
        self.python_bin = resolve_python_path()
        self.npm_bin = resolve_npm_path()

        self.processes: Dict[str, ServiceProcess] = {}
        self.is_shutting_down = False
        self.shutdown_event = threading.Event()

    def log(self, prefix: str, color: str, message: str):
        """Formats and prints multiplexed log messages with aligned service tags."""
        if self.use_color:
            tag = f"{color}{CLR_BOLD}[{prefix:>12}]{CLR_RESET}"
        else:
            tag = f"[{prefix:>12}]"
        print(f"{tag} {message}", flush=True)

    def log_system(self, message: str, color: str = CLR_WHITE):
        """Emits an orchestrator system-level log."""
        self.log("ORCHESTRATOR", color, message)

    def free_port(self, port: int, wait_release: bool = True):
        """Forcefully kills any lingering process bound to a specified TCP port on Windows."""
        if sys.platform != "win32":
            return
        try:
            cmd = f'netstat -ano -p tcp | findstr ":{port} "'
            output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            for line in output.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = parts[-1]
                    if pid and pid != "0" and pid != str(os.getpid()):
                        self.log_system(f"Releasing port {port} by terminating lingering PID {pid}...", CLR_YELLOW)
                        subprocess.run(["taskkill", "/F", "/T", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if wait_release:
                for _ in range(8):
                    try:
                        verify_out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
                        listening = [l for l in verify_out.strip().splitlines() if "LISTENING" in l]
                        if not listening:
                            break
                    except subprocess.CalledProcessError:
                        break
                    time.sleep(0.2)
        except Exception:
            pass

    def poll_backend_health(self, max_retries: int = 40, delay_sec: float = 0.5) -> bool:
        """
        Polls the FastAPI /docs endpoint until responsive.
        Default: 40 retries x 0.5s = 20-second timeout.
        """
        target_url = f"http://localhost:{self.port}/docs"
        self.log_system(f"Polling FastAPI backend accessibility on {target_url} (0.5s cadence, 20s timeout)...", CLR_CYAN)

        for attempt in range(1, max_retries + 1):
            if self.is_shutting_down:
                return False
            try:
                req = urllib.request.Request(
                    target_url,
                    headers={"User-Agent": "QuantumAML-Runner/1.0"},
                )
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    if resp.status == 200:
                        self.log_system(
                            f"Backend verified operational (HTTP 200 OK) in {attempt * delay_sec:.1f}s!",
                            CLR_GREEN,
                        )
                        return True
            except Exception:
                pass

            time.sleep(delay_sec)

        self.log_system(
            f"Error: Backend did not respond within {max_retries * delay_sec:.0f}s timeout.",
            CLR_RED,
        )
        self.log_system("Remediation Guidance:", CLR_BOLD + CLR_WHITE)
        self.log_system(f"  1. Verify port {self.port} availability: netstat -ano | findstr :{self.port}", CLR_YELLOW)
        self.log_system("  2. Ensure dependencies are installed: pip install -r requirements.txt", CLR_YELLOW)
        self.log_system(f"  3. Test backend standalone: {self.python_bin} -m uvicorn app.main:app --port {self.port}", CLR_YELLOW)
        self.log_system("  4. Verify system event logs for unhandled lifespan initialization faults.", CLR_YELLOW)
        return False

    def build_service_commands(self) -> Dict[str, List[str]]:
        """Constructs process execution commands for each service."""
        return {
            "backend": [
                self.python_bin,
                "-m",
                "uvicorn",
                "app.main:app",
                "--port",
                str(self.port),
                "--reload",
            ],
            "banking": [
                self.python_bin,
                "streamer.py",
                "--interval",
                str(self.streamer_interval),
            ],
            "crypto": [
                self.python_bin,
                "live_crypto_feed.py",
                "--rate-limit",
                str(self.crypto_rate_limit),
            ],
            "frontend": [
                self.npm_bin,
                "run",
                "dev",
            ],
        }

    def start_all(self):
        """Launches runtime services following the strict staged health-gated sequence."""
        self._print_banner()

        # Release ports if previously held by orphaned processes
        self.free_port(self.port)
        if not self.no_frontend:
            self.free_port(5173)

        commands = self.build_service_commands()

        # Step 1: Spawn FastAPI Backend
        self.log_system("Phase 1: Starting FastAPI inference & broadcast hub...", CLR_CYAN)
        backend_svc = ServiceProcess(
            service_id="backend",
            name="BACKEND",
            color=CLR_CYAN,
            cmd=commands["backend"],
            cwd=self.base_dir,
        )
        self.processes["backend"] = backend_svc
        backend_svc.start(self.log)

        # Step 2: Poll Health Endpoint (20s timeout, 0.5s interval)
        is_healthy = self.poll_backend_health(max_retries=40, delay_sec=0.5)

        if not is_healthy or self.is_shutting_down:
            self.log_system("Aborting launch sequence due to backend startup failure.", CLR_RED)
            self.shutdown()
            return

        # Step 3: Launch Remaining Services Concurrently
        self.log_system("Phase 2: Backend healthy. Launching concurrent generators & frontend...", CLR_CYAN)

        # 3a. Banking Generator
        banking_svc = ServiceProcess(
            service_id="banking",
            name="BANKING",
            color=CLR_GREEN,
            cmd=commands["banking"],
            cwd=self.base_dir,
        )
        self.processes["banking"] = banking_svc
        banking_svc.start(self.log)

        # 3b. Crypto Ingestion Feed (unless disabled)
        if not self.no_crypto:
            crypto_svc = ServiceProcess(
                service_id="crypto",
                name="CRYPTO",
                color=CLR_YELLOW,
                cmd=commands["crypto"],
                cwd=self.base_dir,
            )
            self.processes["crypto"] = crypto_svc
            crypto_svc.start(self.log)
        else:
            self.log_system("[SKIP] Crypto mempool feed disabled via --no-crypto flag.", CLR_DIM)

        # 3c. Vite React Frontend (unless disabled)
        if not self.no_frontend:
            if os.path.isdir(self.frontend_dir):
                frontend_svc = ServiceProcess(
                    service_id="frontend",
                    name="FRONTEND",
                    color=CLR_MAGENTA,
                    cmd=commands["frontend"],
                    cwd=self.frontend_dir,
                )
                self.processes["frontend"] = frontend_svc
                frontend_svc.start(self.log)
            else:
                self.log_system(f"Warning: Frontend directory '{self.frontend_dir}' not found.", CLR_YELLOW)
        else:
            self.log_system("[SKIP] Frontend UI disabled via --no-frontend flag (headless mode).", CLR_DIM)

        self.log_system("All requested QuantumAML Nexus services running. Press Ctrl+C to terminate.", CLR_BOLD + CLR_GREEN)

        # Keep main thread alive waiting for shutdown signal
        try:
            while not self.is_shutting_down:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        """Interprets shutdown signal and forcefully purges all process trees and ports."""
        if self.is_shutting_down:
            return
        self.is_shutting_down = True

        print("\n", flush=True)
        self.log_system("Intercepted shutdown signal (Ctrl+C). Initiating fail-safe teardown...", CLR_BOLD + CLR_YELLOW)

        # Terminate processes in reverse dependency order
        service_order = ["frontend", "crypto", "banking", "backend"]
        for svc_id in service_order:
            svc = self.processes.get(svc_id)
            if svc and svc.proc:
                self.log_system(f"Stopping {svc.name} (PID: {svc.proc.pid})...", CLR_DIM)
                svc.terminate_tree()

        # Ensure ports are freed
        self.free_port(self.port)
        self.free_port(5173)

        self.log_system("Clean process tree purge complete. Ports released. Teardown finished.", CLR_BOLD + CLR_GREEN)
        self.shutdown_event.set()

    def _print_banner(self):
        width = 86
        border = "=" * width
        crypto_status = "DISABLED" if self.no_crypto else "ACTIVE"
        frontend_status = "DISABLED" if self.no_frontend else "ACTIVE"

        print(f"\n{CLR_CYAN}{border}{CLR_RESET}")
        print(f"{CLR_BOLD}{CLR_WHITE}{'QUANTUMAML NEXUS - MULTI-PROCESS ORCHESTRATION RUNNER':^{width}}{CLR_RESET}")
        print(f"{CLR_CYAN}{border}{CLR_RESET}")
        print(f"  Python Binary:   {CLR_DIM}{self.python_bin}{CLR_RESET}")
        print(f"  Backend Port:    {CLR_CYAN}http://localhost:{self.port}{CLR_RESET}")
        print(f"  WebSocket Hub:   {CLR_CYAN}ws://localhost:{self.port}/ws/live{CLR_RESET}")
        print(f"  Frontend Status: {CLR_MAGENTA}{frontend_status}{CLR_RESET} ({self.frontend_dir})")
        print(f"  Crypto Feed:     {CLR_YELLOW}{crypto_status}{CLR_RESET}")
        print(f"  Streamer Speed:  {CLR_GREEN}{self.streamer_interval}s interval{CLR_RESET}")
        print(f"{CLR_CYAN}{'-' * width}{CLR_RESET}\n")


def main():
    parser = argparse.ArgumentParser(
        description="QuantumAML Nexus - Unified Platform Process Runner"
    )
    parser.add_argument(
        "--backend-port",
        "--port",
        dest="port",
        type=int,
        default=8000,
        help="FastAPI server port (default: 8000)",
    )
    parser.add_argument(
        "--no-crypto",
        action="store_true",
        help="Skip launching the live crypto mempool feed",
    )
    parser.add_argument(
        "--no-frontend",
        action="store_true",
        help="Headless API/backend streaming mode (no React UI)",
    )
    parser.add_argument(
        "--streamer-interval",
        type=float,
        default=1.5,
        help="Cadence for Indian banking switch streamer in seconds (default: 1.5)",
    )
    parser.add_argument(
        "--crypto-rate-limit",
        type=float,
        default=1.0,
        help="Maximum processed transactions per second for Bitcoin mempool (default: 1.0)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI terminal colors",
    )

    args = parser.parse_args()

    orchestrator = Orchestrator(
        port=args.port,
        streamer_interval=args.streamer_interval,
        crypto_rate_limit=args.crypto_rate_limit,
        no_crypto=args.no_crypto,
        no_frontend=args.no_frontend,
        no_color=args.no_color,
    )

    # Attach signal listeners for graceful shutdown
    def handle_signal(sig, frame):
        orchestrator.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    orchestrator.start_all()


if __name__ == "__main__":
    main()
