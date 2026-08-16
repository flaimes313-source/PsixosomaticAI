"""
Репозиторий для работы с уточнениями.
"""
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.models.clarification import Clarification
from app.utils.logging import logger


class ClarificationRepository:
    """Репозиторий для операций с уточнениями"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        analysis_id: int,
        user_id: int,
        question: str,
        answer: str,
    ) -> Clarification:
        """Создает новое уточнение."""
        clarification = Clarification(
            analysis_id=analysis_id,
            user_id=user_id,
            question=question,
            answer=answer,
        )
        
        self.session.add(clarification)
        await self.session.commit()
        await self.session.refresh(clarification)
        
        logger.info(
            f"Clarification created: analysis_id={analysis_id}, "
            f"user_id={user_id}, question={question[:30]}..."
        )
        
        return clarification

    async def get_by_analysis_id(
        self,
        analysis_id: int,
        limit: int = 10,
    ) -> List[Clarification]:
        """Получает все уточнения для анализа."""
        result = await self.session.execute(
            select(Clarification)
            .where(Clarification.analysis_id == analysis_id)
            .order_by(Clarification.created_at)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_user_id(
        self,
        user_id: int,
        limit: int = 20,
    ) -> List[Clarification]:
        """Получает все уточнения пользователя."""
        result = await self.session.execute(
            select(Clarification)
            .where(Clarification.user_id == user_id)
            .order_by(desc(Clarification.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_count_by_analysis(self, analysis_id: int) -> int:
        """Получает количество уточнений для анализа."""
        result = await self.session.execute(
            select(Clarification).where(Clarification.analysis_id == analysis_id)
        )
        return len(result.scalars().all())

    async def delete_by_analysis_id(self, analysis_id: int) -> int:
        """Удаляет все уточнения для анализа."""
        clarifications = await self.get_by_analysis_id(analysis_id, limit=9999)
        count = len(clarifications)
        
        for clarification in clarifications:
            await self.session.delete(clarification)
        
        await self.session.commit()
        
        logger.info(f"Clarifications deleted for analysis: analysis_id={analysis_id}, count={count}")
        return count