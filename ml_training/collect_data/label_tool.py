"""
Simple CLI labeling tool for jump clip annotation.
Iterates through videos in a directory, shows metadata, and asks the user to label each.

Usage:
    python label_tool.py --clips-dir ../../data/elite_clips --poses-dir ../../data/poses
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_labeling(clips_dir: str, poses_dir: str):
    clips_dir = Path(clips_dir)
    poses_dir = Path(poses_dir)
    poses_dir.mkdir(parents=True, exist_ok=True)

    video_files = sorted(clips_dir.glob("*.mp4"))
    if not video_files:
        print(f"No .mp4 files found in {clips_dir}")
        return

    labeled = 0
    skipped = 0

    for video_path in video_files:
        pose_json = poses_dir / (video_path.stem + ".json")

        # Check if already labeled
        if pose_json.exists():
            existing = json.loads(pose_json.read_text())
            if "label" in existing:
                print(f"[skip] Already labeled: {video_path.name} → {existing['label']}")
                skipped += 1
                continue

        print(f"\n{'='*60}")
        print(f"File: {video_path.name}")

        # Check for sidecar metadata
        sidecar = clips_dir / (video_path.stem + ".json")
        suggested_label = "elite"
        if sidecar.exists():
            meta = json.loads(sidecar.read_text())
            suggested_label = meta.get("label", "elite")
            print(f"Sidecar label suggestion: {suggested_label}")

        print("Options: [e]lite  [s]ub_elite  [k]ip  [q]uit")

        # Optionally open the video
        open_vid = input("Open video? [y/N]: ").strip().lower()
        if open_vid == "y":
            _open_video(video_path)

        choice = input(f"Label [{suggested_label[0]}]: ").strip().lower() or suggested_label[0]

        if choice == "q":
            print("Quit.")
            break
        elif choice == "k":
            skipped += 1
            continue
        elif choice in ("e", "elite"):
            label = "elite"
        elif choice in ("s", "sub_elite", "sub"):
            label = "sub_elite"
        else:
            label = suggested_label

        # Write / update the pose JSON
        data = {}
        if pose_json.exists():
            data = json.loads(pose_json.read_text())
        data["label"] = label
        data["source_video"] = str(video_path)
        pose_json.write_text(json.dumps(data, indent=2))
        print(f"Labeled as: {label}")
        labeled += 1

    print(f"\nDone. Labeled: {labeled}, Skipped: {skipped}")


def _open_video(path: Path):
    """Open video with the system default player."""
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)])
    else:
        subprocess.run(["xdg-open", str(path)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Label jump clips for training")
    parser.add_argument("--clips-dir", default="../../data/elite_clips")
    parser.add_argument("--poses-dir", default="../../data/poses")
    args = parser.parse_args()
    run_labeling(args.clips_dir, args.poses_dir)
