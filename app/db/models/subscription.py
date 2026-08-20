"""
Модель подписки пользователя.
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.db.base import Base


class PlanType(str, enum.Enum):
    """Типы тарифов."""
    FREE = "free"
    PRO = "pro"


class SubscriptionStatus(str, enum.Enum):
    """Статусы подписки."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Subscription(Base):
    """Модель подписки пользователя."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, unique=True, index=True)  # Telegram ID
    
    plan = Column(SQLEnum(PlanType), nullable=False, default=PlanType.FREE)
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # NULL = бессрочно (или FREE)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self):
        return f"<Subscription user_id={self.user_id} plan={self.plan} status={self.status}>"