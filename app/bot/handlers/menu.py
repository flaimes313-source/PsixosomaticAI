"""
Обработчики кнопок главного меню.
"""
from aiogram import Router, types
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import get_main_menu_keyboard
from app.bot.handlers.history import show_history
from app.utils.logging import logger

router = Router()


@router.message(lambda msg: msg.text == "🧠 Проверить стресс")
async def handle_stress_check(message: types.Message, db_session: AsyncSession):
    """Обработчик кнопки 'Проверить стресс'."""
    logger.info(f"User requested stress check: telegram_id={message.from_user.id}")
    
    await message.answer(
        "🧠 Проверка стресса\n\n"
        "Эта функция будет подключена на следующем этапе.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(lambda msg: msg.text == "📋 История")
async def handle_history_button(message: types.Message, db_session: AsyncSession):
    """Обработчик кнопки 'История'."""
    logger.info(f"User requested history via button: telegram_id={message.from_user.id}")
    await show_history(message, db_session)


@router.message(lambda msg: msg.text == "⚙️ Настройки")
async def handle_settings(message: types.Message, db_session: AsyncSession):
    """Обработчик кнопки 'Настройки'."""
    logger.info(f"User requested settings: telegram_id={message.from_user.id}")
    
    await message.answer(
        "⚙️ Настройки\n\n"
        "Здесь можно настроить профиль и уведомления.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(lambda msg: msg.text == "❓ Помощь")
async def handle_help_button(message: types.Message, db_session: AsyncSession):
    """Обработчик кнопки 'Помощь'."""
    logger.info(f"User requested help via button: telegram_id={message.from_user.id}")
    
    help_text = (
        "❓ Помощь\n\n"
        "🧠 Разобрать симптом\n"
        "Помогает исследовать возможную связь\n"
        "телесных ощущений со стрессом и эмоциями.\n\n"
        "🧠 Проверить стресс\n"
        "Позволяет пройти небольшой опрос\n"
        "о текущем состоянии.\n\n"
        "📋 История\n"
        "Сохраняет все предыдущие разборы симптомов.\n\n"
        "⚙️ Настройки\n"
        "Настройки профиля и уведомлений.\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ Если тебе сейчас плохо или есть\n"
        "сильные/необычные физические симптомы,\n"
        "обратись к врачу или в экстренную помощь."
    )
    
    await message.answer(help_text, reply_markup=get_main_menu_keyboard())


@router.message(lambda msg: msg.text == "🔐 Конфиденциальность")
async def handle_privacy_button(message: types.Message, db_session: AsyncSession):
    """Обработчик кнопки 'Конфиденциальность'."""
    logger.info(f"User requested privacy via button: telegram_id={message.from_user.id}")
    
    privacy_text = (
        "🔐 Конфиденциальность\n\n"
        "Мы сохраняем технические данные,\n"
        "необходимые для работы бота:\n"
        "• Telegram ID\n"
        "• Имя и фамилия\n"
        "• Время взаимодействия\n"
        "• История анализов\n\n"
        "В следующих версиях будет реализовано\n"
        "удаление пользовательских данных.\n\n"
        "Важно: бот не ставит медицинские диагнозы\n"
        "и не заменяет профессиональную помощь."
    )
    
    await message.answer(privacy_text, reply_markup=get_main_menu_keyboard())


@router.message(lambda msg: msg.text == "🔙 Назад")
async def handle_back(message: types.Message, db_session: AsyncSession):
    """Обработчик кнопки 'Назад'."""
    await message.answer(
        "Возвращаемся в главное меню",
        reply_markup=get_main_menu_keyboard(),
    )