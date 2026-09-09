"""
Обработчик для просмотра истории сессий (хронологическая лента).
Использует DiaryRepository.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from zoneinfo import ZoneInfo

from app.db.repositories.diary_repository import DiaryRepository
from app.db.models.user import User
from app.db.models.diary_event import DiaryEvent
from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


def get_user_timezone(user) -> ZoneInfo:
    user_tz_str = user.timezone or "UTC"
    try:
        return ZoneInfo(user_tz_str)
    except:
        return ZoneInfo("UTC")


def format_event_for_history(event, user_tz) -> str:
    """Форматирует событие для истории (кратко)."""
    time_str = event.created_at.astimezone(user_tz).strftime("%d.%m.%Y %H:%M")
    
    emoji_map = {
        "describe_user": "📝",
        "describe_ai": "🧠",
        "survey_morning": "🌅",
        "survey_day": "☀️",
        "survey_evening": "🌆",
        "analysis": "🧠",
        "clarification_question": "❓",
        "clarification_answer": "💬",
    }
    
    emoji = emoji_map.get(event.event_type, "📋")
    
    type_names = {
        "describe_user": "Ты написал",
        "describe_ai": "Ответ AI",
        "survey_morning": "Утренний опрос",
        "survey_day": "Дневной опрос",
        "survey_evening": "Вечерний опрос",
        "analysis": "Анализ",
        "clarification_question": "Ты спросил",
        "clarification_answer": "Ответ AI",
    }
    
    type_name = type_names.get(event.event_type, event.event_type)
    content_preview = event.content[:80] + "..." if event.content and len(event.content) > 80 else event.content or ""
    
    return f"{emoji} {time_str} — <b>{type_name}</b>\n{content_preview}\n"


def format_event_full_history(event: DiaryEvent, user_tz) -> str:
    """Форматирует событие для полного просмотра в истории."""
    time_str = event.created_at.astimezone(user_tz).strftime("%d.%m.%Y %H:%M")
    
    emoji_map = {
        "describe_user": "📝",
        "describe_ai": "🧠",
        "survey_morning": "🌅",
        "survey_day": "☀️",
        "survey_evening": "🌆",
        "analysis": "🧠",
        "clarification_question": "❓",
        "clarification_answer": "💬",
    }
    
    emoji = emoji_map.get(event.event_type, "📋")
    
    type_names = {
        "describe_user": "Ты написал",
        "describe_ai": "Ответ AI",
        "survey_morning": "Утренний опрос",
        "survey_day": "Дневной опрос",
        "survey_evening": "Вечерний опрос",
        "analysis": "Анализ",
        "clarification_question": "Ты спросил",
        "clarification_answer": "Ответ AI",
    }
    
    type_name = type_names.get(event.event_type, event.event_type)
    
    return f"{emoji} <b>{type_name}</b>\n🕐 {time_str}\n\n{event.content}\n"


@router.message(F.text == "📋 История")
@router.callback_query(F.data == "diary_history")
async def show_history(event: types.Message | CallbackQuery, db_session: AsyncSession, state: FSMContext = None):
    """Показывает историю (хронологическая лента)."""
    if isinstance(event, CallbackQuery):
        await event.answer()
        telegram_id = event.from_user.id
        message = event.message
        if state:
            await state.clear()
    else:
        telegram_id = event.from_user.id
        message = event
        if state:
            await state.clear()
    
    result = await db_session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer(
            "⚠️ Вы еще не зарегистрированы.\nОтправьте /start",
            reply_markup=get_main_menu_keyboard(),
        )
        return
    
    user_tz = get_user_timezone(user)
    diary_repo = DiaryRepository(db_session)
    
    # Получаем последние 50 событий
    events = await diary_repo.get_latest_events(user.id, limit=50)
    
    if not events:
        await message.answer(
            "📋 <b>История пуста</b>\n\n"
            "Начни с кнопки 📝 Описать состояние\n"
            "или дождись опросов (утро/день/вечер).",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML",
        )
        return
    
    text = "📋 <b>История</b>\n\n"
    
    keyboard_buttons = []
    for idx, event in enumerate(events):
        text += format_event_for_history(event, user_tz)
        text += "\n"
        keyboard_buttons.append(
            [InlineKeyboardButton(
                text=f"📖 Подробнее #{idx+1}",
                callback_data=f"history_event_detail_{event.id}"
            )]
        )
    
    if len(events) >= 50:
        text += "\n📌 Показаны последние 50 событий"
    
    keyboard_buttons.append([
        InlineKeyboardButton(
            text="🔙 В профиль",
            callback_data="back_to_profile_from_history"
        )
    ])
    keyboard_buttons.append([
        InlineKeyboardButton(
            text="🔙 В меню",
            callback_data="back_to_menu"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    if isinstance(event, CallbackQuery):
        await message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("history_event_detail_"))
async def show_history_event_detail(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает полное содержимое события в истории."""
    await callback.answer()
    
    event_id = int(callback.data.replace("history_event_detail_", ""))
    telegram_id = callback.from_user.id
    
    result = await db_session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.message.edit_text(
            "⚠️ Пожалуйста, отправьте /start",
            reply_markup=None,
        )
        return
    
    diary_repo = DiaryRepository(db_session)
    event = await diary_repo.get_event(event_id, user.id)
    
    if not event:
        await callback.message.edit_text(
            "❌ Событие не найдено.",
            reply_markup=None,
        )
        return
    
    user_tz = get_user_timezone(user)
    
    # Форматируем полное содержимое
    text = format_event_full_history(event, user_tz)
    
    # Кнопка "Назад"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 Назад к истории",
                callback_data="diary_history"
            )]
        ]
    )
    
    # Если это сообщение в списке — редактируем его
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception:
        # Если не удалось отредактировать — отправляем новое
        await callback.message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )


@router.callback_query(F.data == "back_to_profile_from_history")
async def back_to_profile_from_history(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Возврат в профиль из истории."""
    await callback.answer()
    await state.clear()
    
    from app.bot.handlers.profile import show_profile_from_callback
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await show_profile_from_callback(callback, state, db_session)


@router.callback_query(F.data == "back_to_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )