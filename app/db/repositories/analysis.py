"""
Репозиторий для работы с анализами симптомов.
"""
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.models.analysis import Analysis
from app.utils.logging import logger


class AnalysisRepository:
    """Репозиторий для операций с анализами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
        analysis: str,
    ) -> Analysis:
        """
        Создаёт новый анализ.
        """
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
        
        logger.info(f"Analysis created: id={analysis_obj.id}, user_id={user_id}")
        return analysis_obj

    async def get_by_id(self, analysis_id: int, user_id: int) -> Optional[Analysis]:
        """
        Получает анализ по ID с проверкой пользователя.
        """
        result = await self.session.execute(
            select(Analysis).where(
                Analysis.id == analysis_id,
                Analysis.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_user_analyses(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Analysis]:
        """
        Получает все анализы пользователя (сортировка по дате создания).
        """
        result = await self.session.execute(
            select(Analysis)
            .where(Analysis.user_id == user_id)
            .order_by(desc(Analysis.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_user_analyses_count(self, user_id: int) -> int:
        """
        Получает общее количество анализов пользователя.
        """
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(Analysis).where(Analysis.user_id == user_id)
        )
        return result.scalar() or 0

    async def update(
        self,
        analysis_id: int,
        user_id: int,
        **kwargs,
    ) -> Optional[Analysis]:
        """
        Обновляет анализ.
        """
        analysis = await self.get_by_id(analysis_id, user_id)
        if not analysis:
            return None
        
        allowed_fields = ['symptom', 'duration', 'intensity', 'context', 'analysis']
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(analysis, key, value)
        
        await self.session.commit()
        await self.session.refresh(analysis)
        
        logger.info(f"Analysis updated: id={analysis_id}, user_id={user_id}")
        return analysis

    async def delete(self, analysis_id: int, user_id: int) -> bool:
        """
        Удаляет анализ.
        """
        analysis = await self.get_by_id(analysis_id, user_id)
        if not analysis:
            return False
        
        await self.session.delete(analysis)
        await self.session.commit()
        
        logger.info(f"Analysis deleted: id={analysis_id}, user_id={user_id}")
        return True