from pydantic import BaseModel
from typing import Any


class AnalysisResult(BaseModel):
    job_id: str
    user_id: str
    filename: str
    jump_height_inches: float
    jump_height_cm: float
    flight_time_ms: float
    confidence: float
    scorecard: dict[str, Any]
    biomechanics: dict[str, Any]
    claude_report: str
    pose_frames_sample: list[dict]  # Subset of frames for frontend visualization
    jump_event: dict[str, Any]
    video_metadata: dict[str, Any]
    created_at: str
