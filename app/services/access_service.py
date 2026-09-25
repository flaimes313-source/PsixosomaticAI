"""
Сервис для управления доступом к функциям бота.
Поддерживает: FREE, PRO_TRIAL (3 дня), PRO (платный), whitelist.
"""
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.db.repositories.subscription import SubscriptionRepository
from app.db.repositories.usage import UsageRepository
from app.db.models.subscription import (
    Subscription,
    PlanType,
    SubscriptionStatus,
)
from app.db.models.whitelist import ProWhitelist
from app.db.models.user import User
from app.services.features import Feature, AccessLevel, get_feature_access, FreeLimits
from app.utils.logging import logger


# Константы
TRIAL_DURATION_DAYS = 3
FREE_DIALOG_MAX_QUESTIONS = 3


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

    async def _is_whitelist(self, telegram_id: int) -> bool:
        """Проверяет, есть ли пользователь в whitelist."""
        result = await self.db_session.execute(
            select(ProWhitelist).where(ProWhitelist.user_id == telegram_id)
        )
        return result.scalar_one_or_none() is not None

    async def _get_current_month(self) -> str:
        """Получить текущий месяц в формате YYYY-MM."""
        return datetime.now().strftime("%Y-%m")

    def _now_utc(self) -> datetime:
        """Текущее время в UTC (aware)."""
        return datetime.now(ZoneInfo("UTC"))

    # ==================== ПРОВЕРКА PRO (WHITELIST + ПОДПИСКА) ====================

    async def is_pro(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь PRO.
        Учитывает: whitelist, PRO_TRIAL, платный PRO.
        """
        # 1. Белый список — всегда PRO
        if await self._is_whitelist(user_id):
            logger.info(f"User {user_id} is PRO via whitelist")
            return True

        # 2. Активная подписка (PRO или PRO_TRIAL)
        subscription = await self.subscription_repo.get_active_subscription(user_id)
        if not subscription:
            return False

        # 3. Проверяем срок
        if subscription.expires_at:
            now = self._now_utc()
            if subscription.expires_at < now:
                await self.subscription_repo.expire_subscription(user_id)
                return False

        # 4. Проверяем статус
        return subscription.status in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.PRO_TRIAL,
        )

    # ==================== TRIAL ====================

    async def is_in_trial(self, telegram_id: int) -> bool:
        """Идёт ли у пользователя активный пробный PRO."""
        subscription = await self.subscription_repo.get_active_subscription(telegram_id)
        if not subscription:
            return False

        if subscription.status != SubscriptionStatus.PRO_TRIAL:
            return False

        if subscription.expires_at and subscription.expires_at < self._now_utc():
            return False

        return True

    async def start_trial_if_needed(self, telegram_id: int) -> Tuple[bool, str]:
        """
        Запускает 3-дневный пробный PRO, если пользователь ещё не использовал trial.

        ВАЖНО:
        - Whitelist-пользователи trial НЕ получают.
        - Пользователи с активной платной подпиской trial НЕ получают.
        - Повторно trial не даётся (trial_used=True).

        Returns:
            (started, message) — started=True, если trial был запущен сейчас;
                                 started=False, если уже использован/активен/whitelist.
        """
        user = await self._get_user(telegram_id)
        if not user:
            return False, "Пользователь не найден"

        # 0. Whitelist — trial не нужен
        if await self._is_whitelist(telegram_id):
            logger.info(f"User {telegram_id} is in whitelist, skipping trial")
            return False, "Whitelist user"

        # 1. Уже был trial?
        if user.trial_used:
            logger.info(f"User {telegram_id} already used trial")
            return False, "Trial already used"

        # 2. Уже есть активная платная подписка?
        existing = await self.subscription_repo.get_active_subscription(telegram_id)
        if existing and existing.status == SubscriptionStatus.ACTIVE:
            logger.info(f"User {telegram_id} already has active PRO, skipping trial")
            return False, "Already PRO"

        # 3. Запускаем trial
        now = self._now_utc()
        ends_at = now + timedelta(days=TRIAL_DURATION_DAYS)

        await self.subscription_repo.create_or_update_trial(
            user_id=telegram_id,
            expires_at=ends_at,
        )

        user.trial_used = True
        user.trial_started_at = now
        user.trial_ends_at = ends_at
        await self.db_session.commit()

        logger.info(f"🎁 Trial started for user {telegram_id}, ends at {ends_at}")
        return True, "Trial started"

    # ==================== ОПИСАТЬ СОСТОЯНИЕ (ОСНОВНАЯ ЛОГИКА) ====================

    async def can_start_new_describe_dialog(self, telegram_id: int) -> Tuple[bool, str]:
        """
        Может ли пользователь начать НОВЫЙ диалог «Описать состояние».
        """
        # 1. PRO, trial или whitelist — всегда можно
        if await self.is_pro(telegram_id):
            return True, ""

        # 2. FREE: проверяем, использован ли единственный бесплатный диалог
        user = await self._get_user(telegram_id)
        if not user:
            return False, "⚠️ Пользователь не найден"

        if not user.free_dialog_used:
            return True, ""

        # 3. Уже использован — блокируем
        return False, (
            "⭐ <b>Бесплатный диалог уже использован</b>\n\n"
            "Хочешь продолжить общаться с Сомой без ограничений?\n\n"
            "В PRO доступны:\n"
            "♾️ неограниченные диалоги\n"
            "♾️ неограниченные уточняющие вопросы\n\n"
            "Автоматического списания нет."
        )

    async def reset_free_dialog_counter(self, telegram_id: int) -> None:
        """Сбрасывает счётчик уточнений. Вызывается при старте НОВОГО бесплатного диалога."""
        user = await self._get_user(telegram_id)
        if not user:
            return
        user.free_dialog_questions_count = 0
        await self.db_session.commit()
        logger.info(f"Free dialog counter reset for user {telegram_id}")

    async def increment_free_question(self, telegram_id: int) -> int:
        """Увеличивает счётчик уточнений в бесплатном диалоге. Возвращает новое значение."""
        user = await self._get_user(telegram_id)
        if not user:
            return 0
        user.free_dialog_questions_count += 1
        await self.db_session.commit()
        logger.info(
            f"Free dialog question count: user={telegram_id}, "
            f"count={user.free_dialog_questions_count}"
        )
        return user.free_dialog_questions_count

    async def can_continue_free_dialog(self, telegram_id: int) -> Tuple[bool, str]:
        """Может ли пользователь продолжить бесплатный диалог (задать ещё уточнение)."""
        if await self.is_pro(telegram_id):
            return True, ""

        user = await self._get_user(telegram_id)
        if not user:
            return False, "⚠️ Пользователь не найден"

        if user.free_dialog_used:
            return False, self._get_free_dialog_exhausted_message()

        if user.free_dialog_questions_count >= FREE_DIALOG_MAX_QUESTIONS:
            return False, self._get_free_dialog_exhausted_message()

        return True, ""

    async def finish_free_dialog(self, telegram_id: int) -> None:
        """Помечает бесплатный диалог как использованный."""
        user = await self._get_user(telegram_id)
        if not user:
            return
        user.free_dialog_used = True
        await self.db_session.commit()
        logger.info(f"Free dialog marked as used for user {telegram_id}")

    def _get_free_dialog_exhausted_message(self) -> str:
        return (
            "⭐ <b>Бесплатный диалог завершён</b>\n\n"
            "Ты использовал все 3 уточняющих вопроса.\n\n"
            "Хочешь продолжить общаться с Сомой без ограничений?\n\n"
            "В PRO доступны:\n"
            "♾️ неограниченные диалоги\n"
            "♾️ неограниченные уточняющие вопросы\n\n"
            "Автоматического списания нет."
        )

    # ==================== СТАРЫЕ МЕТОДЫ (СОХРАНЯЕМ ДЛЯ СОВМЕСТИМОСТИ) ====================

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
        if await self._is_whitelist(user_id):
            return {
                "plan": PlanType.PRO,
                "status": SubscriptionStatus.ACTIVE,
                "is_active": True,
                "expires_at": None,
                "is_whitelist": True,
                "is_trial": False,
            }

        subscription = await self.subscription_repo.get_by_user_id(user_id)

        if not subscription:
            return {
                "plan": PlanType.FREE,
                "status": SubscriptionStatus.ACTIVE,
                "is_active": True,
                "expires_at": None,
                "is_whitelist": False,
                "is_trial": False,
            }

        now = self._now_utc()
        is_active = (
            subscription.status in (
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.PRO_TRIAL,
            ) and
            (subscription.expires_at is None or subscription.expires_at > now)
        )

        return {
            "plan": subscription.plan,
            "status": subscription.status,
            "is_active": is_active,
            "expires_at": subscription.expires_at,
            "is_whitelist": False,
            "is_trial": subscription.status == SubscriptionStatus.PRO_TRIAL,
        }

    async def get_diary_limit(self, user_id: int) -> int:
        """Получить лимит записей в дневнике (-1 = безлимит)."""
        if await self.is_pro(user_id):
            return -1
        return FreeLimits.DIARY_ENTRIES_TOTAL

    async def get_analysis_limit(self, user_id: int) -> int:
        """Получить лимит AI-анализов в месяц (-1 = безлимит)."""
        if await self.is_pro(user_id):
            return -1
        return FreeLimits.BODY_ANALYSES_PER_MONTH

    async def can_create_diary_entry(self, user_id: int) -> bool:
        """Проверяет, может ли пользователь создать запись в дневнике."""
        can_use, _ = await self.can_add_diary_entry(user_id)
        return can_use

    async def can_run_dynamics(self, user_id: int, period_days: int) -> bool:
        """Проверяет, может ли пользователь запустить динамику."""
        if period_days <= 7:
            return True
        return await self.is_pro(user_id)

    # ==================== СТАРЫЕ ПРОВЕРКИ ЛИМИТОВ (FREE) ====================

    async def can_use_body_analysis(self, telegram_id: int) -> Tuple[bool, str]:
        """УСТАРЕЛО. Оставлено для совместимости."""
        if await self.is_pro(telegram_id):
            return True, ""

        user = await self._get_user(telegram_id)
        if not user:
            return False, "⚠️ Пользователь не найден"

        current_month = await self._get_current_month()
        if user.body_analysis_month != current_month:
            user.body_analysis_count = 0
            user.body_analysis_month = current_month
            await self.db_session.commit()

        if user.body_analysis_count < FreeLimits.BODY_ANALYSES_PER_MONTH:
            return True, ""

        return False, (
            "❌ Лимит бесплатных анализов исчерпан.\n\n"
            "⭐ В PRO доступны дополнительные AI-анализы."
        )

    async def can_use_help_dialog(self, telegram_id: int) -> Tuple[bool, str]:
        """УСТАРЕЛО."""
        if await self.is_pro(telegram_id):
            return True, ""

        user = await self._get_user(telegram_id)
        if not user:
            return False, "⚠️ Пользователь не найден"

        current_month = await self._get_current_month()
        if user.help_analysis_month != current_month:
            user.help_analysis_count = 0
            user.help_analysis_month = current_month
            await self.db_session.commit()

        if user.help_analysis_count < FreeLimits.HELP_SESSIONS_PER_MONTH:
            return True, ""

        return False, "❌ Лимит бесплатных разборов исчерпан."

    async def can_add_diary_entry(self, telegram_id: int) -> Tuple[bool, str]:
        """Проверяет лимит дневника."""
        if await self.is_pro(telegram_id):
            return True, ""

        user = await self._get_user(telegram_id)
        if not user:
            return False, "⚠️ Пользователь не найден"

        if user.diary_entries_count < FreeLimits.DIARY_ENTRIES_TOTAL:
            return True, ""

        return False, (
            f"📔 Вы использовали все {FreeLimits.DIARY_ENTRIES_TOTAL} "
            "бесплатных записей в дневнике.\n\n"
            "⭐ Перейдите в PRO для безлимита."
        )

    async def can_use_clarification(
        self, telegram_id: int, analysis_id: int
    ) -> Tuple[bool, str]:
        """Проверяет лимит уточнений к одному анализу."""
        if await self.is_pro(telegram_id):
            return True, ""

        from app.db.models.clarification import Clarification
        result = await self.db_session.execute(
            select(func.count()).select_from(Clarification).where(
                Clarification.analysis_id == analysis_id
            )
        )
        count = result.scalar() or 0

        if count < FreeLimits.CLARIFICATIONS_PER_BODY:
            return True, ""

        return False, "❌ Лимит уточнений по этому анализу исчерпан."

    # ==================== СТАРЫЕ СЧЁТЧИКИ (СОВМЕСТИМОСТЬ) ====================

    async def increment_body_analysis(self, telegram_id: int) -> bool:
        """УСТАРЕЛО."""
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
        """УСТАРЕЛО."""
        user = await self._get_user(telegram_id)
        if not user:
            return False

        current_month = await self._get_current_month()
        if user.help_analysis_month != current_month:
            user.help_analysis_count = 0
            user.help_analysis_month = current_month

        user.help_analysis_count += 1
        await self.db_session.commit()
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