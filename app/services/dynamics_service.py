"""
Сервис для формирования отчёта динамики.
"""
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.dynamics_repository import DynamicsRepository
from app.services.ai_service import ai_service
from app.schemas.dynamics import DynamicsStatistics
from app.utils.logging import logger


class DynamicsService:
    """Сервис для работы с динамикой."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.repository = DynamicsRepository(db_session)

    async def get_report(
        self,
        user_id: int,
        period_days: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
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

        # Получаем данные из репозитория
        data = await self.repository.get_dynamics_data(user_id, start_date, end_date)
        
        if data["count"] == 0:
            return {
                "success": False,
                "message": f"За период с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')} записей нет.",
                "data": data,
            }

        # Собираем статистику
        entries = data["entries"]
        entries_list = [e["entry"] for e in entries]
        
        mood_stats = await self.repository.get_mood_stats(entries_list)
        stress_stats = await self.repository.get_stress_stats(entries_list)
        sleep_stats = await self.repository.get_sleep_stats(entries_list)
        top_symptoms = await self.repository.get_top_symptoms(entries_list)
        factors = await self.repository.get_factors(entries_list)

        # Формируем статистику для AI
        stats = DynamicsStatistics(
            period_days=data["period_days"],
            entries_count=data["count"],
            start_date=start_date,
            end_date=end_date,
            average_mood=mood_stats.get("average", 0),
            min_mood=mood_stats.get("min", 0),
            max_mood=mood_stats.get("max", 0),
            average_stress=stress_stats.get("average", 0),
            min_stress=stress_stats.get("min", 0),
            max_stress=stress_stats.get("max", 0),
            average_sleep=sleep_stats.get("average", 0),
            min_sleep=sleep_stats.get("min", 0),
            max_sleep=sleep_stats.get("max", 0),
            top_symptoms=top_symptoms,
            relevant_contexts=list(factors.keys())[:5],
        )

        # Отправляем в AI
        report = await ai_service.analyze_dynamics(stats)
        
        if report:
            return {
                "success": True,
                "report": report,
                "data": data,
                "stats": stats,
            }
        else:
            # fallback-отчёт
            return {
                "success": True,
                "report": self._create_fallback_report(stats),
                "data": data,
                "stats": stats,
            }

    def _create_fallback_report(self, stats: DynamicsStatistics) -> Dict[str, Any]:
        """
        Создаёт отчёт-заглушку при ошибке AI.
        """
        return {
            "summary": f"За {stats.period_days} дней сделано {stats.entries_count} записей.",
            "main_patterns": [
                f"Настроение в среднем: {stats.average_mood:.1f}/5" if stats.average_mood else "Нет данных о настроении",
                f"Стресс в среднем: {stats.average_stress:.1f}/10" if stats.average_stress else "Нет данных о стрессе",
                f"Сон в среднем: {stats.average_sleep:.1f} ч" if stats.average_sleep else "Нет данных о сне",
            ],
            "possible_connections": [],
            "positive_changes": [],
            "areas_to_watch": [
                "Продолжай отслеживать своё состояние",
                "Обрати внимание на регулярность записей",
            ],
            "next_steps": [
                "Веди дневник регулярно",
                "Отслеживай связь между настроением и событиями",
            ],
            "medical_note": "ℹ️ Это наблюдение по дневниковым данным, а не медицинская диагностика.",
        }