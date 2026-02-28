"""
Export pre-computed elite embeddings gallery.
Loads all elite-labeled pose JSONs, runs them through the trained model,
and saves the embedding dictionary to data/gallery/elite_embeddings.pt.

Usage:
    python export_gallery.py
    python export_gallery.py --checkpoint ../backend/ml/checkpoints/elite_model_best.pt
"""

import sys
import os
import json
import argparse
from pathlib import Path

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ml.elite_jump_model import EliteJumpModel
from ml.normalize import normalize_skeleton
from ml.dataset import _DictFrame


def export_gallery(poses_dir: str, checkpoint: str, output: str):
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    device = torch.device("cpu")
    model = EliteJumpModel(embedding_dim=512).to(device)

    if os.path.exists(checkpoint):
        state = torch.load(checkpoint, map_location=device)
        model.load_state_dict(state)
        print(f"Loaded checkpoint: {checkpoint}")
    else:
        print(f"[WARNING] Checkpoint not found at {checkpoint} — using random weights.")
        print("  Train the model first with: python train.py")

    model.eval()

    poses_dir = Path(poses_dir)
    elite_files = []
    for pose_file in poses_dir.glob("*.json"):
        try:
            data = json.loads(pose_file.read_text())
            if data.get("label") == "elite" and not data.get("augmented"):
                elite_files.append((pose_file, data))
        except Exception:
            continue

    if not elite_files:
        print(f"No elite pose JSONs found in {poses_dir}.")
        print("  Use collect_data/scraper.py + collect_data/label_tool.py to create labeled data.")
        # Export empty gallery so the app still runs
        torch.save({}, output_path)
        print(f"Saved empty gallery to {output_path}")
        return

    gallery = {}
    with torch.no_grad():
        for pose_file, data in elite_files:
            frames_data = data.get("frames", [])
            if not frames_data:
                continue
            pseudo_frames = [_DictFrame(fd) for fd in frames_data]
            seq = normalize_skeleton(pseudo_frames)
            x = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)
            emb = model(x).squeeze(0)  # (512,)

            athlete = data.get("athlete", pose_file.stem)
            gallery[athlete] = emb
            print(f"  Added: {athlete} ({emb.shape})")

    torch.save(gallery, output_path)
    print(f"\nExported gallery with {len(gallery)} elite embeddings → {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export elite embeddings gallery")
    parser.add_argument("--poses-dir", default="../data/poses")
    parser.add_argument("--checkpoint", default="../backend/ml/checkpoints/elite_model_best.pt")
    parser.add_argument("--output", default="../data/gallery/elite_embeddings.pt")
    args = parser.parse_args()
    export_gallery(args.poses_dir, args.checkpoint, args.output)
