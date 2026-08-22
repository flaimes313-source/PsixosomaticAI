"""
Репозиторий для работы с платежами.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from app.db.models.payment import Payment, PaymentStatus
from app.utils.logging import logger


class PaymentRepository:
    """Репозиторий для управления платежами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        amount: Decimal,
        currency: str,
        plan: str,
        duration_days: int,
        description: Optional[str] = None,
        idempotence_key: Optional[str] = None,
        subscription_id: Optional[int] = None,
        payment_metadata: Optional[dict] = None,
    ) -> Payment:
        """Создать новый платеж."""
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            plan=plan,
            duration_days=duration_days,
            description=description,
            idempotence_key=idempotence_key,
            subscription_id=subscription_id,
            payment_metadata=payment_metadata,
            status=PaymentStatus.PENDING,
        )
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        
        logger.info(f"Payment created: id={payment.id}, user_id={user_id}, amount={amount}")
        return payment

    async def get_by_id(self, payment_id: int, user_id: Optional[int] = None) -> Optional[Payment]:
        """Получить платеж по ID."""
        stmt = select(Payment).where(Payment.id == payment_id)
        if user_id is not None:
            stmt = stmt.where(Payment.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_provider_payment_id(self, provider_payment_id: str) -> Optional[Payment]:
        """Получить платеж по ID провайдера."""
        result = await self.session.execute(
            select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotence_key(self, idempotence_key: str) -> Optional[Payment]:
        """Получить платеж по ключу идемпотентности."""
        result = await self.session.execute(
            select(Payment).where(Payment.idempotence_key == idempotence_key)
        )
        return result.scalar_one_or_none()

    async def get_user_payments(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Payment]:
        """Получить платежи пользователя."""
        result = await self.session.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(desc(Payment.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def update_status(
        self,
        payment_id: int,
        status: PaymentStatus,
        provider_payment_id: Optional[str] = None,
        paid_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ) -> Optional[Payment]:
        """Обновить статус платежа."""
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.status = status
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        if paid_at:
            payment.paid_at = paid_at
        if expires_at:
            payment.expires_at = expires_at
        payment.updated_at = func.now()
        
        await self.session.commit()
        await self.session.refresh(payment)
        
        logger.info(f"Payment {payment_id} status updated to {status}")
        return payment

    async def mark_succeeded(
        self,
        payment_id: int,
        provider_payment_id: str,
        paid_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ) -> Optional[Payment]:
        """Отметить платеж как успешный."""
        return await self.update_status(
            payment_id,
            PaymentStatus.SUCCEEDED,
            provider_payment_id=provider_payment_id,
            paid_at=paid_at or datetime.now(),
            expires_at=expires_at,
        )

    async def mark_cancelled(self, payment_id: int) -> Optional[Payment]:
        """Отметить платеж как отмененный."""
        return await self.update_status(payment_id, PaymentStatus.CANCELLED)

    async def mark_failed(self, payment_id: int) -> Optional[Payment]:
        """Отметить платеж как неудачный."""
        return await self.update_status(payment_id, PaymentStatus.FAILED)

    async def get_pending_payments(self, older_than_minutes: int = 5) -> List[Payment]:
        """Получить зависшие платежи."""
        from datetime import timedelta
        from zoneinfo import ZoneInfo
        
        cutoff = datetime.now(ZoneInfo("UTC")) - timedelta(minutes=older_than_minutes)
        result = await self.session.execute(
            select(Payment)
            .where(
                Payment.status == PaymentStatus.PENDING,
                Payment.created_at < cutoff
            )
            .order_by(Payment.created_at)
        )
        return result.scalars().all()