"""
Pydantic-схемы для использования.
"""
from pydantic import BaseModel
from datetime import date
from typing import Optional


class UsageInfo(BaseModel):
    """Информация об использовании."""
    user_id: int
    analyses_count: int
    dynamics_count: int
    period_start: date
    period_end: Optional[date] = None

    class Config:
        from_attributes = True


class UsageLimits(BaseModel):
    """Лимиты использования."""
    max_analyses_per_month: int = 10
    max_diary_entries_free: int = 30