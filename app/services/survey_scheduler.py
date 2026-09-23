"""
Сервис для автоматической рассылки утреннего сообщения по расписанию.
Отправляет одно короткое сообщение в локальное время каждого пользователя.
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

from app.db.models.user import User
from app.utils.logging import logger


class SurveyScheduler:
    """
    Сервис для отправки утреннего сообщения.
    Отправляет одно короткое сообщение в 9:00 по локальному времени каждого пользователя.
    """

    # Время отправки (в локальном времени пользователя)
    MORNING_HOUR = 9

    # Окно отправки (в минутах от начала часа)
    # Если сообщение не ушло в 9:00 (ошибка/рестарт) — попробуем до 9:15
    SEND_WINDOW_MINUTES = 15

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
                await self._check_and_send_morning()
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in SurveyScheduler: {e}")
                await asyncio.sleep(60)

    async def _check_and_send_morning(self):
        """Проверяет локальное время каждого пользователя и отправляет утреннее сообщение."""
        now = datetime.now()
        logger.info(f"⏰ Survey tick: {now.strftime('%H:%M:%S')}")

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

                sent_count = 0

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

                    # Отправляем, если сейчас 9:00–9:15 и ещё не отправляли сегодня
                    if (user_hour == self.MORNING_HOUR
                            and 0 <= user_minute < self.SEND_WINDOW_MINUTES):
                        if not self._is_already_sent_today(user.telegram_id, "morning", user_now):
                            success = await self._send_morning_message(user)
                            if success:
                                self._mark_as_sent(user.telegram_id, "morning")
                                sent_count += 1
                                await asyncio.sleep(0.2)

                if sent_count > 0:
                    logger.info(f"✅ Morning messages sent: {sent_count}")

        except Exception as e:
            logger.error(f"Error sending morning messages: {e}")

    def _is_already_sent_today(self, telegram_id: int, survey_type: str, user_now: datetime) -> bool:
        """Проверяет, отправляли ли уже этот тип сообщения сегодня (по локальной дате пользователя)."""
        key = f"{telegram_id}_{survey_type}"
        last_sent = self._sent_sessions.get(key)

        if not last_sent:
            return False

        if last_sent.date() == user_now.date():
            logger.info(f"⏭ Already sent {survey_type} today for user {telegram_id}")
            return True

        return False

    def _mark_as_sent(self, telegram_id: int, survey_type: str):
        """Помечает сообщение как отправленное СЕГОДНЯ. Только после успешной отправки."""
        key = f"{telegram_id}_{survey_type}"
        self._sent_sessions[key] = datetime.now()
        logger.info(f"📌 Marked {survey_type} as sent for user {telegram_id}")

    async def _send_morning_message(self, user: User) -> bool:
        """
        Отправляет утреннее сообщение одному пользователю.
        Возвращает True при успехе, False при ошибке.
        """
        try:
            text = random.choice(self.MORNING_TEXTS)
            keyboard = self._get_morning_keyboard()

            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

            logger.info(f"✅ Morning message sent to user {user.telegram_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error sending morning message to {user.telegram_id}: {e}")
            return False

    def _get_morning_keyboard(self):
        """Возвращает клавиатуру с кнопкой запуска сценария «Описать состояние»."""
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="🌿 Описать состояние",
                    callback_data="survey_start_morning"
                )]
            ]
        )