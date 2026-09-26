"""
Сервис для отправки утреннего сообщения «Описать состояние».
Работает вместо SurveyScheduler — настраивается через профиль.
"""
import asyncio
import random
from datetime import datetime, time, timedelta, date
from typing import Optional, List
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories.reminder import ReminderRepository
from app.db.repositories.diary_repository import DiaryRepository
from app.db.models.user import User
from app.utils.logging import logger


class ReminderService:
    """Сервис для отправки утреннего сообщения «Описать состояние»."""

    # Варианты утреннего сообщения (выбираются случайно)
    MORNING_TEXTS = [
        (
            "🌿 Доброе утро. Как ты сегодня?\n\n"
            "Если захочешь, просто опиши своё состояние своими словами. "
            "Сома поможет разобраться."
        ),
        (
            "🌅 Утро. Как ты?\n\n"
            "Если есть что-то, чем хочется поделиться — напиши. Сома рядом."
        ),
        (
            "☀️ Доброе утро. Как ты себя чувствуешь?\n\n"
            "Опиши, если хочешь — без правил и форматов."
        ),
        (
            "🌿 Новое утро. Как ты?\n\n"
            "Если что-то беспокоит или радует — расскажи. Сома поможет разобраться."
        ),
        (
            "🌅 С добрым утром. Как ты сегодня?\n\n"
            "Можешь просто написать, что происходит — своими словами."
        ),
        (
            "☀️ Доброе утро. Как ты?\n\n"
            "Начни с того, что сейчас важнее всего — Сома поможет разобраться."
        ),
        (
            "🌿 Утро. Как ты?\n\n"
            "Если хочешь, опиши своё состояние — Сома рядом и готова слушать."
        ),
    ]

    def __init__(self, session_factory: async_sessionmaker, bot):
        self.session_factory = session_factory
        self.bot = bot
        self.running = False
        self.task = None

    async def start(self):
        if self.running:
            logger.warning("ReminderService already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        logger.info("✅ ReminderService started")

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        logger.info("ReminderService stopped")

    async def _scheduler_loop(self):
        logger.info("🔄 Reminder scheduler loop started")
        while self.running:
            try:
                await self._check_reminders()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error in reminder scheduler loop: {e}")
                await asyncio.sleep(30)

    async def _check_reminders(self):
        async with self.session_factory() as session:
            reminder_repo = ReminderRepository(session)
            settings_list = await reminder_repo.get_active_reminders()

            if not settings_list:
                return

            for settings in settings_list:
                if not settings.enabled or not settings.reminder_time:
                    continue

                if await reminder_repo.is_reminder_sent_today(settings.user_id):
                    continue

                try:
                    user_tz = ZoneInfo(settings.timezone)
                except Exception:
                    user_tz = ZoneInfo("UTC")

                user_now = datetime.now(user_tz)
                user_time = user_now.time()
                user_weekday = user_now.weekday()

                reminder_hour = settings.reminder_time.hour
                reminder_minute = settings.reminder_time.minute

                # Окно ±1 минута
                if (user_time.hour == reminder_hour and
                        abs(user_time.minute - reminder_minute) <= 1):

                    if settings.days_of_week is not None and len(settings.days_of_week) > 0:
                        if user_weekday not in settings.days_of_week:
                            continue

                    await self._send_morning_message(settings.user_id, session)
                    await reminder_repo.update_last_sent(settings.user_id)

    async def _send_morning_message(self, user_id: int, session: AsyncSession):
        """Отправляет утреннее сообщение «Описать состояние»."""
        try:
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"User {user_id} not found for reminder")
                return

            text = random.choice(self.MORNING_TEXTS)

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

            # Только одна кнопка — «Описать состояние»
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🌿 Описать состояние",
                        callback_data="reminder_open_describe"
                    )]
                ]
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            logger.info(f"✅ Morning message sent to user {user_id}")

        except Exception as e:
            logger.error(f"❌ Error sending morning message to user {user_id}: {e}")