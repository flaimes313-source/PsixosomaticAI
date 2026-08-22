"""
Модель платежа.
"""
from sqlalchemy import Column, Integer, BigInteger, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.db.base import Base


class PaymentStatus(str, enum.Enum):
    """Статусы платежа."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Payment(Base):
    """Модель платежа."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram ID
    
    # Связь с подпиской (опционально)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    
    # Данные от провайдера
    provider = Column(String(50), default="yookassa", nullable=False)
    provider_payment_id = Column(String(100), nullable=True, index=True)  # ID от ЮKassa
    
    # Статус
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Сумма и валюта
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB", nullable=False)
    
    # Описание
    description = Column(String(255), nullable=True)
    
    # Данные тарифа
    plan = Column(String(20), nullable=False)  # 'pro'
    duration_days = Column(Integer, nullable=False)  # 30
    
    # Ключ идемпотентности
    idempotence_key = Column(String(100), nullable=True, unique=True, index=True)
    
    # Метаданные (JSON) — переименовано, чтобы не конфликтовать с SQLAlchemy
    payment_metadata = Column(JSON, nullable=True)  # ← ИСПРАВЛЕНО: было metadata
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Payment id={self.id} user_id={self.user_id} status={self.status} amount={self.amount}>"