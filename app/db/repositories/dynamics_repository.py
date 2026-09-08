"""
Репозиторий для сбора статистики из дневника для динамики.
"""
from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional

from app.db.models.diary import DiaryEntry
from app.db.models.user import User
from app.utils.logging import logger


class DynamicsRepository:
    """Репозиторий для сбора данных динамики."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_entries_for_period(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> List[DiaryEntry]:
        """
        Получает все записи дневника за период.
        """
        result = await self.session.execute(
            select(DiaryEntry)
            .where(
                DiaryEntry.user_id == user_id,
                func.date(DiaryEntry.created_at) >= start_date,
                func.date(DiaryEntry.created_at) <= end_date,
            )
            .order_by(DiaryEntry.created_at.asc())
        )
        return result.scalars().all()

    async def get_dynamics_data(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        Собирает статистику за период.
        """
        entries = await self.get_entries_for_period(user_id, start_date, end_date)
        
        if not entries:
            return {
                "entries": [],
                "count": 0,
                "start_date": start_date,
                "end_date": end_date,
                "period_days": (end_date - start_date).days + 1,
            }

        # Собираем данные
        data = {
            "entries": [],
            "count": len(entries),
            "start_date": start_date,
            "end_date": end_date,
            "period_days": (end_date - start_date).days + 1,
            
            # Статистика по типам записей
            "survey_morning": [],
            "survey_day": [],
            "survey_evening": [],
            "describe_state": [],
            "analysis": [],
            "clarification": [],
            
            # Общие показатели
            "mood_values": [],
            "stress_values": [],
            "sleep_values": [],
            "intensity_values": [],
        }

        for entry in entries:
            entry_data = {
                "date": entry.created_at,
                "type": entry.entry_type,
                "entry": entry,
            }
            
            data["entries"].append(entry_data)
            
            # Сортируем по типу
            if entry.entry_type in data:
                data[entry.entry_type].append(entry)
            
            # Собираем числовые показатели
            # Из утреннего опроса
            if entry.entry_type == "survey_morning":
                # Извлекаем числовые значения из текста
                pass
            
            # Из дневного опроса
            if entry.entry_type == "survey_day":
                pass
            
            # Из вечернего опроса
            if entry.entry_type == "survey_evening":
                pass
            
            # Из описания состояния
            if entry.entry_type == "describe_state":
                pass

        return data

    async def get_mood_stats(self, entries: List[DiaryEntry]) -> Dict[str, Any]:
        """
        Анализирует настроение из записей.
        """
        mood_values = []
        for entry in entries:
            # Из утреннего опроса
            if entry.entry_type == "survey_morning" and entry.morning_q3:
                mood_map = {
                    "Спокойное": 4,
                    "Радостное": 5,
                    "Нейтральное": 3,
                    "Тревожное": 2,
                    "Раздражённое": 1,
                }
                val = mood_map.get(entry.morning_q3)
                if val:
                    mood_values.append(val)
            
            # Из вечернего опроса
            if entry.entry_type == "survey_evening" and entry.evening_q1:
                mood_map = {
                    "Хорошо": 4,
                    "Нормально": 3,
                    "Тревожно": 2,
                    "Устало": 2,
                }
                val = mood_map.get(entry.evening_q1)
                if val:
                    mood_values.append(val)
        
        if not mood_values:
            return {"average": None, "min": None, "max": None, "count": 0}
        
        return {
            "average": sum(mood_values) / len(mood_values),
            "min": min(mood_values),
            "max": max(mood_values),
            "count": len(mood_values),
        }

    async def get_stress_stats(self, entries: List[DiaryEntry]) -> Dict[str, Any]:
        """
        Анализирует стресс из записей.
        """
        stress_values = []
        for entry in entries:
            if entry.entry_type == "survey_morning":
                # Ищем упоминания стресса в тексте
                text = f"{entry.morning_q1 or ''} {entry.morning_q2 or ''} {entry.morning_q3 or ''} {entry.morning_q4 or ''}"
                if "тревог" in text.lower() or "стресс" in text.lower():
                    stress_values.append(5)
            
            if entry.entry_type == "survey_evening" and entry.evening_q2:
                stress_map = {
                    "Стресс": 7,
                    "Работа": 5,
                    "Переживания": 6,
                    "Недосып": 4,
                }
                val = stress_map.get(entry.evening_q2)
                if val:
                    stress_values.append(val)
        
        if not stress_values:
            return {"average": None, "min": None, "max": None, "count": 0}
        
        return {
            "average": sum(stress_values) / len(stress_values),
            "min": min(stress_values),
            "max": max(stress_values),
            "count": len(stress_values),
        }

    async def get_sleep_stats(self, entries: List[DiaryEntry]) -> Dict[str, Any]:
        """
        Анализирует сон из записей.
        """
        sleep_values = []
        for entry in entries:
            if entry.entry_type == "survey_morning" and entry.morning_q5:
                sleep_map = {
                    "Отлично": 8,
                    "Часто просыпался": 5,
                    "Плохо": 4,
                    "Видел сны": 6,
                }
                val = sleep_map.get(entry.morning_q5)
                if val:
                    sleep_values.append(val)
        
        if not sleep_values:
            return {"average": None, "min": None, "max": None, "count": 0}
        
        return {
            "average": sum(sleep_values) / len(sleep_values),
            "min": min(sleep_values),
            "max": max(sleep_values),
            "count": len(sleep_values),
        }

    async def get_top_symptoms(self, entries: List[DiaryEntry], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получает топ-5 повторяющихся симптомов.
        """
        symptom_counts = {}
        
        for entry in entries:
            if entry.entry_type == "survey_morning" and entry.morning_q2:
                symptom = entry.morning_q2
                symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
            
            if entry.entry_type == "survey_evening" and entry.evening_q1:
                if entry.evening_q1 not in ["Хорошо", "Нормально", "Тревожно", "Устало"]:
                    symptom = entry.evening_q1
                    symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
            
            if entry.entry_type == "describe_state" and entry.description:
                # Просто берём первые 50 символов как симптом
                symptom = entry.description[:50]
                symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
        
        sorted_symptoms = sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"symptom": s, "count": c}
            for s, c in sorted_symptoms[:limit]
        ]

    async def get_factors(self, entries: List[DiaryEntry]) -> Dict[str, int]:
        """
        Анализирует факторы, влияющие на состояние.
        """
        factors = {}
        
        for entry in entries:
            # Из дневного опроса
            if entry.entry_type == "survey_day" and entry.day_q3:
                factor = entry.day_q3
                factors[factor] = factors.get(factor, 0) + 1
            
            # Из вечернего опроса
            if entry.entry_type == "survey_evening":
                if entry.evening_q2:
                    factor = entry.evening_q2
                    factors[factor] = factors.get(factor, 0) + 1
                if entry.evening_q3:
                    factor = entry.evening_q3
                    factors[factor] = factors.get(factor, 0) + 1
                if entry.evening_q4:
                    factor = entry.evening_q4
                    factors[factor] = factors.get(factor, 0) + 1
        
        return dict(sorted(factors.items(), key=lambda x: x[1], reverse=True))