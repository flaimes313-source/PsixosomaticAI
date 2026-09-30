"""
Репозиторий для работы с обращениями в поддержку.
"""
from typing import List, Optional
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.models.support import SupportRequest
from app.utils.logging import logger


class SupportRepository:
    """Репозиторий для SupportRequest."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, request_id: int) -> Optional[SupportRequest]:
        """Получить обращение по ID."""
        result = await self.session.execute(
            select(SupportRequest).where(SupportRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_new(self, limit: int = 100) -> List[SupportRequest]:
        """Получить неотвеченные обращения."""
        result = await self.session.execute(
            select(SupportRequest)
            .where(SupportRequest.is_answered == False)
            .order_by(desc(SupportRequest.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SupportRequest]:
        """
        Получить все обращения.
        Сортировка: сначала новые (is_answered=False), потом по дате.
        """
        result = await self.session.execute(
            select(SupportRequest)
            .order_by(
                SupportRequest.is_answered.asc(),   # False (новые) — вперёд
                desc(SupportRequest.created_at),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_new(self) -> int:
        """Количество неотвеченных."""
        result = await self.session.execute(
            select(func.count())
            .select_from(SupportRequest)
            .where(SupportRequest.is_answered == False)
        )
        return result.scalar() or 0

    async def count_all(self) -> int:
        """Общее количество."""
        result = await self.session.execute(
            select(func.count()).select_from(SupportRequest)
        )
        return result.scalar() or 0

    async def mark_answered(
        self,
        request_id: int,
        answer_text: str,
        answered_by: int,
    ) -> bool:
        """Помечает обращение как отвеченное и сохраняет ответ."""
        request = await self.get_by_id(request_id)
        if not request:
            return False

        request.is_answered = True
        request.answer = answer_text
        request.answered_by = answered_by
        request.answered_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(request)
        logger.info(f"Support request #{request_id} marked as answered")
        return True