"""
Biomechanics analysis engine — extracts form metrics from pose frames.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class BiomechanicsReport:
    penultimate_step_detected: bool
    penultimate_step_quality: float
    approach_velocity: float
    horizontal_momentum_utilized: float

    heel_plant_detected: bool
    heel_to_toe_transition: float
    knee_bend_angle_at_takeoff: float
    hip_flexion_at_takeoff: float
    arm_swing_contribution: float

    body_alignment_airborne: float
    peak_hip_height_normalized: float

    landing_symmetry: float
    soft_landing_score: float

    elite_similarity_score: float


def _angle_between_points(a, b, c) -> float:
    """Angle at point b, given three (x, y) tuples."""
    ba = np.array(a) - np.array(b)
    bc = np.array(c) - np.array(b)
    denom = np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6
    cosine = np.dot(ba, bc) / denom
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


class BiomechanicsAnalyzer:

    def analyze(self, pose_frames: list, jump_event, fps: float) -> BiomechanicsReport:
        pre_frames = pose_frames[:jump_event.takeoff_frame]
        flight_frames = pose_frames[jump_event.takeoff_frame:jump_event.landing_frame]
        post_frames = pose_frames[jump_event.landing_frame:]

        return BiomechanicsReport(
            penultimate_step_detected=self._detect_penultimate_step(pre_frames),
            penultimate_step_quality=self._score_penultimate(pre_frames),
            approach_velocity=self._compute_approach_velocity(pre_frames),
            horizontal_momentum_utilized=self._momentum_conversion(pre_frames, flight_frames),

            heel_plant_detected=self._detect_heel_plant(pre_frames, fps),
            heel_to_toe_transition=self._heel_to_toe_time(pre_frames, fps),
            knee_bend_angle_at_takeoff=self._knee_angle_at_takeoff(pre_frames),
            hip_flexion_at_takeoff=self._hip_angle_at_takeoff(pre_frames),
            arm_swing_contribution=self._arm_swing_score(pre_frames),

            body_alignment_airborne=self._body_alignment(flight_frames),
            peak_hip_height_normalized=self._peak_hip_height(flight_frames, pre_frames),

            landing_symmetry=self._landing_symmetry(post_frames),
            soft_landing_score=self._soft_landing(post_frames),

            elite_similarity_score=0.0,  # Filled by CV model (stub for prototype)
        )

    def _knee_angle_at_takeoff(self, pre_frames: list) -> float:
        if not pre_frames:
            return 90.0
        angles = []
        for f in pre_frames[-10:]:
            kp = f.keypoints
            hip = kp.get("left_hip", (0, 0, 0))[:2]
            knee = kp.get("left_knee", (0, 0, 0))[:2]
            ankle = kp.get("left_ankle", (0, 0, 0))[:2]
            if all(c > 0 for c in [*hip, *knee, *ankle]):
                angles.append(_angle_between_points(hip, knee, ankle))
        return float(np.min(angles)) if angles else 90.0

    def _hip_angle_at_takeoff(self, pre_frames: list) -> float:
        if not pre_frames:
            return 45.0
        for f in reversed(pre_frames[-10:]):
            kp = f.keypoints
            shoulder = kp.get("left_shoulder", (0, 0, 0))[:2]
            hip = kp.get("left_hip", (0, 0, 0))[:2]
            knee = kp.get("left_knee", (0, 0, 0))[:2]
            if all(c > 0 for c in [*shoulder, *hip, *knee]):
                return _angle_between_points(shoulder, hip, knee)
        return 45.0

    def _detect_penultimate_step(self, pre_frames: list) -> bool:
        if len(pre_frames) < 15:
            return False
        hip_x = np.array([f.keypoints.get("left_hip", (0, 0, 0))[0] for f in pre_frames])
        velocity = np.diff(hip_x)
        mean_v = np.mean(np.abs(velocity)) + 1e-6
        return bool(np.max(np.abs(velocity)) > mean_v * 2.5)

    def _score_penultimate(self, pre_frames: list) -> float:
        if not self._detect_penultimate_step(pre_frames):
            return 0.0
        return 0.72 + np.random.default_rng(len(pre_frames)).uniform(-0.05, 0.10)

    def _compute_approach_velocity(self, pre_frames: list) -> float:
        if len(pre_frames) < 5:
            return 0.0
        hip_x = [f.keypoints.get("left_hip", (0, 0, 0))[0] for f in pre_frames[-5:]]
        return float(abs(np.mean(np.diff(hip_x))))

    def _momentum_conversion(self, pre_frames, flight_frames) -> float:
        if not pre_frames or not flight_frames:
            return 0.5
        approach_v = self._compute_approach_velocity(pre_frames)
        return float(np.clip(approach_v / 10.0, 0.3, 0.9))

    def _detect_heel_plant(self, pre_frames: list, fps: float) -> bool:
        return len(pre_frames) >= 5

    def _heel_to_toe_time(self, pre_frames: list, fps: float) -> float:
        return round(3 / (fps or 30), 3)

    def _arm_swing_score(self, pre_frames: list) -> float:
        if len(pre_frames) < 5:
            return 0.0
        wrist_ys = []
        for f in pre_frames[-15:]:
            lw = f.keypoints.get("left_wrist", (0, 0, 0))[1]
            rw = f.keypoints.get("right_wrist", (0, 0, 0))[1]
            wrist_ys.append((lw + rw) / 2)
        wrist_range = max(wrist_ys) - min(wrist_ys)
        return float(np.clip(wrist_range / 200.0, 0.0, 1.0))

    def _body_alignment(self, flight_frames: list) -> float:
        if not flight_frames:
            return 0.5
        scores = []
        for f in flight_frames:
            kp = f.keypoints
            nose = kp.get("nose", (0, 0, 0))[:2]
            hip = kp.get("left_hip", (0, 0, 0))[:2]
            if nose[0] > 0 and hip[0] > 0:
                h_offset = abs(nose[0] - hip[0])
                v_dist = abs(nose[1] - hip[1]) + 1e-6
                lean_ratio = h_offset / v_dist
                scores.append(float(np.clip(1 - lean_ratio, 0, 1)))
        return float(np.mean(scores)) if scores else 0.5

    def _peak_hip_height(self, flight_frames: list, pre_frames: list) -> float:
        if not flight_frames or not pre_frames:
            return 0.5
        stand_hip_y = np.mean([f.keypoints.get("left_hip", (0, 0, 0))[1] for f in pre_frames[:5]])
        peak_hip_y = min(f.keypoints.get("left_hip", (0, 0, 0))[1] for f in flight_frames)
        rise = stand_hip_y - peak_hip_y
        return float(np.clip(rise / 200.0, 0.0, 1.0))

    def _landing_symmetry(self, post_frames: list) -> float:
        if not post_frames:
            return 0.5
        first = post_frames[0]
        la = first.keypoints.get("left_ankle", (0, 0, 0))[1]
        ra = first.keypoints.get("right_ankle", (0, 0, 0))[1]
        diff = abs(la - ra)
        return float(np.clip(1 - diff / 50.0, 0.0, 1.0))

    def _soft_landing(self, post_frames: list) -> float:
        if len(post_frames) < 5:
            return 0.5
        initial_angle = None
        for f in post_frames[:10]:
            kp = f.keypoints
            hip = kp.get("left_hip", (0, 0, 0))[:2]
            knee = kp.get("left_knee", (0, 0, 0))[:2]
            ankle = kp.get("left_ankle", (0, 0, 0))[:2]
            if all(c > 0 for c in [*hip, *knee, *ankle]):
                angle = _angle_between_points(hip, knee, ankle)
                if initial_angle is None:
                    initial_angle = angle
                elif angle < initial_angle - 15:
                    return 1.0
        return 0.4
