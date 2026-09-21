"""
Сервис для автоматической рассылки опросов по расписанию.
Отправляет опросы в локальное время каждого пользователя.
"""
import asyncio
from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, and_, or_

from app.db.models.user import User
from app.utils.logging import logger


class SurveyScheduler:
    """
    Сервис для планирования и отправки опросов.
    Отправляет утренний, дневной и вечерний опросы в заданное время
    в часовом поясе каждого пользователя.
    """
    
    # Время опросов (в локальном времени пользователя)
    MORNING_HOUR = 8
    DAY_HOUR = 13
    EVENING_HOUR = 20
    
    # Окно отправки (в минутах от начала часа)
    # Например, окно 15 минут означает, что опрос можно отправить
    # с 08:00 до 08:15 включительно, если он ещё не отправлен.
    SEND_WINDOW_MINUTES = 15
    
    def __init__(
        self,
        session_maker: async_sessionmaker,
        bot: Bot,
    ):
        self.session_maker = session_maker
        self.bot = bot
        self._running = False
        self._task: Optional[asyncio.Task] = None
        # Для предотвращения дублей в рамках одного запуска
        # {key: datetime} — когда была успешная отправка
        self._sent_sessions = {}

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
        logger.info("🔄 SurveyScheduler loop started")
        while self._running:
            try:
                await self._check_and_send_surveys()
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in SurveyScheduler: {e}")
                await asyncio.sleep(60)

    async def _check_and_send_surveys(self):
        """Проверяет время у КАЖДОГО пользователя и отправляет опросы."""
        now = datetime.now()
        logger.info(f"⏰ Survey tick: {now.strftime('%H:%M:%S')}")
        await self._send_surveys_to_users()

    async def _send_surveys_to_users(self):
        """
        Отправляет опросы пользователям, у которых сейчас нужное локальное время.
        """
        try:
            async with self.session_maker() as session:
                result = await session.execute(
                    select(User).where(
                        User.is_active == True,
                        User.deleted_at.is_(None)
                    )
                )
                users = result.scalars().all()
                
                logger.info(f"📋 Checking {len(users)} users")
                
                morning_sent = 0
                day_sent = 0
                evening_sent = 0
                
                for user in users:
                    try:
                        tz_str = user.timezone or "UTC"
                        try:
                            tz = ZoneInfo(tz_str)
                        except Exception:
                            tz = ZoneInfo("UTC")
                        
                        user_now = datetime.now(tz)
                        user_hour = user_now.hour
                        user_minute = user_now.minute
                    except Exception as e:
                        logger.error(f"Error getting user timezone {user.telegram_id}: {e}")
                        continue
                    
                    logger.info(
                        f"👤 User {user.telegram_id}: tz={tz_str}, "
                        f"local_time={user_now.strftime('%H:%M')}"
                    )
                    
                    # ==================== УТРЕННИЙ ====================
                    # Отправляем, если сейчас 8:00–8:15 и ещё не отправляли
                    if (user_hour == self.MORNING_HOUR 
                            and 0 <= user_minute < self.SEND_WINDOW_MINUTES):
                        if not self._is_already_sent_today(user.telegram_id, "morning", user_now):
                            success = await self._send_survey_to_user(user, "morning")
                            if success:
                                self._mark_as_sent(user.telegram_id, "morning")
                                morning_sent += 1
                                await asyncio.sleep(0.2)
                    
                    # ==================== ДНЕВНОЙ ====================
                    elif (user_hour == self.DAY_HOUR 
                            and 0 <= user_minute < self.SEND_WINDOW_MINUTES):
                        if not self._is_already_sent_today(user.telegram_id, "day", user_now):
                            success = await self._send_survey_to_user(user, "day")
                            if success:
                                self._mark_as_sent(user.telegram_id, "day")
                                day_sent += 1
                                await asyncio.sleep(0.2)
                    
                    # ==================== ВЕЧЕРНИЙ ====================
                    elif (user_hour == self.EVENING_HOUR 
                            and 0 <= user_minute < self.SEND_WINDOW_MINUTES):
                        if not self._is_already_sent_today(user.telegram_id, "evening", user_now):
                            success = await self._send_survey_to_user(user, "evening")
                            if success:
                                self._mark_as_sent(user.telegram_id, "evening")
                                evening_sent += 1
                                await asyncio.sleep(0.2)
                
                if morning_sent > 0:
                    logger.info(f"✅ Morning surveys sent: {morning_sent}")
                if day_sent > 0:
                    logger.info(f"✅ Day surveys sent: {day_sent}")
                if evening_sent > 0:
                    logger.info(f"✅ Evening surveys sent: {evening_sent}")
                    
        except Exception as e:
            logger.error(f"Error sending surveys: {e}")

    def _is_already_sent_today(self, telegram_id: int, survey_type: str, user_now: datetime) -> bool:
        """
        Проверяет, отправляли ли уже этот тип опроса сегодня (по локальной дате пользователя).
        Флаг хранится как (дата, время) — так мы не зависим от «30 минут».
        """
        key = f"{telegram_id}_{survey_type}"
        last_sent = self._sent_sessions.get(key)
        
        if not last_sent:
            return False
        
        # Сравниваем по локальной дате пользователя
        if last_sent.date() == user_now.date():
            logger.info(f"⏭ Already sent {survey_type} today for user {telegram_id}")
            return True
        
        return False

    def _mark_as_sent(self, telegram_id: int, survey_type: str):
        """
        Помечает опрос как отправленный СЕГОДНЯ.
        Вызывается ТОЛЬКО после успешной отправки.
        """
        key = f"{telegram_id}_{survey_type}"
        self._sent_sessions[key] = datetime.now()
        logger.info(f"📌 Marked {survey_type} as sent for user {telegram_id}")

    async def _send_survey_to_user(self, user: User, survey_type: str) -> bool:
        """
        Отправляет опрос одному пользователю.
        Возвращает True при успехе, False при ошибке.
        """
        try:
            if survey_type == "morning":
                text = self._get_morning_survey_text()
            elif survey_type == "day":
                text = self._get_day_survey_text()
            elif survey_type == "evening":
                text = self._get_evening_survey_text()
            else:
                return False
            
            keyboard = self._get_survey_start_keyboard(survey_type)
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            
            logger.info(f"✅ {survey_type} survey sent to user {user.telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending {survey_type} survey to {user.telegram_id}: {e}")
            return False

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