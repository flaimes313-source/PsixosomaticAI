"""
Репозиторий для работы с пользователями.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional

from app.db.models.user import User  # <-- ПРАВИЛЬНЫЙ ИМПОРТ
from app.utils.logging import logger


class UserRepository:
    """Репозиторий для операций с пользователями"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по telegram_id."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> User:
        """Создать нового пользователя."""
        now = datetime.now(timezone.utc)
        
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        logger.info(f"User created: telegram_id={telegram_id}")
        return user

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> User:
        """Получить пользователя или создать, если не существует."""
        user = await self.get_by_telegram_id(telegram_id)
        now = datetime.now(timezone.utc)
        
        if user:
            if username is not None:
                user.username = username
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            if language_code is not None:
                user.language_code = language_code
            
            user.last_seen_at = now
            user.updated_at = now
            await self.session.commit()
            await self.session.refresh(user)
            logger.info(f"User updated: telegram_id={telegram_id}")
            return user
        
        return await self.create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )

    async def update_last_seen(self, telegram_id: int) -> Optional[User]:
        """Обновить время последнего визита."""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.last_seen_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        return None

    async def update_profile(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> Optional[User]:
        """Обновить профиль пользователя."""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        
        if username is not None:
            user.username = username
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if language_code is not None:
            user.language_code = language_code
        
        user.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(user)
        return user