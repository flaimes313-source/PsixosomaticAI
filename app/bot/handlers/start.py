"""
Обработчик команды /start.
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.repositories.user import UserRepository
from app.db.models.user import User
from app.bot.keyboards import get_main_menu_keyboard
from app.bot.keyboards.timezone import get_timezone_keyboard, get_timezone_skip_keyboard
from app.bot.states import RegistrationStates
from app.utils.logging import logger

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, db_session: AsyncSession, state: FSMContext):
    """
    Обработчик команды /start.
    
    Приоритет: /start всегда очищает FSM состояние.
    """
    tg_user = message.from_user
    
    # Очищаем любое состояние FSM
    await state.clear()
    
    user_repo = UserRepository(db_session)
    
    # Проверяем, есть ли пользователь
    user = await user_repo.get_by_telegram_id(tg_user.id)
    
    if user and user.timezone:
        # Если пользователь уже есть и часовой пояс выбран - показываем меню
        await show_main_menu(message, tg_user, db_session)
        return
    
    # Если пользователь есть, но timezone не выбран
    if user and not user.timezone:
        # Спрашиваем часовой пояс
        await state.set_state(RegistrationStates.waiting_for_timezone)
        await state.update_data(telegram_id=tg_user.id)
        
        await message.answer(
            "🌍 Укажите ваш часовой пояс.\n\n"
            "Это нужно для корректного отображения времени.\n"
            "Выберите один из вариантов ниже или нажмите 'Пропустить'.\n\n"
            "⚠️ Если вы используете VPN, выберите ваш реальный часовой пояс.",
            reply_markup=get_timezone_keyboard(),
        )
        return
    
    # Если пользователя нет - создаем и спрашиваем timezone
    await state.set_state(RegistrationStates.waiting_for_timezone)
    await state.update_data(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        language_code=tg_user.language_code,
    )
    
    await message.answer(
        "🌍 Укажите ваш часовой пояс.\n\n"
        "Это нужно для корректного отображения времени.\n"
        "Выберите один из вариантов ниже или нажмите 'Пропустить'.\n\n"
        "⚠️ Если вы используете VPN, выберите ваш реальный часовой пояс.",
        reply_markup=get_timezone_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_timezone)
async def process_timezone(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка выбора часового пояса."""
    text = message.text.strip()
    
    # Пропуск
    if text == "⏭ Пропустить (UTC)":
        timezone = "UTC"
    else:
        # Извлекаем время из текста (например, "UTC+03:00 (Москва)" -> "UTC+03:00")
        import re
        match = re.search(r'(UTC[+-]\d{2}:\d{2})', text)
        if match:
            timezone = match.group(1)
        else:
            # Если не удалось распарсить - используем UTC
            timezone = "UTC"
            await message.answer(
                "⚠️ Не удалось определить часовой пояс. Будет использован UTC.",
            )
    
    data = await state.get_data()
    
    telegram_id = data.get("telegram_id")
    username = data.get("username")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    language_code = data.get("language_code")
    
    user_repo = UserRepository(db_session)
    
    # Создаем или обновляем пользователя с timezone
    user = await user_repo.get_or_create(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code,
    )
    
    # Обновляем timezone
    if user:
        user.timezone = timezone
        await db_session.commit()
        await db_session.refresh(user)
    
    await state.clear()
    
    await message.answer(
        f"✅ Часовой пояс установлен: {timezone}\n\n"
        "Теперь время будет отображаться в вашем часовом поясе.",
        reply_markup=get_main_menu_keyboard(),
    )
    
    # Показываем приветствие
    welcome_text = (
        "Привет 👋\n\n"
        "Я помогу тебе разобраться в связи\n"
        "стресса, эмоций и телесных ощущений.\n\n"
        "Важно:\n"
        "я не ставлю диагнозы и не заменяю врача.\n\n"
        "Можем начать с разбора симптома\n"
        "или поговорить о твоём состоянии."
    )
    
    await message.answer(
        text=welcome_text,
        reply_markup=get_main_menu_keyboard(),
    )
    
    logger.info(f"User registered with timezone: telegram_id={telegram_id}, timezone={timezone}")


@router.message(RegistrationStates.waiting_for_timezone)
async def process_timezone_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод в состоянии выбора timezone."""
    await message.answer(
        "Пожалуйста, выберите часовой пояс из списка\n"
        "или нажмите 'Пропустить'.",
        reply_markup=get_timezone_keyboard(),
    )


async def show_main_menu(message: types.Message, tg_user, db_session: AsyncSession):
    """Показывает главное меню."""
    user_repo = UserRepository(db_session)
    await user_repo.update_last_seen(tg_user.id)
    
    welcome_text = (
        "Привет 👋\n\n"
        "Я помогу тебе разобраться в связи\n"
        "стресса, эмоций и телесных ощущений.\n\n"
        "Важно:\n"
        "я не ставлю диагнозы и не заменяю врача.\n\n"
        "Можем начать с разбора симптома\n"
        "или поговорить о твоём состоянии."
    )
    
    await message.answer(
        text=welcome_text,
        reply_markup=get_main_menu_keyboard(),
    )