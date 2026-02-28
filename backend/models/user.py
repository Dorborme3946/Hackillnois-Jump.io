from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    user_id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    created_at: str
    total_jumps: int = 0
    best_height_inches: float = 0.0
    best_overall_score: int = 0
