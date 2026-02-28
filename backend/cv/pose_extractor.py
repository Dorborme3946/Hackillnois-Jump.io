"""
Pose extractor with two modes:
  1. Real: Uses YOLOv8-pose (requires ultralytics + GPU)
  2. Mock: Generates synthetic jump pose data for prototype demo
"""

import cv2
import numpy as np
import math
from dataclasses import dataclass, field

KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]


@dataclass
class PoseFrame:
    frame_idx: int
    timestamp_ms: float
    keypoints: dict  # name -> (x, y, confidence)
    bbox: tuple
    has_object_in_hands: bool = False


def _build_standing_pose(cx: float, cy_ground: float, scale: float = 1.0) -> dict:
    """Build a canonical standing pose centered at (cx, cy_ground)."""
    s = scale
    return {
        "nose":           (cx,       cy_ground - 290 * s, 0.95),
        "left_eye":       (cx - 10 * s, cy_ground - 305 * s, 0.90),
        "right_eye":      (cx + 10 * s, cy_ground - 305 * s, 0.90),
        "left_ear":       (cx - 20 * s, cy_ground - 295 * s, 0.85),
        "right_ear":      (cx + 20 * s, cy_ground - 295 * s, 0.85),
        "left_shoulder":  (cx - 35 * s, cy_ground - 240 * s, 0.95),
        "right_shoulder": (cx + 35 * s, cy_ground - 240 * s, 0.95),
        "left_elbow":     (cx - 45 * s, cy_ground - 175 * s, 0.90),
        "right_elbow":    (cx + 45 * s, cy_ground - 175 * s, 0.90),
        "left_wrist":     (cx - 45 * s, cy_ground - 110 * s, 0.88),
        "right_wrist":    (cx + 45 * s, cy_ground - 110 * s, 0.88),
        "left_hip":       (cx - 22 * s, cy_ground - 165 * s, 0.95),
        "right_hip":      (cx + 22 * s, cy_ground - 165 * s, 0.95),
        "left_knee":      (cx - 22 * s, cy_ground - 80 * s,  0.93),
        "right_knee":     (cx + 22 * s, cy_ground - 80 * s,  0.93),
        "left_ankle":     (cx - 15 * s, cy_ground,            0.95),
        "right_ankle":    (cx + 15 * s, cy_ground,            0.95),
    }


def generate_mock_jump_frames(
    video_path: str | None = None,
    fps: float = 30.0,
    seed: int | None = None,
) -> list[PoseFrame]:
    """
    Generate synthetic pose frames simulating a vertical jump.
    Phases:
      0–14  : standing still
      15–24 : approach / crouch (loading)
      25–26 : explosive extension (takeoff)
      27–48 : flight arc (22 frames ≈ 733 ms → ~25-28" jump)
      49–54 : landing + absorption
      55–59 : recovery stand
    """
    rng = np.random.default_rng(seed or 42)

    TOTAL_FRAMES = 60
    W, H = 854, 480
    cx = W / 2 + rng.uniform(-20, 20)
    GROUND_Y = H - 40.0   # ankle Y when standing
    SCALE = 1.0

    TAKEOFF_FRAME = 27
    LANDING_FRAME = 49
    FLIGHT_FRAMES = LANDING_FRAME - TAKEOFF_FRAME  # 22 frames

    # Pixel rise at apex — maps to ~25 inches jump
    APEX_RISE_PX = 180.0 + rng.uniform(-15, 15)

    frames: list[PoseFrame] = []

    for i in range(TOTAL_FRAMES):
        t_ms = (i / fps) * 1000.0
        phase_offset = 0.0  # vertical body shift in pixels (up = negative)
        crouch_depth = 0.0  # how deep the crouch is (down = positive)
        arm_swing = 0.0     # arms raised (negative = arms going up)
        knee_bend = 0.0     # extra knee bend (down = positive)

        if i < 15:
            # Standing still
            pass

        elif i < TAKEOFF_FRAME:
            # Approach and crouch/load
            t_phase = (i - 15) / (TAKEOFF_FRAME - 15)
            crouch_depth = math.sin(t_phase * math.pi) * 30.0
            arm_swing = -t_phase * 60.0  # arms swing back then forward
            knee_bend = math.sin(t_phase * math.pi) * 25.0

        elif TAKEOFF_FRAME <= i < LANDING_FRAME:
            # Flight arc — parabolic
            t_flight = (i - TAKEOFF_FRAME) / FLIGHT_FRAMES
            phase_offset = -APEX_RISE_PX * math.sin(t_flight * math.pi)
            arm_swing = -80.0 * (1.0 - abs(2 * t_flight - 1))  # arms up at apex

        else:
            # Landing and recovery
            t_land = min((i - LANDING_FRAME) / 6.0, 1.0)
            crouch_depth = (1.0 - t_land) * 20.0
            knee_bend = (1.0 - t_land) * 20.0

        # Build base standing pose, then apply offsets
        base = _build_standing_pose(cx, GROUND_Y + crouch_depth, SCALE)

        # Apply vertical body shift (flight) and small noise
        noise_scale = 2.0
        kp = {}
        for name, (x, y, conf) in base.items():
            nx = x + rng.uniform(-noise_scale, noise_scale)
            ny = y + phase_offset + rng.uniform(-noise_scale, noise_scale)

            # Arm swing adjustments
            if "wrist" in name or "elbow" in name:
                ny += arm_swing
            # Knee bend
            if "knee" in name or "ankle" in name:
                ny += knee_bend

            kp[name] = (float(np.clip(nx, 0, W)), float(np.clip(ny, 0, H)), conf)

        ankle_y = (kp["left_ankle"][1] + kp["right_ankle"][1]) / 2
        x1 = cx - 60
        x2 = cx + 60
        y1 = kp["nose"][1] - 10
        y2 = ankle_y + 5

        frames.append(PoseFrame(
            frame_idx=i,
            timestamp_ms=t_ms,
            keypoints=kp,
            bbox=(float(x1), float(y1), float(x2), float(y2)),
            has_object_in_hands=False,
        ))

    return frames


class PoseExtractor:
    """
    Attempts to use YOLOv8-pose. Falls back to mock data generator if not installed.
    """

    def __init__(self, model_path: str = "yolov8x-pose.pt"):
        self._yolo = None
        try:
            from ultralytics import YOLO
            self._yolo = YOLO(model_path)
            self._obj_model = YOLO("yolov8n.pt")
        except Exception:
            pass  # Will use mock mode

    @property
    def using_mock(self) -> bool:
        return self._yolo is None

    def extract_all_frames(self, video_path: str) -> list[PoseFrame]:
        if self._yolo is None:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            # Use a seed derived from video file size for variety
            import os
            seed = int(os.path.getsize(video_path)) % 10000
            return generate_mock_jump_frames(video_path, fps, seed=seed)

        # Real YOLO path
        return self._extract_with_yolo(video_path)

    def _extract_with_yolo(self, video_path: str) -> list[PoseFrame]:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            pose_result = self._yolo(frame, verbose=False)[0]
            obj_result = self._obj_model(frame, verbose=False, classes=[32, 37])
            has_object = len(obj_result.boxes) > 0

            if pose_result.keypoints is not None and len(pose_result.keypoints) > 0:
                kpts_data = self._select_primary_person(pose_result)
                if kpts_data is not None:
                    keypoints = {}
                    for i, name in enumerate(KEYPOINT_NAMES):
                        x, y, conf = kpts_data[i]
                        keypoints[name] = (float(x), float(y), float(conf))

                    bbox = pose_result.boxes.xyxy[0].tolist() if pose_result.boxes else (0, 0, 0, 0)
                    frames.append(PoseFrame(
                        frame_idx=frame_idx,
                        timestamp_ms=(frame_idx / fps) * 1000,
                        keypoints=keypoints,
                        bbox=tuple(bbox),
                        has_object_in_hands=has_object,
                    ))
            frame_idx += 1

        cap.release()
        return frames

    def _select_primary_person(self, result):
        if result.keypoints is None or len(result.keypoints.data) == 0:
            return None
        if len(result.keypoints.data) == 1:
            return result.keypoints.data[0].cpu().numpy()
        boxes = result.boxes.xyxy.cpu().numpy()
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        best_idx = int(np.argmax(areas))
        return result.keypoints.data[best_idx].cpu().numpy()
