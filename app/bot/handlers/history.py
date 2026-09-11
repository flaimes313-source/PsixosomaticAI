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


def format_dialog_full_history(events: list, user_tz) -> str:
    """Форматирует полный диалог/опрос для истории."""
    if not events:
        return "📝 Пустой диалог"
    
    first_event = events[0]
    date_str = first_event.created_at.astimezone(user_tz).strftime("%d.%m.%Y")
    event_types = [e.event_type for e in events]
    
    if "survey_morning" in event_types:
        text = f"🌅 <b>Утренний опрос</b>\n📅 {date_str}\n\n"
    elif "survey_day" in event_types:
        text = f"☀️ <b>Дневной опрос</b>\n📅 {date_str}\n\n"
    elif "survey_evening" in event_types:
        text = f"🌆 <b>Вечерний опрос</b>\n📅 {date_str}\n\n"
    else:
        text = f"💬 <b>Диалог</b>\n📅 {date_str}\n\n"
    
    for event in events:
        time_str = event.created_at.astimezone(user_tz).strftime("%H:%M")
        
        if event.event_type == "describe_user":
            text += f"👤 <b>Ты</b> 🕐 {time_str}\n{event.content}\n\n"
        elif event.event_type == "describe_ai":
            text += f"🧠 <b>AI</b> 🕐 {time_str}\n{event.content}\n\n"
        elif event.event_type == "clarification_question":
            text += f"❓ <b>Ты спросил</b> 🕐 {time_str}\n{event.content}\n\n"
        elif event.event_type == "clarification_answer":
            text += f"💬 <b>Ответ AI</b> 🕐 {time_str}\n{event.content}\n\n"
        elif event.event_type.startswith("survey_"):
            question = "Вопрос"
            if event.payload and isinstance(event.payload, dict):
                question = event.payload.get("question", "Вопрос")
            text += f"❓ <b>{question}</b>\n📝 {event.content}\n\n"
        elif event.event_type == "analysis":
            text += f"🧠 <b>Анализ</b> 🕐 {time_str}\n{event.content}\n\n"
    
    return text


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
    
    # Группируем по сессиям
    sessions = {}
    for event in events:
        if event.event_type in [
            "describe_user", "describe_ai", "clarification_question", "clarification_answer",
            "survey_morning", "survey_day", "survey_evening", "analysis"
        ]:
            session_id = event.session_id or f"single_{event.id}"
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(event)
    
    text = "📋 <b>История</b>\n\n"
    keyboard_buttons = []
    idx = 0
    
    for session_id, session_events in sessions.items():
        idx += 1
        first_event = session_events[0]
        time_str = first_event.created_at.astimezone(user_tz).strftime("%d.%m.%Y %H:%M")
        event_types = [e.event_type for e in session_events]
        
        # Определяем тип
        if "survey_morning" in event_types:
            preview = f"🌅 <b>Утренний опрос</b>\n🕐 {time_str}\n{len(session_events)} вопросов"
        elif "survey_day" in event_types:
            preview = f"☀️ <b>Дневной опрос</b>\n🕐 {time_str}\n{len(session_events)} вопросов"
        elif "survey_evening" in event_types:
            preview = f"🌆 <b>Вечерний опрос</b>\n🕐 {time_str}\n{len(session_events)} вопросов"
        else:
            user_message = "Нет сообщений"
            for ev in session_events:
                if ev.event_type == "describe_user":
                    user_message = ev.content
                    break
            preview = f"💬 <b>Диалог</b>\n🕐 {time_str}\n📝 {user_message[:80]}..."
        
        text += preview + "\n\n"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"📖 Подробнее #{idx}",
                callback_data=f"history_dialog_detail_{session_id}"
            )
        ])
    
    if len(events) >= 50:
        text += "\n📌 Показаны последние 50 событий"
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 В профиль", callback_data="back_to_profile_from_history")
    ])
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    if isinstance(event, CallbackQuery):
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("history_dialog_detail_"))
async def show_history_dialog_detail(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает полный диалог/опрос в истории."""
    await callback.answer()
    
    session_id = callback.data.replace("history_dialog_detail_", "")
    telegram_id = callback.from_user.id
    
    result = await db_session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.message.edit_text("⚠️ Пожалуйста, отправьте /start", reply_markup=None)
        return
    
    diary_repo = DiaryRepository(db_session)
    events = await diary_repo.get_session_events(user.id, session_id)
    
    if not events:
        await callback.message.edit_text("❌ Диалог не найден.", reply_markup=None)
        return
    
    user_tz = get_user_timezone(user)
    text = format_dialog_full_history(events, user_tz)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к истории", callback_data="diary_history")]
        ]
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


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
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text="Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )