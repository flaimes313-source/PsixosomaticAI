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
    Отправляет утренний, дневной и вечерний опросы в заданное время.
    """
    
    # Время по умолчанию (UTC)
    MORNING_TIME = time(8, 0)    # 8:00
    DAY_TIME = time(13, 0)       # 13:00
    EVENING_TIME = time(20, 0)   # 20:00
    
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
                now = datetime.now()
                
                # Проверяем каждые 30 секунд
                await self._check_and_send_surveys()
                
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in SurveyScheduler: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_send_surveys(self):
        """Проверяет время и отправляет опросы."""
        now = datetime.now()
        current_time = now.time()
        
        minute_window = 60
        
        if self._is_time_match(current_time, self.MORNING_TIME, minute_window):
            await self._send_morning_surveys()
        
        if self._is_time_match(current_time, self.DAY_TIME, minute_window):
            await self._send_day_surveys()
        
        if self._is_time_match(current_time, self.EVENING_TIME, minute_window):
            await self._send_evening_surveys()
    
    def _is_time_match(self, current: time, target: time, window_seconds: int = 60) -> bool:
        current_seconds = current.hour * 3600 + current.minute * 60 + current.second
        target_seconds = target.hour * 3600 + target.minute * 60
        diff = current_seconds - target_seconds
        return 0 <= diff < window_seconds
    
    async def _send_morning_surveys(self):
        """Отправляет утренние опросы."""
        logger.info("🌅 Sending morning surveys...")
        await self._send_survey_to_users("morning")
    
    async def _send_day_surveys(self):
        """Отправляет дневные опросы."""
        logger.info("☀️ Sending day surveys...")
        await self._send_survey_to_users("day")
    
    async def _send_evening_surveys(self):
        """Отправляет вечерние опросы."""
        logger.info("🌆 Sending evening surveys...")
        await self._send_survey_to_users("evening")
    
    async def _send_survey_to_users(self, survey_type: str):
        """Отправляет опрос всем активным пользователям."""
        try:
            async with self.session_maker() as session:
                result = await session.execute(
                    select(User).where(
                        User.is_active == True,
                        User.deleted_at.is_(None)
                    )
                )
                users = result.scalars().all()
                
                logger.info(f"Sending {survey_type} survey to {len(users)} users")
                
                for user in users:
                    await self._send_survey_to_user(user, survey_type)
                    await asyncio.sleep(0.2)
                    
        except Exception as e:
            logger.error(f"Error sending {survey_type} surveys: {e}")
    
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