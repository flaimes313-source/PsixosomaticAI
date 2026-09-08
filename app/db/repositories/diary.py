"""
Репозиторий для работы с дневником.
"""
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from app.db.models.diary import DiaryEntry
from app.db.models.analysis import Analysis
from app.db.models.clarification import Clarification
from app.utils.logging import logger


class DiaryRepository:
    """Репозиторий для операций с дневником."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== ОСНОВНЫЕ МЕТОДЫ ====================

    async def create_entry(self, **kwargs) -> DiaryEntry:
        """
        Создаёт запись в дневнике.
        """
        entry = DiaryEntry(**kwargs)
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def get_entry(self, entry_id: int, user_id: int) -> Optional[DiaryEntry]:
        """Получает запись по ID."""
        result = await self.session.execute(
            select(DiaryEntry).where(
                DiaryEntry.id == entry_id,
                DiaryEntry.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_entries_by_date(
        self,
        user_id: int,
        entry_date: date,
    ) -> List[DiaryEntry]:
        """Получает записи за конкретную дату."""
        result = await self.session.execute(
            select(DiaryEntry)
            .where(
                DiaryEntry.user_id == user_id,
                func.date(DiaryEntry.created_at) == entry_date
            )
            .order_by(DiaryEntry.created_at.asc())
        )
        return result.scalars().all()

    async def get_today_entries(self, user_id: int) -> List[DiaryEntry]:
        """Получает записи за сегодня."""
        today = date.today()
        return await self.get_entries_by_date(user_id, today)

    async def get_dates_with_entries(
        self,
        user_id: int,
        limit: int = 15,
    ) -> List[tuple]:
        """Получает даты с записями."""
        result = await self.session.execute(
            select(
                func.date(DiaryEntry.created_at).label("entry_date"),
                func.count(DiaryEntry.id).label("count")
            )
            .where(DiaryEntry.user_id == user_id)
            .group_by(func.date(DiaryEntry.created_at))
            .order_by(desc(func.date(DiaryEntry.created_at)))
            .limit(limit)
        )
        return [(row.entry_date, row.count) for row in result.all()]

    async def get_entries_count_by_user(self, user_id: int) -> int:
        """Получает общее количество записей пользователя."""
        result = await self.session.execute(
            select(func.count()).select_from(DiaryEntry).where(
                DiaryEntry.user_id == user_id
            )
        )
        return result.scalar() or 0

    async def delete_entry(self, entry_id: int, user_id: int) -> bool:
        """Удаляет запись."""
        entry = await self.get_entry(entry_id, user_id)
        if not entry:
            return False
        await self.session.delete(entry)
        await self.session.commit()
        return True

    # ==================== МЕТОДЫ ДЛЯ СОХРАНЕНИЯ ====================

    async def save_survey_morning(
        self,
        user_id: int,
        answers: Dict[str, Any],
        analysis_text: Optional[str] = None,
        micro_action: Optional[str] = None,
        summary: Optional[str] = None,
        medical_warning: Optional[str] = None,
        analysis_id: Optional[int] = None,
    ) -> DiaryEntry:
        """
        Сохраняет утренний опрос в дневник.
        """
        symptom_text = f"Утренний опрос: {answers.get('q1', '')} {answers.get('q2', '')}"
        return await self.create_entry(
            user_id=user_id,
            entry_type="survey_morning",
            symptom=symptom_text[:200],
            symptom_intensity=5,
            mood=3,
            morning_q1=answers.get("q1"),
            morning_q2=answers.get("q2"),
            morning_q3=answers.get("q3"),
            morning_q4=answers.get("q4"),
            morning_q5=answers.get("q5"),
            morning_clarification=answers.get("clarification"),
            analysis_text=analysis_text,
            micro_action=micro_action,
            summary=summary,
            medical_warning=medical_warning,
            analysis_id=analysis_id,
        )

    async def save_survey_day(
        self,
        user_id: int,
        answers: Dict[str, Any],
        analysis_id: Optional[int] = None,
    ) -> DiaryEntry:
        """
        Сохраняет дневной опрос в дневник.
        """
        symptom_text = f"Дневной опрос: {answers.get('q1', '')}"
        return await self.create_entry(
            user_id=user_id,
            entry_type="survey_day",
            symptom=symptom_text[:200],
            symptom_intensity=5,
            mood=3,
            day_q1=answers.get("q1"),
            day_q2=answers.get("q2"),
            day_q3=answers.get("q3"),
            analysis_id=analysis_id,
        )

    async def save_survey_evening(
        self,
        user_id: int,
        answers: Dict[str, Any],
        analysis_text: Optional[str] = None,
        micro_action: Optional[str] = None,
        summary: Optional[str] = None,
        medical_warning: Optional[str] = None,
        analysis_id: Optional[int] = None,
    ) -> DiaryEntry:
        """
        Сохраняет вечерний опрос в дневник.
        """
        symptom_text = f"Вечерний опрос: {answers.get('q1', '')}"
        return await self.create_entry(
            user_id=user_id,
            entry_type="survey_evening",
            symptom=symptom_text[:200],
            symptom_intensity=5,
            mood=3,
            evening_q1=answers.get("q1"),
            evening_q2=answers.get("q2"),
            evening_q3=answers.get("q3"),
            evening_q4=answers.get("q4"),
            evening_q5=answers.get("q5"),
            evening_clarification=answers.get("clarification"),
            analysis_text=analysis_text,
            micro_action=micro_action,
            summary=summary,
            medical_warning=medical_warning,
            analysis_id=analysis_id,
        )

    async def save_describe_state(
        self,
        user_id: int,
        description: str,
        ai_response: str,
        analysis_id: Optional[int] = None,
        analysis_text: Optional[str] = None,
        micro_action: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> DiaryEntry:
        """
        Сохраняет запись через «Описать состояние» в дневник.
        """
        return await self.create_entry(
            user_id=user_id,
            entry_type="describe_state",
            symptom=description[:200],
            symptom_intensity=5,
            mood=3,  # ← ДОБАВЛЯЕМ
            description=description,
            ai_response=ai_response,
            analysis_text=analysis_text or ai_response,
            micro_action=micro_action,
            summary=summary or description[:100],
            analysis_id=analysis_id,
        )

    async def save_clarification(
        self,
        user_id: int,
        question: str,
        answer: str,
        analysis_id: int,
    ) -> DiaryEntry:
        """
        Сохраняет уточняющий вопрос и ответ в дневник.
        """
        return await self.create_entry(
            user_id=user_id,
            entry_type="clarification",
            symptom=question[:200],
            symptom_intensity=5,
            mood=3,
            clarification_question=question,
            clarification_answer=answer,
            analysis_id=analysis_id,
        )

    async def save_analysis(
        self,
        user_id: int,
        symptom: str,
        analysis_text: str,
        micro_action: Optional[str] = None,
        summary: Optional[str] = None,
        medical_warning: Optional[str] = None,
        analysis_id: Optional[int] = None,
    ) -> DiaryEntry:
        """
        Сохраняет разбор (анализ) в дневник.
        """
        return await self.create_entry(
            user_id=user_id,
            entry_type="analysis",
            symptom=symptom[:200],
            symptom_intensity=5,
            mood=3,
            description=symptom,
            analysis_text=analysis_text,
            micro_action=micro_action,
            summary=summary,
            medical_warning=medical_warning,
            analysis_id=analysis_id,
        )