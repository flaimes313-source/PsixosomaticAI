"""
Репозиторий для работы с анализами симптомов.
"""
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List

from app.db.models.analysis import Analysis
from app.db.models.user import User
from app.utils.logging import logger


class AnalysisRepository:
    """Репозиторий для операций с анализами"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        symptom: str,
        duration: str,
        intensity: int,
        analysis: str,
        context: Optional[str] = None,
    ) -> Analysis:
        """Создает новый анализ симптома."""
        analysis_obj = Analysis(
            user_id=user_id,
            symptom=symptom,
            duration=duration,
            intensity=intensity,
            context=context,
            analysis=analysis,
        )
        
        self.session.add(analysis_obj)
        await self.session.commit()
        await self.session.refresh(analysis_obj)
        
        logger.info(
            f"Analysis created: user_id={user_id}, "
            f"symptom={symptom[:30]}..."
        )
        
        return analysis_obj

    async def get_by_id(self, analysis_id: int) -> Optional[Analysis]:
        """Получает анализ по ID."""
        result = await self.session.execute(
            select(Analysis).where(Analysis.id == analysis_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Analysis]:
        """Получает список анализов пользователя."""
        result = await self.session.execute(
            select(Analysis)
            .where(Analysis.user_id == user_id)
            .order_by(desc(Analysis.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_last_analysis(self, user_id: int) -> Optional[Analysis]:
        """Получает последний анализ пользователя."""
        result = await self.session.execute(
            select(Analysis)
            .where(Analysis.user_id == user_id)
            .order_by(desc(Analysis.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_count_by_user(self, user_id: int) -> int:
        """Получает количество анализов пользователя."""
        result = await self.session.execute(
            select(Analysis).where(Analysis.user_id == user_id)
        )
        return len(result.scalars().all())

    async def delete(self, analysis_id: int) -> bool:
        """Удаляет анализ по ID."""
        analysis = await self.get_by_id(analysis_id)
        if not analysis:
            return False
        
        await self.session.delete(analysis)
        await self.session.commit()
        
        logger.info(f"Analysis deleted: id={analysis_id}")
        return True

    async def delete_all_by_user(self, user_id: int) -> int:
        """Удаляет все анализы пользователя."""
        analyses = await self.get_by_user_id(user_id, limit=9999)
        count = len(analyses)
        
        for analysis in analyses:
            await self.session.delete(analysis)
        
        await self.session.commit()
        
        logger.info(f"All analyses deleted for user: user_id={user_id}, count={count}")
        return count