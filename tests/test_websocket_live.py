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
