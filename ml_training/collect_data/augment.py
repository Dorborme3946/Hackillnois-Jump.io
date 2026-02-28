"""
Data augmentation for jump pose sequences.
Generates additional training samples from existing labeled pose JSONs.

Augmentations:
    - Random Gaussian noise on keypoint coordinates
    - Speed variation (temporal stretch/compress ±20%)
    - Horizontal mirror flip (swap left/right keypoints)
    - Random frame dropout (simulate low-confidence keypoints)

Usage:
    python augment.py --poses-dir ../../data/poses --factor 3
"""

import argparse
import json
import copy
import random
from pathlib import Path

import numpy as np

# Keypoint index pairs for left ↔ right mirroring
MIRROR_PAIRS = [
    (1, 2),   # left_eye / right_eye
    (3, 4),   # left_ear / right_ear
    (5, 6),   # left_shoulder / right_shoulder
    (7, 8),   # left_elbow / right_elbow
    (9, 10),  # left_wrist / right_wrist
    (11, 12), # left_hip / right_hip
    (13, 14), # left_knee / right_knee
    (15, 16), # left_ankle / right_ankle
]

KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]


def augment_pose_json(pose_data: dict, noise_std: float = 0.01, speed_factor: float = 1.0, mirror: bool = False) -> dict:
    """Return an augmented copy of a pose JSON dict."""
    aug = copy.deepcopy(pose_data)
    frames = aug.get("frames", [])

    if not frames:
        return aug

    # Speed variation: subsample or repeat frames
    if abs(speed_factor - 1.0) > 0.01:
        n_frames = max(5, int(len(frames) * speed_factor))
        indices = np.linspace(0, len(frames) - 1, n_frames).astype(int)
        frames = [frames[i] for i in indices]

    new_frames = []
    for frame in frames:
        kpts = frame.get("keypoints", {})
        new_kpts = {}
        for name, vals in kpts.items():
            x, y = float(vals[0]), float(vals[1])
            conf = float(vals[2]) if len(vals) > 2 else 0.9

            # Add Gaussian noise
            x += random.gauss(0, noise_std)
            y += random.gauss(0, noise_std)

            # Random dropout (low confidence)
            if random.random() < 0.05:
                conf = 0.0
                x = y = 0.0

            new_kpts[name] = [x, y, conf]

        if mirror:
            # Swap left/right pairs
            for i, j in MIRROR_PAIRS:
                li, ri = KEYPOINT_NAMES[i], KEYPOINT_NAMES[j]
                if li in new_kpts and ri in new_kpts:
                    new_kpts[li], new_kpts[ri] = new_kpts[ri], new_kpts[li]
            # Flip x-coordinate (negate)
            for name, vals in new_kpts.items():
                vals[0] = -vals[0]

        new_frames.append({"keypoints": new_kpts})

    aug["frames"] = new_frames
    aug["augmented"] = True
    return aug


def augment_directory(poses_dir: str, factor: int = 3):
    """Generate `factor` augmented copies of each labeled pose JSON."""
    poses_dir = Path(poses_dir)
    existing = list(poses_dir.glob("*.json"))
    print(f"Found {len(existing)} pose JSONs. Generating {factor}x augmentations...")

    generated = 0
    for pose_path in existing:
        data = json.loads(pose_path.read_text())
        if data.get("augmented"):
            continue  # Don't re-augment

        for i in range(factor):
            speed = random.uniform(0.8, 1.2)
            mirror = random.random() < 0.5
            noise = random.uniform(0.005, 0.02)

            aug_data = augment_pose_json(data, noise_std=noise, speed_factor=speed, mirror=mirror)
            aug_path = poses_dir / f"{pose_path.stem}_aug{i}.json"
            aug_path.write_text(json.dumps(aug_data, indent=2))
            generated += 1

    print(f"Generated {generated} augmented samples.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Augment pose training data")
    parser.add_argument("--poses-dir", default="../../data/poses")
    parser.add_argument("--factor", type=int, default=3, help="Augmentations per original sample")
    args = parser.parse_args()
    augment_directory(args.poses_dir, args.factor)
