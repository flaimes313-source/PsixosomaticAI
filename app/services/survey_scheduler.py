"""
Сервис для автоматической рассылки опросов по расписанию.
"""
import asyncio
from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, and_, or_

from app.db.models.user import User
from app.db.models.reminder import ReminderSettings
from app.utils.logging import logger


class SurveyScheduler:
    """
    Сервис для планирования и отправки опросов.
    Отправляет утренний, дневной и вечерний опросы в заданное время (по часовому поясу пользователя).
    """
    
    # Время опросов (в локальном времени пользователя)
    MORNING_HOUR = 8
    DAY_HOUR = 13
    EVENING_HOUR = 20
    
    def __init__(
        self,
        session_maker: async_sessionmaker,
        bot: Bot,
    ):
        self.session_maker = session_maker
        self.bot = bot
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Запускает шедулер."""
        if self._running:
            logger.warning("SurveyScheduler already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("SurveyScheduler started")
    
    async def stop(self):
        """Останавливает шедулер."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("SurveyScheduler stopped")
    
    async def _run(self):
        """Основной цикл шедулера."""
        while self._running:
            try:
                # Проверяем каждые 30 секунд
                await self._check_and_send_surveys()
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in SurveyScheduler: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_send_surveys(self):
        """Проверяет время и отправляет опросы пользователям."""
        now = datetime.now()
        current_time = now.time()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # ==================== НОВАЯ ЛОГИКА: ОТПРАВКА ПО ЧАСОВОМУ ПОЯСУ ====================
        # Проверяем каждую минуту (не каждые 30 секунд, чтобы не пропустить)
        if current_minute == 0:  # Проверяем только в начале каждой минуты
            # Утренний опрос (8:00)
            if current_hour == self.MORNING_HOUR:
                await self._send_morning_surveys()
            
            # Дневной опрос (13:00)
            if current_hour == self.DAY_HOUR:
                await self._send_day_surveys()
            
            # Вечерний опрос (20:00)
            if current_hour == self.EVENING_HOUR:
                await self._send_evening_surveys()
        # =================================================================================
    
    async def _send_morning_surveys(self):
        """Отправляет утренние опросы всем пользователям (по их часовому поясу)."""
        logger.info("🌅 Sending morning surveys...")
        await self._send_survey_to_users("morning", self.MORNING_HOUR)
    
    async def _send_day_surveys(self):
        """Отправляет дневные опросы всем пользователям (по их часовому поясу)."""
        logger.info("☀️ Sending day surveys...")
        await self._send_survey_to_users("day", self.DAY_HOUR)
    
    async def _send_evening_surveys(self):
        """Отправляет вечерние опросы всем пользователям (по их часовому поясу)."""
        logger.info("🌆 Sending evening surveys...")
        await self._send_survey_to_users("evening", self.EVENING_HOUR)
    
    async def _send_survey_to_users(self, survey_type: str, target_hour: int):
        """
        Отправляет опрос всем пользователям, у которых сейчас target_hour по их часовому поясу.
        """
        try:
            async with self.session_maker() as session:
                # Получаем всех активных пользователей
                result = await session.execute(
                    select(User).where(
                        User.is_active == True,
                        User.deleted_at.is_(None)
                    )
                )
                users = result.scalars().all()
                
                logger.info(f"Sending {survey_type} survey: checking {len(users)} users")
                
                sent_count = 0
                for user in users:
                    # Проверяем, совпадает ли час у пользователя
                    if await self._should_send_survey_to_user(user, target_hour):
                        await self._send_survey_to_user(user, survey_type)
                        sent_count += 1
                        await asyncio.sleep(0.2)  # Задержка между отправками
                
                logger.info(f"{survey_type} survey sent to {sent_count} users")
                    
        except Exception as e:
            logger.error(f"Error sending {survey_type} surveys: {e}")
    
    async def _should_send_survey_to_user(self, user: User, target_hour: int) -> bool:
        """
        Проверяет, должен ли пользователь получить опрос в данный момент.
        """
        try:
            # Получаем часовой пояс пользователя
            tz_str = user.timezone or "UTC"
            try:
                tz = ZoneInfo(tz_str)
            except Exception:
                tz = ZoneInfo("UTC")
            
            # Текущее время в часовом поясе пользователя
            now = datetime.now(tz)
            current_hour = now.hour
            current_minute = now.minute
            
            # Проверяем, совпадает ли час (и минута = 0, чтобы отправить ровно в начале часа)
            return current_hour == target_hour and current_minute == 0
            
        except Exception as e:
            logger.error(f"Error checking timezone for user {user.telegram_id}: {e}")
            return False
    
    async def _send_survey_to_user(self, user: User, survey_type: str):
        """Отправляет опрос одному пользователю."""
        try:
            # Определяем текст опроса
            if survey_type == "morning":
                text = self._get_morning_survey_text()
            elif survey_type == "day":
                text = self._get_day_survey_text()
            elif survey_type == "evening":
                text = self._get_evening_survey_text()
            else:
                return
            
            # Отправляем сообщение с кнопкой "Начать опрос"
            keyboard = self._get_survey_start_keyboard(survey_type)
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            
            logger.info(f"Survey {survey_type} sent to user {user.telegram_id}")
            
        except Exception as e:
            logger.error(f"Error sending {survey_type} survey to {user.telegram_id}: {e}")
    
    def _get_survey_start_keyboard(self, survey_type: str):
        """Возвращает клавиатуру для запуска опроса."""
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        survey_names = {
            "morning": "🌅 Утренний опрос",
            "day": "☀️ Дневной опрос",
            "evening": "🌆 Вечерний опрос",
        }
        
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=survey_names.get(survey_type, "Начать опрос"),
                    callback_data=f"survey_start_{survey_type}"
                )],
                [InlineKeyboardButton(
                    text="⏭ Пропустить",
                    callback_data=f"survey_skip_{survey_type}"
                )]
            ]
        )
    
    def _get_morning_survey_text(self) -> str:
        return (
            "🌅 <b>Доброе утро!</b>\n\n"
            "Пришло время для утреннего опроса.\n"
            "Это поможет тебе лучше понять своё состояние.\n\n"
            "Нажми кнопку ниже, чтобы начать."
        )
    
    def _get_day_survey_text(self) -> str:
        return (
            "☀️ <b>Добрый день!</b>\n\n"
            "Время для дневного чек-ина.\n"
            "Как проходит твой день?\n\n"
            "Нажми кнопку ниже, чтобы начать."
        )
    
    def _get_evening_survey_text(self) -> str:
        return (
            "🌆 <b>Добрый вечер!</b>\n\n"
            "Пришло время подвести итоги дня.\n"
            "Ответь на несколько вопросов.\n\n"
            "Нажми кнопку ниже, чтобы начать."
        )