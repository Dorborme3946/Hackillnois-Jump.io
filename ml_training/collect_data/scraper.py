"""
YouTube clip downloader for elite jump footage.
Requires yt-dlp:  pip install yt-dlp

Usage:
    python scraper.py --url "https://www.youtube.com/watch?v=..." --output ../../data/elite_clips
    python scraper.py --playlist "..." --output ../../data/elite_clips --label sub_elite
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def download_clip(url: str, output_dir: str, label: str = "elite", start_sec: float = 0.0, end_sec: float = 0.0):
    """Download a YouTube video (or clip) into output_dir."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    yt_dlp_args = [
        sys.executable, "-m", "yt_dlp",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", str(output_dir / "%(id)s.%(ext)s"),
        "--no-playlist",
    ]

    if start_sec > 0 or end_sec > 0:
        # Download only the relevant section
        section = f"*{start_sec:.1f}-{end_sec:.1f}"
        yt_dlp_args += ["--download-sections", section, "--force-keyframes-at-cuts"]

    yt_dlp_args.append(url)

    result = subprocess.run(yt_dlp_args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] yt-dlp failed for {url}:\n{result.stderr}")
        return

    print(f"[OK] Downloaded: {url}")

    # Write a metadata sidecar so the dataset loader knows the label
    video_id = _extract_video_id(url)
    meta_path = output_dir / f"{video_id}.json"
    meta_path.write_text(json.dumps({
        "url": url,
        "label": label,
        "start_sec": start_sec,
        "end_sec": end_sec,
    }, indent=2))


def download_playlist(playlist_url: str, output_dir: str, label: str = "sub_elite"):
    """Download all videos in a YouTube playlist."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    yt_dlp_args = [
        sys.executable, "-m", "yt_dlp",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", str(output_dir / "%(id)s.%(ext)s"),
        "--yes-playlist",
        playlist_url,
    ]
    subprocess.run(yt_dlp_args)


def _extract_video_id(url: str) -> str:
    import re
    match = re.search(r"v=([^&]+)", url)
    if match:
        return match.group(1)
    # Short URL format
    match = re.search(r"youtu\.be/([^?]+)", url)
    if match:
        return match.group(1)
    return "unknown"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download elite jump footage")
    parser.add_argument("--url", help="Single YouTube URL")
    parser.add_argument("--playlist", help="YouTube playlist URL")
    parser.add_argument("--output", default="../../data/elite_clips")
    parser.add_argument("--label", choices=["elite", "sub_elite"], default="elite")
    parser.add_argument("--start", type=float, default=0.0, help="Clip start (seconds)")
    parser.add_argument("--end", type=float, default=0.0, help="Clip end (seconds)")
    args = parser.parse_args()

    if args.url:
        download_clip(args.url, args.output, args.label, args.start, args.end)
    elif args.playlist:
        download_playlist(args.playlist, args.output, args.label)
    else:
        parser.print_help()
