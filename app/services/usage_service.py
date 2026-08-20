"""
Сервис для управления счётчиками использования.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.usage import UsageRepository
from app.utils.logging import logger


class UsageService:
    """Сервис для работы с использованием."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.usage_repo = UsageRepository(db_session)

    async def increment_analysis(self, user_id: int) -> bool:
        """
        Увеличить счётчик анализов.
        Возвращает True, если успешно.
        """
        try:
            await self.usage_repo.increment_analysis(user_id)
            return True
        except Exception as e:
            logger.error(f"Failed to increment analysis count for user {user_id}: {e}")
            return False

    async def increment_dynamics(self, user_id: int) -> bool:
        """
        Увеличить счётчик динамики.
        Возвращает True, если успешно.
        """
        try:
            await self.usage_repo.increment_dynamics(user_id)
            return True
        except Exception as e:
            logger.error(f"Failed to increment dynamics count for user {user_id}: {e}")
            return False

    async def get_usage_info(self, user_id: int) -> dict:
        """
        Получить информацию об использовании.
        """
        usage = await self.usage_repo.get_current_usage(user_id)
        return {
            "analyses_count": usage.analyses_count,
            "dynamics_count": usage.dynamics_count,
            "period_start": usage.period_start,
            "analyses_limit": 10,  # FREE лимит
            "dynamics_limit": 5,   # FREE лимит
        }

    async def reset_usage(self, user_id: int) -> bool:
        """
        Сбросить использование (принудительно).
        """
        try:
            usage = await self.usage_repo.get_by_user_id(user_id)
            if usage:
                await self.usage_repo.reset_period_if_needed(user_id)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to reset usage for user {user_id}: {e}")
            return False