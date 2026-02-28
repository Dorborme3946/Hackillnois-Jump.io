"""
Supermemory integration for long-term per-user jump history.
Falls back to in-memory store if API key not configured.
"""

import json
from datetime import datetime, timezone

# Fallback in-process store
_local_memory: dict[str, list[dict]] = {}

SUPERMEMORY_API = "https://api.supermemory.ai/v3"


class SupermemoryClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    @property
    def _use_local(self) -> bool:
        return not self.api_key

    async def store_jump_analysis(
        self,
        user_id: str,
        job_id: str,
        scorecard: dict,
        biomechanics: dict,
        claude_report: str,
        jump_height_inches: float,
        video_metadata: dict,
    ) -> str:
        if self._use_local:
            entry = {
                "id": job_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "jump_height_inches": jump_height_inches,
                "scorecard": scorecard,
                "biomechanics": biomechanics,
                "report_snippet": claude_report[:200],
            }
            _local_memory.setdefault(user_id, []).append(entry)
            return job_id

        import httpx
        content = f"""
JUMP ANALYSIS — {datetime.now(timezone.utc).isoformat()}
User: {user_id}
Jump ID: {job_id}
HEIGHT: {jump_height_inches:.1f} inches
OVERALL SCORE: {scorecard['overall_score']}/99
SCORES: {json.dumps(scorecard)}
BIOMECHANICS: {json.dumps(biomechanics, indent=2)}
COACHING REPORT:
{claude_report}
"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPERMEMORY_API}/memories",
                headers=self.headers,
                json={
                    "content": content,
                    "metadata": {
                        "userId": user_id,
                        "jumpId": job_id,
                        "type": "jump_analysis",
                        "heightInches": jump_height_inches,
                        "overallScore": scorecard["overall_score"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                },
                timeout=10.0,
            )
            return response.json().get("id", job_id)

    async def retrieve_user_history(self, user_id: str, limit: int = 10) -> list[dict]:
        if self._use_local:
            history = _local_memory.get(user_id, [])
            return history[-limit:]

        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPERMEMORY_API}/memories/search",
                headers=self.headers,
                params={
                    "q": f"jump analysis user:{user_id}",
                    "limit": limit,
                    "filters": json.dumps({"userId": user_id, "type": "jump_analysis"}),
                },
                timeout=10.0,
            )
            return response.json().get("results", [])
