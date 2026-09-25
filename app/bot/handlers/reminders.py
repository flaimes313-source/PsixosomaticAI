"""
Обработчик для раздела «Утреннее сообщение».
Пользователь может включить/выключить напоминание, изменить время и дни.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, Chat, User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, time
from typing import Optional, List

from app.bot.states import ReminderStates
from app.bot.keyboards.reminders import (
    get_reminders_menu_keyboard,
    get_time_preset_keyboard,
    get_days_keyboard,
    get_cancel_keyboard,
    get_reminders_menu_keyboard_with_back_to_profile,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.db.repositories.reminder import ReminderRepository
from app.db.models.user import User
from app.utils.logging import logger

router = Router()


@router.message(F.text == "🔔 Напоминания")
async def show_reminders_menu(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает меню утреннего напоминания (из главного меню)."""
    await state.clear()

    telegram_id = message.from_user.id
    reminder_repo = ReminderRepository(db_session)
    settings = await reminder_repo.get_or_create(telegram_id)

    status = "✅ включено" if settings.enabled else "❌ выключено"
    time_str = settings.reminder_time.strftime("%H:%M") if settings.reminder_time else "09:00"
    days_str = _format_days(settings.days_of_week) if settings.days_of_week else "каждый день"

    text = (
        f"🔔 <b>Утреннее сообщение</b>\n\n"
        f"Статус: {status}\n"
        f"Время: {time_str}\n"
        f"Дни: {days_str}\n\n"
        "Сома будет присылать короткое утреннее сообщение, "
        "чтобы ты мог описать своё состояние.\n\n"
        "Выбери действие:"
    )

    await message.answer(
        text,
        reply_markup=get_reminders_menu_keyboard(settings.enabled),
        parse_mode="HTML",
    )
    logger.info(f"User opened reminders from menu: {telegram_id}")


async def show_reminders_from_profile(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает настройки утреннего напоминания с возвратом в профиль."""
    await state.clear()

    telegram_id = message.from_user.id
    reminder_repo = ReminderRepository(db_session)
    settings = await reminder_repo.get_or_create(telegram_id)

    status = "✅ включено" if settings.enabled else "❌ выключено"
    time_str = settings.reminder_time.strftime("%H:%M") if settings.reminder_time else "09:00"
    days_str = _format_days(settings.days_of_week) if settings.days_of_week else "каждый день"

    text = (
        f"🔔 <b>Утреннее сообщение</b>\n\n"
        f"Статус: {status}\n"
        f"Время: {time_str}\n"
        f"Дни: {days_str}\n\n"
        "Сома будет присылать короткое утреннее сообщение, "
        "чтобы ты мог описать своё состояние.\n\n"
        "Выбери действие:"
    )

    await message.answer(
        text,
        reply_markup=get_reminders_menu_keyboard_with_back_to_profile(settings.enabled),
        parse_mode="HTML",
    )
    logger.info(f"User opened reminders from profile: {telegram_id}")


@router.callback_query(F.data == "reminders_enable")
async def enable_reminders(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Включает напоминания и запрашивает время."""
    await callback.answer()

    telegram_id = callback.from_user.id
    reminder_repo = ReminderRepository(db_session)

    user_result = await db_session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()
    user_timezone = user.timezone if user and user.timezone else "UTC"

    await reminder_repo.update(
        telegram_id,
        enabled=True,
        timezone=user_timezone,
    )

    await state.set_state(ReminderStates.waiting_for_time)

    await callback.message.edit_text(
        "🕐 <b>Настройка времени</b>\n\n"
        "Во сколько присылать утреннее сообщение?\n"
        "Выбери время:",
        reply_markup=get_time_preset_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("reminders_time_"))
async def set_reminder_time(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Устанавливает время напоминания."""
    await callback.answer()

    time_str = callback.data.replace("reminders_time_", "")

    if time_str == "custom":
        await state.set_state(ReminderStates.waiting_for_custom_time)
        await callback.message.edit_text(
            "⏰ <b>Введите время</b>\n\n"
            "Напиши время в формате <b>HH:MM</b>\n"
            "Например: 09:00\n\n"
            "Или нажми 'Отмена' для возврата.",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    try:
        hour, minute = map(int, time_str.split(':'))
        reminder_time = time(hour=hour, minute=minute)
    except:
        await callback.message.edit_text(
            "⚠️ Неверный формат времени. Попробуй ещё раз.",
            reply_markup=get_time_preset_keyboard(),
        )
        return

    telegram_id = callback.from_user.id
    reminder_repo = ReminderRepository(db_session)

    user_result = await db_session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()
    user_timezone = user.timezone if user and user.timezone else "UTC"

    await reminder_repo.update(
        telegram_id,
        reminder_time=reminder_time,
        timezone=user_timezone,
    )

    await state.set_state(ReminderStates.waiting_for_days)
    await state.update_data(reminder_time=reminder_time)

    await callback.message.edit_text(
        "📅 <b>Выбери дни недели</b>\n\n"
        "В какие дни отправлять утреннее сообщение?\n"
        "Выбери дни:",
        reply_markup=get_days_keyboard(),
        parse_mode="HTML",
    )


@router.message(ReminderStates.waiting_for_custom_time)
async def process_custom_time(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает пользовательское время."""
    text = message.text.strip()

    if text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Настройка отменена.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    try:
        if len(text) != 5 or text[2] != ':':
            raise ValueError
        hour, minute = map(int, text.split(':'))
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError
        reminder_time = time(hour=hour, minute=minute)
    except:
        await message.answer(
            "⚠️ Неверный формат. Введи время в формате <b>HH:MM</b>\n"
            "Например: 09:00",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    telegram_id = message.from_user.id
    reminder_repo = ReminderRepository(db_session)

    user_result = await db_session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()
    user_timezone = user.timezone if user and user.timezone else "UTC"

    await reminder_repo.update(
        telegram_id,
        reminder_time=reminder_time,
        timezone=user_timezone,
    )

    await state.set_state(ReminderStates.waiting_for_days)
    await state.update_data(reminder_time=reminder_time)

    await message.answer(
        "📅 <b>Выбери дни недели</b>\n\n"
        "В какие дни отправлять утреннее сообщение?\n"
        "Выбери дни:",
        reply_markup=get_days_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "reminders_days_all")
async def set_all_days(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await callback.answer()
    await _save_days(callback, state, db_session, None)


@router.callback_query(F.data == "reminders_days_weekdays")
async def set_weekdays(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await callback.answer()
    await _save_days(callback, state, db_session, [0, 1, 2, 3, 4])


@router.callback_query(F.data == "reminders_days_weekend")
async def set_weekend(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await callback.answer()
    await _save_days(callback, state, db_session, [5, 6])


@router.callback_query(F.data == "reminders_days_custom")
async def start_custom_days(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await callback.answer()
    await _save_days(callback, state, db_session, None)
    await callback.message.answer(
        "ℹ️ В текущей версии выбраны все дни недели.\n"
        "Позже можно будет настроить отдельные дни.",
    )


async def _save_days(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, days: Optional[List[int]]):
    telegram_id = callback.from_user.id
    reminder_repo = ReminderRepository(db_session)

    user_result = await db_session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()
    user_timezone = user.timezone if user and user.timezone else "UTC"

    data = await state.get_data()
    reminder_time = data.get('reminder_time')

    if not reminder_time:
        settings = await reminder_repo.get_by_user_id(telegram_id)
        if settings and settings.reminder_time:
            reminder_time = settings.reminder_time
        else:
            reminder_time = time(hour=9, minute=0)

    await reminder_repo.update(
        telegram_id,
        enabled=True,
        reminder_time=reminder_time,
        timezone=user_timezone,
        days_of_week=days,
    )

    await state.clear()

    days_str = _format_days(days) if days else "каждый день"
    time_str = reminder_time.strftime("%H:%M")

    await callback.message.edit_text(
        f"✅ <b>Утреннее сообщение настроено!</b>\n\n"
        f"🕐 Время: {time_str}\n"
        f"📅 Дни: {days_str}\n"
        f"🔔 Статус: включено\n\n"
        "Ты будешь получать короткое утреннее сообщение в выбранные дни.",
        reply_markup=get_reminders_menu_keyboard(True),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "reminders_disable")
async def disable_reminders(callback: CallbackQuery, db_session: AsyncSession):
    """Отключает напоминания."""
    try:
        await callback.answer("Утреннее сообщение отключено")

        telegram_id = callback.from_user.id
        reminder_repo = ReminderRepository(db_session)
        await reminder_repo.update(telegram_id, enabled=False)

        await callback.message.edit_text(
            "🔕 <b>Утреннее сообщение отключено</b>\n\n"
            "Ты больше не будешь получать утренние сообщения.\n\n"
            "Чтобы снова включить — нажми '✅ Включить'.",
            reply_markup=get_reminders_menu_keyboard(False),
            parse_mode="HTML",
        )
        logger.info(f"Reminders disabled for user: {telegram_id}")
    except Exception as e:
        logger.error(f"Error disabling reminders: {e}")
        await callback.answer("❌ Ошибка при отключении", show_alert=True)


@router.callback_query(F.data == "reminders_back_to_menu")
async def back_to_reminders_menu(callback: CallbackQuery, db_session: AsyncSession):
    await callback.answer()

    telegram_id = callback.from_user.id
    reminder_repo = ReminderRepository(db_session)
    settings = await reminder_repo.get_or_create(telegram_id)

    status = "✅ включено" if settings.enabled else "❌ выключено"
    time_str = settings.reminder_time.strftime("%H:%M") if settings.reminder_time else "09:00"
    days_str = _format_days(settings.days_of_week) if settings.days_of_week else "каждый день"

    text = (
        f"🔔 <b>Утреннее сообщение</b>\n\n"
        f"Статус: {status}\n"
        f"Время: {time_str}\n"
        f"Дни: {days_str}\n\n"
        "Выбери действие:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_reminders_menu_keyboard(settings.enabled),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "reminders_close")
async def close_reminders(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


# ==================== ВОЗВРАТ В ПРОФИЛЬ ====================

@router.callback_query(F.data == "reminders_back_to_profile")
async def back_to_profile_from_reminders(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await callback.answer()
    await state.clear()

    from app.bot.handlers.profile import show_profile_from_callback
    await callback.message.delete()
    await show_profile_from_callback(callback, state, db_session)


# ==================== ОТКРЫТИЕ «ОПИСАТЬ СОСТОЯНИЕ» ИЗ НАПОМИНАНИЯ ====================

@router.callback_query(F.data == "reminder_open_describe")
async def reminder_open_describe(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Открывает сценарий «Описать состояние» из утреннего сообщения."""
    await callback.answer()

    try:
        # Удаляем утреннее сообщение с кнопками
        try:
            await callback.message.delete()
        except Exception:
            pass

        # Запускаем тот же сценарий, что и кнопка «📝 Описать состояние»
        from app.bot.handlers.describe_state import _start_describe_state_flow
        await _start_describe_state_flow(callback.message, state, db_session)

        logger.info(f"✅ describe_state opened from morning message for user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"❌ Error opening describe_state from reminder: {e}", exc_info=True)
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text="⚠️ Произошла ошибка. Попробуй ещё раз через меню.",
            reply_markup=get_main_menu_keyboard(),
        )


# ==================== ВСПОМОГАТЕЛЬНАЯ ====================

def _format_days(days: Optional[List[int]]) -> str:
    if not days:
        return "каждый день"

    day_names = {
        0: "Пн",
        1: "Вт",
        2: "Ср",
        3: "Чт",
        4: "Пт",
        5: "Сб",
        6: "Вс",
    }
    return " ".join(day_names.get(d, "") for d in sorted(days))