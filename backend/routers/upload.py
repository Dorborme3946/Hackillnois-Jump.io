"""
POST /api/upload — Accept video file, create a job, kick off analysis pipeline.
"""

import os
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, BackgroundTasks, Depends

from config import get_settings
from models.job import JobStatus
import storage
from validators.video_validator import VideoValidator
from cv.pose_extractor import PoseExtractor
from cv.jump_height_calculator import JumpHeightCalculator
from cv.biomechanics_analyzer import BiomechanicsAnalyzer
from scoring.scorer import compute_scorecard
from ai.claude_analyzer import generate_jump_report
from memory.supermemory_client import SupermemoryClient

router = APIRouter()
validator = VideoValidator()


@router.post("/upload", response_model=JobStatus)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(default="anonymous"),
    settings=Depends(get_settings),
):
    """Upload a video file and queue it for jump analysis."""
    # Basic file checks
    suffix = Path(file.filename or "video.mp4").suffix.lower()
    if suffix not in VideoValidator.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{suffix}'. Supported: {VideoValidator.SUPPORTED_FORMATS}",
        )

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    os.makedirs(settings.upload_dir, exist_ok=True)
    save_path = os.path.join(settings.upload_dir, f"{job_id}{suffix}")

    # Stream file to disk
    async with aiofiles.open(save_path, "wb") as f:
        content = await file.read()
        if len(content) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large.")
        await f.write(content)

    # Create job record
    job = {
        "job_id": job_id,
        "status": "pending",
        "step": "queued",
        "created_at": now,
        "updated_at": now,
        "user_id": user_id,
        "filename": file.filename or "video.mp4",
        "video_path": save_path,
        "error": None,
    }
    storage.set_job(job_id, job)
    storage.add_user_job(user_id, job_id)

    # Run analysis in background
    background_tasks.add_task(
        _run_analysis_pipeline, job_id, save_path, user_id, file.filename or "video.mp4", settings
    )

    return JobStatus(**{k: v for k, v in job.items() if k != "video_path"})


async def _run_analysis_pipeline(job_id: str, video_path: str, user_id: str, filename: str, settings):
    """Full analysis pipeline: validate → pose → height → biomechanics → score → Claude → memory."""

    def _update(status: str, step: str, error: str | None = None):
        now = datetime.now(timezone.utc).isoformat()
        job = storage.get_job(job_id) or {}
        job.update({"status": status, "step": step, "updated_at": now, "error": error})
        storage.set_job(job_id, job)

    try:
        # Step 1: Validate
        _update("processing", "validating")
        validation = await asyncio.get_event_loop().run_in_executor(
            None, validator.validate, video_path
        )
        if not validation.is_valid:
            _update("failed", "validation_failed", "; ".join(validation.errors))
            return

        video_meta = {
            "width": validation.width,
            "height": validation.height,
            "fps": validation.fps,
            "frame_count": validation.frame_count,
            "duration_seconds": validation.duration_seconds,
            "warnings": validation.warnings,
        }

        # Step 2: Pose extraction
        _update("processing", "extracting_pose")
        pose_extractor = PoseExtractor()
        pose_frames = await asyncio.get_event_loop().run_in_executor(
            None, pose_extractor.extract_all_frames, video_path
        )

        if not pose_frames:
            _update("failed", "pose_extraction_failed", "No human pose detected in video.")
            return

        # Step 3: Jump height calculation
        _update("processing", "calculating_height")
        calc = JumpHeightCalculator()
        jump_events = await asyncio.get_event_loop().run_in_executor(
            None, calc.calculate, pose_frames, validation.fps
        )
        best_jump = calc.get_best_jump(jump_events)

        if best_jump is None:
            # No clear flight phase — use a graceful zero result
            from cv.jump_height_calculator import JumpEvent
            best_jump = JumpEvent(
                takeoff_frame=0, takeoff_ms=0.0,
                landing_frame=len(pose_frames) - 1,
                landing_ms=pose_frames[-1].timestamp_ms if pose_frames else 0.0,
                flight_time_ms=0.0, height_inches=0.0,
                height_cm=0.0, confidence=0.0,
            )

        # Step 4: Biomechanics analysis
        _update("processing", "analyzing_biomechanics")
        bio_analyzer = BiomechanicsAnalyzer()
        biomechanics_report = await asyncio.get_event_loop().run_in_executor(
            None, bio_analyzer.analyze, pose_frames, best_jump, validation.fps
        )
        biomechanics_dict = {
            "penultimate_step_detected": biomechanics_report.penultimate_step_detected,
            "penultimate_step_quality": biomechanics_report.penultimate_step_quality,
            "approach_velocity": biomechanics_report.approach_velocity,
            "horizontal_momentum_utilized": biomechanics_report.horizontal_momentum_utilized,
            "heel_plant_detected": biomechanics_report.heel_plant_detected,
            "heel_to_toe_transition": biomechanics_report.heel_to_toe_transition,
            "knee_bend_angle_at_takeoff": biomechanics_report.knee_bend_angle_at_takeoff,
            "hip_flexion_at_takeoff": biomechanics_report.hip_flexion_at_takeoff,
            "arm_swing_contribution": biomechanics_report.arm_swing_contribution,
            "body_alignment_airborne": biomechanics_report.body_alignment_airborne,
            "peak_hip_height_normalized": biomechanics_report.peak_hip_height_normalized,
            "landing_symmetry": biomechanics_report.landing_symmetry,
            "soft_landing_score": biomechanics_report.soft_landing_score,
            "elite_similarity_score": biomechanics_report.elite_similarity_score,
        }

        # Step 5: Scoring
        _update("processing", "scoring")
        scorecard = compute_scorecard(
            jump_height_inches=best_jump.height_inches,
            bio=biomechanics_report,
            elite_similarity=biomechanics_report.elite_similarity_score,
        )
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

        # Step 6: Retrieve Supermemory history
        _update("processing", "fetching_history")
        mem_client = SupermemoryClient(api_key=settings.supermemory_api_key)
        user_history = await mem_client.retrieve_user_history(user_id, limit=5)

        # Step 7: Claude AI report
        _update("processing", "generating_report")
        claude_report = await asyncio.get_event_loop().run_in_executor(
            None,
            generate_jump_report,
            scorecard_dict,
            biomechanics_dict,
            best_jump.height_inches,
            user_history,
            settings.anthropic_api_key,
        )

        # Step 8: Store in Supermemory
        _update("processing", "storing_memory")
        await mem_client.store_jump_analysis(
            user_id=user_id,
            job_id=job_id,
            scorecard=scorecard_dict,
            biomechanics=biomechanics_dict,
            claude_report=claude_report,
            jump_height_inches=best_jump.height_inches,
            video_metadata=video_meta,
        )

        # Build pose frames sample (every 5th frame, max 60)
        step = max(1, len(pose_frames) // 60)
        sample_frames = []
        for f in pose_frames[::step][:60]:
            sample_frames.append({
                "frame_idx": f.frame_idx,
                "timestamp_ms": f.timestamp_ms,
                "keypoints": {k: list(v) for k, v in f.keypoints.items()},
            })

        now = datetime.now(timezone.utc).isoformat()
        result = {
            "job_id": job_id,
            "user_id": user_id,
            "filename": filename,
            "jump_height_inches": best_jump.height_inches,
            "jump_height_cm": best_jump.height_cm,
            "flight_time_ms": best_jump.flight_time_ms,
            "confidence": best_jump.confidence,
            "scorecard": scorecard_dict,
            "biomechanics": biomechanics_dict,
            "claude_report": claude_report,
            "pose_frames_sample": sample_frames,
            "jump_event": {
                "takeoff_frame": best_jump.takeoff_frame,
                "takeoff_ms": best_jump.takeoff_ms,
                "landing_frame": best_jump.landing_frame,
                "landing_ms": best_jump.landing_ms,
                "flight_time_ms": best_jump.flight_time_ms,
                "height_inches": best_jump.height_inches,
                "height_cm": best_jump.height_cm,
                "confidence": best_jump.confidence,
            },
            "video_metadata": video_meta,
            "created_at": now,
        }
        storage.set_result(job_id, result)
        _update("done", "complete")

    except Exception as exc:
        _update("failed", "pipeline_error", str(exc))
        raise
