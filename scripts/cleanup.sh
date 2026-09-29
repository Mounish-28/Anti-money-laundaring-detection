#!/usr/bin/env bash
# =============================================================================
# scripts/cleanup.sh: Wrapper for QuantumAML Nexus Safe Cleanup Utility
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

VENV_PYTHON="$ROOT_DIR/.venv/Scripts/python.exe"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
fi
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python"
fi

"$VENV_PYTHON" "$SCRIPT_DIR/safe_project_cleanup.py" "$@"
