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
    await show_dynamics_menu(message, state, db_session)


@router.message(lambda msg: msg.text == "🔔 Напоминания")
async def handle_reminders_button(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обработчик кнопки 'Напоминания'.
    """
    logger.info(f"User requested reminders via button: telegram_id={message.from_user.id}")
    
    from app.bot.handlers.reminders import show_reminders_menu
    await show_reminders_menu(message, state, db_session)


# ==================== ИЗМЕНЕНО: "⭐ PRO" → "⭐ Сома. PRO" ====================

@router.message(lambda msg: msg.text == "⭐ Сома. PRO")
async def handle_pro_button(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обработчик кнопки '⭐ Сома. PRO'.
    """
    logger.info(f"User requested PRO via button: telegram_id={message.from_user.id}")
    
    from app.bot.handlers.pro import show_pro_menu
    await show_pro_menu(message, state, db_session)


# ==================== ИСПРАВЛЕНО: "🩺 Что я чувствую в теле" ====================

@router.message(lambda msg: msg.text == "🩺 Что я чувствую в теле")
async def handle_body_analysis_button(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обработчик кнопки '🩺 Что я чувствую в теле'.
    Запускает анализ симптома.
    """
    logger.info(f"User requested body analysis via button: telegram_id={message.from_user.id}")
    
    # Проверяем лимит через AccessService
    from app.services.access_service import AccessService
    
    access_service = AccessService(db_session)
    can_use, limit_message = await access_service.can_use_body_analysis(message.from_user.id)
    
    if not can_use:
        from app.bot.keyboards.pro import get_pro_locked_keyboard
        
        await message.answer(
            limit_message,
            reply_markup=get_pro_locked_keyboard(),
            parse_mode="HTML",
        )
        return
    
    # ==================== ИСПРАВЛЕНО: используем symptom.py ====================
    from app.bot.handlers.symptom import start_symptom_analysis
    await start_symptom_analysis(message, state)


# ==================== НОВЫЙ ОБРАБОТЧИК: "🧠 Помогите разобраться" ====================

@router.message(lambda msg: msg.text == "🧠 Помогите разобраться")
async def handle_help_dialog_button(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обработчик кнопки '🧠 Помогите разобраться'.
    Запускает свободный AI-диалог.
    """
    logger.info(f"User requested help dialog via button: telegram_id={message.from_user.id}")
    
    from app.bot.handlers.help_me import start_help_dialog
    await start_help_dialog(message, state, db_session)


# ==================== ОБРАБОТЧИК: "📖 Как это работает?" ====================

@router.message(lambda msg: msg.text == "📖 Как это работает?")
async def handle_how_it_works_button(message: types.Message, db_session: AsyncSession):
    """
    Обработчик кнопки '📖 Как это работает?'.
    """
    logger.info(f"User requested how it works via button: telegram_id={message.from_user.id}")
    
    from app.bot.handlers.how_it_works import show_how_it_works
    await show_how_it_works(message, db_session)


# ==================== ОБРАБОТЧИК: "👤 Профиль" ====================

@router.message(lambda msg: msg.text == "👤 Профиль")
async def handle_profile_button(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обработчик кнопки '👤 Профиль'.
    """
    logger.info(f"User requested profile via button: telegram_id={message.from_user.id}")
    
    from app.bot.handlers.profile import show_profile
    await show_profile(message, state, db_session)


# ==================== ОБРАБОТЧИК: "❓ Поддержка" ====================

@router.message(lambda msg: msg.text == "❓ Поддержка")
async def handle_support_button(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обработчик кнопки '❓ Поддержка'.
    """
    logger.info(f"User requested support via button: telegram_id={message.from_user.id}")
    
    from app.bot.handlers.support import show_support
    await show_support(message, state, db_session)