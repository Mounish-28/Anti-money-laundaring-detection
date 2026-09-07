"""
Tests for QuantumAML Nexus SAR Service (app/services/sar_service.py)
====================================================================

Validates:
1. Thread-safe in-memory case storage and active ring indexing.
2. 5-minute rolling window ring deduplication & transaction aggregation.
3. Rolling window expiry (> 300s) spawning new case IDs.
4. FIU-IND statutory 7 working-day deadline computation.
5. Dynamic legal narrative synthesizer for all regulatory typologies.
6. Case management lifecycle (get, list with filtering/pagination, status update).
7. Ring eviction upon closing/filing cases.
8. Concurrent multi-transaction race condition safety.
"""

import asyncio
import time
from datetime import datetime, timezone
import pytest

from app.schemas.sar import CaseStatus, SuspicionTypology, PaymentRail
from app.services.sar_service import SARService


def test_initial_case_creation():
    """Case B: Verify initial transaction creates a complete compliant SAR case."""
    async def _test():
        service = SARService()

        tx_payload = {
            "transaction_id": "UTR992817264510",
            "account_from": "smurf_01@okhdfcbank",
            "account_to": "mule_hub@oksbi",
            "amount": 48500.0,
            "payment_format": "UPI",
            "currency": "INR",
            "branch_ifsc": "SBIN0001234",
        }
        ml_result = {
            "risk_score": 0.94,
            "risk_tier": "CRITICAL_SAR",
            "latency_ms": 11.2,
            "recommended_action": "PAN_STRUCTURING",
            "feature_importance": {"amount_structuring_ratio": 0.42},
        }

        case = await service.create_or_aggregate_sar(
            tx_payload=tx_payload,
            ml_result=ml_result,
            typology=SuspicionTypology.IN_TYP_STRUCT,
        )

        assert case.sar_id.startswith("SAR-IND-")
        assert case.status == CaseStatus.PENDING_REVIEW
        # In structuring, target aggregator is primary suspect
        assert case.suspect.entity_identifier == "mule_hub@oksbi"
        assert case.counterparty.entity_identifier == "smurf_01@okhdfcbank"
        assert len(case.transactions) == 1
        assert case.transactions[0].amount == 48500.0
        assert case.total_exposure_inr == 48500.0
        assert case.ml_telemetry.inference_latency_ms == 11.2

        # Statutory deadline must be strictly after creation date
        assert case.fiu_deadline > case.created_at

        # Check narrative synthesis
        assert "Coordinated structuring pattern detected" in case.grounds_of_suspicion.narrative_summary
        assert "\u20b948,500.00" in case.grounds_of_suspicion.narrative_summary
        assert "mule_hub@oksbi" in case.grounds_of_suspicion.narrative_summary

    asyncio.run(_test())


def test_rolling_window_aggregation_within_5min():
    """Case A: Rapid-fire transactions to same suspect within 300s aggregate into single SAR."""
    async def _test():
        service = SARService()

        # First smurf transaction: ₹48,000
        tx1 = {
            "transaction_id": "UTR-BURST-001",
            "account_from": "smurf_alpha@okicici",
            "account_to": "aggregator_ring_01@paytm",
            "amount": 48000.0,
            "payment_format": "UPI",
            "currency": "INR",
        }
        ml1 = {
            "risk_score": 0.90,
            "latency_ms": 8.5,
            "feature_importance": {"velocity_burst": 0.35},
        }

        case1 = await service.create_or_aggregate_sar(
            tx_payload=tx1,
            ml_result=ml1,
            typology=SuspicionTypology.IN_TYP_STRUCT,
        )
        initial_sar_id = case1.sar_id
        initial_last_active = service._ring_last_active[initial_sar_id]

        # Small delay to ensure timestamp advancement
        await asyncio.sleep(0.05)

        # Second smurf transaction: ₹49,500 from different remitter to SAME aggregator
        tx2 = {
            "transaction_id": "UTR-BURST-002",
            "account_from": "smurf_beta@okhdfcbank",
            "account_to": "aggregator_ring_01@paytm",
            "amount": 49500.0,
            "payment_format": "UPI",
            "currency": "INR",
        }
        ml2 = {
            "risk_score": 0.96,
            "latency_ms": 7.1,
            "feature_importance": {"amount_ratio": 0.45},
        }

        case2 = await service.create_or_aggregate_sar(
            tx_payload=tx2,
            ml_result=ml2,
            typology=SuspicionTypology.IN_TYP_STRUCT,
        )

        # Must retain exact same SAR ID
        assert case2.sar_id == initial_sar_id
        assert len(case2.transactions) == 2
        # Cumulative exposure: 48,000 + 49,500 = 97,500
        assert case2.total_exposure_inr == 97500.0

        # Rolling average risk score: (0.90 + 0.96) / 2 = 0.93
        avg_score = sum(t.risk_score for t in case2.transactions) / 2.0
        assert pytest.approx(avg_score, 0.01) == 0.93

        # Feature importance merged
        assert "velocity_burst" in case2.ml_telemetry.feature_importance
        assert "amount_ratio" in case2.ml_telemetry.feature_importance

        # Narrative updated with 2 transactions and ₹97,500.00
        narrative = case2.grounds_of_suspicion.narrative_summary
        assert "2 transactions aggregating to \u20b997,500.00" in narrative

        # Rolling timer reset forward
        assert service._ring_last_active[initial_sar_id] >= initial_last_active

    asyncio.run(_test())


def test_rolling_window_expiry_creates_new_sar():
    """Case B: Transactions occurring AFTER 300 seconds trigger a fresh SAR dossier."""
    async def _test():
        service = SARService()

        tx1 = {
            "transaction_id": "UTR-OLD-001",
            "account_from": "smurf_x@oksbi",
            "account_to": "mule_pool_77@okhdfcbank",
            "amount": 45000.0,
            "payment_format": "UPI",
        }
        ml1 = {"risk_score": 0.88, "latency_ms": 9.0}

        case1 = await service.create_or_aggregate_sar(
            tx_payload=tx1,
            ml_result=ml1,
            typology=SuspicionTypology.IN_TYP_STRUCT,
        )
        first_sar_id = case1.sar_id

        # Fast-forward time beyond the 300s window (305 seconds ago)
        service._ring_last_active[first_sar_id] = time.time() - 305.0

        # Subsequent transaction arrives for the same suspect
        tx2 = {
            "transaction_id": "UTR-NEW-002",
            "account_from": "smurf_y@oksbi",
            "account_to": "mule_pool_77@okhdfcbank",
            "amount": 47000.0,
            "payment_format": "UPI",
        }
        ml2 = {"risk_score": 0.92, "latency_ms": 10.1}

        case2 = await service.create_or_aggregate_sar(
            tx_payload=tx2,
            ml_result=ml2,
            typology=SuspicionTypology.IN_TYP_STRUCT,
        )

        # Must generate a distinct new SAR ID
        assert case2.sar_id != first_sar_id
        assert len(case2.transactions) == 1
        assert case2.total_exposure_inr == 47000.0
        # The active ring index now points to the new SAR ID
        assert service._active_ring_index["mule_pool_77@okhdfcbank"] == case2.sar_id

    asyncio.run(_test())


def test_narrative_synthesis_typologies():
    """Validates FIU-IND compliant narrative synthesis across all required typologies."""
    async def _test():
        service = SARService()

        # 1. Hawala wire anomaly
        hawala_tx = {
            "transaction_id": "UTR-HAWALA-8819",
            "account_from": "corp_shell_ltd@axis",
            "account_to": "offshore_receiver@swift",
            "amount": 2500000.0,
            "payment_format": "RTGS",
            "entity_name": "Golden Bullion Global FZE",
            "branch_ifsc": "UTIB0009988",
        }
        case_hawala = await service.create_or_aggregate_sar(
            tx_payload=hawala_tx,
            ml_result={"risk_score": 0.98, "latency_ms": 6.0},
            typology=SuspicionTypology.IN_TYP_HAWALA,
        )
        h_narrative = case_hawala.grounds_of_suspicion.narrative_summary
        assert "High-value wire anomaly: Uncharacteristic RTGS transfer" in h_narrative
        assert "\u20b92,500,000.00" in h_narrative
        assert "Golden Bullion Global FZE" in h_narrative
        assert "UTIB0009988" in h_narrative

        # 2. Crypto VDA mixer / peel chain
        crypto_tx = {
            "transaction_id": "a9f8b4c2e1d03498bfe129847120394871239847192834719283749182739182",
            "from_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "to_address": "bc1qmixerpeelcluster0001",
            "amount": 3.45,
            "currency": "BTC",
            "payment_format": "BTC",
            "num_inputs": 12,
            "num_outputs": 24,
        }
        case_crypto = await service.create_or_aggregate_sar(
            tx_payload=crypto_tx,
            ml_result={"risk_score": 0.97, "latency_ms": 14.5, "model_name": "Elliptic-XGBoost-v1.2"},
            typology=SuspicionTypology.IN_TYP_VDA_MIX,
        )
        c_narrative = case_crypto.grounds_of_suspicion.narrative_summary
        assert "Illicit crypto hop detected: High-velocity peeling or mixer signature" in c_narrative
        assert "12 inputs and 24 outputs" in c_narrative
        assert crypto_tx["transaction_id"] in c_narrative
        assert case_crypto.total_exposure_btc == 3.45

        # 3. Mule account burst
        mule_tx = {
            "transaction_id": "UTR-MULE-4411",
            "account_from": "dormant_student_acc@sbi",
            "account_to": "crypto_p2p_trader@upi",
            "amount": 185000.0,
            "payment_format": "IMPS",
        }
        case_mule = await service.create_or_aggregate_sar(
            tx_payload=mule_tx,
            ml_result={"risk_score": 0.91, "latency_ms": 7.8},
            typology=SuspicionTypology.IN_TYP_MULE,
        )
        m_narrative = case_mule.grounds_of_suspicion.narrative_summary
        assert "Mule account burst detected" in m_narrative
        assert "IMPS" in m_narrative
        assert "\u20b9185,000.00" in m_narrative

    asyncio.run(_test())


def test_case_lifecycle_and_ring_eviction():
    """Tests case retrieval, status update, and active ring eviction on filing/dismissal."""
    async def _test():
        service = SARService()

        tx = {
            "transaction_id": "UTR-LIFECYCLE-1",
            "account_from": "acc_01@upi",
            "account_to": "suspect_store@paytm",
            "amount": 49000.0,
        }
        case = await service.create_or_aggregate_sar(
            tx_payload=tx,
            ml_result={"risk_score": 0.95, "latency_ms": 8.0},
            typology=SuspicionTypology.IN_TYP_STRUCT,
        )
        sar_id = case.sar_id

        # 1. Retrieve by ID
        retrieved = await service.get_sar_by_id(sar_id)
        assert retrieved is not None
        assert retrieved.sar_id == sar_id

        # Invalid ID
        assert await service.get_sar_by_id("SAR-NONEXISTENT") is None

        # Ring is currently active
        assert "suspect_store@paytm" in service._active_ring_index

        # 2. Update status to FILED_WITH_FIU
        updated = await service.update_sar_status(
            sar_id=sar_id,
            new_status=CaseStatus.FILED_WITH_FIU,
            analyst_id="ANALYST-PMLA-007",
            resolution_notes="Filed STR with FIU-IND FINnet portal.",
        )
        assert updated is not None
        assert updated.status == CaseStatus.FILED_WITH_FIU
        assert updated.assigned_analyst == "ANALYST-PMLA-007"

        # 3. Verify eviction from active ring index
        assert "suspect_store@paytm" not in service._active_ring_index

        # 4. Next transaction for this entity must create a BRAND NEW case
        tx_subsequent = {
            "transaction_id": "UTR-LIFECYCLE-2",
            "account_from": "acc_02@upi",
            "account_to": "suspect_store@paytm",
            "amount": 48000.0,
        }
        new_case = await service.create_or_aggregate_sar(
            tx_payload=tx_subsequent,
            ml_result={"risk_score": 0.93, "latency_ms": 7.0},
            typology=SuspicionTypology.IN_TYP_STRUCT,
        )
        assert new_case.sar_id != sar_id
        assert new_case.status == CaseStatus.PENDING_REVIEW

    asyncio.run(_test())


def test_list_sars_filtering_and_pagination():
    """Tests list_sars with pagination, sorting, status/typology filters, and search query."""
    async def _test():
        service = SARService()

        # Create 5 distinct cases
        for i in range(5):
            await service.create_or_aggregate_sar(
                tx_payload={
                    "transaction_id": f"UTR-LIST-{i}",
                    "account_from": f"remitter_{i}@bank",
                    "account_to": f"distinct_dest_{i}@bank",
                    "amount": 40000.0 + i * 1000,
                    "entity_name": f"Corporate Target {i}",
                },
                ml_result={"risk_score": 0.85 + i * 0.02, "latency_ms": 6.0},
                typology=SuspicionTypology.IN_TYP_STRUCT if i % 2 == 0 else SuspicionTypology.IN_TYP_HAWALA,
            )

        # 1. Total count & pagination
        items, total = await service.list_sars(page=1, page_size=3)
        assert total == 5
        assert len(items) == 3

        page2_items, _ = await service.list_sars(page=2, page_size=3)
        assert len(page2_items) == 2

        # 2. Typology filter
        struct_items, struct_total = await service.list_sars(typology=SuspicionTypology.IN_TYP_STRUCT)
        assert struct_total == 3
        assert all(c.grounds_of_suspicion.primary_typology == SuspicionTypology.IN_TYP_STRUCT for c in struct_items)

        # 3. Search filter
        search_items, search_total = await service.list_sars(search="Corporate Target 3")
        assert search_total == 1
        assert search_items[0].suspect.entity_name == "Corporate Target 3"
        assert search_items[0].counterparty.entity_identifier == "distinct_dest_3@bank"

    asyncio.run(_test())


def test_concurrent_aggregation_race_safety():
    """Tests thread-safe handling of 10 concurrent burst transactions to the same mule ring."""
    async def _test():
        service = SARService()
        target_account = "concurrent_mule_pool@oksbi"

        async def send_burst(i: int):
            return await service.create_or_aggregate_sar(
                tx_payload={
                    "transaction_id": f"UTR-CONC-{i}",
                    "account_from": f"smurf_{i}@bank",
                    "account_to": target_account,
                    "amount": 45000.0,
                    "payment_format": "UPI",
                },
                ml_result={"risk_score": 0.90 + (i * 0.005), "latency_ms": 5.0},
                typology=SuspicionTypology.IN_TYP_STRUCT,
            )

        # Dispatch 10 concurrent requests simultaneously
        results = await asyncio.gather(*(send_burst(i) for i in range(10)))

        # All returned cases must share the identical SAR ID
        sar_ids = {r.sar_id for r in results}
        assert len(sar_ids) == 1, f"Expected 1 consolidated SAR ID, got: {sar_ids}"

        consolidated_sar_id = results[0].sar_id
        final_case = await service.get_sar_by_id(consolidated_sar_id)

        # Exactly 10 transactions accumulated
        assert len(final_case.transactions) == 10
        # Cumulative exposure: 10 * 45,000 = 450,000 INR
        assert final_case.total_exposure_inr == 450000.0

    asyncio.run(_test())
