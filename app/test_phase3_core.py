"""
Verification script for Phase 3 core algorithmic engines and security middleware.
"""

from app.domains.investigation.bm25_service import BM25SearchService
from app.domains.investigation.quicksort_service import QuickSortLedgerService
from app.domains.bank.collaborative_filter import CollaborativeFilteringService
from app.domains.bank.hash_lookup_service import RobinHoodHashTable


def test_bm25():
    docs = [
        {
            "id": "doc1",
            "title": "Wire MT103",
            "content": "Offshore Alpha LLC wire transfer routing 021000021 to Apex Holdings",
        },
        {
            "id": "doc2",
            "title": "Signal Chat",
            "content": "Keep Cayman wire under 500k to avoid escalation Marcus Vance",
        },
    ]
    engine = BM25SearchService()
    engine.index_corpus(docs)
    res = engine.search("Cayman wire routing")
    assert len(res["results"]) > 0, "BM25 should return matches"
    print(f"BM25 Search PASSED: {len(res['results'])} matches in {res['latency_ms']}ms")


def test_quicksort():
    # Test small partition insertion sort
    small_records = [
        {"id": "1", "amount": 499500.0, "risk": 0.98},
        {"id": "2", "amount": 9900.0, "risk": 0.91},
        {"id": "3", "amount": 9900.0, "risk": 0.91},  # duplicate
        {"id": "4", "amount": 495000.0, "risk": 0.97},
    ]
    small_res = QuickSortLedgerService.sort(
        small_records, [{"key": "amount", "direction": "desc"}]
    )
    sorted_amounts = [r["amount"] for r in small_res["sorted_records"]]
    assert sorted_amounts == [
        499500.0,
        495000.0,
        9900.0,
        9900.0,
    ], "QuickSort order should be descending"

    # Test large dataset (> 16 elements) to trigger 3-way DNF duplicate pivot partitioning
    large_records = [
        {
            "id": f"tx_{i}",
            "amount": 9900.0 if i % 3 == 0 else float(i * 1000),
            "risk": 0.5,
        }
        for i in range(40)
    ]
    large_res = QuickSortLedgerService.sort(
        large_records, [{"key": "amount", "direction": "desc"}]
    )
    assert (
        large_res["duplicate_pivots"] >= 1
    ), "Duplicate pivots should be handled in 3-way DNF"
    print(
        f"QuickSort PASSED: sorted {large_res['element_count']} elements in {large_res['duration_ms']}ms (DNF duplicates handled: {large_res['duplicate_pivots']})"
    )


def test_hash_table():
    table = RobinHoodHashTable(64)
    table.insert(
        "ACC-021000021-994821", {"entity": "Offshore Alpha LLC", "balance": 1240500.0}
    )
    res = table.lookup("ACC-021000021-994821")
    assert res["found"] is True, "Hash lookup should find inserted key"
    assert res["value"]["entity"] == "Offshore Alpha LLC"
    print(f"Robin Hood Hash Lookup PASSED: latency {res['latency_micros']}µs")


def test_collaborative_filtering():
    accounts = [
        {
            "id": "acc1",
            "name": "Offshore Alpha",
            "vector": [0.95, 0.98, 0.92, 0.78, 0.91, 0.85, 0.88, 0.94],
        },
        {
            "id": "acc2",
            "name": "Normal Peer A",
            "vector": [0.35, 0.40, 0.05, 0.12, 0.38, 0.08, 0.10, 0.25],
        },
        {
            "id": "acc3",
            "name": "Normal Peer B",
            "vector": [0.38, 0.42, 0.04, 0.10, 0.35, 0.06, 0.08, 0.22],
        },
    ]
    cf = CollaborativeFilteringService(peer_k=2)
    cf.load_accounts(accounts)
    eval_res = cf.evaluate_account(accounts[0])
    assert (
        eval_res["is_anomaly"] is True
    ), f"Account should be flagged anomaly, got score {eval_res['anomaly_score']}"
    assert (
        eval_res["anomaly_score"] >= 0.40
    ), "Anomaly score should meet or exceed threshold"
    print(
        f"Collaborative Filtering PASSED: anomaly score {eval_res['anomaly_score']} with {len(eval_res['deviations'])} deviations"
    )


if __name__ == "__main__":
    test_bm25()
    test_quicksort()
    test_hash_table()
    test_collaborative_filtering()
    print("ALL PHASE 3 BACKEND CORE ALGORITHM TESTS PASSED!")
