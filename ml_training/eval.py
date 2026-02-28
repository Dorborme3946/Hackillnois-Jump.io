"""
Evaluation script for the EliteJumpModel.
Computes cosine similarity distributions for elite vs sub-elite clips.

Usage:
    python eval.py --poses-dir ../data/poses --checkpoint ../backend/ml/checkpoints/elite_model_best.pt
"""

import sys
import os
import argparse
import json
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ml.elite_jump_model import EliteJumpModel
from ml.normalize import normalize_skeleton
from ml.dataset import _DictFrame


def evaluate(poses_dir: str, checkpoint: str):
    device = torch.device("cpu")
    model = EliteJumpModel(embedding_dim=512).to(device)
    state = torch.load(checkpoint, map_location=device)
    model.load_state_dict(state)
    model.eval()
    print(f"Loaded checkpoint: {checkpoint}")

    poses_dir = Path(poses_dir)
    pose_files = list(poses_dir.glob("*.json"))

    elite_scores = []
    sub_scores = []

    with torch.no_grad():
        for pose_file in pose_files:
            data = json.loads(pose_file.read_text())
            label = data.get("label", "sub_elite")
            frames_data = data.get("frames", [])
            if not frames_data:
                continue

            pseudo_frames = [_DictFrame(fd) for fd in frames_data]
            seq = normalize_skeleton(pseudo_frames)
            x = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)
            emb = model(x)  # (1, 512)
            # Use L2 norm as a proxy score (larger = more confident embedding)
            score = float(emb.norm().item())

            if label == "elite":
                elite_scores.append(score)
            else:
                sub_scores.append(score)

    if elite_scores:
        print(f"\nElite clips ({len(elite_scores)}): mean={np.mean(elite_scores):.4f} std={np.std(elite_scores):.4f}")
    if sub_scores:
        print(f"Sub-elite clips ({len(sub_scores)}): mean={np.mean(sub_scores):.4f} std={np.std(sub_scores):.4f}")

    if elite_scores and sub_scores:
        # Simple separation metric
        gap = np.mean(elite_scores) - np.mean(sub_scores)
        print(f"\nSeparation gap: {gap:.4f} (higher = better discrimination)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate EliteJumpModel")
    parser.add_argument("--poses-dir", default="../data/poses")
    parser.add_argument("--checkpoint", default="../backend/ml/checkpoints/elite_model_best.pt")
    args = parser.parse_args()
    evaluate(args.poses_dir, args.checkpoint)
