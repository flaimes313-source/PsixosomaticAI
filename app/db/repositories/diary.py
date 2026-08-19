"""
Репозиторий для работы с дневниковыми записями.
"""
from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple

from app.db.models.diary import DiaryEntry
from app.utils.logging import logger


class DiaryRepository:
    """Репозиторий для операций с дневниковыми записями"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_entry(
        self,
        user_id: int,
        symptom: str,
        symptom_intensity: int,
        mood: int,
        stress: int,
        sleep_hours: float,
        context: Optional[str] = None,
        note: Optional[str] = None,
        analysis_id: Optional[int] = None,
        entry_date: Optional[date] = None,
    ) -> DiaryEntry:
        """
        Создает новую дневниковую запись.
        """
        if entry_date is None:
            entry_date = date.today()
        
        entry = DiaryEntry(
            user_id=user_id,
            analysis_id=analysis_id,
            symptom=symptom,
            symptom_intensity=symptom_intensity,
            mood=mood,
            stress=stress,
            sleep_hours=sleep_hours,
            context=context,
            note=note,
            entry_date=entry_date,
        )
        
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        
        logger.info(f"Diary entry created: user_id={user_id}, id={entry.id}")
        return entry

    async def get_entry(self, entry_id: int, user_id: int) -> Optional[DiaryEntry]:
        """
        Получает запись по ID, проверяя принадлежность пользователю.
        """
        result = await self.session.execute(
            select(DiaryEntry).where(
                DiaryEntry.id == entry_id,
                DiaryEntry.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_user_entries(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
    ) -> List[DiaryEntry]:
        """
        Получает все записи пользователя (сортировка по дате создания).
        """
        result = await self.session.execute(
            select(DiaryEntry)
            .where(DiaryEntry.user_id == user_id)
            .order_by(desc(DiaryEntry.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_entries_by_date(
        self,
        user_id: int,
        entry_date: date,
    ) -> List[DiaryEntry]:
        """
        Получает все записи пользователя за конкретную дату.
        """
        result = await self.session.execute(
            select(DiaryEntry)
            .where(
                DiaryEntry.user_id == user_id,
                DiaryEntry.entry_date == entry_date
            )
            .order_by(DiaryEntry.created_at)
        )
        return result.scalars().all()

    async def get_entries_by_period(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> List[DiaryEntry]:
        """
        Получает записи пользователя за период.
        """
        result = await self.session.execute(
            select(DiaryEntry)
            .where(
                DiaryEntry.user_id == user_id,
                DiaryEntry.entry_date >= start_date,
                DiaryEntry.entry_date <= end_date
            )
            .order_by(desc(DiaryEntry.entry_date), DiaryEntry.created_at)
        )
        return result.scalars().all()

    async def get_entries_by_date_range(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> List[DiaryEntry]:
        """
        Получает записи пользователя за диапазон дат (по created_at).
        """
        result = await self.session.execute(
            select(DiaryEntry)
            .where(
                DiaryEntry.user_id == user_id,
                DiaryEntry.created_at >= start_date,
                DiaryEntry.created_at <= end_date
            )
            .order_by(DiaryEntry.created_at)
        )
        return result.scalars().all()

    async def get_entries_count_by_user(self, user_id: int) -> int:
        """
        Получает общее количество записей пользователя.
        """
        result = await self.session.execute(
            select(func.count()).select_from(DiaryEntry).where(DiaryEntry.user_id == user_id)
        )
        return result.scalar() or 0

    async def get_dates_with_entries(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Tuple[date, int]]:
        """
        Получает список дат с количеством записей для пользователя.
        """
        result = await self.session.execute(
            select(
                DiaryEntry.entry_date,
                func.count(DiaryEntry.id).label("count")
            )
            .where(DiaryEntry.user_id == user_id)
            .group_by(DiaryEntry.entry_date)
            .order_by(desc(DiaryEntry.entry_date))
            .limit(limit)
            .offset(offset)
        )
        return [(row.entry_date, row.count) for row in result.all()]

    async def get_entries_for_date_with_count(
        self,
        user_id: int,
        entry_date: date,
    ) -> Tuple[List[DiaryEntry], int]:
        """
        Получает записи за дату и их количество.
        """
        entries = await self.get_entries_by_date(user_id, entry_date)
        return entries, len(entries)

    async def update_entry(
        self,
        entry_id: int,
        user_id: int,
        **kwargs,
    ) -> Optional[DiaryEntry]:
        """
        Обновляет запись.
        """
        entry = await self.get_entry(entry_id, user_id)
        if not entry:
            return None
        
        allowed_fields = [
            'symptom', 'symptom_intensity', 'mood', 'stress',
            'sleep_hours', 'context', 'note'
        ]
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(entry, key, value)
        
        await self.session.commit()
        await self.session.refresh(entry)
        
        logger.info(f"Diary entry updated: id={entry_id}, user_id={user_id}")
        return entry

    async def delete_entry(self, entry_id: int, user_id: int) -> bool:
        """
        Удаляет запись.
        """
        entry = await self.get_entry(entry_id, user_id)
        if not entry:
            return False
        
        await self.session.delete(entry)
        await self.session.commit()
        
        logger.info(f"Diary entry deleted: id={entry_id}, user_id={user_id}")
        return True

    async def get_entries_by_analysis_id(
        self,
        analysis_id: int,
        user_id: int,
    ) -> List[DiaryEntry]:
        """
        Получает записи, связанные с анализом.
        """
        result = await self.session.execute(
            select(DiaryEntry)
            .where(
                DiaryEntry.analysis_id == analysis_id,
                DiaryEntry.user_id == user_id
            )
            .order_by(DiaryEntry.created_at)
        )
        return result.scalars().all()

    async def get_today_entries(self, user_id: int) -> List[DiaryEntry]:
        """
        Получает записи пользователя за сегодня.
        """
        today = date.today()
        return await self.get_entries_by_date(user_id, today)