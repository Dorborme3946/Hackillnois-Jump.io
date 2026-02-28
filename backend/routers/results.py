"""
GET /api/results/{job_id} — Retrieve full analysis result once job is done.
DELETE /api/videos/{job_id} — Delete video from storage.
"""

import os
from fastapi import APIRouter, HTTPException
from models.result import AnalysisResult
import storage

router = APIRouter()


@router.get("/results/{job_id}", response_model=AnalysisResult)
async def get_result(job_id: str):
    """Return the full analysis result for a completed job."""
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "done":
        raise HTTPException(
            status_code=202,
            detail=f"Job is not complete yet. Current status: {job['status']} / {job.get('step', '')}",
        )

    result = storage.get_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found.")
    return AnalysisResult(**result)


@router.delete("/videos/{job_id}")
async def delete_video(job_id: str):
    """Delete the uploaded video file from local storage."""
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    video_path = job.get("video_path", "")
    if video_path and os.path.exists(video_path):
        os.remove(video_path)
        return {"deleted": True, "job_id": job_id}
    return {"deleted": False, "reason": "File not found on disk."}
