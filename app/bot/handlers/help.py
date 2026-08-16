"""
Обработчик команды /help.
"""
from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


@router.message(Command("help"))
async def cmd_help(message: types.Message, db_session: AsyncSession):
    """
    Обработчик команды /help.
    """
    logger.info(f"User requested help: telegram_id={message.from_user.id}")
    
    help_text = (
        "❓ Помощь\n\n"
        "🧠 Разобрать симптом\n"
        "Помогает исследовать возможную связь\n"
        "телесных ощущений со стрессом и эмоциями.\n\n"
        "🧠 Проверить стресс\n"
        "Позволяет пройти небольшой опрос\n"
        "о текущем состоянии.\n\n"
        "📋 История\n"
        "В следующих версиях здесь будут\n"
        "сохраняться предыдущие разборы.\n\n"
        "⚙️ Настройки\n"
        "Настройки профиля и уведомлений.\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ Если тебе сейчас плохо или есть\n"
        "сильные/необычные физические симптомы,\n"
        "обратись к врачу или в экстренную помощь."
    )
    
    await message.answer(help_text, reply_markup=get_main_menu_keyboard())