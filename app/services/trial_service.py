"""
Сервис для управления пробным и платным PRO.

Делает три вещи:
1. Проверяет истёкшие подписки (PRO_TRIAL и PRO) → переводит в EXPIRED.
2. Шлёт напоминания об окончании ПЛАТНОГО PRO за 3 / 1 / 0 дней.
3. Не трогает whitelist и не продлевает подписки автоматически.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models.subscription import (
    Subscription,
    PlanType,
    SubscriptionStatus,
)
from app.db.models.user import User
from app.utils.logging import logger


# ==================== ТЕКСТЫ НАПОМИНАНИЙ ====================

REMINDER_3_DAYS = (
    "🌿 До окончания твоего PRO осталось 3 дня.\n\n"
    "Если хочешь продолжить общаться с Сомой без ограничений — "
    "можно продлить подписку."
)

REMINDER_1_DAY = (
    "⏳ Завтра закончится твой PRO.\n\n"
    "Продли подписку, чтобы сохранить безлимитный доступ."
)

REMINDER_TODAY = (
    "🌿 Сегодня заканчивается твой PRO.\n\n"
    "После этого дня диалоги станут ограниченными. "
    "Можно продлить подписку в любой момент."
)

PRO_RENEW_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="⭐ Продлить PRO",
            callback_data="pro_from_reminder"
        )],
    ]
)


class TrialService:
    """
    Сервис для управления пробным и платным PRO.
    Запускается в main.py как фоновый процесс.
    """

    # Как часто проверять (в секундах)
    CHECK_INTERVAL = 60

    def __init__(self, session_factory: async_sessionmaker, bot: Bot):
        self.session_factory = session_factory
        self.bot = bot
        self.running = False
        self.task: Optional[asyncio.Task] = None
        # Отправленные напоминания: {user_id: {"3d": True, "1d": True, "0d": True}}
        # Чтобы не спамить одним и тем же
        self._reminders_sent: dict = {}

    async def start(self):
        """Запускает фоновый цикл."""
        if self.running:
            logger.warning("TrialService already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._loop())
        logger.info("✅ TrialService started")

    async def stop(self):
        """Останавливает фоновый цикл."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        logger.info("TrialService stopped")

    async def _loop(self):
        """Основной цикл — каждые 60 секунд."""
        logger.info("🔄 TrialService loop started")
        while self.running:
            try:
                await self._check_expired_subscriptions()
                await self._check_reminders()
                await asyncio.sleep(self.CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in TrialService loop: {e}", exc_info=True)
                await asyncio.sleep(60)

    # ==================== 1. ИСТЁКШИЕ ПОДПИСКИ ====================

    async def _check_expired_subscriptions(self):
        """
        Находит подписки с истёкшим сроком (PRO и PRO_TRIAL)
        и переводит их в статус EXPIRED.
        """
        async with self.session_factory() as session:
            now = datetime.now(ZoneInfo("UTC"))

            result = await session.execute(
                select(Subscription).where(
                    Subscription.status.in_([
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.PRO_TRIAL,
                    ]),
                    Subscription.expires_at.isnot(None),
                    Subscription.expires_at < now,
                )
            )
            expired_list = list(result.scalars().all())

            if not expired_list:
                return

            for sub in expired_list:
                old_status = sub.status.value
                sub.status = SubscriptionStatus.EXPIRED
                sub.plan = PlanType.FREE
                logger.info(
                    f"⏰ Subscription expired: user={sub.user_id}, "
                    f"was={old_status}, expires_at={sub.expires_at}"
                )

                # Сбрасываем флаги напоминаний
                self._reminders_sent.pop(sub.user_id, None)

            await session.commit()
            logger.info(f"✅ Processed {len(expired_list)} expired subscriptions")

    # ==================== 2. НАПОМИНАНИЯ ОБ ОКОНЧАНИИ PRO ====================

    async def _check_reminders(self):
        """
        Шлёт напоминания об окончании ПЛАТНОГО PRO за 3 / 1 / 0 дней.
        Trial не напоминаем — он бесплатный.
        """
        async with self.session_factory() as session:
            now = datetime.now(ZoneInfo("UTC"))

            # Только активный PRO (не trial, не whitelist)
            result = await session.execute(
                select(Subscription).where(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at.isnot(None),
                )
            )
            active_pro = list(result.scalars().all())

            for sub in active_pro:
                try:
                    delta = sub.expires_at - now
                    days_left = delta.days

                    # 3 дня
                    if days_left == 3:
                        await self._send_reminder_if_needed(
                            sub.user_id, "3d", REMINDER_3_DAYS
                        )
                    # 1 день
                    elif days_left == 1:
                        await self._send_reminder_if_needed(
                            sub.user_id, "1d", REMINDER_1_DAY
                        )
                    # Сегодня (0 дней)
                    elif days_left == 0 and delta.total_seconds() > 0:
                        await self._send_reminder_if_needed(
                            sub.user_id, "0d", REMINDER_TODAY
                        )
                except Exception as e:
                    logger.error(f"Error sending reminder for user {sub.user_id}: {e}")

    async def _send_reminder_if_needed(
        self,
        user_id: int,
        key: str,
        text: str,
    ):
        """Отправляет напоминание, если оно ещё не отправлено."""
        sent = self._reminders_sent.setdefault(user_id, {})
        if sent.get(key):
            return

        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=PRO_RENEW_KEYBOARD,
                parse_mode="HTML",
            )
            sent[key] = True
            logger.info(f"📢 PRO reminder '{key}' sent to user {user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to send PRO reminder to {user_id}: {e}")
            # Не помечаем как отправленное — попробуем в следующий раз