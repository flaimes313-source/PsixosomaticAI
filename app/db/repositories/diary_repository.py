"""
Репозиторий для работы с DiaryEvent.
Единый репозиторий для всех событий пользователя.
"""
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import uuid

from app.db.models.diary_event import DiaryEvent
from app.utils.logging import logger


class DiaryRepository:
    """Репозиторий для операций с DiaryEvent."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== СОЗДАНИЕ СОБЫТИЙ ====================

    async def create_event(
        self,
        user_id: int,  # ← ВНУТРЕННИЙ ID ИЗ USERS
        event_type: str,
        source: Optional[str] = None,
        session_id: Optional[str] = None,
        role: Optional[str] = None,
        content: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        event_date: Optional[date] = None,
        analysis_id: Optional[int] = None,
        parent_event_id: Optional[int] = None,
    ) -> DiaryEvent:
        """
        Создаёт новое событие в дневнике.
        user_id - внутренний ID пользователя из таблицы users.
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        if event_date is None:
            event_date = datetime.now().date()
        
        event = DiaryEvent(
            user_id=user_id,
            event_type=event_type,
            source=source,
            session_id=session_id,
            role=role,
            content=content,
            payload=payload,
            event_date=event_date,
            analysis_id=analysis_id,
            parent_event_id=parent_event_id,
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        
        logger.info(f"DiaryEvent created: id={event.id}, type={event_type}, user_id={user_id}")
        return event

    # ==================== ОСТАЛЬНЫЕ МЕТОДЫ БЕЗ ИЗМЕНЕНИЙ ====================

    async def get_event(self, event_id: int, user_id: int) -> Optional[DiaryEvent]:
        """Получает событие по ID."""
        result = await self.session.execute(
            select(DiaryEvent).where(
                DiaryEvent.id == event_id,
                DiaryEvent.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_user_events(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        event_types: Optional[List[str]] = None,
    ) -> List[DiaryEvent]:
        """Получает события пользователя с фильтрацией."""
        query = select(DiaryEvent).where(DiaryEvent.user_id == user_id)
        
        if event_types:
            query = query.where(DiaryEvent.event_type.in_(event_types))
        
        query = query.order_by(desc(DiaryEvent.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_events_by_date(
        self,
        user_id: int,
        event_date: date,
    ) -> List[DiaryEvent]:
        """Получает события за конкретную дату."""
        result = await self.session.execute(
            select(DiaryEvent)
            .where(
                DiaryEvent.user_id == user_id,
                DiaryEvent.event_date == event_date
            )
            .order_by(DiaryEvent.created_at.asc())
        )
        return result.scalars().all()

    async def get_events_by_period(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        event_types: Optional[List[str]] = None,
    ) -> List[DiaryEvent]:
        """Получает события за период."""
        query = select(DiaryEvent).where(
            DiaryEvent.user_id == user_id,
            DiaryEvent.event_date >= start_date,
            DiaryEvent.event_date <= end_date,
        )
        
        if event_types:
            query = query.where(DiaryEvent.event_type.in_(event_types))
        
        query = query.order_by(DiaryEvent.created_at.asc())
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_session_events(
        self,
        user_id: int,
        session_id: str,
    ) -> List[DiaryEvent]:
        """Получает все события сессии."""
        result = await self.session.execute(
            select(DiaryEvent)
            .where(
                DiaryEvent.user_id == user_id,
                DiaryEvent.session_id == session_id
            )
            .order_by(DiaryEvent.created_at.asc())
        )
        return result.scalars().all()

    async def get_dates_with_events(
        self,
        user_id: int,
        limit: int = 30,
    ) -> List[tuple]:
        """Получает даты с событиями."""
        result = await self.session.execute(
            select(
                DiaryEvent.event_date,
                func.count(DiaryEvent.id).label("count")
            )
            .where(DiaryEvent.user_id == user_id)
            .group_by(DiaryEvent.event_date)
            .order_by(desc(DiaryEvent.event_date))
            .limit(limit)
        )
        return [(row.event_date, row.count) for row in result.all()]

    async def count_user_events(self, user_id: int) -> int:
        """Подсчитывает общее количество событий пользователя."""
        result = await self.session.execute(
            select(func.count()).select_from(DiaryEvent).where(
                DiaryEvent.user_id == user_id
            )
        )
        return result.scalar() or 0

    async def get_latest_events(
        self,
        user_id: int,
        limit: int = 10,
    ) -> List[DiaryEvent]:
        """Получает последние события пользователя."""
        result = await self.session.execute(
            select(DiaryEvent)
            .where(DiaryEvent.user_id == user_id)
            .order_by(desc(DiaryEvent.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def delete_event(self, event_id: int, user_id: int) -> bool:
        """Удаляет событие."""
        event = await self.get_event(event_id, user_id)
        if not event:
            return False
        await self.session.delete(event)
        await self.session.commit()
        return True

    async def delete_session_events(self, user_id: int, session_id: str) -> int:
        """Удаляет все события сессии."""
        result = await self.session.execute(
            select(DiaryEvent).where(
                DiaryEvent.user_id == user_id,
                DiaryEvent.session_id == session_id
            )
        )
        events = result.scalars().all()
        count = len(events)
        for event in events:
            await self.session.delete(event)
        await self.session.commit()
        return count