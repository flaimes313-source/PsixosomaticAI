"""
Сервис для управления напоминаниями и их отправки.
"""
import asyncio
from datetime import datetime, time, timedelta
from typing import Optional, List
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories.reminder import ReminderRepository
from app.db.repositories.diary import DiaryRepository
from app.db.models.user import User
from app.utils.logging import logger


class ReminderService:
    """Сервис для работы с напоминаниями."""

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

                if (user_time.hour == reminder_hour and 
                    abs(user_time.minute - reminder_minute) <= 1):

                    if settings.days_of_week is not None and len(settings.days_of_week) > 0:
                        if user_weekday not in settings.days_of_week:
                            continue

                    await self._send_reminder(settings.user_id, session)
                    await reminder_repo.update_last_sent(settings.user_id)

    async def _send_reminder(self, user_id: int, session: AsyncSession):
        try:
            diary_repo = DiaryRepository(session)
            today_entries = await diary_repo.get_today_entries(user_id)

            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"User {user_id} not found for reminder")
                return

            if today_entries:
                message = (
                    "📔 <b>Дневник</b>\n\n"
                    "Ты уже отметил состояние сегодня. 👀\n"
                    "Хочешь добавить ещё одну запись?\n\n"
                    "Нажми кнопку ниже:"
                )
            else:
                message = (
                    "📔 <b>Дневник</b>\n\n"
                    "Как ты себя чувствуешь сегодня?\n"
                    "Отметь состояние — это займёт около минуты. 🧠\n\n"
                    "Нажми кнопку ниже:"
                )

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="📔 Заполнить дневник",
                        callback_data="reminder_open_diary"
                    )],
                    [InlineKeyboardButton(
                        text="🔕 Отключить напоминания",
                        callback_data="reminders_disable"
                    )]
                ]
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            logger.info(f"✅ Reminder sent to user {user_id}")

        except Exception as e:
            logger.error(f"❌ Error sending reminder to user {user_id}: {e}")