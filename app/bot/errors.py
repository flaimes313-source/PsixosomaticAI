"""
Глобальный обработчик ошибок для Telegram бота.
"""
import traceback
from aiogram import Router
from aiogram.types import ErrorEvent
from aiogram.exceptions import TelegramAPIError

from app.utils.logging import logger


router = Router(name="errors")


@router.errors()
async def global_error_handler(event: ErrorEvent):
    """
    Глобальный обработчик ошибок.
    
    Логирует ошибку и отправляет пользователю понятное сообщение.
    """
    # Получаем информацию об ошибке
    exception = event.exception
    update = event.update
    
    # Определяем пользователя (если есть)
    user_id = None
    if update.message and update.message.from_user:
        user_id = update.message.from_user.id
    elif update.callback_query and update.callback_query.from_user:
        user_id = update.callback_query.from_user.id
    
    # Логируем ошибку с полным traceback
    logger.error(
        f"Global error handler caught exception: {exception}\n"
        f"User ID: {user_id}\n"
        f"Update: {update}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    
    # Отправляем пользователю понятное сообщение (если есть пользователь)
    if user_id:
        try:
            from aiogram import Bot
            from app.config import settings
            
            bot = Bot(token=settings.BOT_TOKEN)
            await bot.send_message(
                chat_id=user_id,
                text="😔 Произошла техническая ошибка.\n\n"
                     "Попробуй ещё раз через несколько секунд.\n"
                     "Если ошибка повторяется, обратись к разработчику."
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")
    
    # Возвращаем False, чтобы ошибка не пробрасывалась дальше
    return False