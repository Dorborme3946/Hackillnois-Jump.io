"""In-memory storage for prototype (replaces Supabase/PostgreSQL)."""
from typing import Dict, List, Any

# job_id -> job dict
jobs: Dict[str, Dict[str, Any]] = {}

# job_id -> full analysis result dict
results: Dict[str, Dict[str, Any]] = {}

# user_id -> list of job_ids (most recent last)
user_jobs: Dict[str, List[str]] = {}


def get_job(job_id: str) -> Dict[str, Any] | None:
    return jobs.get(job_id)


def set_job(job_id: str, data: Dict[str, Any]) -> None:
    jobs[job_id] = data


def get_result(job_id: str) -> Dict[str, Any] | None:
    return results.get(job_id)


def set_result(job_id: str, data: Dict[str, Any]) -> None:
    results[job_id] = data


def get_user_jobs(user_id: str) -> List[Dict[str, Any]]:
    job_ids = user_jobs.get(user_id, [])
    return [jobs[jid] for jid in job_ids if jid in jobs]


def add_user_job(user_id: str, job_id: str) -> None:
    if user_id not in user_jobs:
        user_jobs[user_id] = []
    user_jobs[user_id].append(job_id)
