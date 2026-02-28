"""
Skeleton normalization utilities for the elite jump model.
Produces a translation- and scale-invariant pose sequence of fixed length.
"""

import numpy as np
from scipy.interpolate import interp1d

from cv.pose_extractor import KEYPOINT_NAMES

TARGET_FRAMES = 60


def normalize_skeleton(pose_frames: list) -> np.ndarray:
    """
    Convert a variable-length list of PoseFrame objects into a fixed
    (TARGET_FRAMES, 17, 3) numpy array that is:
      1. Translation invariant — centered on hip midpoint
      2. Scale invariant     — divided by shoulder width
      3. Fixed length        — linearly interpolated to TARGET_FRAMES

    Returns:
        np.ndarray of shape (TARGET_FRAMES, 17, 3) — (x, y, confidence)
    """
    if not pose_frames:
        return np.zeros((TARGET_FRAMES, 17, 3), dtype=np.float32)

    raw = []
    for f in pose_frames:
        frame_kpts = []
        for name in KEYPOINT_NAMES:
            kp = f.keypoints.get(name, (0.0, 0.0, 0.5))
            frame_kpts.append([kp[0], kp[1], kp[2]])
        raw.append(frame_kpts)

    raw = np.array(raw, dtype=np.float32)  # (T, 17, 3)
    T = raw.shape[0]

    # Center on hip midpoint (indices 11=left_hip, 12=right_hip)
    hip_mid = (raw[:, 11, :2] + raw[:, 12, :2]) / 2  # (T, 2)
    raw[:, :, :2] -= hip_mid[:, np.newaxis, :]

    # Scale by mean shoulder width (indices 5=left_shoulder, 6=right_shoulder)
    shoulder_dist = np.linalg.norm(
        raw[:, 5, :2] - raw[:, 6, :2], axis=1
    ).mean()
    if shoulder_dist > 1e-6:
        raw[:, :, :2] /= shoulder_dist

    # Interpolate to TARGET_FRAMES
    if T == TARGET_FRAMES:
        return raw

    t_orig = np.linspace(0, 1, T)
    t_new = np.linspace(0, 1, TARGET_FRAMES)
    normalized = np.zeros((TARGET_FRAMES, 17, 3), dtype=np.float32)

    for j in range(17):
        for c in range(3):
            if T > 1:
                f_interp = interp1d(t_orig, raw[:, j, c], kind="linear")
                normalized[:, j, c] = f_interp(t_new)
            else:
                normalized[:, j, c] = raw[0, j, c]

    return normalized
