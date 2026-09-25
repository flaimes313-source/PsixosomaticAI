"""
Сервис для преобразования событий дневника в структурированные данные для AI.

Простая логика:
- Собираем только сообщения пользователя (describe_user).
- Формируем текстовый промпт со списком записей за период.
- Никаких метрик, шкал, опросов и старых анализов.
"""
from datetime import date, datetime
from typing import List, Dict, Any
from zoneinfo import ZoneInfo

from app.db.models.diary_event import DiaryEvent
from app.utils.logging import logger


class DynamicsDataBuilder:
    """
    Строит текстовый промпт из событий дневника для отправки в YandexGPT.
    """

    @staticmethod
    def build(
        events: List[DiaryEvent],
        start_date: date,
        end_date: date,
        user_timezone: str = "UTC",
    ) -> Dict[str, Any]:
        """
        Преобразует события в структуру:
        {
            "period": {...},
            "total_events": N,
            "entries": [
                {"date": "2026-09-20", "time": "14:32", "content": "..."},
                ...
            ]
        }
        """
        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        entries = []

        for event in events:
            # Берём только сообщения пользователя (то, что он сам написал)
            if event.event_type != "describe_user":
                continue

            if not event.content:
                continue

            # Локальное время
            try:
                local_time = event.created_at.astimezone(tz)
            except Exception:
                local_time = event.created_at

            entries.append({
                "date": local_time.strftime("%Y-%m-%d"),
                "time": local_time.strftime("%H:%M"),
                "content": event.content.strip(),
            })

        # Сортируем по дате+времени
        entries.sort(key=lambda x: (x["date"], x["time"]))

        return {
            "period": {
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
                "days": (end_date - start_date).days + 1,
            },
            "total_events": len(events),
            "total_entries": len(entries),
            "entries": entries,
        }

    @staticmethod
    def build_prompt(data: Dict[str, Any]) -> str:
        """
        Формирует текстовый промпт с записями пользователя за период.

        Никаких JSON-инструкций и метрик — только записи.
        Функция анализа — в системном промпте DYNAMICS_PROMPT.
        """
        period = data.get("period", {})
        entries = data.get("entries", [])

        prompt = (
            f"Период: {period.get('from')} — {period.get('to')} "
            f"({period.get('days')} дней)\n"
            f"Всего записей пользователя: {len(entries)}\n\n"
        )

        if not entries:
            prompt += "Записей за период нет.\n"
            return prompt

        prompt += "=== ЗАПИСИ ПОЛЬЗОВАТЕЛЯ ===\n\n"

        for entry in entries:
            prompt += (
                f"[{entry['date']} {entry['time']}]\n"
                f"{entry['content']}\n\n"
            )

        prompt += (
            "=== ЗАДАНИЕ ===\n\n"
            "Проанализируй записи и составь наблюдения по структуре, "
            "которая описана в системной инструкции.\n"
        )

        return prompt