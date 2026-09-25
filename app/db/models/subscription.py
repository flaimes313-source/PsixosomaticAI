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
    PRO_TRIAL = "pro_trial"   # пробный PRO на 3 дня


def _enum_values(enum_cls):
    """Возвращает список .value для использования в SQLAlchemy Enum."""
    return [e.value for e in enum_cls]


class Subscription(Base):
    """Модель подписки пользователя."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, unique=True, index=True)  # Telegram ID

    # ВАЖНО: values_callable заставляет SQLAlchemy использовать .value (нижний регистр),
    # а не .name. Без этого SQLAlchemy пытается вставить 'PRO_TRIAL' вместо 'pro_trial'
    # и падает с InvalidTextRepresentationError.
    plan = Column(
        SQLEnum(PlanType, values_callable=_enum_values),
        nullable=False,
        default=PlanType.FREE,
    )
    status = Column(
        SQLEnum(SubscriptionStatus, values_callable=_enum_values),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )

    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # NULL = бессрочно (или FREE)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self):
        return f"<Subscription user_id={self.user_id} plan={self.plan} status={self.status}>"