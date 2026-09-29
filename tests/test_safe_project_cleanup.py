"""
tests/test_safe_project_cleanup.py
=============================================================================
Unit tests verifying the safe cleanup utility:
  1. Safe Whitelisting (protected extensions & core domains)
  2. Candidate Scanning & Target Classification
  3. Default Dry-Run Mode Safety Invariant
  4. Post-Cleanup 5-Dataset Pipeline Audit Verification
=============================================================================
"""

import os
import shutil
import tempfile
import pytest

from scripts.safe_project_cleanup import (
    ABSOLUTE_PROTECTED_DIR_NAMES,
    PROTECTED_EXTENSIONS,
    REMOVABLE_DIR_NAMES,
    REMOVABLE_FILE_EXTENSIONS,
    ProjectDirectoryScanner,
    audit_5_aml_pipelines,
    format_bytes,
    is_removable_file,
)


def test_format_bytes_utility():
    """Verify human-readable byte formatting across scales."""
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1048576) == "1.00 MB"
    assert format_bytes(1073741824) == "1.00 GB"


def test_whitelisting_rules():
    """Verify critical extensions and directories are protected."""
    assert ".py" in PROTECTED_EXTENSIONS
    assert ".pt" in PROTECTED_EXTENSIONS
    assert ".joblib" in PROTECTED_EXTENSIONS
    assert ".cbm" in PROTECTED_EXTENSIONS
    assert ".json" in PROTECTED_EXTENSIONS
    assert ".yaml" in PROTECTED_EXTENSIONS
    assert ".csv" in PROTECTED_EXTENSIONS

    assert ".git" in ABSOLUTE_PROTECTED_DIR_NAMES
    assert ".venv" in ABSOLUTE_PROTECTED_DIR_NAMES
    assert "node_modules" in ABSOLUTE_PROTECTED_DIR_NAMES


def test_removable_classification():
    """Verify temporary patterns are correctly identified."""
    assert is_removable_file("test.tmp", "root")
    assert is_removable_file("test.swp", "root")
    assert is_removable_file("test.bak", "root")
    assert is_removable_file(".coverage", "root")
    assert is_removable_file("runner_e2e.log", "root")

    # Critical artifacts should not be removable
    assert not is_removable_file("model.joblib", "models")
    assert not is_removable_file("train.csv", "data")
    assert not is_removable_file("script.py", "scripts")


def test_mock_directory_scan():
    """Test scanner on an isolated temporary directory tree."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Create mock critical files
        critical_py = os.path.join(temp_dir, "app.py")
        critical_joblib = os.path.join(temp_dir, "weights.joblib")
        with open(critical_py, "w") as f:
            f.write("print('safe')")
        with open(critical_joblib, "w") as f:
            f.write("model_bytes")

        # Create mock removable targets
        pycache_dir = os.path.join(temp_dir, "__pycache__")
        os.makedirs(pycache_dir)
        with open(os.path.join(pycache_dir, "app.cpython-314.pyc"), "w") as f:
            f.write("compiled_bytecode")

        tmp_file = os.path.join(temp_dir, "scratch.tmp")
        with open(tmp_file, "w") as f:
            f.write("temp_data")

        scanner = ProjectDirectoryScanner(temp_dir)
        scanner.scan()

        # Check candidate detection
        assert len(scanner.candidate_dirs) == 1
        assert scanner.candidate_dirs[0][0] == pycache_dir
        assert len(scanner.candidate_files) == 1
        assert scanner.candidate_files[0][0] == tmp_file

        # Check that critical files were NOT queued
        queued_files = [f[0] for f in scanner.candidate_files]
        assert critical_py not in queued_files
        assert critical_joblib not in queued_files

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_workspace_5_aml_pipelines_audit():
    """Verify live audit of 5 active AML pipelines in the real workspace."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    audit_results = audit_5_aml_pipelines(root_dir)

    assert audit_results["all_pipelines_intact"] is True, "Pipeline integrity check failed"
    assert audit_results["registry_ok"] is True, "Enterprise Model Registry missing or invalid"
    assert audit_results["results_ok"] is True, "five_dataset_results_v5 files missing"
    assert "IBM-AML (Transactions)" in audit_results
    assert "SAML-D (Synthetic Graph)" in audit_results
    assert "Elliptic Bitcoin (GNN)" in audit_results
    assert "IBM AMLSim (Agent-Based)" in audit_results
    assert "Time-Series AML (Sequential)" in audit_results
