"""
Сервис для преобразования событий дневника в структурированные данные для AI.
"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

from app.db.models.diary_event import DiaryEvent
from app.utils.logging import logger


class DynamicsDataBuilder:
    """
    Строит структурированные данные из событий дневника для отправки в YandexGPT.
    """

    @staticmethod
    def build(
        events: List[DiaryEvent],
        start_date: date,
        end_date: date,
        user_timezone: str = "UTC",
    ) -> Dict[str, Any]:
        """
        Преобразует события в структурированный JSON для AI.
        """
        try:
            tz = ZoneInfo(user_timezone)
        except:
            tz = ZoneInfo("UTC")

        # Группируем события по дням
        events_by_day = {}
        for event in events:
            event_date = event.event_date
            if event_date not in events_by_day:
                events_by_day[event_date] = []
            events_by_day[event_date].append(event)

        # Сортируем дни
        sorted_dates = sorted(events_by_day.keys())

        # Собираем данные
        result = {
            "period": {
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
                "days": (end_date - start_date).days + 1,
            },
            "total_events": len(events),
            "daily_data": [],
            "all_descriptions": [],
            "all_analyses": [],
            "survey_data": {
                "morning": [],
                "day": [],
                "evening": [],
            },
            "summary": {
                "mood_values": [],
                "energy_values": [],
                "body_tension_values": [],
                "sleep_values": [],
            },
        }

        for day in sorted_dates:
            day_events = events_by_day.get(day, [])
            
            # Собираем данные за день
            day_data = {
                "date": day.strftime("%Y-%m-%d"),
                "events": [],
                "mood": None,
                "energy": None,
                "body_tension": None,
                "sleep": None,
                "descriptions": [],
                "analyses": [],
            }

            for event in day_events:
                # Добавляем событие
                event_info = {
                    "type": event.event_type,
                    "source": event.source,
                    "time": event.created_at.astimezone(tz).strftime("%H:%M"),
                    "content": event.content[:200] if event.content else None,
                }
                
                # Извлекаем метрики из payload
                if event.payload:
                    if "mood" in event.payload:
                        day_data["mood"] = event.payload.get("mood")
                        result["summary"]["mood_values"].append(day_data["mood"])
                    if "energy" in event.payload:
                        day_data["energy"] = event.payload.get("energy")
                        result["summary"]["energy_values"].append(day_data["energy"])
                    if "body_tension" in event.payload:
                        day_data["body_tension"] = event.payload.get("body_tension")
                        result["summary"]["body_tension_values"].append(day_data["body_tension"])
                    if "sleep" in event.payload:
                        day_data["sleep"] = event.payload.get("sleep")
                        result["summary"]["sleep_values"].append(day_data["sleep"])

                # Собираем описания и анализы
                if event.event_type == "describe_user":
                    result["all_descriptions"].append({
                        "date": day.strftime("%Y-%m-%d"),
                        "time": event.created_at.astimezone(tz).strftime("%H:%M"),
                        "content": event.content,
                    })
                
                if event.event_type == "analysis":
                    result["all_analyses"].append({
                        "date": day.strftime("%Y-%m-%d"),
                        "content": event.content[:300] if event.content else None,
                    })
                    if event.payload and "summary" in event.payload:
                        result["all_analyses"][-1]["summary"] = event.payload.get("summary")

                # Сортируем по типу опроса
                if event.source == "morning_survey":
                    result["survey_data"]["morning"].append({
                        "date": day.strftime("%Y-%m-%d"),
                        "answer": event.content,
                        "payload": event.payload,
                    })
                elif event.source == "day_survey":
                    result["survey_data"]["day"].append({
                        "date": day.strftime("%Y-%m-%d"),
                        "answer": event.content,
                        "payload": event.payload,
                    })
                elif event.source == "evening_survey":
                    result["survey_data"]["evening"].append({
                        "date": day.strftime("%Y-%m-%d"),
                        "answer": event.content,
                        "payload": event.payload,
                    })

                day_data["events"].append(event_info)

            result["daily_data"].append(day_data)

        # Вычисляем средние значения
        for key in ["mood_values", "energy_values", "body_tension_values", "sleep_values"]:
            values = result["summary"].get(key, [])
            if values:
                result["summary"][key.replace("_values", "_average")] = sum(values) / len(values)
            else:
                result["summary"][key.replace("_values", "_average")] = None

        return result

    @staticmethod
    def build_prompt(data: Dict[str, Any]) -> str:
        """
        Формирует промпт для YandexGPT на основе структурированных данных.
        """
        period = data.get("period", {})
        days = period.get("days", 0)
        
        prompt = f"""
Проанализируй данные пользователя за период {period.get('from')} — {period.get('to')} ({days} дней).

Всего зафиксировано {data.get('total_events', 0)} событий.

"""
        # Добавляем сводку по дням
        if data.get("daily_data"):
            prompt += "=== ДАННЫЕ ПО ДНЯМ ===\n\n"
            for day_data in data.get("daily_data", []):
                prompt += f"📅 {day_data.get('date')}\n"
                if day_data.get("mood") is not None:
                    prompt += f"  Настроение: {day_data.get('mood')}/10\n"
                if day_data.get("energy") is not None:
                    prompt += f"  Энергия: {day_data.get('energy')}/10\n"
                if day_data.get("body_tension") is not None:
                    prompt += f"  Напряжение тела: {day_data.get('body_tension')}/10\n"
                if day_data.get("sleep") is not None:
                    prompt += f"  Сон: {day_data.get('sleep')} ч\n"
                prompt += "\n"

        # Добавляем описания состояний
        if data.get("all_descriptions"):
            prompt += "=== ОПИСАНИЯ СОСТОЯНИЙ ===\n\n"
            for desc in data.get("all_descriptions", [])[:5]:
                prompt += f"{desc.get('date')} {desc.get('time')}: {desc.get('content')}\n\n"

        # Добавляем анализы
        if data.get("all_analyses"):
            prompt += "=== ПРЕДЫДУЩИЕ АНАЛИЗЫ ===\n\n"
            for analysis in data.get("all_analyses", [])[:3]:
                if analysis.get("summary"):
                    prompt += f"{analysis.get('date')}: {analysis.get('summary')}\n\n"

        # Добавляем опросы
        survey_types = {
            "morning": "УТРЕННИЕ ОПРОСЫ",
            "day": "ДНЕВНЫЕ ОПРОСЫ",
            "evening": "ВЕЧЕРНИЕ ОПРОСЫ",
        }
        for survey_key, survey_name in survey_types.items():
            if data.get("survey_data", {}).get(survey_key):
                prompt += f"=== {survey_name} ===\n\n"
                for item in data.get("survey_data", {}).get(survey_key, []):
                    prompt += f"{item.get('date')}: {item.get('answer')}\n"
                prompt += "\n"

        # Добавляем сводку
        summary = data.get("summary", {})
        if summary.get("mood_average") is not None:
            prompt += f"Среднее настроение за период: {summary.get('mood_average'):.1f}/10\n"
        if summary.get("energy_average") is not None:
            prompt += f"Средняя энергия: {summary.get('energy_average'):.1f}/10\n"
        if summary.get("body_tension_average") is not None:
            prompt += f"Среднее напряжение тела: {summary.get('body_tension_average'):.1f}/10\n"
        if summary.get("sleep_average") is not None:
            prompt += f"Средний сон: {summary.get('sleep_average'):.1f} ч\n"

        prompt += """

=== ЗАДАНИЕ ===

Проанализируй данные пользователя и составь отчёт по следующей структуре:

1. Общая картина — что происходило за период (2-3 предложения)
2. Настроение — изменения, тенденции
3. Энергия — изменения, тенденции  
4. Телесное напряжение — изменения, тенденции
5. Сон — изменения, тенденции
6. Повторяющиеся состояния — что чаще всего возникало
7. Факторы ухудшения — что влияло негативно
8. Факторы улучшения — что помогало
9. Прогресс — что изменилось положительно
10. Рекомендации — 1-2 конкретные рекомендации

ВАЖНЫЕ ПРАВИЛА:
- Используй ТОЛЬКО данные из контекста
- Не придумывай значения
- Если данных недостаточно — укажи это
- Будь поддерживающим и бережным
- Не ставь диагнозов
- Отвечай на русском языке

ОТВЕЧАЙ В ФОРМАТЕ JSON:
{
    "summary": "Общая картина",
    "mood_analysis": "Анализ настроения",
    "energy_analysis": "Анализ энергии",
    "tension_analysis": "Анализ напряжения тела",
    "sleep_analysis": "Анализ сна",
    "recurring_states": ["состояние 1", "состояние 2"],
    "improvement_factors": ["фактор 1", "фактор 2"],
    "decline_factors": ["фактор 1", "фактор 2"],
    "progress": ["прогресс 1", "прогресс 2"],
    "recommendations": ["рекомендация 1", "рекомендация 2"]
}
"""

        return prompt