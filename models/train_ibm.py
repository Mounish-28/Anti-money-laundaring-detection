"""
Production Retraining Pipeline for IBM Transactions AML Detection
Enforces 7 Engine Features, 80/20 train/test split, and balanced class weights.
"""

import os
import sys

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base_dir not in sys.path:
    sys.path.insert(0, _base_dir)

from scripts.retrain_ibm import retrain_ibm  # noqa: E402


def run_ibm_retraining():
    return retrain_ibm()


if __name__ == "__main__":
    run_ibm_retraining()
