"""
Сервис для управления подписками.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from app.db.repositories.subscription import SubscriptionRepository
from app.db.models.subscription import PlanType, SubscriptionStatus
from app.utils.logging import logger


class SubscriptionService:
    """Сервис для работы с подписками."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.subscription_repo = SubscriptionRepository(db_session)

    async def activate_pro(self, user_id: int, duration_days: int = 30) -> Optional[dict]:
        """
        Активировать PRO-подписку.
        """
        try:
            subscription = await self.subscription_repo.activate_pro(user_id, duration_days)
            return {
                "user_id": user_id,
                "plan": subscription.plan,
                "status": subscription.status,
                "expires_at": subscription.expires_at,
            }
        except Exception as e:
            logger.error(f"Failed to activate PRO for user {user_id}: {e}")
            return None

    async def deactivate_pro(self, user_id: int) -> bool:
        """
        Деактивировать PRO-подписку (вернуть FREE).
        """
        try:
            subscription = await self.subscription_repo.deactivate_pro(user_id)
            return subscription is not None
        except Exception as e:
            logger.error(f"Failed to deactivate PRO for user {user_id}: {e}")
            return False

    async def expire_subscription(self, user_id: int) -> bool:
        """
        Перевести подписку в статус EXPIRED.
        """
        try:
            subscription = await self.subscription_repo.expire_subscription(user_id)
            return subscription is not None
        except Exception as e:
            logger.error(f"Failed to expire subscription for user {user_id}: {e}")
            return False

    async def check_expired_subscriptions(self) -> int:
        """
        Проверить все подписки и перевести истекшие в EXPIRED.
        Возвращает количество обработанных.
        """
        try:
            expired = await self.subscription_repo.get_expired_active_subscriptions()
            count = 0
            for sub in expired:
                await self.subscription_repo.expire_subscription(sub.user_id)
                count += 1
            if count > 0:
                logger.info(f"Expired {count} subscriptions")
            return count
        except Exception as e:
            logger.error(f"Failed to check expired subscriptions: {e}")
            return 0

    async def get_subscription_info(self, user_id: int) -> dict:
        """
        Получить информацию о подписке пользователя.
        """
        subscription = await self.subscription_repo.get_by_user_id(user_id)
        
        if not subscription:
            return {
                "plan": PlanType.FREE,
                "status": SubscriptionStatus.ACTIVE,
                "is_active": True,
                "expires_at": None,
                "days_left": None,
            }
        
        now = datetime.now(ZoneInfo("UTC"))
        is_active = subscription.status == SubscriptionStatus.ACTIVE
        
        days_left = None
        if subscription.expires_at and is_active:
            delta = subscription.expires_at - now
            days_left = max(0, delta.days)
        
        return {
            "plan": subscription.plan,
            "status": subscription.status,
            "is_active": is_active and (subscription.expires_at is None or subscription.expires_at > now),
            "expires_at": subscription.expires_at,
            "days_left": days_left,
        }