"""
Flight-time based jump height calculator.
Formula: h = g * (t_flight / 2)^2 / 2
"""

import numpy as np
from dataclasses import dataclass

try:
    from scipy.signal import savgol_filter
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@dataclass
class JumpEvent:
    takeoff_frame: int
    takeoff_ms: float
    landing_frame: int
    landing_ms: float
    flight_time_ms: float
    height_inches: float
    height_cm: float
    confidence: float


GRAVITY = 9.81  # m/s²
MIN_FLIGHT_MS = 100
MAX_FLIGHT_MS = 1200


class JumpHeightCalculator:

    def calculate(self, pose_frames: list, fps: float) -> list[JumpEvent]:
        if not pose_frames:
            return []

        timestamps = [f.timestamp_ms for f in pose_frames]
        left_y = np.array([f.keypoints.get("left_ankle", (0, 0, 0))[1] for f in pose_frames])
        right_y = np.array([f.keypoints.get("right_ankle", (0, 0, 0))[1] for f in pose_frames])

        if HAS_SCIPY and len(left_y) >= 11:
            window = min(11, len(left_y) - (1 if len(left_y) % 2 == 0 else 0))
            if window >= 5 and window % 2 == 1:
                left_y = savgol_filter(left_y, window, 3)
                right_y = savgol_filter(right_y, window, 3)

        avg_ankle_y = (left_y + right_y) / 2
        ground_level = self._estimate_ground_level(avg_ankle_y)
        return self._detect_flight_segments(avg_ankle_y, timestamps, ground_level, fps)

    def _estimate_ground_level(self, ankle_y: np.ndarray) -> float:
        hist, bin_edges = np.histogram(ankle_y, bins=min(50, len(ankle_y)))
        peak_bin = int(np.argmax(hist))
        return float((bin_edges[peak_bin] + bin_edges[peak_bin + 1]) / 2)

    def _detect_flight_segments(self, avg_y, timestamps, ground_level, fps) -> list[JumpEvent]:
        events = []
        LIFTOFF_THRESHOLD = 0.04  # 4% above ground

        safe_ground = ground_level if abs(ground_level) > 1e-6 else 1.0
        normalized = (ground_level - avg_y) / abs(safe_ground)

        in_flight = False
        liftoff_idx = None

        for i in range(len(normalized)):
            is_airborne = normalized[i] > LIFTOFF_THRESHOLD

            if is_airborne and not in_flight:
                in_flight = True
                liftoff_idx = i
            elif not is_airborne and in_flight:
                in_flight = False
                landing_idx = i
                flight_ms = timestamps[landing_idx] - timestamps[liftoff_idx]

                if MIN_FLIGHT_MS <= flight_ms <= MAX_FLIGHT_MS:
                    height_m = GRAVITY * ((flight_ms / 1000) / 2) ** 2 / 2
                    height_inches = height_m * 39.3701
                    height_cm = height_m * 100

                    events.append(JumpEvent(
                        takeoff_frame=liftoff_idx,
                        takeoff_ms=timestamps[liftoff_idx],
                        landing_frame=landing_idx,
                        landing_ms=timestamps[landing_idx],
                        flight_time_ms=round(flight_ms, 1),
                        height_inches=round(height_inches, 1),
                        height_cm=round(height_cm, 1),
                        confidence=self._compute_confidence(normalized[liftoff_idx:landing_idx]),
                    ))

        return events

    def _compute_confidence(self, segment: np.ndarray) -> float:
        if len(segment) < 3:
            return 0.5
        mid = len(segment) // 2
        first_half_max = float(np.max(segment[:mid]))
        second_half_max = float(np.max(segment[mid:]))
        symmetry = 1 - abs(first_half_max - second_half_max) / (first_half_max + 1e-6)
        return float(np.clip(symmetry, 0.0, 1.0))

    def get_best_jump(self, events: list[JumpEvent]) -> JumpEvent | None:
        if not events:
            return None
        return max(events, key=lambda e: e.height_inches)
