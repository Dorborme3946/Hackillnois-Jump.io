"""
Dataset loader for elite jump model training.
Expects pose JSON files in data/poses/ with a label field.
"""

import json
import os
import random
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from ml.normalize import normalize_skeleton, TARGET_FRAMES


class PoseSequenceDataset(Dataset):
    """
    Loads pre-extracted pose JSON files for triplet training.

    JSON file format:
    {
        "label": "elite" | "sub_elite",
        "athlete": "athlete_name",
        "frames": [
            {"keypoints": {"nose": [x, y, conf], ...}},
            ...
        ]
    }
    """

    def __init__(self, poses_dir: str, split: str = "train", train_ratio: float = 0.85):
        self.poses_dir = Path(poses_dir)
        all_files = sorted(self.poses_dir.glob("*.json"))

        random.seed(42)
        random.shuffle(all_files)
        split_idx = int(len(all_files) * train_ratio)

        if split == "train":
            self.files = all_files[:split_idx]
        else:
            self.files = all_files[split_idx:]

        self.elite_files = [f for f in self.files if self._is_elite(f)]
        self.sub_elite_files = [f for f in self.files if not self._is_elite(f)]

    def _is_elite(self, path: Path) -> bool:
        try:
            with open(path) as f:
                data = json.load(f)
            return data.get("label", "sub_elite") == "elite"
        except Exception:
            return False

    def _load_sequence(self, path: Path) -> np.ndarray:
        with open(path) as f:
            data = json.load(f)

        frames_data = data.get("frames", [])
        # Build pseudo-PoseFrame-like objects for normalize_skeleton
        pseudo_frames = [_DictFrame(fd) for fd in frames_data]
        return normalize_skeleton(pseudo_frames)

    def __len__(self):
        return len(self.elite_files)

    def __getitem__(self, idx):
        """Return (anchor, positive, negative) triplet."""
        anchor_path = self.elite_files[idx % len(self.elite_files)]
        pos_path = random.choice(self.elite_files)
        neg_path = random.choice(self.sub_elite_files) if self.sub_elite_files else pos_path

        anchor = torch.tensor(self._load_sequence(anchor_path), dtype=torch.float32)
        positive = torch.tensor(self._load_sequence(pos_path), dtype=torch.float32)
        negative = torch.tensor(self._load_sequence(neg_path), dtype=torch.float32)

        return anchor, positive, negative


class _DictFrame:
    """Thin wrapper so dict-based frame data works with normalize_skeleton."""

    def __init__(self, frame_dict: dict):
        raw_kpts = frame_dict.get("keypoints", {})
        self.keypoints = {}
        for name, val in raw_kpts.items():
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                self.keypoints[name] = (float(val[0]), float(val[1]), float(val[2]) if len(val) > 2 else 0.9)
            else:
                self.keypoints[name] = (0.0, 0.0, 0.0)
