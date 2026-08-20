"""
Обработчики кнопок главного меню.
"""
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import get_main_menu_keyboard
from app.bot.handlers.history import show_history
from app.utils.logging import logger

router = Router()


@router.message(lambda msg: msg.text == "📋 История")
async def handle_history_button(message: types.Message, db_session: AsyncSession):
    """Обработчик кнопки 'История'."""
    logger.info(f"User requested history via button: telegram_id={message.from_user.id}")
    await show_history(message, db_session)


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
        "📊 Моя динамика\n"
        "Анализирует твои записи за период\n"
        "и показывает возможные закономерности.\n\n"
        "🔔 Напоминания\n"
        "Настрой ежедневные напоминания\n"
        "заполнять дневник.\n\n"
        "📋 История\n"
        "Сохраняет все предыдущие разборы симптомов.\n\n"
        "⚙️ Настройки\n"
        "Профиль и управление данными.\n\n"
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
        "Вы можете удалить все свои данные\n"
        "в разделе ⚙️ Настройки.\n\n"
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


# ==================== НОВЫЕ ОБРАБОТЧИКИ ====================

@router.message(lambda msg: msg.text == "📊 Моя динамика")
async def handle_dynamics_button(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обработчик кнопки 'Моя динамика'.
    """
    logger.info(f"User requested dynamics via button: telegram_id={message.from_user.id}")
    
    from app.bot.handlers.dynamics import show_dynamics_menu
    await show_dynamics_menu(message, state, db_session)  # ← ИСПРАВЛЕНО


@router.message(lambda msg: msg.text == "🔔 Напоминания")
async def handle_reminders_button(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обработчик кнопки 'Напоминания'.
    """
    logger.info(f"User requested reminders via button: telegram_id={message.from_user.id}")
    
    from app.bot.handlers.reminders import show_reminders_menu
    await show_reminders_menu(message, state, db_session)  # ← ИСПРАВЛЕНО


@router.message(lambda msg: msg.text == "⭐ PRO")
async def handle_pro_button(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обработчик кнопки 'PRO'.
    """
    logger.info(f"User requested PRO via button: telegram_id={message.from_user.id}")
    
    from app.bot.handlers.pro import show_pro_menu
    await show_pro_menu(message, state, db_session)  # ← ДОБАВЛЕНО