"""
Сервис для управления доступом к функциям бота.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from zoneinfo import ZoneInfo

from app.db.repositories.subscription import SubscriptionRepository
from app.db.repositories.usage import UsageRepository
from app.db.models.subscription import PlanType, SubscriptionStatus
from app.db.models.whitelist import ProWhitelist
from app.db.models.user import User
from app.services.features import Feature, AccessLevel, get_feature_access, FreeLimits
from app.utils.logging import logger


class AccessService:
    """Сервис проверки доступа к функциям."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.subscription_repo = SubscriptionRepository(db_session)
        self.usage_repo = UsageRepository(db_session)

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    async def _get_user(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по telegram_id."""
        result = await self.db_session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def _get_current_month(self) -> str:
        """Получить текущий месяц в формате YYYY-MM."""
        return datetime.now().strftime("%Y-%m")

    # ==================== СУЩЕСТВУЮЩИЕ МЕТОДЫ (НЕ МЕНЯЕМ) ====================

    async def is_pro(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь PRO (подписка или белый список).
        """
        # Проверка белого списка
        result = await self.db_session.execute(
            select(ProWhitelist).where(ProWhitelist.user_id == user_id)
        )
        if result.scalar_one_or_none():
            logger.info(f"User {user_id} is PRO via whitelist")
            return True

        # Проверяем обычную подписку
        subscription = await self.subscription_repo.get_active_subscription(user_id)
        if not subscription:
            return False
        
        # Проверяем, не истекла ли подписка
        if subscription.expires_at:
            now = datetime.now(ZoneInfo("UTC"))
            if subscription.expires_at < now:
                await self.subscription_repo.expire_subscription(user_id)
                return False
        
        return subscription.plan == PlanType.PRO and subscription.status == SubscriptionStatus.ACTIVE

    async def get_user_plan(self, user_id: int) -> PlanType:
        """Получить текущий план пользователя."""
        if await self.is_pro(user_id):
            return PlanType.PRO

        subscription = await self.subscription_repo.get_active_subscription(user_id)
        if not subscription:
            return PlanType.FREE
        
        return subscription.plan

    async def can_use_feature(self, user_id: int, feature: Feature) -> bool:
        """Проверяет, может ли пользователь использовать фичу."""
        required_level = get_feature_access(feature)
        
        if required_level == AccessLevel.FREE:
            return True
        
        if required_level == AccessLevel.PRO:
            return await self.is_pro(user_id)
        
        return False

    async def get_plan_info(self, user_id: int) -> dict:
        """Получить информацию о плане пользователя."""
        # Проверяем белый список
        result = await self.db_session.execute(
            select(ProWhitelist).where(ProWhitelist.user_id == user_id)
        )
        if result.scalar_one_or_none():
            return {
                "plan": PlanType.PRO,
                "status": SubscriptionStatus.ACTIVE,
                "is_active": True,
                "expires_at": None,
                "is_whitelist": True,
            }

        subscription = await self.subscription_repo.get_by_user_id(user_id)
        
        if not subscription:
            return {
                "plan": PlanType.FREE,
                "status": SubscriptionStatus.ACTIVE,
                "is_active": True,
                "expires_at": None,
                "is_whitelist": False,
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
            "is_whitelist": False,
        }

    # ==================== СТАРЫЕ МЕТОДЫ (СОХРАНЯЕМ ДЛЯ СОВМЕСТИМОСТИ) ====================

    async def get_diary_limit(self, user_id: int) -> int:
        """Получить лимит записей в дневнике."""
        if await self.is_pro(user_id):
            return -1  # -1 = безлимит
        return FreeLimits.DIARY_ENTRIES_TOTAL  # 10 записей

    async def get_analysis_limit(self, user_id: int) -> int:
        """Получить лимит AI-анализов в месяц."""
        if await self.is_pro(user_id):
            return -1
        return FreeLimits.BODY_ANALYSES_PER_MONTH  # 1 анализ в месяц

    async def can_create_diary_entry(self, user_id: int) -> bool:
        """Проверяет, может ли пользователь создать запись в дневнике."""
        can_use, _ = await self.can_add_diary_entry(user_id)
        return can_use

    async def can_run_dynamics(self, user_id: int, period_days: int) -> bool:
        """Проверяет, может ли пользователь запустить динамику на период."""
        if period_days <= 7:
            return True
        return await self.is_pro(user_id)

    async def check_and_increment_analysis(self, user_id: int) -> tuple[bool, str]:
        """Старый метод — для совместимости."""
        can_use, message = await self.can_use_body_analysis(user_id)
        if can_use:
            await self.increment_body_analysis(user_id)
        return can_use, message

    async def check_and_increment_dynamics(self, user_id: int) -> tuple[bool, str]:
        """Проверяет лимит динамики."""
        if await self.is_pro(user_id):
            return True, ""

        usage = await self.usage_repo.get_current_usage(user_id)
        if usage.dynamics_count >= 5:
            return False, "⚠️ Лимит бесплатных анализов динамики (5 в месяц) исчерпан. Переходи на PRO!"
        return True, ""

    # ==================== НОВЫЕ МЕТОДЫ ДЛЯ ПРОВЕРКИ ЛИМИТОВ ====================

    async def can_use_body_analysis(self, telegram_id: int) -> tuple[bool, str]:
        """
        Проверяет, может ли пользователь использовать "Что я чувствую в теле".
        Возвращает: (разрешено, сообщение)
        """
        # 1. Если PRO — безлимит
        if await self.is_pro(telegram_id):
            return True, ""
        
        # 2. Получаем пользователя
        user = await self._get_user(telegram_id)
        if not user:
            return False, "⚠️ Пользователь не найден."
        
        # 3. Проверяем месяц
        current_month = await self._get_current_month()
        if user.body_analysis_month != current_month:
            user.body_analysis_count = 0
            user.body_analysis_month = current_month
            await self.db_session.commit()
        
        # 4. Проверяем лимит
        if user.body_analysis_count < FreeLimits.BODY_ANALYSES_PER_MONTH:
            return True, ""
        else:
            return False, (
                "❌ Вы уже использовали бесплатный анализ "
                "«Что я чувствую в теле» в этом месяце.\n\n"
                "⭐ В PRO доступны дополнительные AI-анализы, "
                "расширенная динамика и другие возможности."
            )

    async def can_use_help_dialog(self, telegram_id: int) -> tuple[bool, str]:
        """
        Проверяет, может ли пользователь использовать "Помогите разобраться".
        Возвращает: (разрешено, сообщение)
        """
        # 1. Если PRO — безлимит
        if await self.is_pro(telegram_id):
            return True, ""
        
        # 2. Получаем пользователя
        user = await self._get_user(telegram_id)
        if not user:
            return False, "⚠️ Пользователь не найден."
        
        # 3. Проверяем месяц
        current_month = await self._get_current_month()
        if user.help_analysis_month != current_month:
            user.help_analysis_count = 0
            user.help_analysis_month = current_month
            await self.db_session.commit()
        
        # 4. Проверяем лимит
        if user.help_analysis_count < FreeLimits.HELP_SESSIONS_PER_MONTH:
            return True, ""
        else:
            return False, (
                "❌ Вы уже использовали бесплатный разбор "
                "«Помогите разобраться» в этом месяце.\n\n"
                "⭐ Перейдите в PRO, чтобы продолжить "
                "разговоры с AI без этого ограничения."
            )

    async def can_add_diary_entry(self, telegram_id: int) -> tuple[bool, str]:
        """
        Проверяет, может ли пользователь добавить запись в дневник.
        Возвращает: (разрешено, сообщение)
        """
        # 1. Если PRO — безлимит
        if await self.is_pro(telegram_id):
            return True, ""
        
        # 2. Получаем пользователя
        user = await self._get_user(telegram_id)
        if not user:
            return False, "⚠️ Пользователь не найден."
        
        # 3. Проверяем лимит
        if user.diary_entries_count < FreeLimits.DIARY_ENTRIES_TOTAL:
            return True, ""
        else:
            return False, (
                "📔 Вы использовали все 10 бесплатных записей в дневнике.\n\n"
                "⭐ Перейдите в PRO, чтобы вести дневник без ограничений."
            )

    async def can_use_clarification(self, telegram_id: int, analysis_id: int) -> tuple[bool, str]:
        """
        Проверяет, может ли пользователь задать уточняющий вопрос.
        Возвращает: (разрешено, сообщение)
        """
        # 1. Если PRO — безлимит
        if await self.is_pro(telegram_id):
            return True, ""
        
        # 2. Проверяем, сколько уже задано вопросов к этому анализу
        from app.db.models.clarification import Clarification
        result = await self.db_session.execute(
            select(func.count()).select_from(Clarification).where(
                Clarification.analysis_id == analysis_id
            )
        )
        count = result.scalar() or 0
        
        if count < FreeLimits.CLARIFICATIONS_PER_BODY:
            return True, ""
        else:
            return False, (
                f"❌ Вы уже задали {FreeLimits.CLARIFICATIONS_PER_BODY} вопросов "
                "по этому анализу.\n\n"
                "⭐ В PRO доступны дополнительные уточнения."
            )

    # ==================== МЕТОДЫ УВЕЛИЧЕНИЯ СЧЁТЧИКОВ ====================

    async def increment_body_analysis(self, telegram_id: int) -> bool:
        """Увеличивает счётчик 'Что я чувствую в теле'."""
        user = await self._get_user(telegram_id)
        if not user:
            return False
        
        current_month = await self._get_current_month()
        if user.body_analysis_month != current_month:
            user.body_analysis_count = 0
            user.body_analysis_month = current_month
        
        user.body_analysis_count += 1
        await self.db_session.commit()
        logger.info(f"BODY_ANALYSIS_COUNT: user={telegram_id}, count={user.body_analysis_count}")
        return True

    async def increment_help_analysis(self, telegram_id: int) -> bool:
        """Увеличивает счётчик 'Помогите разобраться'."""
        user = await self._get_user(telegram_id)
        if not user:
            return False
        
        current_month = await self._get_current_month()
        if user.help_analysis_month != current_month:
            user.help_analysis_count = 0
            user.help_analysis_month = current_month
        
        user.help_analysis_count += 1
        await self.db_session.commit()
        logger.info(f"HELP_ANALYSIS_COUNT: user={telegram_id}, count={user.help_analysis_count}")
        return True

    async def increment_diary_entries(self, telegram_id: int) -> bool:
        """Увеличивает счётчик записей в дневнике."""
        user = await self._get_user(telegram_id)
        if not user:
            return False
        
        user.diary_entries_count += 1
        await self.db_session.commit()
        logger.info(f"DIARY_ENTRIES_COUNT: user={telegram_id}, count={user.diary_entries_count}")
        return True