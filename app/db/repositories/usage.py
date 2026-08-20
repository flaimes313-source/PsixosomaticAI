"""
Репозиторий для работы с использованием (счётчики).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from datetime import date, datetime, timedelta
from typing import Optional

from app.db.models.usage import UserUsage
from app.utils.logging import logger


class UsageRepository:
    """Репозиторий для управления счётчиками использования."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: int) -> Optional[UserUsage]:
        """Получить счётчики пользователя."""
        result = await self.session.execute(
            select(UserUsage).where(UserUsage.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: int) -> UserUsage:
        """Получить или создать счётчики для пользователя."""
        usage = await self.get_by_user_id(user_id)
        if not usage:
            usage = UserUsage(
                user_id=user_id,
                analyses_count=0,
                dynamics_count=0,
                period_start=date.today(),
            )
            self.session.add(usage)
            await self.session.commit()
            await self.session.refresh(usage)
            logger.info(f"Usage created for user {user_id}")
        return usage

    async def reset_period_if_needed(self, user_id: int) -> bool:
        """Сбросить период, если начался новый месяц."""
        usage = await self.get_by_user_id(user_id)
        if not usage:
            return False

        today = date.today()
        # Если период начался в другом месяце
        if usage.period_start.month != today.month or usage.period_start.year != today.year:
            usage.period_start = today
            usage.analyses_count = 0
            usage.dynamics_count = 0
            usage.updated_at = func.now()
            
            await self.session.commit()
            await self.session.refresh(usage)
            
            logger.info(f"Usage period reset for user {user_id}")
            return True
        
        return False

    async def increment_analysis(self, user_id: int) -> Optional[UserUsage]:
        """Увеличить счётчик анализов."""
        usage = await self.get_or_create(user_id)
        
        # Сначала сбрасываем период, если нужно
        await self.reset_period_if_needed(user_id)
        
        usage.analyses_count += 1
        usage.updated_at = func.now()
        
        await self.session.commit()
        await self.session.refresh(usage)
        
        logger.info(f"Analysis count incremented for user {user_id}: {usage.analyses_count}")
        return usage

    async def increment_dynamics(self, user_id: int) -> Optional[UserUsage]:
        """Увеличить счётчик динамики."""
        usage = await self.get_or_create(user_id)
        
        # Сначала сбрасываем период, если нужно
        await self.reset_period_if_needed(user_id)
        
        usage.dynamics_count += 1
        usage.updated_at = func.now()
        
        await self.session.commit()
        await self.session.refresh(usage)
        
        logger.info(f"Dynamics count incremented for user {user_id}: {usage.dynamics_count}")
        return usage

    async def get_current_usage(self, user_id: int) -> Optional[UserUsage]:
        """Получить текущее использование (с автоматическим сбросом)."""
        usage = await self.get_or_create(user_id)
        await self.reset_period_if_needed(user_id)
        return usage

    async def delete_usage(self, user_id: int) -> bool:
        """Удалить счётчики пользователя."""
        usage = await self.get_by_user_id(user_id)
        if not usage:
            return False
        
        await self.session.delete(usage)
        await self.session.commit()
        
        logger.info(f"Usage deleted for user {user_id}")
        return True