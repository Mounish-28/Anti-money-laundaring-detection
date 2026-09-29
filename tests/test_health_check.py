import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from health_check import HealthChecker


def get_checker():
    return HealthChecker(
        host="localhost",
        port=8000,
        stream_timeout=1.0,
        allow_idle_streamers=True,
        no_color=True,
    )


def test_rest_accessibility_success():
    async def run():
        checker = get_checker()
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.get.return_value = mock_resp

        res = await checker.test_rest_accessibility(mock_client)
        assert res.passed is True
        assert "HTTP 200 OK" in res.details
        assert res.latency_ms >= 0

    asyncio.run(run())


def test_rest_accessibility_failure():
    async def run():
        checker = get_checker()
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection refused")

        res = await checker.test_rest_accessibility(mock_client)
        assert res.passed is False
        assert "FastAPI is unreachable" in res.error_diagnostic

    asyncio.run(run())


def test_catboost_banking_success():
    async def run():
        checker = get_checker()
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "entity_id": "test_id",
            "risk_score": 0.8845,
            "risk_tier": "ELEVATED",
            "latency_ms": 14.2,
        }
        mock_client.post.return_value = mock_resp

        res = await checker.test_catboost_banking(mock_client)
        assert res.passed is True
        assert "SLA Met" in res.details
        assert res.latency_ms == 14.2

    asyncio.run(run())


def test_catboost_banking_sla_violation():
    async def run():
        checker = get_checker()
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "entity_id": "test_id",
            "risk_score": 0.45,
            "risk_tier": "LOW",
            "latency_ms": 65.0,  # Exceeds 50ms SLA
        }
        mock_client.post.return_value = mock_resp

        res = await checker.test_catboost_banking(mock_client)
        assert res.passed is False
        assert "SLA VIOLATION" in res.details
        assert "exceeded sub-50ms SLA target" in res.error_diagnostic

    asyncio.run(run())


def test_xgboost_crypto_success():
    async def run():
        checker = get_checker()
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "entity_id": "btc_node_001",
            "risk_score": 0.05,
            "risk_tier": "LOW",
            "latency_ms": 18.5,
        }
        mock_client.post.return_value = mock_resp

        res = await checker.test_xgboost_crypto(mock_client)
        assert res.passed is True
        assert "SLA Met" in res.details
        assert res.latency_ms == 18.5

    asyncio.run(run())


def test_websocket_broadcast_delivery():
    async def run():
        checker = get_checker()
        mock_client = AsyncMock()
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_client.post.return_value = mock_post_resp

        mock_ws = AsyncMock()
        target_id = None

        async def mock_recv():
            nonlocal target_id
            return json.dumps(
                {
                    "engine": "FIAT_BANKING",
                    "transaction_id": target_id,
                    "rail": "IMPS",
                    "risk_tier": "LOW",
                    "latency_ms": 5.0,
                }
            )

        mock_ws.recv.side_effect = mock_recv
        mock_ws_ctx = AsyncMock()
        mock_ws_ctx.__aenter__.return_value = mock_ws
        mock_ws_ctx.__aexit__.return_value = None

        with patch("websockets.connect", return_value=mock_ws_ctx):
            with patch("uuid.uuid4") as mock_uuid:
                mock_uuid.return_value.hex = "mockuuid123"
                target_id = "WS-VERIFY-TRIGGER-mockuuid"
                res = await checker.test_websocket_broadcast(mock_client)
                assert res.passed is True
                assert "Push Delivered" in res.details

    asyncio.run(run())


def test_streamer_verification_with_events():
    async def run():
        checker = get_checker()
        mock_ws = AsyncMock()
        messages = [
            json.dumps({"engine": "FIAT_BANKING", "currency": "INR", "rail": "UPI"}),
            json.dumps(
                {"engine": "CRYPTO_FORENSICS", "currency": "BTC", "rail": "BTC"}
            ),
        ]
        idx = 0

        async def mock_recv():
            nonlocal idx
            if idx < len(messages):
                msg = messages[idx]
                idx += 1
                return msg
            await asyncio.sleep(2.0)
            raise asyncio.TimeoutError()

        mock_ws.recv.side_effect = mock_recv
        mock_ws_ctx = AsyncMock()
        mock_ws_ctx.__aenter__.return_value = mock_ws
        mock_ws_ctx.__aexit__.return_value = None

        with patch("websockets.connect", return_value=mock_ws_ctx):
            res = await checker.test_streamer_verification()
            assert res.passed is True
            assert "2 Live Events" in res.details
            assert "1 Fiat Banking" in res.details
            assert "1 Crypto Mempool" in res.details

    asyncio.run(run())


def test_streamer_verification_idle_warning():
    async def run():
        checker = get_checker()
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = asyncio.TimeoutError()
        mock_ws_ctx = AsyncMock()
        mock_ws_ctx.__aenter__.return_value = mock_ws
        mock_ws_ctx.__aexit__.return_value = None

        with patch("websockets.connect", return_value=mock_ws_ctx):
            res = await checker.test_streamer_verification()
            assert res.is_warning is True
            assert res.passed is True
            assert "Streamers Idle" in res.details

    asyncio.run(run())
