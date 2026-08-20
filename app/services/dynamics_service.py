"""
Сервис для расчёта статистики и подготовки данных для AI.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from collections import Counter

from app.db.repositories.diary import DiaryRepository
from app.db.repositories.analysis import AnalysisRepository
from app.schemas.dynamics import (
    DynamicsStatistics,
    PeriodType,
    SymptomStats,
    PeriodStats
)
from app.utils.logging import logger


class DynamicsService:
    """Сервис для анализа динамики симптомов."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.diary_repo = DiaryRepository(db_session)
        self.analysis_repo = AnalysisRepository(db_session)

    async def calculate_statistics(
        self,
        user_id: int,
        period_type: PeriodType
    ) -> Optional[DynamicsStatistics]:
        """Рассчитать статистику за период."""
        # Определяем период
        days_map = {
            PeriodType.DAYS_7: 7,
            PeriodType.DAYS_14: 14,
            PeriodType.DAYS_30: 30,
            PeriodType.DAYS_90: 90,
        }
        period_days = days_map[period_type]
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        # Получаем записи за период
        entries = await self.diary_repo.get_entries_by_date_range(
            user_id, start_date, end_date
        )

        if len(entries) < 3:
            logger.info(f"Not enough entries for dynamics: {len(entries)}")
            return None

        # --- 1. Общая статистика ---
        intensities = [e.symptom_intensity for e in entries]
        stresses = [e.stress for e in entries]
        moods = [e.mood for e in entries]
        sleeps = [e.sleep_hours for e in entries]

        stats = DynamicsStatistics(
            period_type=period_type,
            period_days=period_days,
            entries_count=len(entries),
            start_date=start_date,
            end_date=end_date,
            
            average_intensity=round(sum(intensities) / len(intensities), 1),
            min_intensity=min(intensities),
            max_intensity=max(intensities),
            
            average_stress=round(sum(stresses) / len(stresses), 1),
            min_stress=min(stresses),
            max_stress=max(stresses),
            
            average_mood=round(sum(moods) / len(moods), 1),
            min_mood=min(moods),
            max_mood=max(moods),
            
            average_sleep=round(sum(sleeps) / len(sleeps), 1),
            min_sleep=min(sleeps),
            max_sleep=max(sleeps),
        )

        # --- 2. Топ симптомов ---
        symptom_counter = Counter()
        symptom_intensities = {}
        
        for entry in entries:
            symptom_counter[entry.symptom] += 1
            if entry.symptom not in symptom_intensities:
                symptom_intensities[entry.symptom] = []
            symptom_intensities[entry.symptom].append(entry.symptom_intensity)

        top_symptoms = []
        for symptom, count in symptom_counter.most_common(5):
            avg_intensity = round(sum(symptom_intensities[symptom]) / len(symptom_intensities[symptom]), 1)
            top_symptoms.append(SymptomStats(
                symptom=symptom,
                count=count,
                average_intensity=avg_intensity,
                min_intensity=min(symptom_intensities[symptom]),
                max_intensity=max(symptom_intensities[symptom])
            ))
        stats.top_symptoms = top_symptoms

        # --- 3. Сравнение первой и последней части периода ---
        if len(entries) >= 6:
            half = len(entries) // 2
            first_half = entries[:half]
            last_half = entries[-half:]

            stats.first_period = self._calculate_period_stats(first_half)
            stats.last_period = self._calculate_period_stats(last_half)

        # --- 4. Корреляции ---
        stats.stress_symptom_comparison = self._compare_by_stress(entries)
        stats.sleep_symptom_comparison = self._compare_by_sleep(entries)
        stats.mood_symptom_comparison = self._compare_by_mood(entries)

        # --- 5. Контексты ---
        contexts = [e.context for e in entries if e.context]
        if contexts:
            stats.relevant_contexts = contexts[-5:]  # Последние 5
            context_counter = Counter()
            for ctx in contexts:
                # Простое выделение ключевых слов
                words = ctx.lower().split()
                for word in words:
                    if len(word) > 3:
                        context_counter[word] += 1
            
            stats.frequent_contexts = [
                {"word": word, "count": count}
                for word, count in context_counter.most_common(5)
            ]

        # --- 6. Предыдущие анализы (кратко) --- ИСПРАВЛЕНО
        analyses = await self.analysis_repo.get_user_analyses(user_id, limit=3)
        if analyses:
            summary_parts = []
            for analysis in analyses:
                if analysis.symptom:
                    # Используем поле analysis (текст) вместо possible_causes
                    analysis_text = analysis.analysis[:80] if analysis.analysis else ""
                    summary_parts.append(f"{analysis.symptom}: {analysis_text}...")
            stats.previous_analyses_summary = "\n".join(summary_parts)

        logger.info(f"Calculated dynamics statistics for user {user_id}: {len(entries)} entries")
        return stats

    def _calculate_period_stats(self, entries) -> PeriodStats:
        """Рассчитать статистику для одного периода."""
        return PeriodStats(
            start_date=entries[0].created_at,
            end_date=entries[-1].created_at,
            entries_count=len(entries),
            average_intensity=round(sum(e.symptom_intensity for e in entries) / len(entries), 1),
            average_stress=round(sum(e.stress for e in entries) / len(entries), 1),
            average_mood=round(sum(e.mood for e in entries) / len(entries), 1),
            average_sleep=round(sum(e.sleep_hours for e in entries) / len(entries), 1),
        )

    def _compare_by_stress(self, entries) -> Dict[str, Any]:
        """Сравнить интенсивность симптомов при разном стрессе."""
        high_stress = [e for e in entries if e.stress >= 7]
        low_stress = [e for e in entries if e.stress <= 4]

        result = {}
        if high_stress:
            result["high_stress_intensity"] = round(
                sum(e.symptom_intensity for e in high_stress) / len(high_stress), 1
            )
            result["high_stress_count"] = len(high_stress)
        if low_stress:
            result["low_stress_intensity"] = round(
                sum(e.symptom_intensity for e in low_stress) / len(low_stress), 1
            )
            result["low_stress_count"] = len(low_stress)
        return result

    def _compare_by_sleep(self, entries) -> Dict[str, Any]:
        """Сравнить интенсивность симптомов при разном сне."""
        good_sleep = [e for e in entries if e.sleep_hours >= 7]
        bad_sleep = [e for e in entries if e.sleep_hours < 6]

        result = {}
        if good_sleep:
            result["good_sleep_intensity"] = round(
                sum(e.symptom_intensity for e in good_sleep) / len(good_sleep), 1
            )
            result["good_sleep_count"] = len(good_sleep)
        if bad_sleep:
            result["bad_sleep_intensity"] = round(
                sum(e.symptom_intensity for e in bad_sleep) / len(bad_sleep), 1
            )
            result["bad_sleep_count"] = len(bad_sleep)
        return result

    def _compare_by_mood(self, entries) -> Dict[str, Any]:
        """Сравнить интенсивность симптомов при разном настроении."""
        good_mood = [e for e in entries if e.mood >= 4]
        bad_mood = [e for e in entries if e.mood <= 2]

        result = {}
        if good_mood:
            result["good_mood_intensity"] = round(
                sum(e.symptom_intensity for e in good_mood) / len(good_mood), 1
            )
            result["good_mood_count"] = len(good_mood)
        if bad_mood:
            result["bad_mood_intensity"] = round(
                sum(e.symptom_intensity for e in bad_mood) / len(bad_mood), 1
            )
            result["bad_mood_count"] = len(bad_mood)
        return result