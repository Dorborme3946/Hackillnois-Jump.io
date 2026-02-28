"""
0–99 scoring system for jump analysis metrics.
Weights from Section 9 of the spec.
"""

from dataclasses import dataclass

WEIGHTS = {
    "jump_height":       0.30,
    "arm_swing":         0.10,
    "knee_bend":         0.10,
    "penultimate_step":  0.10,
    "heel_plant":        0.05,
    "hip_drive":         0.10,
    "body_alignment":    0.05,
    "landing":           0.05,
    "elite_similarity":  0.15,
}

ELITE_JUMP_INCHES = 44.0  # ~44" = NBA elite


@dataclass
class JumpScorecard:
    jump_height_score: int
    arm_swing_score: int
    knee_bend_score: int
    penultimate_step_score: int
    heel_plant_score: int
    hip_drive_score: int
    body_alignment_score: int
    landing_score: int
    elite_similarity_score: int
    overall_score: int

    def to_dict(self) -> dict:
        return {
            "jump_height_score": self.jump_height_score,
            "arm_swing_score": self.arm_swing_score,
            "knee_bend_score": self.knee_bend_score,
            "penultimate_step_score": self.penultimate_step_score,
            "heel_plant_score": self.heel_plant_score,
            "hip_drive_score": self.hip_drive_score,
            "body_alignment_score": self.body_alignment_score,
            "landing_score": self.landing_score,
            "elite_similarity_score": self.elite_similarity_score,
            "overall_score": self.overall_score,
        }


def _scale(value: float, min_v: float, max_v: float) -> int:
    return int(min(99, max(0, (value - min_v) / (max_v - min_v + 1e-6) * 99)))


def _knee_bend_score(angle: float) -> int:
    optimal = 90.0
    deviation = abs(angle - optimal)
    return max(0, min(99, 99 - int(deviation * 1.5)))


def compute_scorecard(
    jump_height_inches: float,
    bio,  # BiomechanicsReport
    elite_similarity: float = 50.0,
) -> JumpScorecard:

    scores = {
        "jump_height":      _scale(jump_height_inches, 0, ELITE_JUMP_INCHES),
        "arm_swing":        int(bio.arm_swing_contribution * 99),
        "knee_bend":        _knee_bend_score(bio.knee_bend_angle_at_takeoff),
        "penultimate_step": int(bio.penultimate_step_quality * 99) if bio.penultimate_step_detected else 20,
        "heel_plant":       85 if bio.heel_plant_detected else 30,
        "hip_drive":        int(bio.peak_hip_height_normalized * 99),
        "body_alignment":   int(bio.body_alignment_airborne * 99),
        "landing":          int(bio.soft_landing_score * 99),
        "elite_similarity": int(elite_similarity),
    }

    overall = int(sum(scores[k] * WEIGHTS[k] for k in WEIGHTS))

    return JumpScorecard(
        jump_height_score=scores["jump_height"],
        arm_swing_score=scores["arm_swing"],
        knee_bend_score=scores["knee_bend"],
        penultimate_step_score=scores["penultimate_step"],
        heel_plant_score=scores["heel_plant"],
        hip_drive_score=scores["hip_drive"],
        body_alignment_score=scores["body_alignment"],
        landing_score=scores["landing"],
        elite_similarity_score=scores["elite_similarity"],
        overall_score=overall,
    )
