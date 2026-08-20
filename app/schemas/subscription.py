"""
Pydantic-схемы для подписки.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum


class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SubscriptionInfo(BaseModel):
    """Информация о подписке пользователя."""
    user_id: int
    plan: PlanType
    status: SubscriptionStatus
    started_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    """Создание подписки."""
    user_id: int
    plan: PlanType = PlanType.FREE
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    expires_at: Optional[datetime] = None