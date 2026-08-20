"""
Сервис для управления доступом к функциям бота.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from zoneinfo import ZoneInfo

from app.db.repositories.subscription import SubscriptionRepository
from app.db.repositories.usage import UsageRepository
from app.db.models.subscription import PlanType, SubscriptionStatus
from app.services.features import Feature, AccessLevel, get_feature_access
from app.utils.logging import logger


class AccessService:
    """Сервис проверки доступа к функциям."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.subscription_repo = SubscriptionRepository(db_session)
        self.usage_repo = UsageRepository(db_session)

    async def is_pro(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь PRO.
        """
        subscription = await self.subscription_repo.get_active_subscription(user_id)
        if not subscription:
            return False
        
        # Проверяем, не истекла ли подписка
        if subscription.expires_at:
            now = datetime.now(ZoneInfo("UTC"))
            if subscription.expires_at < now:
                # Подписка истекла — деактивируем
                await self.subscription_repo.expire_subscription(user_id)
                return False
        
        return subscription.plan == PlanType.PRO and subscription.status == SubscriptionStatus.ACTIVE

    async def get_user_plan(self, user_id: int) -> PlanType:
        """
        Получить текущий план пользователя.
        """
        subscription = await self.subscription_repo.get_active_subscription(user_id)
        if not subscription:
            return PlanType.FREE
        
        return subscription.plan

    async def can_use_feature(self, user_id: int, feature: Feature) -> bool:
        """
        Проверяет, может ли пользователь использовать фичу.
        """
        # Получаем требуемый уровень доступа для фичи
        required_level = get_feature_access(feature)
        
        # Если фича бесплатная — доступ всегда есть
        if required_level == AccessLevel.FREE:
            return True
        
        # Если фича PRO — проверяем подписку
        if required_level == AccessLevel.PRO:
            return await self.is_pro(user_id)
        
        return False

    async def get_plan_info(self, user_id: int) -> dict:
        """
        Получить информацию о плане пользователя для отображения.
        """
        subscription = await self.subscription_repo.get_by_user_id(user_id)
        
        if not subscription:
            return {
                "plan": PlanType.FREE,
                "status": SubscriptionStatus.ACTIVE,
                "is_active": True,
                "expires_at": None,
            }
        
        is_active = (
            subscription.status == SubscriptionStatus.ACTIVE and
            (subscription.expires_at is None or subscription.expires_at > datetime.now(ZoneInfo("UTC")))
        )
        
        return {
            "plan": subscription.plan,
            "status": subscription.status,
            "is_active": is_active,
            "expires_at": subscription.expires_at,
        }

    async def get_diary_limit(self, user_id: int) -> int:
        """
        Получить лимит записей в дневнике для пользователя.
        """
        if await self.is_pro(user_id):
            return -1  # -1 = безлимит
        return 30  # FREE: 30 записей

    async def get_analysis_limit(self, user_id: int) -> int:
        """
        Получить лимит AI-анализов в месяц для пользователя.
        """
        if await self.is_pro(user_id):
            return -1  # -1 = безлимит
        return 10  # FREE: 10 анализов в месяц

    async def can_create_diary_entry(self, user_id: int) -> bool:
        """
        Проверяет, может ли пользователь создать запись в дневнике.
        """
        limit = await self.get_diary_limit(user_id)
        if limit == -1:
            return True
        
        # Считаем количество записей за всё время
        from app.db.repositories.diary import DiaryRepository
        diary_repo = DiaryRepository(self.db_session)
        count = await diary_repo.get_entries_count_by_user(user_id)
        
        return count < limit

    async def can_run_dynamics(self, user_id: int, period_days: int) -> bool:
        """
        Проверяет, может ли пользователь запустить динамику на период.
        """
        # 7 дней всегда доступны
        if period_days <= 7:
            return True
        
        # 30 и 90 дней — только PRO
        return await self.is_pro(user_id)

    async def check_and_increment_analysis(self, user_id: int) -> tuple[bool, str]:
        """
        Проверяет лимит анализов и увеличивает счётчик (если можно).
        Возвращает (можно_использовать, сообщение).
        """
        # Проверяем, PRO ли пользователь
        is_pro_user = await self.is_pro(user_id)
        if is_pro_user:
            # PRO — безлимит
            return True, ""

        # FREE — проверяем лимит
        usage = await self.usage_repo.get_current_usage(user_id)
        if usage.analyses_count >= 10:
            return False, "⚠️ Лимит бесплатных анализов (10 в месяц) исчерпан. Переходи на PRO для неограниченных анализов!"

        return True, ""

    async def check_and_increment_dynamics(self, user_id: int) -> tuple[bool, str]:
        """
        Проверяет лимит динамики и увеличивает счётчик (если можно).
        Возвращает (можно_использовать, сообщение).
        """
        # PRO — безлимит
        if await self.is_pro(user_id):
            return True, ""

        # FREE — проверяем лимит (например, 5 запусков динамики в месяц)
        usage = await self.usage_repo.get_current_usage(user_id)
        if usage.dynamics_count >= 5:
            return False, "⚠️ Лимит бесплатных анализов динамики (5 в месяц) исчерпан. Переходи на PRO для большего количества анализов!"

        return True, ""