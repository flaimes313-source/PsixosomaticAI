"""
Pydantic-схемы для платежей.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PaymentCreate(BaseModel):
    """Создание платежа."""
    user_id: int
    amount: Decimal = Field(..., description="Сумма")
    currency: str = "RUB"
    plan: str = "pro"
    duration_days: int = 30
    description: Optional[str] = None
    idempotence_key: Optional[str] = None
    subscription_id: Optional[int] = None
    metadata: Optional[dict] = None


class PaymentInfo(BaseModel):
    """Информация о платеже."""
    id: int
    user_id: int
    status: PaymentStatus
    amount: Decimal
    currency: str
    plan: str
    duration_days: int
    description: Optional[str] = None
    provider_payment_id: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    """Ответ при создании платежа."""
    payment_id: int
    status: PaymentStatus
    amount: Decimal
    currency: str
    confirmation_url: Optional[str] = None
    message: str


class YooKassaWebhookData(BaseModel):
    """Данные из webhook ЮKassa."""
    event: str
    object: dict  # payment object