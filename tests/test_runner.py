import os
import sys
import subprocess
from unittest.mock import MagicMock, patch
import pytest

from runner import (
    resolve_python_path,
    resolve_npm_path,
    ServiceProcess,
    Orchestrator,
    SERVICE_CONFIGS,
)


def test_resolve_python_path():
    py_path = resolve_python_path()
    assert py_path is not None
    assert isinstance(py_path, str)
    assert os.path.exists(py_path) or py_path == sys.executable


def test_resolve_npm_path():
    npm_path = resolve_npm_path()
    assert npm_path is not None
    assert "npm" in npm_path.lower()


def test_orchestrator_build_commands():
    orchestrator = Orchestrator(port=8080, streamer_interval=2.0, crypto_rate_limit=1.5)
    cmds = orchestrator.build_service_commands()

    assert "backend" in cmds
    assert "banking" in cmds
    assert "crypto" in cmds
    assert "frontend" in cmds

    # Verify backend parameters
    assert "uvicorn" in cmds["backend"]
    assert "8080" in cmds["backend"]
    assert "--reload" in cmds["backend"]

    # Verify banking streamer parameters
    assert "streamer.py" in cmds["banking"]
    assert "2.0" in cmds["banking"]

    # Verify crypto parameters
    assert "live_crypto_feed.py" in cmds["crypto"]
    assert "1.5" in cmds["crypto"]

    # Verify frontend parameters
    assert "run" in cmds["frontend"]
    assert "dev" in cmds["frontend"]


def test_poll_backend_health_success():
    orchestrator = Orchestrator(port=8000)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = orchestrator.poll_backend_health(max_retries=2, delay_sec=0.01)
        assert res is True


def test_poll_backend_health_timeout():
    orchestrator = Orchestrator(port=8000)

    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        res = orchestrator.poll_backend_health(max_retries=2, delay_sec=0.01)
        assert res is False


def test_service_process_terminate_tree():
    svc = ServiceProcess(
        service_id="test",
        name="TEST",
        color="\033[92m",
        cmd=["dummy"],
        cwd=".",
    )
    mock_proc = MagicMock()
    mock_proc.pid = 99999
    svc.proc = mock_proc

    with patch("subprocess.run") as mock_run:
        svc.terminate_tree()
        if sys.platform == "win32":
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "taskkill" in args
            assert "99999" in args


def test_orchestrator_graceful_shutdown():
    orchestrator = Orchestrator(port=8000)
    mock_svc = MagicMock()
    mock_svc.name = "BACKEND"
    mock_svc.proc.pid = 1234
    orchestrator.processes["backend"] = mock_svc

    orchestrator.shutdown()
    assert orchestrator.is_shutting_down is True
    assert orchestrator.shutdown_event.is_set()
    mock_svc.terminate_tree.assert_called_once()


def test_orchestrator_cli_flags():
    orch = Orchestrator(
        port=9000,
        backend_port=9090,
        no_crypto=True,
        no_frontend=True,
        streamer_interval=3.0,
        crypto_rate_limit=0.5,
    )
    assert orch.port == 9090
    assert orch.no_crypto is True
    assert orch.no_frontend is True
    assert orch.streamer_interval == 3.0
    assert orch.crypto_rate_limit == 0.5

