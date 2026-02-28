"""
Modal GPU worker — jump height calculation, biomechanics analysis, and scoring.
Runs CPU-only but benefits from Modal's isolated environment and parallelism.
"""

import modal
from modal_workers.app import app, jumpai_image


@app.function(
    image=jumpai_image,
    timeout=120,
    retries=1,
)
def score_jump_remote(frames_data: list, fps: float) -> dict:
    """
    Given extracted pose frames, compute height, biomechanics, and scorecard.

    Args:
        frames_data: List of frame dicts as returned by extract_pose_remote.
        fps: Video frame rate.

    Returns:
        dict with keys: jump_event, biomechanics, scorecard
    """
    import sys
    sys.path.insert(0, "/root/backend")

    from cv.pose_extractor import PoseFrame
    from cv.jump_height_calculator import JumpHeightCalculator, JumpEvent
    from cv.biomechanics_analyzer import BiomechanicsAnalyzer
    from scoring.scorer import compute_scorecard

    # Reconstruct PoseFrame objects from dict data
    pose_frames = []
    for fd in frames_data:
        kp_raw = fd.get("keypoints", {})
        keypoints = {}
        for name, vals in kp_raw.items():
            keypoints[name] = tuple(vals)
        pose_frames.append(PoseFrame(
            frame_idx=fd["frame_idx"],
            timestamp_ms=fd["timestamp_ms"],
            keypoints=keypoints,
            bbox=(0.0, 0.0, 0.0, 0.0),
            has_object_in_hands=fd.get("has_object_in_hands", False),
        ))

    # Height calculation
    calc = JumpHeightCalculator()
    jump_events = calc.calculate(pose_frames, fps)
    best_jump = calc.get_best_jump(jump_events)

    if best_jump is None:
        best_jump = JumpEvent(
            takeoff_frame=0, takeoff_ms=0.0,
            landing_frame=len(pose_frames) - 1,
            landing_ms=pose_frames[-1].timestamp_ms if pose_frames else 0.0,
            flight_time_ms=0.0, height_inches=0.0, height_cm=0.0, confidence=0.0,
        )

    # Biomechanics
    bio_analyzer = BiomechanicsAnalyzer()
    bio = bio_analyzer.analyze(pose_frames, best_jump, fps)

    bio_dict = {
        "penultimate_step_detected": bio.penultimate_step_detected,
        "penultimate_step_quality": bio.penultimate_step_quality,
        "approach_velocity": bio.approach_velocity,
        "horizontal_momentum_utilized": bio.horizontal_momentum_utilized,
        "heel_plant_detected": bio.heel_plant_detected,
        "heel_to_toe_transition": bio.heel_to_toe_transition,
        "knee_bend_angle_at_takeoff": bio.knee_bend_angle_at_takeoff,
        "hip_flexion_at_takeoff": bio.hip_flexion_at_takeoff,
        "arm_swing_contribution": bio.arm_swing_contribution,
        "body_alignment_airborne": bio.body_alignment_airborne,
        "peak_hip_height_normalized": bio.peak_hip_height_normalized,
        "landing_symmetry": bio.landing_symmetry,
        "soft_landing_score": bio.soft_landing_score,
        "elite_similarity_score": bio.elite_similarity_score,
    }

    scorecard = compute_scorecard(best_jump.height_inches, bio, bio.elite_similarity_score)
    scorecard_dict = {
        "jump_height_score": scorecard.jump_height_score,
        "arm_swing_score": scorecard.arm_swing_score,
        "knee_bend_score": scorecard.knee_bend_score,
        "penultimate_step_score": scorecard.penultimate_step_score,
        "heel_plant_score": scorecard.heel_plant_score,
        "hip_drive_score": scorecard.hip_drive_score,
        "body_alignment_score": scorecard.body_alignment_score,
        "landing_score": scorecard.landing_score,
        "elite_similarity_score": scorecard.elite_similarity_score,
        "overall_score": scorecard.overall_score,
    }

    jump_event_dict = {
        "takeoff_frame": best_jump.takeoff_frame,
        "takeoff_ms": best_jump.takeoff_ms,
        "landing_frame": best_jump.landing_frame,
        "landing_ms": best_jump.landing_ms,
        "flight_time_ms": best_jump.flight_time_ms,
        "height_inches": best_jump.height_inches,
        "height_cm": best_jump.height_cm,
        "confidence": best_jump.confidence,
    }

    return {
        "jump_event": jump_event_dict,
        "biomechanics": bio_dict,
        "scorecard": scorecard_dict,
    }
