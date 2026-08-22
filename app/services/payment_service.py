"""
Сервис для управления платежами.
"""
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.repositories.payment import PaymentRepository
from app.db.repositories.subscription import SubscriptionRepository
from app.db.models.payment import PaymentStatus
from app.db.models.subscription import PlanType, SubscriptionStatus
from app.db.models.user import User
from app.services.yookassa_service import YooKassaService
from app.services.access_service import AccessService
from app.utils.logging import logger
from app.config import settings


class PaymentService:
    """Сервис для управления платежами."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.payment_repo = PaymentRepository(db_session)
        self.subscription_repo = SubscriptionRepository(db_session)
        self.yookassa = YooKassaService()
        self.access_service = AccessService(db_session)

    async def create_pro_payment(
        self,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Создать платёж для PRO.
        """
        # Проверяем, что пользователь существует
        result = await self.db_session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return {"success": False, "error": "Пользователь не найден"}

        # Проверяем текущую подписку
        subscription = await self.subscription_repo.get_by_user_id(user_id)
        
        amount = Decimal(str(settings.PRO_PRICE_RUB))
        currency = "RUB"
        duration_days = settings.PRO_DURATION_DAYS

        # Создаём ключ идемпотентности
        import uuid
        idempotence_key = str(uuid.uuid4())

        # Создаём платеж в БД
        payment = await self.payment_repo.create(
            user_id=user_id,
            amount=amount,
            currency=currency,
            plan="pro",
            duration_days=duration_days,
            description=f"Psychosomatic PRO — {duration_days} дней",
            idempotence_key=idempotence_key,
            subscription_id=subscription.id if subscription else None,
            payment_metadata={
                "user_id": str(user_id),
                "plan": "pro",
                "duration_days": str(duration_days),
                "payment_id": str(idempotence_key),
            },
        )

        # Создаём платеж в ЮKassa
        result = await self.yookassa.create_payment(
            amount=amount,
            currency=currency,
            description=f"Psychosomatic PRO — {duration_days} дней",
            return_url=settings.YOOKASSA_RETURN_URL,
            payment_metadata={
                "user_id": str(user_id),
                "plan": "pro",
                "duration_days": str(duration_days),
                "payment_internal_id": str(payment.id),
            },
            idempotence_key=idempotence_key,
        )

        if not result.get("success"):
            # Отмечаем платеж как неудачный
            await self.payment_repo.mark_failed(payment.id)
            return {
                "success": False,
                "error": result.get("error", "Ошибка при создании платежа"),
            }

        # Обновляем платеж с provider_payment_id
        provider_payment_id = result.get("payment_id")
        await self.payment_repo.update_status(
            payment.id,
            PaymentStatus.PENDING,
            provider_payment_id=provider_payment_id,
        )

        return {
            "success": True,
            "payment_id": payment.id,
            "provider_payment_id": provider_payment_id,
            "status": result.get("status"),
            "confirmation_url": result.get("confirmation_url"),
            "amount": amount,
            "currency": currency,
        }

    async def process_successful_webhook(
        self,
        provider_payment_id: str,
        event_data: dict,
    ) -> Dict[str, Any]:
        """
        Обработка успешного платежа от webhook.
        """
        # Находим платеж в БД
        payment = await self.payment_repo.get_by_provider_payment_id(provider_payment_id)
        if not payment:
            logger.warning(f"Payment not found: {provider_payment_id}")
            return {"success": False, "error": "Payment not found"}

        # Защита от повторной обработки
        if payment.status == PaymentStatus.SUCCEEDED:
            logger.info(f"Payment already processed: {provider_payment_id}")
            return {"success": True, "already_processed": True}

        # Проверяем платеж в ЮKassa
        yk_result = await self.yookassa.get_payment(provider_payment_id)
        if not yk_result.get("success"):
            logger.error(f"Failed to get payment from YooKassa: {provider_payment_id}")
            return {"success": False, "error": "Failed to get payment from YooKassa"}

        yk_data = yk_result.get("data", {})
        
        # Проверяем статус
        if yk_data.get("status") != "succeeded":
            logger.info(f"Payment not succeeded: {yk_data.get('status')}")
            return {"success": False, "error": f"Status: {yk_data.get('status')}"}

        # Проверяем сумму
        amount_data = yk_data.get("amount", {})
        yk_amount = Decimal(amount_data.get("value", "0"))
        if yk_amount != payment.amount:
            logger.error(f"Amount mismatch: {yk_amount} != {payment.amount}")
            return {"success": False, "error": "Amount mismatch"}

        # Проверяем валюту
        yk_currency = amount_data.get("currency", "")
        if yk_currency != payment.currency:
            logger.error(f"Currency mismatch: {yk_currency} != {payment.currency}")
            return {"success": False, "error": "Currency mismatch"}

        # Проверяем metadata
        yk_metadata = yk_data.get("metadata", {})
        if yk_metadata.get("plan") != "pro":
            logger.error(f"Plan mismatch: {yk_metadata.get('plan')} != pro")
            return {"success": False, "error": "Plan mismatch"}

        user_id = int(yk_metadata.get("user_id", 0))
        if user_id != payment.user_id:
            logger.error(f"User mismatch: {user_id} != {payment.user_id}")
            return {"success": False, "error": "User mismatch"}

        # ==================== АКТИВАЦИЯ PRO ====================
        # Используем транзакцию
        try:
            # Получаем текущую подписку
            subscription = await self.subscription_repo.get_by_user_id(user_id)
            
            # Определяем дату окончания
            now = datetime.now(ZoneInfo("UTC"))
            if subscription and subscription.plan == PlanType.PRO and subscription.expires_at:
                # Продлеваем с текущей даты окончания
                new_expires_at = subscription.expires_at + timedelta(days=payment.duration_days)
            else:
                # Новая подписка
                new_expires_at = now + timedelta(days=payment.duration_days)

            # Обновляем или создаём подписку
            if subscription:
                subscription.plan = PlanType.PRO
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.expires_at = new_expires_at
                subscription.started_at = now
                await self.db_session.commit()
                await self.db_session.refresh(subscription)
            else:
                subscription = await self.subscription_repo.activate_pro(
                    user_id=user_id,
                    duration_days=payment.duration_days,
                )

            # Отмечаем платеж как успешный
            await self.payment_repo.mark_succeeded(
                payment.id,
                provider_payment_id=provider_payment_id,
                paid_at=now,
                expires_at=new_expires_at,
            )

            logger.info(f"PRO activated for user {user_id} via payment {payment.id}")

            return {
                "success": True,
                "user_id": user_id,
                "expires_at": new_expires_at,
                "payment_id": payment.id,
            }

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error activating PRO: {e}")
            return {"success": False, "error": str(e)}

    async def get_user_payments(self, user_id: int, limit: int = 10) -> list:
        """Получить платежи пользователя."""
        return await self.payment_repo.get_user_payments(user_id, limit)

    async def get_payment_info(self, payment_id: int, user_id: int) -> Optional[dict]:
        """Получить информацию о платеже."""
        payment = await self.payment_repo.get_by_id(payment_id, user_id)
        if not payment:
            return None
        
        return {
            "id": payment.id,
            "status": payment.status.value if hasattr(payment.status, 'value') else payment.status,
            "amount": payment.amount,
            "currency": payment.currency,
            "plan": payment.plan,
            "duration_days": payment.duration_days,
            "description": payment.description,
            "created_at": payment.created_at,
            "paid_at": payment.paid_at,
            "expires_at": payment.expires_at,
        }