from fastapi.testclient import TestClient

from app.main import app
from live_crypto_feed import (
    BitcoinTxParser,
    EllipticTensorBuilder,
    format_crypto_log,
)


def test_elliptic_tensor_builder_dimensions():
    """Verifies that the Elliptic tensor builder outputs exactly 166 valid numerical floats."""
    tensor = EllipticTensorBuilder.build_tensor(
        in_count=3,
        out_count=2,
        btc_value=1.452,
        fee_btc=0.00015,
        output_values=[1.0, 0.452],
        size_bytes=225,
        timestep=49,
    )

    assert len(tensor) == 166
    assert tensor[0] == 49.0
    for val in tensor:
        assert isinstance(val, float)
        assert not (val != val)  # No NaN
        assert abs(val) < 1e9  # No Inf


def test_bitcoin_tx_parser_blockchain_info():
    """Validates extraction of live Bitcoin primitives and 166-D tensor generation from blockchain.info format."""
    mock_blockchain_info_msg = {
        "op": "utx",
        "x": {
            "hash": "74146f0c91559816bfb4421b4a66399120ba4ec2e08b76c8c4a4fcf85bc1d442",
            "size": 222,
            "vin_sz": 1,
            "vout_sz": 2,
            "inputs": [
                {
                    "prev_out": {
                        "addr": "bc1qrejm9rk9pad6p8e2m226w2yw3qarhppny4gle5",
                        "value": 165574,
                    }
                }
            ],
            "out": [
                {
                    "addr": "3HtUPtPdHFzRrCaV4S3n8SFMiMCiQrZyRh",
                    "value": 150000,
                },
                {
                    "addr": "bc1qchange998811223344",
                    "value": 13574,
                },
            ],
        },
    }

    parsed = BitcoinTxParser.parse_blockchain_info(mock_blockchain_info_msg)
    assert parsed is not None
    assert (
        parsed["tx_hash"]
        == "74146f0c91559816bfb4421b4a66399120ba4ec2e08b76c8c4a4fcf85bc1d442"
    )
    assert parsed["in_count"] == 1
    assert parsed["out_count"] == 2
    assert parsed["btc_value"] == round((150000 + 13574) / 1e8, 8)
    assert parsed["from_address"] == "bc1qrejm9rk9pad6p8e2m226w2yw3qarhppny4gle5"
    assert parsed["to_address"] == "3HtUPtPdHFzRrCaV4S3n8SFMiMCiQrZyRh"
    assert len(parsed["features"]) == 166


def test_bitcoin_tx_parser_mempool_space():
    """Validates extraction of live Bitcoin primitives from mempool.space format."""
    mock_mempool_msg = {
        "txid": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "size": 340,
        "fee": 2500,
        "vin": [{}, {}],
        "vout": [
            {
                "scriptpubkey_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                "value": 348120000,
            }
        ],
    }

    parsed = BitcoinTxParser.parse_mempool_space(mock_mempool_msg)
    assert parsed is not None
    assert (
        parsed["tx_hash"]
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert parsed["btc_value"] == round(348120000 / 1e8, 8)
    assert parsed["to_address"] == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    assert len(parsed["features"]) == 166


def test_format_crypto_log():
    """Validates terminal log rendering."""
    resp = {
        "risk_tier": "HIGH",
        "risk_score": 0.9612,
        "latency_ms": 14.8,
    }
    line = format_crypto_log(
        tx_hash="74146f0c91559816bfb4421b4a66399120ba4ec2e08b76c8c4a4fcf85bc1d442",
        btc_value=3.4812,
        in_count=3,
        out_count=2,
        resp=resp,
        err="",
    )
    assert "[CRYPTO]" in line
    assert "74146f0c91" in line
    assert "3.4812 BTC" in line
    assert "HIGH" in line
    assert "HTTP 200" in line


def test_fastapi_score_crypto_contract_integration():
    """End-to-end integration: Validates that parsed live Bitcoin payloads conform to FastAPI /api/v1/score/crypto."""
    client = TestClient(app)
    mock_msg = {
        "op": "utx",
        "x": {
            "hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
            "size": 225,
            "vin_sz": 2,
            "vout_sz": 2,
            "inputs": [{"prev_out": {"addr": "bc1qsender", "value": 50000000}}],
            "out": [{"addr": "bc1qreceiver", "value": 49950000}],
        },
    }

    parsed = BitcoinTxParser.parse_blockchain_info(mock_msg)
    assert parsed is not None

    # POST to FastAPI
    response = client.post("/api/v1/score/crypto", json=parsed)
    assert response.status_code == 200
    data = response.json()
    assert data["entity_id"] == parsed["tx_hash"]
    assert data["dataset"] == "Elliptic Bitcoin"
    assert 0.0 <= data["risk_score"] <= 1.0
    assert data["risk_tier"] in {"LOW", "ELEVATED", "HIGH", "CRITICAL_SAR"}
    assert data["latency_ms"] > 0
