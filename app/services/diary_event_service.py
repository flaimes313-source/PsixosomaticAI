"""
Сервис для работы с DiaryEvent.
Единая точка сохранения всех событий.
"""
from datetime import date, datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.repositories.diary_repository import DiaryRepository
from app.db.models.user import User
from app.utils.logging import logger


class DiaryEventService:
    """
    Сервис для создания событий в дневнике.
    Используется всеми обработчиками для единообразного сохранения.
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.repository = DiaryRepository(db_session)

    async def _get_user_id(self, telegram_id: int) -> Optional[int]:
        """Получает внутренний ID пользователя по telegram_id."""
        try:
            result = await self.db_session.execute(
                select(User.id).where(User.telegram_id == telegram_id)
            )
            user_id = result.scalar_one_or_none()
            return user_id
        except Exception as e:
            logger.error(f"Error getting user id for telegram_id {telegram_id}: {e}")
            return None

    async def record_event(
        self,
        telegram_id: int,
        event_type: str,
        source: Optional[str] = None,
        session_id: Optional[str] = None,
        role: Optional[str] = None,
        content: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        event_date: Optional[date] = None,
        analysis_id: Optional[int] = None,
        parent_event_id: Optional[int] = None,
    ) -> Optional[int]:
        """
        Единый метод для записи любого события в дневник.
        Принимает telegram_id и преобразует его в user_id.
        """
        try:
            # Получаем внутренний user_id
            user_id = await self._get_user_id(telegram_id)
            
            if not user_id:
                logger.error(f"User not found for telegram_id: {telegram_id}")
                return None
            
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            if event_date is None:
                event_date = datetime.now().date()
            
            event = await self.repository.create_event(
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
            
            return event.id
            
        except Exception as e:
            logger.error(f"Failed to record event: {e}")
            return None

    async def record_user_message(
        self,
        telegram_id: int,
        content: str,
        session_id: str,
        source: str = "describe_state",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Записывает сообщение пользователя."""
        return await self.record_event(
            telegram_id=telegram_id,
            event_type="describe_user",
            source=source,
            session_id=session_id,
            role="user",
            content=content,
            payload=payload,
        )

    async def record_ai_response(
        self,
        telegram_id: int,
        content: str,
        session_id: str,
        source: str = "describe_state",
        payload: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[int] = None,
    ) -> Optional[int]:
        """Записывает ответ AI."""
        return await self.record_event(
            telegram_id=telegram_id,
            event_type="describe_ai",
            source=source,
            session_id=session_id,
            role="assistant",
            content=content,
            payload=payload,
            analysis_id=analysis_id,
        )

    async def record_survey_answer(
        self,
        telegram_id: int,
        question: str,
        answer: str,
        survey_type: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Записывает ответ на опрос."""
        return await self.record_event(
            telegram_id=telegram_id,
            event_type=f"survey_{survey_type}",
            source=f"{survey_type}_survey",
            role="user",
            content=answer,
            payload=payload or {"question": question},
        )

    async def record_analysis(
        self,
        telegram_id: int,
        content: str,
        session_id: str,
        payload: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[int] = None,
    ) -> Optional[int]:
        """Записывает анализ."""
        return await self.record_event(
            telegram_id=telegram_id,
            event_type="analysis",
            source="describe_state",
            session_id=session_id,
            role="assistant",
            content=content,
            payload=payload,
            analysis_id=analysis_id,
        )

    async def record_clarification(
        self,
        telegram_id: int,
        question: str,
        answer: str,
        session_id: str,
        analysis_id: Optional[int] = None,
    ) -> Optional[int]:
        """Записывает уточняющий вопрос и ответ."""
        # Вопрос
        await self.record_event(
            telegram_id=telegram_id,
            event_type="clarification_question",
            source="describe_state",
            session_id=session_id,
            role="user",
            content=question,
            analysis_id=analysis_id,
        )
        
        # Ответ
        return await self.record_event(
            telegram_id=telegram_id,
            event_type="clarification_answer",
            source="describe_state",
            session_id=session_id,
            role="assistant",
            content=answer,
            analysis_id=analysis_id,
        )