"""
GET /api/jobs/{job_id} — Poll job status.
"""

from fastapi import APIRouter, HTTPException
from models.job import JobStatus
import storage

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Return current status of a processing job."""
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatus(**{k: v for k, v in job.items() if k != "video_path"})
