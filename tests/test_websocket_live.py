from fastapi.testclient import TestClient

from app.main import app, manager


def test_connection_manager_registration():
    """Verifies that the global manager instance is initialized and active."""
    assert manager is not None
    assert isinstance(manager.active_connections, list)


def test_websocket_broadcast_fiat_transaction():
    """
    Verifies that connecting to /ws/live receives real-time normalized broadcast
    payloads when /api/v1/score/transaction evaluates a fiat transaction.
    """
    client = TestClient(app)
    payload = {
        "transaction_id": "ws_tx_test_001",
        "from_bank": "10",
        "to_bank": "12",
        "account_from": "ACC_SEND_777",
        "account_to": "ACC_RECV_888",
        "amount": 150000.0,
        "currency": "US Dollar",
        "payment_format": "Wire Transfer",
    }

    with client.websocket_connect("/ws/live") as websocket:
        # Score the transaction
        response = client.post("/api/v1/score/transaction", json=payload)
        assert response.status_code == 200

        # Receive streamed broadcast payload
        message = websocket.receive_json()
        assert message["engine"] == "FIAT_BANKING"
        assert message["transaction_id"] == "ws_tx_test_001"
        assert "timestamp" in message
        assert message["rail"] == "Wire Transfer"
        assert message["from_entity"] == "ACC_SEND_777"
        assert message["to_entity"] == "ACC_RECV_888"
        assert message["amount"] == 150000.0
        assert message["currency"] == "INR"
        assert isinstance(message["risk_score"], float)
        assert isinstance(message["risk_tier"], str)
        assert isinstance(message["latency_ms"], float)
        assert isinstance(message["flags"], list)


def test_websocket_broadcast_crypto_transaction():
    """
    Verifies that connecting to /ws/live receives real-time normalized broadcast
    payloads when /api/v1/score/crypto evaluates an Elliptic crypto node.
    """
    client = TestClient(app)
    payload = {
        "node_id": "btc_node_ws_002",
        "features": [2.45] + [0.01] * 165,
    }

    with client.websocket_connect("/ws/live") as websocket:
        # Score the crypto transaction
        response = client.post("/api/v1/score/crypto", json=payload)
        assert response.status_code == 200

        # Receive streamed broadcast payload
        message = websocket.receive_json()
        assert message["engine"] == "CRYPTO_FORENSICS"
        assert message["transaction_id"] == "btc_node_ws_002"
        assert "timestamp" in message
        assert message["rail"] == "BTC"
        assert message["from_entity"] == "node_btc_node_ws_002"
        assert message["to_entity"] == "cluster_btc_node"
        assert message["amount"] == 2.45
        assert message["currency"] == "BTC"
        assert isinstance(message["risk_score"], float)
        assert isinstance(message["risk_tier"], str)
        assert isinstance(message["latency_ms"], float)
        assert isinstance(message["flags"], list)


def test_websocket_disconnect_cleanup():
    """Verifies that disconnecting a WebSocket client cleans up the active connection list."""
    client = TestClient(app)
    initial_count = len(manager.active_connections)

    with client.websocket_connect("/ws/live") as websocket:
        assert len(manager.active_connections) == initial_count + 1

    # After context exit, the connection should be purged
    assert len(manager.active_connections) == initial_count


def test_websocket_live_manual_dispatch_roundtrip():
    """
    Verifies bidirectional duplex event dispatching over /ws/live:
    A client dispatches a manual transaction, receives DISPATCH_ACK,
    and all subscribers on /ws/live receive the broadcast instantaneously.
    """
    client = TestClient(app)

    with client.websocket_connect("/ws/live") as ws1:
        with client.websocket_connect("/ws/live") as ws2:
            dispatch_frame = {
                "type": "DISPATCH",
                "transaction": {
                    "transaction_id": "MANUAL_TX_LIVE_77",
                    "rail": "UPI",
                    "amount": 49500.0,
                    "currency": "INR",
                    "from_entity": "mule_wallet_44",
                    "to_entity": "aggregator_shell_99",
                    "risk_tier": "CRITICAL_SAR",
                    "risk_score": 0.985,
                    "flags": ["PAN_STRUCTURING_EVASION", "MULE_BURST"],
                },
            }
            # Client 1 dispatches over the duplex connection
            ws1.send_json(dispatch_frame)

            # Client 1 receives instant ACK
            ack = ws1.receive_json()
            assert ack["type"] == "DISPATCH_ACK"
            assert ack["status"] == "BROADCASTED"
            assert ack["transaction_id"] == "MANUAL_TX_LIVE_77"

            # Both client 1 and client 2 receive the broadcasted event
            b1 = ws1.receive_json()
            assert b1["transaction_id"] == "MANUAL_TX_LIVE_77"
            assert b1["amount"] == 49500.0
            assert b1["risk_tier"] == "CRITICAL_SAR"

            b2 = ws2.receive_json()
            assert b2["transaction_id"] == "MANUAL_TX_LIVE_77"
            assert b2["from_entity"] == "mule_wallet_44"

