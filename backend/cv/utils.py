"""Coordinate and geometry helper utilities."""

import numpy as np


def normalize_keypoints(keypoints: dict, frame_width: float, frame_height: float) -> dict:
    """Normalize keypoint coordinates to [0, 1] range."""
    return {
        name: (x / frame_width, y / frame_height, conf)
        for name, (x, y, conf) in keypoints.items()
    }


def midpoint(a: tuple, b: tuple) -> tuple:
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def distance(a: tuple, b: tuple) -> float:
    return float(np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))


def pose_frames_to_json(frames) -> list[dict]:
    """Serialize a subset of PoseFrames for API response."""
    result = []
    for f in frames:
        result.append({
            "frame_idx": f.frame_idx,
            "timestamp_ms": f.timestamp_ms,
            "keypoints": {
                name: {"x": x, "y": y, "conf": conf}
                for name, (x, y, conf) in f.keypoints.items()
            },
            "bbox": list(f.bbox),
        })
    return result
