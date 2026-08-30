"""
Middleware для обработки запросов в Telegram боте.
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.utils.logging import logger


class DBSessionMiddleware(BaseMiddleware):
    """
    Middleware для управления сессией базы данных.
    
    Открывает сессию перед обработкой обновления
    и закрывает после завершения обработки.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """
        Обработка обновления с управлением сессией БД.
        """
        async with AsyncSessionLocal() as session:
            data["db_session"] = session
            
            try:
                result = await handler(event, data)
                return result
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in handler, transaction rolled back: {e}")
                raise