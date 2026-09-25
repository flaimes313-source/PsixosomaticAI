"""
Сервис для анализа динамики.
Использует DiaryRepository и DynamicsDataBuilder + новый промпт Сомы.
Возвращает ТЕКСТ (не JSON) — как ответ от AI.

Логика:
- 0 записей → заглушка «Пока нечего анализировать»
- 1-2 записи → заглушка «Пока наблюдений немного»
- 3+ записей → обычный анализ через AI
"""
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.repositories.diary_repository import DiaryRepository
from app.db.models.user import User
from app.services.dynamics_data_builder import DynamicsDataBuilder
from app.services.yandex_gpt import YandexGPTClient, YandexGPTError
from app.services.diary_event_service import DiaryEventService
from app.services.ai_service import SOMA_BASE_PROMPT, DYNAMICS_PROMPT
from app.utils.logging import logger


# Порог для "недостаточно данных"
MIN_EVENTS_FOR_ANALYSIS = 3


class DynamicsService:
    """Сервис для анализа динамики."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.repository = DiaryRepository(db_session)
        self.builder = DynamicsDataBuilder()
        self.client = YandexGPTClient()

    async def get_report(
        self,
        user_id: int,
        period_days: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        user_timezone: str = "UTC",
    ) -> Dict[str, Any]:
        """
        Получает отчёт о динамике за период.

        Returns:
            dict с полями:
                success: bool
                report_text: str  — текст отчёта или заглушки
                events_count: int
                period_days: int
                start_date: date
                end_date: date
                is_empty: bool      — записей вообще нет
                is_too_few: bool    — записей < MIN_EVENTS_FOR_ANALYSIS
        """
        if start_date is None:
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days - 1)

        if end_date is None:
            end_date = date.today()

        logger.info(
            f"Getting dynamics report: user_id={user_id}, "
            f"from={start_date} to={end_date}"
        )

        # ==================== ПОЛУЧАЕМ СОБЫТИЯ ====================
        events = await self.repository.get_events_by_period(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
        events_count = len(events)

        # ==================== ЗАГЛУШКА: НЕТ ЗАПИСЕЙ ====================
        if events_count == 0:
            logger.info(f"No events for user {user_id} in period")
            return {
                "success": True,
                "report_text": (
                    "📊 <b>Пока нечего анализировать</b>\n\n"
                    "За выбранный период нет записей.\n\n"
                    "Начни с 📝 «Описать состояние», когда захочешь "
                    "рассказать, что сейчас происходит."
                ),
                "events_count": 0,
                "period_days": period_days,
                "start_date": start_date,
                "end_date": end_date,
                "is_empty": True,
                "is_too_few": False,
            }

        # ==================== ЗАГЛУШКА: МАЛО ЗАПИСЕЙ ====================
        if events_count < MIN_EVENTS_FOR_ANALYSIS:
            logger.info(
                f"Too few events for user {user_id}: {events_count} "
                f"(min {MIN_EVENTS_FOR_ANALYSIS})"
            )
            return {
                "success": True,
                "report_text": (
                    "🌿 <b>Пока наблюдений немного.</b>\n\n"
                    "За выбранный период недостаточно записей, чтобы "
                    "уверенно говорить о повторяющихся тенденциях "
                    "или изменениях.\n\n"
                    "Можно просто продолжать описывать состояние "
                    "своими словами. Когда накопится больше наблюдений, "
                    "будет легче заметить повторяющиеся темы."
                ),
                "events_count": events_count,
                "period_days": period_days,
                "start_date": start_date,
                "end_date": end_date,
                "is_empty": False,
                "is_too_few": True,
            }

        # ==================== ОБЫЧНЫЙ АНАЛИЗ ЧЕРЕЗ AI ====================
        data = self.builder.build(events, start_date, end_date, user_timezone)
        prompt = self.builder.build_prompt(data)

        logger.info(f"Dynamics prompt created, length={len(prompt)}")

        try:
            # Системный промпт = Сома + функция «Динамика»
            system_prompt = f"{SOMA_BASE_PROMPT}\n\n{'='*60}\n\n{DYNAMICS_PROMPT}"

            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=3000,
            )

            # ==================== ОТВЕТ AI — ЭТО ТЕКСТ, НЕ JSON ====================
            report_text = response.strip() if response else ""

            if not report_text:
                logger.warning("AI returned empty dynamics report")
                report_text = self._get_fallback_text(start_date, end_date, events_count)

            # ==================== СОХРАНЯЕМ ОТЧЁТ ====================
            try:
                user_result = await self.db_session.execute(
                    select(User).where(User.id == user_id)
                )
                user_obj = user_result.scalar_one_or_none()

                if user_obj:
                    diary_service = DiaryEventService(self.db_session)
                    await diary_service.record_event(
                        telegram_id=user_obj.telegram_id,
                        event_type="dynamics_report",
                        source="dynamics",
                        role="system",
                        content=report_text[:500],  # обрезаем для БД
                        payload={
                            "period_from": start_date.isoformat(),
                            "period_to": end_date.isoformat(),
                            "period_days": period_days,
                            "events_count": events_count,
                        },
                    )
            except Exception as e:
                logger.error(f"Failed to save dynamics report: {e}")
            # =============================================================

            return {
                "success": True,
                "report_text": report_text,
                "events_count": events_count,
                "period_days": period_days,
                "start_date": start_date,
                "end_date": end_date,
                "is_empty": False,
                "is_too_few": False,
            }

        except YandexGPTError as e:
            logger.error(f"YandexGPT error in dynamics: {e}")
            return {
                "success": True,
                "report_text": self._get_fallback_text(start_date, end_date, events_count),
                "events_count": events_count,
                "period_days": period_days,
                "start_date": start_date,
                "end_date": end_date,
                "is_empty": False,
                "is_too_few": False,
            }
        except Exception as e:
            logger.error(f"Error in dynamics: {e}", exc_info=True)
            return {
                "success": True,
                "report_text": self._get_fallback_text(start_date, end_date, events_count),
                "events_count": events_count,
                "period_days": period_days,
                "start_date": start_date,
                "end_date": end_date,
                "is_empty": False,
                "is_too_few": False,
            }

    def _get_fallback_text(
        self,
        start_date: date,
        end_date: date,
        events_count: int,
    ) -> str:
        """Текст-заглушка, если AI недоступен или вернул пусто."""
        return (
            "📊 <b>Твоя динамика</b>\n\n"
            "К сожалению, сейчас не удалось получить наблюдения по записям. "
            "Попробуй ещё раз через некоторое время.\n\n"
            f"За период {start_date.strftime('%d.%m.%Y')} — "
            f"{end_date.strftime('%d.%m.%Y')} у тебя {events_count} записей."
        )