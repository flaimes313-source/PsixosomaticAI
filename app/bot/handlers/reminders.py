"""
Обработчик для раздела "Напоминания".
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import time, datetime
from typing import Optional, List

from app.bot.states import ReminderStates  # ← ИСПРАВЛЕНО (без .reminders)
from app.bot.keyboards.reminders import (
    get_reminders_menu_keyboard,
    get_time_preset_keyboard,
    get_days_keyboard,
    get_cancel_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.db.repositories.reminder import ReminderRepository
from app.utils.logging import logger

router = Router()


@router.message(F.text == "🔔 Напоминания")
async def show_reminders_menu(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает меню напоминаний."""
    await state.clear()
    
    telegram_id = message.from_user.id
    reminder_repo = ReminderRepository(db_session)
    settings = await reminder_repo.get_or_create(telegram_id)
    
    # Формируем статус
    status = "✅ включены" if settings.enabled else "❌ выключены"
    time_str = settings.reminder_time.strftime("%H:%M") if settings.reminder_time else "не задано"
    days_str = _format_days(settings.days_of_week) if settings.days_of_week else "каждый день"
    
    text = (
        f"🔔 <b>Напоминания</b>\n\n"
        f"Статус: {status}\n"
        f"Время: {time_str}\n"
        f"Дни: {days_str}\n\n"
        "Выбери действие:"
    )
    
    await message.answer(
        text,
        reply_markup=get_reminders_menu_keyboard(settings.enabled),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "reminders_enable")
async def enable_reminders(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Включает напоминания и запрашивает время."""
    await callback.answer()
    
    telegram_id = callback.from_user.id
    reminder_repo = ReminderRepository(db_session)
    
    # Включаем, но время ещё не задано
    settings = await reminder_repo.update(telegram_id, enabled=True)
    
    await state.set_state(ReminderStates.waiting_for_time)
    
    await callback.message.edit_text(
        "🕐 <b>Настройка времени</b>\n\n"
        "Во сколько напоминать заполнить дневник?\n"
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
            "Например: 21:30\n\n"
            "Или нажми 'Отмена' для возврата.",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
        return
    
    # Парсим время
    try:
        hour, minute = map(int, time_str.split(':'))
        reminder_time = time(hour=hour, minute=minute)
    except:
        await callback.message.edit_text(
            "⚠️ Неверный формат времени. Попробуй ещё раз.",
            reply_markup=get_time_preset_keyboard(),
        )
        return
    
    # Сохраняем время в БД
    telegram_id = callback.from_user.id
    reminder_repo = ReminderRepository(db_session)
    await reminder_repo.update(telegram_id, reminder_time=reminder_time)
    
    # Переходим к выбору дней
    await state.set_state(ReminderStates.waiting_for_days)
    await state.update_data(reminder_time=reminder_time)
    
    await callback.message.edit_text(
        "📅 <b>Выбери дни недели</b>\n\n"
        "В какие дни отправлять напоминание?\n"
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
    
    # Валидация формата HH:MM
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
            "Например: 21:30",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
        return
    
    # Сохраняем время
    telegram_id = message.from_user.id
    reminder_repo = ReminderRepository(db_session)
    await reminder_repo.update(telegram_id, reminder_time=reminder_time)
    
    await state.set_state(ReminderStates.waiting_for_days)
    await state.update_data(reminder_time=reminder_time)
    
    await message.answer(
        "📅 <b>Выбери дни недели</b>\n\n"
        "В какие дни отправлять напоминание?\n"
        "Выбери дни:",
        reply_markup=get_days_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "reminders_days_all")
async def set_all_days(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Устанавливает все дни недели."""
    await callback.answer()
    await _save_days(callback, state, db_session, None)


@router.callback_query(F.data == "reminders_days_weekdays")
async def set_weekdays(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Устанавливает только будни (Пн-Пт)."""
    await callback.answer()
    await _save_days(callback, state, db_session, [0, 1, 2, 3, 4])


@router.callback_query(F.data == "reminders_days_weekend")
async def set_weekend(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Устанавливает только выходные (Сб-Вс)."""
    await callback.answer()
    await _save_days(callback, state, db_session, [5, 6])


@router.callback_query(F.data == "reminders_days_custom")
async def start_custom_days(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Начинает выбор пользовательских дней."""
    await callback.answer()
    
    # Здесь можно реализовать пошаговый выбор каждого дня
    # Для MVP просто сохраняем все дни
    await _save_days(callback, state, db_session, None)
    await callback.message.answer(
        "ℹ️ В текущей версии выбраны все дни недели.\n"
        "Позже можно будет настроить отдельные дни.",
    )


async def _save_days(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, days: Optional[List[int]]):
    """Сохраняет выбранные дни и завершает настройку."""
    telegram_id = callback.from_user.id
    reminder_repo = ReminderRepository(db_session)
    
    data = await state.get_data()
    reminder_time = data.get('reminder_time')
    
    if not reminder_time:
        # Если время не сохранилось, берём из БД
        settings = await reminder_repo.get_by_user_id(telegram_id)
        if settings and settings.reminder_time:
            reminder_time = settings.reminder_time
        else:
            reminder_time = time(hour=21, minute=0)  # Значение по умолчанию
    
    # Обновляем настройки
    await reminder_repo.update(
        telegram_id,
        enabled=True,
        reminder_time=reminder_time,
        days_of_week=days,  # None = каждый день
    )
    
    await state.clear()
    
    # Показываем финальный статус
    days_str = _format_days(days) if days else "каждый день"
    time_str = reminder_time.strftime("%H:%M")
    
    await callback.message.edit_text(
        f"✅ <b>Напоминания настроены!</b>\n\n"
        f"🕐 Время: {time_str}\n"
        f"📅 Дни: {days_str}\n"
        f"🔔 Статус: включены\n\n"
        "Ты будешь получать напоминание каждый выбранный день.",
        reply_markup=get_reminders_menu_keyboard(True),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "reminders_disable")
async def disable_reminders(callback: CallbackQuery, db_session: AsyncSession):
    """Отключает напоминания."""
    await callback.answer("Напоминания отключены")
    
    telegram_id = callback.from_user.id
    reminder_repo = ReminderRepository(db_session)
    await reminder_repo.update(telegram_id, enabled=False)
    
    await callback.message.edit_text(
        "🔕 <b>Напоминания отключены</b>\n\n"
        "Ты больше не будешь получать напоминания о дневнике.\n\n"
        "Чтобы снова включить — нажми '✅ Включить'.",
        reply_markup=get_reminders_menu_keyboard(False),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "reminders_back_to_menu")
async def back_to_reminders_menu(callback: CallbackQuery, db_session: AsyncSession):
    """Возврат в меню напоминаний."""
    await callback.answer()
    
    telegram_id = callback.from_user.id
    reminder_repo = ReminderRepository(db_session)
    settings = await reminder_repo.get_or_create(telegram_id)
    
    status = "✅ включены" if settings.enabled else "❌ выключены"
    time_str = settings.reminder_time.strftime("%H:%M") if settings.reminder_time else "не задано"
    days_str = _format_days(settings.days_of_week) if settings.days_of_week else "каждый день"
    
    text = (
        f"🔔 <b>Напоминания</b>\n\n"
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
    """Закрывает раздел напоминаний и возвращает в главное меню."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


def _format_days(days: Optional[List[int]]) -> str:
    """Форматирует список дней недели в строку."""
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