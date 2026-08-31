"""
Репозиторий для работы с историей диалогов «Помогите разобраться».
"""
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import uuid4

from app.db.models.help_dialog import HelpDialogMessage
from app.utils.logging import logger


class HelpDialogRepository:
    """Репозиторий для операций с диалогами «Помогите разобраться»."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self, user_id: int) -> str:
        """
        Создаёт новую сессию диалога.
        Возвращает session_id.
        """
        session_id = str(uuid4())
        logger.info(f"Help dialog session created: user={user_id}, session={session_id}")
        return session_id

    async def add_message(
        self,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
    ) -> HelpDialogMessage:
        """
        Добавляет сообщение в историю диалога.
        """
        message = HelpDialogMessage(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_session_history(
        self,
        user_id: int,
        session_id: str,
        limit: int = 20,
    ) -> List[HelpDialogMessage]:
        """
        Получает историю диалога по session_id.
        """
        result = await self.session.execute(
            select(HelpDialogMessage)
            .where(
                HelpDialogMessage.user_id == user_id,
                HelpDialogMessage.session_id == session_id,
            )
            .order_by(HelpDialogMessage.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_last_session(self, user_id: int) -> Optional[str]:
        """
        Получает последнюю активную сессию пользователя.
        """
        result = await self.session.execute(
            select(HelpDialogMessage.session_id)
            .where(HelpDialogMessage.user_id == user_id)
            .order_by(desc(HelpDialogMessage.created_at))
            .limit(1)
        )
        session = result.scalar_one_or_none()
        return session

    async def get_messages_count(self, user_id: int) -> int:
        """
        Получает общее количество сообщений пользователя.
        """
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(HelpDialogMessage).where(
                HelpDialogMessage.user_id == user_id
            )
        )
        return result.scalar() or 0