from pydantic import BaseModel
from typing import Literal
from datetime import datetime


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "done", "failed"]
    step: str = ""
    created_at: str
    updated_at: str
    user_id: str
    filename: str
    error: str | None = None
