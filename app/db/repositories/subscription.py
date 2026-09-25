"""
Репозиторий для работы с подписками.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.db.models.subscription import (
    Subscription,
    PlanType,
    SubscriptionStatus,
)
from app.utils.logging import logger


class SubscriptionRepository:
    """Репозиторий для управления подписками."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== ПОЛУЧЕНИЕ ====================

    async def get_by_user_id(self, user_id: int) -> Optional[Subscription]:
        """Получить подписку по telegram_id (любую — активную или нет)."""
        result = await self.session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """
        Получить активную подписку (ACTIVE или PRO_TRIAL) с неистёкшим сроком.
        """
        now = datetime.now(ZoneInfo("UTC"))
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.PRO_TRIAL,
                ]),
                Subscription.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def get_expired_active_subscriptions(self) -> List[Subscription]:
        """
        Получить все подписки со статусом ACTIVE/PRO_TRIAL, у которых истёк срок.
        Нужно для фонового сервиса проверки.
        """
        now = datetime.now(ZoneInfo("UTC"))
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.PRO_TRIAL,
                ]),
                Subscription.expires_at.isnot(None),
                Subscription.expires_at < now,
            )
        )
        return list(result.scalars().all())

    # ==================== СОЗДАНИЕ / АКТИВАЦИЯ ====================

    async def activate_pro(
        self,
        user_id: int,
        duration_days: int = 30,
    ) -> Subscription:
        """
        Активировать платный PRO (после оплаты).
        """
        now = datetime.now(ZoneInfo("UTC"))
        expires_at = now + timedelta(days=duration_days)

        subscription = await self.get_by_user_id(user_id)

        if not subscription:
            subscription = Subscription(
                user_id=user_id,
                plan=PlanType.PRO,
                status=SubscriptionStatus.ACTIVE,
                started_at=now,
                expires_at=expires_at,
            )
            self.session.add(subscription)
        else:
            subscription.plan = PlanType.PRO
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.started_at = now
            subscription.expires_at = expires_at

        await self.session.commit()
        await self.session.refresh(subscription)
        logger.info(f"✅ PRO activated for user {user_id} until {expires_at}")
        return subscription

    async def create_or_update_trial(
        self,
        user_id: int,
        expires_at: datetime,
    ) -> Subscription:
        """
        Создать/обновить подписку со статусом PRO_TRIAL (3-дневный пробный PRO).
        Вызывается один раз — при первом «Описать состояние».
        """
        now = datetime.now(ZoneInfo("UTC"))

        subscription = await self.get_by_user_id(user_id)

        if not subscription:
            subscription = Subscription(
                user_id=user_id,
                plan=PlanType.PRO,
                status=SubscriptionStatus.PRO_TRIAL,
                started_at=now,
                expires_at=expires_at,
            )
            self.session.add(subscription)
            logger.info(f"🎁 Trial subscription created for user {user_id} until {expires_at}")
        else:
            subscription.plan = PlanType.PRO
            subscription.status = SubscriptionStatus.PRO_TRIAL
            subscription.started_at = now
            subscription.expires_at = expires_at
            logger.info(f"🎁 Trial subscription updated for user {user_id} until {expires_at}")

        await self.session.commit()
        await self.session.refresh(subscription)
        return subscription

    # ==================== ДЕАКТИВАЦИЯ / ИСТЕЧЕНИЕ ====================

    async def deactivate_pro(self, user_id: int) -> Optional[Subscription]:
        """Деактивировать PRO (вернуть FREE)."""
        subscription = await self.get_by_user_id(user_id)
        if not subscription:
            return None

        subscription.status = SubscriptionStatus.CANCELLED
        subscription.plan = PlanType.FREE
        await self.session.commit()
        await self.session.refresh(subscription)
        logger.info(f"⛔ PRO deactivated for user {user_id}")
        return subscription

    async def expire_subscription(self, user_id: int) -> Optional[Subscription]:
        """
        Перевести подписку в статус EXPIRED.
        Используется, когда истёк PRO_TRIAL или платный PRO.
        """
        subscription = await self.get_by_user_id(user_id)
        if not subscription:
            return None

        subscription.status = SubscriptionStatus.EXPIRED
        subscription.plan = PlanType.FREE
        await self.session.commit()
        await self.session.refresh(subscription)
        logger.info(f"⏰ Subscription expired for user {user_id}")
        return subscription