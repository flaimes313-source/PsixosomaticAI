"""
Сервис для анализа динамики.
Использует DiaryRepository и DynamicsDataBuilder.
"""
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.repositories.diary_repository import DiaryRepository
from app.services.dynamics_data_builder import DynamicsDataBuilder
from app.services.yandex_gpt import YandexGPTClient, YandexGPTError
from app.services.diary_event_service import DiaryEventService
from app.utils.logging import logger


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
        """
        # Определяем даты
        if start_date is None:
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days - 1)
        
        if end_date is None:
            end_date = date.today()

        logger.info(f"Getting dynamics report: user={user_id}, from={start_date} to={end_date}")

        # Получаем события за период
        events = await self.repository.get_events_by_period(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        if len(events) < 3:
            return {
                "success": False,
                "message": (
                    "📊 <b>Недостаточно данных для анализа</b>\n\n"
                    "Для полноценной динамики нужно минимум 3 события.\n\n"
                    "Продолжай описывать своё состояние\n"
                    "и проходить короткие опросы."
                ),
                "events_count": len(events),
            }

        # Строим структурированные данные
        data = self.builder.build(events, start_date, end_date, user_timezone)

        # Формируем промпт
        prompt = self.builder.build_prompt(data)

        logger.info(f"Dynamics prompt created, length={len(prompt)}")

        # Отправляем в YandexGPT
        try:
            system_prompt = """
Ты — AI-помощник «Сома. Забота о себе.»
Ты анализируешь дневниковые данные пользователя и формируешь отчёт о динамике.

Ты не врач и не ставишь диагнозов.
Используй только предоставленные данные.
Будь поддерживающим и бережным.
Отвечай на русском языке.
"""

            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=3000,
            )

            # Парсим JSON
            report_data = self._parse_response(response)

            if not report_data:
                return self._create_fallback_report(start_date, end_date, len(events))

            # ==================== СОХРАНЯЕМ ОТЧЁТ В ДНЕВНИК ====================
            diary_service = DiaryEventService(self.db_session)
            await diary_service.record_event(
                user_id=user_id,
                event_type="dynamics_report",
                source="dynamics",
                role="system",
                content=report_data.get("summary", "Отчёт динамики"),
                payload={
                    "period_from": start_date.isoformat(),
                    "period_to": end_date.isoformat(),
                    "period_days": period_days,
                    "report": report_data,
                },
            )
            # ====================================================================

            return {
                "success": True,
                "report": report_data,
                "events_count": len(events),
                "period_days": period_days,
                "start_date": start_date,
                "end_date": end_date,
            }

        except YandexGPTError as e:
            logger.error(f"YandexGPT error in dynamics: {e}")
            return self._create_fallback_report(start_date, end_date, len(events))

        except Exception as e:
            logger.error(f"Error in dynamics: {e}")
            return self._create_fallback_report(start_date, end_date, len(events))

    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Парсит JSON-ответ от YandexGPT."""
        try:
            # Ищем JSON в ответе
            brace_count = 0
            start = -1
            for i, char in enumerate(response):
                if char == '{':
                    if brace_count == 0:
                        start = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start != -1:
                        json_str = response[start:i+1]
                        break
            else:
                data = json.loads(response)
                return data
            
            data = json.loads(json_str)
            
            # Проверяем обязательные поля
            required = ["summary", "mood_analysis", "energy_analysis", 
                       "tension_analysis", "sleep_analysis", "recurring_states",
                       "recommendations"]
            for field in required:
                if field not in data:
                    data[field] = "Нет данных" if field.endswith("analysis") else []
            
            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in dynamics: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing dynamics response: {e}")
            return None

    def _create_fallback_report(
        self,
        start_date: date,
        end_date: date,
        events_count: int,
    ) -> Dict[str, Any]:
        """Создаёт отчёт-заглушку при ошибке."""
        return {
            "success": True,
            "report": {
                "summary": f"За период {start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')} зафиксировано {events_count} событий.",
                "mood_analysis": "Недостаточно данных для анализа настроения.",
                "energy_analysis": "Недостаточно данных для анализа энергии.",
                "tension_analysis": "Недостаточно данных для анализа напряжения.",
                "sleep_analysis": "Недостаточно данных для анализа сна.",
                "recurring_states": ["Продолжай наблюдение"],
                "improvement_factors": ["Продолжай вести дневник"],
                "decline_factors": ["Для точного анализа нужно больше данных"],
                "progress": ["Начат сбор данных"],
                "recommendations": [
                    "Продолжай описывать своё состояние",
                    "Проходи опросы для сбора большего количества данных",
                ],
            },
            "events_count": events_count,
            "period_days": (end_date - start_date).days + 1,
            "start_date": start_date,
            "end_date": end_date,
        }