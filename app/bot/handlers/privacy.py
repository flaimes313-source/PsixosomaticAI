"""
Обработчик команды /privacy.
"""
from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


@router.message(Command("privacy"))
async def cmd_privacy(message: types.Message, db_session: AsyncSession):
    """
    Обработчик команды /privacy.
    
    Показывает информацию о политике конфиденциальности.
    """
    logger.info(f"User requested privacy info: telegram_id={message.from_user.id}")
    
    privacy_text = (
        "🔐 Конфиденциальность\n\n"
        "Мы сохраняем технические данные,\n"
        "необходимые для работы бота:\n"
        "• Telegram ID\n"
        "• Имя и фамилия\n"
        "• Время взаимодействия\n\n"
        "В следующих версиях будет реализовано\n"
        "удаление пользовательских данных.\n\n"
        "Важно: бот не ставит медицинские диагнозы\n"
        "и не заменяет профессиональную помощь."
    )
    
    await message.answer(
        privacy_text,
        reply_markup=get_main_menu_keyboard(),
    )