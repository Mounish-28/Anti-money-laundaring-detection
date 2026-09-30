"""
tests/test_benchmark_simulation.py
=============================================================================
Unit tests for benchmark_simulation.py:
- DatasetSampler multi-dataset extraction
- calculate_classification_metrics
- analyze_benchmark_results
- Markdown report generation
=============================================================================
"""

import os
import pytest
from benchmark_simulation import (
    BenchmarkItem,
    DatasetSampler,
    EvaluationResult,
    analyze_benchmark_results,
    calculate_classification_metrics,
    generate_markdown_report,
)


def test_dataset_sampler_all():
    """Verify DatasetSampler returns samples across all 5 datasets."""
    sampler = DatasetSampler()
    items = sampler.sample_all(n_per_class=3)
    # 5 datasets * (3 pos + 3 neg) = 30 items
    assert len(items) == 30

    datasets_found = set(it.dataset for it in items)
    expected_datasets = {
        "IBM Transactions",
        "SAML-D",
        "Elliptic Bitcoin",
        "IBM AMLSim",
        "Time-Series AML",
    }
    assert datasets_found == expected_datasets

    # Verify both rails represented
    rails = set(it.rail for it in items)
    assert "fiat" in rails
    assert "crypto" in rails

    # Verify both positive and negative ground truths
    labels = set(it.ground_truth for it in items)
    assert labels == {0, 1}


def test_calculate_classification_metrics():
    """Test classification metrics computation for known confusion matrix."""
    y_true = [1, 1, 1, 0, 0, 0]
    y_pred = [1, 1, 0, 0, 0, 1]

    # TP = 2, FP = 1, TN = 2, FN = 1
    m = calculate_classification_metrics(y_true, y_pred)
    assert m["tp"] == 2
    assert m["fp"] == 1
    assert m["tn"] == 2
    assert m["fn"] == 1
    assert m["precision"] == round(2 / 3, 4)
    assert m["recall"] == round(2 / 3, 4)
    assert m["accuracy"] == round(4 / 6, 4)
    assert m["fpr"] == round(1 / 3, 4)


def test_analyze_and_generate_report(tmp_path):
    """Test full analysis aggregation and report markdown writing."""
    item_pos = BenchmarkItem(
        tx_id="TX_TEST_01",
        dataset="SAML-D",
        rail="fiat",
        ground_truth=1,
        typology="Structuring / Smurfing",
        payload={"tx_id": "TX_TEST_01"},
    )
    item_neg = BenchmarkItem(
        tx_id="TX_TEST_02",
        dataset="Elliptic Bitcoin",
        rail="crypto",
        ground_truth=0,
        typology="Licit Crypto Transfer",
        payload={"tx_id": "TX_TEST_02"},
    )

    results = [
        EvaluationResult(
            item=item_pos,
            status_code=200,
            latency_ms=8.5,
            risk_score=91.0,
            alert_triggered=True,
            risk_level="Critical",
            fired_rules=["SUB_THRESHOLD_STRUCTURING"],
            success=True,
        ),
        EvaluationResult(
            item=item_neg,
            status_code=200,
            latency_ms=6.2,
            risk_score=35.0,
            alert_triggered=False,
            risk_level="Low",
            fired_rules=[],
            success=True,
        ),
    ]

    analysis = analyze_benchmark_results(results, total_wall_time=0.05, mode_str="TestMode")
    assert analysis["summary"]["total_transactions"] == 2
    assert analysis["summary"]["successful_requests"] == 2
    assert analysis["summary"]["failed_or_dropped"] == 0
    assert analysis["latency_profiling"]["p50_ms"] > 0
    assert analysis["overall_evaluation"]["f1_score"] == 1.0

    report_file = os.path.join(tmp_path, "test_report.md")
    generate_markdown_report(analysis, report_file)
    assert os.path.exists(report_file)
    with open(report_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "QuantumAML Nexus: Pipeline Performance & Benchmark Report" in content
    assert "SAML-D" in content
    assert "Elliptic Bitcoin" in content
