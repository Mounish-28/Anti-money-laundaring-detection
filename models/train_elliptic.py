"""
Production Retraining Pipeline for Elliptic Bitcoin Illicit Node Detection
Resolves illicit node class imbalance with dynamic scale_pos_weight.
Enforces exact 166-feature tensor format and temporal train/test split.
"""

import os
import sys

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base_dir not in sys.path:
    sys.path.insert(0, _base_dir)

from scripts.retrain_elliptic import retrain_elliptic

def run_elliptic_retraining():
    return retrain_elliptic()

if __name__ == "__main__":
    run_elliptic_retraining()
