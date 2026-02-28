"""
GET /api/users/{uid}/history  — Paginated jump history for a user.
GET /api/users/{uid}/stats    — Aggregate progress stats.
"""

from fastapi import APIRouter, Query, Depends
from config import get_settings
from memory.supermemory_client import SupermemoryClient
import storage

router = APIRouter()


@router.get("/users/{user_id}/history")
async def get_user_history(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    settings=Depends(get_settings),
):
    """Return paginated list of past jump analyses for a user."""
    mem_client = SupermemoryClient(api_key=settings.supermemory_api_key)
    history = await mem_client.retrieve_user_history(user_id, limit=limit)
    return {"user_id": user_id, "count": len(history), "results": history}


@router.get("/users/{user_id}/stats")
async def get_user_stats(user_id: str, settings=Depends(get_settings)):
    """Return aggregate progress statistics derived from jump history."""
    mem_client = SupermemoryClient(api_key=settings.supermemory_api_key)
    history = await mem_client.retrieve_user_history(user_id, limit=50)

    if not history:
        return {"user_id": user_id, "total_jumps": 0, "stats": {}}

    heights = [h.get("jump_height_inches", 0) for h in history if isinstance(h, dict)]
    scores = [h.get("scorecard", {}).get("overall_score", 0) for h in history if isinstance(h, dict)]

    stats = {
        "total_jumps": len(history),
        "best_height_inches": max(heights) if heights else 0,
        "avg_height_inches": round(sum(heights) / len(heights), 1) if heights else 0,
        "best_overall_score": max(scores) if scores else 0,
        "avg_overall_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "recent_heights": heights[-10:],
        "recent_scores": scores[-10:],
    }
    return {"user_id": user_id, "stats": stats}
