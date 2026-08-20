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
        """
        Инициализация сервиса.
        
        Args:
            session_factory: Фабрика сессий БД
            bot: Экземпляр бота для отправки сообщений
        """
        self.session_factory = session_factory
        self.bot = bot  # ← Сохраняем бота
        self.running = False
        self.task = None

    async def start(self):
        """Запускает шедулер."""
        if self.running:
            logger.warning("ReminderService already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        logger.info("ReminderService started")

    async def stop(self):
        """Останавливает шедулер."""
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
        """Основной цикл шедулера."""
        while self.running:
            try:
                await self._check_reminders()
                await asyncio.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                logger.error(f"Error in reminder scheduler loop: {e}")
                await asyncio.sleep(60)

    async def _check_reminders(self):
        """Проверяет, нужно ли отправить напоминания."""
        async with self.session_factory() as session:
            reminder_repo = ReminderRepository(session)
            
            # Получаем все активные напоминания
            settings_list = await reminder_repo.get_active_reminders()
            
            if not settings_list:
                return

            now_utc = datetime.now(ZoneInfo("UTC"))
            current_minute = now_utc.minute
            
            # Проверяем только в начале каждой минуты (0-я секунда)
            if current_minute not in (0, 1, 2):
                return

            # Получаем текущий день недели (0 = понедельник, 6 = воскресенье)
            current_weekday = now_utc.weekday()

            for settings in settings_list:
                if not settings.enabled or not settings.reminder_time:
                    continue

                # Проверяем, не отправляли ли уже сегодня
                if await reminder_repo.is_reminder_sent_today(settings.user_id):
                    continue

                # Получаем часовой пояс пользователя
                try:
                    user_tz = ZoneInfo(settings.timezone)
                except Exception:
                    user_tz = ZoneInfo("UTC")
                
                user_now = datetime.now(user_tz)
                user_time = user_now.time()
                
                # Проверяем время (сравниваем часы и минуты)
                reminder_hour = settings.reminder_time.hour
                reminder_minute = settings.reminder_time.minute
                
                # Если время совпадает (с точностью до минуты)
                if (user_time.hour == reminder_hour and 
                    user_time.minute == reminder_minute):
                    
                    # Проверяем дни недели
                    if settings.days_of_week is not None and len(settings.days_of_week) > 0:
                        if current_weekday not in settings.days_of_week:
                            continue

                    # Отправляем напоминание
                    await self._send_reminder(settings.user_id, session)
                    await reminder_repo.update_last_sent(settings.user_id)

    async def _send_reminder(self, user_id: int, session: AsyncSession):
        """Отправляет напоминание пользователю."""
        try:
            # Проверяем, есть ли уже записи сегодня
            diary_repo = DiaryRepository(session)
            today_entries = await diary_repo.get_today_entries(user_id)
            
            # Находим пользователя
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {user_id} not found for reminder")
                return

            # Формируем сообщение
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

            # Отправляем сообщение с кнопкой
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="📔 Заполнить дневник",
                        callback_data="reminder_open_diary"
                    )],
                    [InlineKeyboardButton(
                        text="🔕 Отключить напоминания",
                        callback_data="reminder_disable"
                    )]
                ]
            )

            await self.bot.send_message(  # ← Используем self.bot
                chat_id=user_id,
                text=message,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            
            logger.info(f"Reminder sent to user {user_id}")

        except Exception as e:
            logger.error(f"Error sending reminder to user {user_id}: {e}")