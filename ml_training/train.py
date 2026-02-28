"""
Top-level training entry point for the elite jump model.
Delegates to backend/ml/train.py with sensible defaults.

Usage (from ml_training/):
    python train.py
    python train.py --epochs 200 --batch-size 32
"""

import sys
import os

# Add backend to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ml.train import train

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train EliteJumpModel")
    parser.add_argument("--poses-dir", default="../data/poses")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()
    train(args.poses_dir, args.epochs, args.batch_size, args.lr)
