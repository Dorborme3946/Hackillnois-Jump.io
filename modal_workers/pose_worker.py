"""
Modal GPU worker — YOLO pose extraction.
Runs on a GPU instance; called remotely from the FastAPI backend.
"""

import modal
from modal_workers.app import app, jumpai_image

GPU_TYPE = "T4"  # Cheapest Modal GPU; upgrade to A10G for production


@app.function(
    image=jumpai_image,
    gpu=GPU_TYPE,
    timeout=300,
    retries=1,
)
def extract_pose_remote(video_bytes: bytes, fps_override: float | None = None) -> dict:
    """
    Accept raw video bytes, run YOLO pose extraction, return pose data.

    Args:
        video_bytes: Raw bytes of the video file.
        fps_override: Optional FPS override for slow-motion detection.

    Returns:
        dict with keys:
            - fps: float
            - frames: list of frame dicts [{frame_idx, timestamp_ms, keypoints, has_object_in_hands}]
    """
    import tempfile
    import os
    import sys

    # Write bytes to temp file so OpenCV / YOLO can read it
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        # Add backend to path so imports work on Modal
        sys.path.insert(0, "/root/backend")
        from cv.pose_extractor import PoseExtractor
        import cv2

        cap = cv2.VideoCapture(tmp_path)
        fps = fps_override or cap.get(cv2.CAP_PROP_FPS)
        cap.release()

        extractor = PoseExtractor()
        pose_frames = extractor.extract_all_frames(tmp_path)

        frames_out = []
        for f in pose_frames:
            frames_out.append({
                "frame_idx": f.frame_idx,
                "timestamp_ms": f.timestamp_ms,
                "keypoints": {k: list(v) for k, v in f.keypoints.items()},
                "has_object_in_hands": f.has_object_in_hands,
            })

        return {"fps": fps, "frames": frames_out}

    finally:
        os.unlink(tmp_path)
