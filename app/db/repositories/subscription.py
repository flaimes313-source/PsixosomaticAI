"""
Репозиторий для работы с подписками.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import Optional, List
from zoneinfo import ZoneInfo

from app.db.models.subscription import Subscription, PlanType, SubscriptionStatus
from app.utils.logging import logger


class SubscriptionRepository:
    """Репозиторий для управления подписками."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: int) -> Optional[Subscription]:
        """Получить подписку пользователя."""
        result = await self.session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """Получить активную подписку пользователя."""
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        return result.scalar_one_or_none()

    async def create_subscription(
        self,
        user_id: int,
        plan: PlanType = PlanType.FREE,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        expires_at: Optional[datetime] = None,
    ) -> Subscription:
        """Создать новую подписку."""
        subscription = Subscription(
            user_id=user_id,
            plan=plan,
            status=status,
            expires_at=expires_at,
        )
        self.session.add(subscription)
        await self.session.commit()
        await self.session.refresh(subscription)
        
        logger.info(f"Subscription created: user_id={user_id}, plan={plan}")
        return subscription

    async def get_or_create(self, user_id: int) -> Subscription:
        """Получить или создать подписку для пользователя."""
        subscription = await self.get_by_user_id(user_id)
        if not subscription:
            subscription = await self.create_subscription(user_id, PlanType.FREE)
        return subscription

    async def activate_pro(
        self,
        user_id: int,
        duration_days: int = 30,
    ) -> Optional[Subscription]:
        """Активировать PRO-подписку."""
        subscription = await self.get_by_user_id(user_id)
        if not subscription:
            subscription = await self.create_subscription(user_id, PlanType.FREE)
        
        subscription.plan = PlanType.PRO
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.started_at = func.now()
        subscription.expires_at = datetime.now(ZoneInfo("UTC")) + timedelta(days=duration_days)
        subscription.updated_at = func.now()
        
        await self.session.commit()
        await self.session.refresh(subscription)
        
        logger.info(f"PRO activated for user {user_id}, expires at {subscription.expires_at}")
        return subscription

    async def deactivate_pro(self, user_id: int) -> Optional[Subscription]:
        """Деактивировать PRO (вернуть FREE)."""
        subscription = await self.get_by_user_id(user_id)
        if not subscription:
            return None
        
        subscription.plan = PlanType.FREE
        subscription.status = SubscriptionStatus.EXPIRED
        subscription.expires_at = None
        subscription.updated_at = func.now()
        
        await self.session.commit()
        await self.session.refresh(subscription)
        
        logger.info(f"PRO deactivated for user {user_id}")
        return subscription

    async def expire_subscription(self, user_id: int) -> Optional[Subscription]:
        """Истечение подписки (перевод в EXPIRED)."""
        subscription = await self.get_by_user_id(user_id)
        if not subscription:
            return None
        
        if subscription.status == SubscriptionStatus.ACTIVE:
            subscription.status = SubscriptionStatus.EXPIRED
            subscription.updated_at = func.now()
            
            await self.session.commit()
            await self.session.refresh(subscription)
            
            logger.info(f"Subscription expired for user {user_id}")
        
        return subscription

    async def cancel_subscription(self, user_id: int) -> Optional[Subscription]:
        """Отменить подписку (перевод в CANCELLED)."""
        subscription = await self.get_by_user_id(user_id)
        if not subscription:
            return None
        
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.updated_at = func.now()
        
        await self.session.commit()
        await self.session.refresh(subscription)
        
        logger.info(f"Subscription cancelled for user {user_id}")
        return subscription

    async def delete_subscription(self, user_id: int) -> bool:
        """Удалить подписку пользователя."""
        subscription = await self.get_by_user_id(user_id)
        if not subscription:
            return False
        
        await self.session.delete(subscription)
        await self.session.commit()
        
        logger.info(f"Subscription deleted for user {user_id}")
        return True

    async def get_expired_active_subscriptions(self) -> List[Subscription]:
        """Получить все активные подписки, у которых истёк срок."""
        now = datetime.now(ZoneInfo("UTC"))
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.plan == PlanType.PRO,
                Subscription.expires_at < now
            )
        )
        return result.scalars().all()