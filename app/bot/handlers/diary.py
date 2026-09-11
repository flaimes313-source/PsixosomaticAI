"""
Обработчик для раздела «Дневник».
Показывает все события пользователя, сгруппированные по датам и сессиям.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.bot.keyboards import get_main_menu_keyboard
from app.db.repositories.diary_repository import DiaryRepository
from app.db.models.user import User
from app.db.models.diary_event import DiaryEvent
from app.utils.logging import logger

router = Router()


def get_user_timezone(user) -> ZoneInfo:
    user_tz_str = user.timezone or "UTC"
    try:
        return ZoneInfo(user_tz_str)
    except:
        return ZoneInfo("UTC")


def format_dialog_preview(events: list, user_tz) -> tuple:
    """Форматирует диалог/опрос для краткого отображения."""
    if not events:
        return "📝 Пустой диалог", None
    
    first_event = events[0]
    time_str = first_event.created_at.astimezone(user_tz).strftime("%H:%M")
    
    event_types = [e.event_type for e in events]
    
    # Опросы
    if "survey_morning" in event_types:
        preview = f"🕐 {time_str}\n🌅 <b>Утренний опрос</b>\n{len(events)} вопросов"
        return preview, first_event.session_id
    elif "survey_day" in event_types:
        preview = f"🕐 {time_str}\n☀️ <b>Дневной опрос</b>\n{len(events)} вопросов"
        return preview, first_event.session_id
    elif "survey_evening" in event_types:
        preview = f"🕐 {time_str}\n🌆 <b>Вечерний опрос</b>\n{len(events)} вопросов"
        return preview, first_event.session_id
    
    # Обычный диалог
    user_message = None
    for event in events:
        if event.event_type == "describe_user":
            user_message = event.content
            break
    
    if not user_message:
        user_message = "Нет сообщений"
    
    preview = f"🕐 {time_str}\n📝 <b>Новый диалог</b>\n{user_message[:80]}..."
    return preview, first_event.session_id


def format_dialog_full(events: list, user_tz) -> str:
    """Форматирует полный диалог/опрос для отображения."""
    if not events:
        return "📝 Пустой диалог"
    
    first_event = events[0]
    date_str = first_event.created_at.astimezone(user_tz).strftime("%d.%m.%Y")
    event_types = [e.event_type for e in events]
    
    # Определяем тип
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
            # Опрос — показываем вопрос и ответ
            question = "Вопрос"
            if event.payload and isinstance(event.payload, dict):
                question = event.payload.get("question", "Вопрос")
            text += f"❓ <b>{question}</b>\n📝 {event.content}\n\n"
        elif event.event_type == "analysis":
            text += f"🧠 <b>Анализ</b> 🕐 {time_str}\n{event.content}\n\n"
    
    return text


def format_event_for_display(event: DiaryEvent, user_tz) -> str:
    """Форматирует одиночное событие (не диалог/опрос)."""
    time_str = event.created_at.astimezone(user_tz).strftime("%H:%M")
    
    if event.event_type == "analysis":
        return f"🕐 {time_str}\n🧠 <b>Анализ:</b>\n{event.content[:100]}...\n"
    else:
        return f"🕐 {time_str}\n📋 {event.event_type}\n"


@router.message(F.text == "📔 Дневник")
async def show_diary(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает дневник — события за сегодня."""
    await state.clear()
    
    telegram_id = message.from_user.id
    
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
    today = datetime.now(user_tz).date()
    
    diary_repo = DiaryRepository(db_session)
    events = await diary_repo.get_events_by_date(user.id, today)
    
    if not events:
        await message.answer(
            "📔 <b>Сегодня записей пока нет</b>\n\n"
            "Начни с кнопки 📝 Описать состояние\n"
            "или дождись опросов (утро/день/вечер).",
            reply_markup=get_diary_menu_keyboard(),
            parse_mode="HTML",
        )
        return
    
    # Группируем ВСЁ по сессиям (диалоги, опросы)
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
    
    text = f"📔 <b>Сегодня ({today.strftime('%d.%m.%Y')})</b>\n\n"
    keyboard_buttons = []
    idx = 0
    
    for session_id, session_events in sessions.items():
        idx += 1
        preview, _ = format_dialog_preview(session_events, user_tz)
        text += preview + "\n\n"
        keyboard_buttons.append(
            [InlineKeyboardButton(
                text=f"📖 Подробнее #{idx}",
                callback_data=f"diary_dialog_detail_{session_id}"
            )]
        )
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="📅 Другие дни", callback_data="diary_dates")
    ])
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 В меню", callback_data="diary_back_to_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"User opened diary: {telegram_id}")


@router.callback_query(F.data.startswith("diary_dialog_detail_"))
async def show_diary_dialog_detail(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает полный диалог/опрос по session_id."""
    await callback.answer()
    
    session_id = callback.data.replace("diary_dialog_detail_", "")
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
    text = format_dialog_full(events, user_tz)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к дневнику", callback_data="diary_back_to_today")]
        ]
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "diary_dates")
async def show_diary_dates(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает даты с событиями."""
    await callback.answer()
    
    telegram_id = callback.from_user.id
    
    result = await db_session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.message.edit_text("⚠️ Пожалуйста, отправьте /start", reply_markup=None)
        return
    
    diary_repo = DiaryRepository(db_session)
    dates = await diary_repo.get_dates_with_events(user.id, limit=30)
    
    if not dates:
        await callback.message.edit_text(
            "📋 У вас пока нет событий в дневнике.",
            reply_markup=get_diary_menu_keyboard(),
        )
        return
    
    text = "📅 <b>Выбери дату</b>\n\n"
    keyboard_buttons = []
    for event_date, count in dates:
        date_str = event_date.strftime("%d.%m.%Y")
        keyboard_buttons.append(
            [InlineKeyboardButton(
                text=f"{date_str} ({count} записей)",
                callback_data=f"diary_date_{event_date.isoformat()}"
            )]
        )
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="diary_back_to_today")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("diary_date_"))
async def show_diary_events_for_date(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает события за конкретную дату."""
    await callback.answer()
    
    date_str = callback.data.replace("diary_date_", "")
    event_date = date.fromisoformat(date_str)
    telegram_id = callback.from_user.id
    
    result = await db_session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.message.edit_text("⚠️ Пожалуйста, отправьте /start", reply_markup=None)
        return
    
    user_tz = get_user_timezone(user)
    diary_repo = DiaryRepository(db_session)
    events = await diary_repo.get_events_by_date(user.id, event_date)
    
    if not events:
        await callback.message.edit_text(
            f"📅 {event_date.strftime('%d.%m.%Y')} — записей нет.",
            reply_markup=get_diary_menu_keyboard(),
        )
        return
    
    text = f"📔 <b>{event_date.strftime('%d.%m.%Y')}</b>\n\n"
    
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
    
    keyboard_buttons = []
    idx = 0
    for session_id, session_events in sessions.items():
        idx += 1
        preview, _ = format_dialog_preview(session_events, user_tz)
        text += preview + "\n\n"
        keyboard_buttons.append(
            [InlineKeyboardButton(
                text=f"📖 Подробнее #{idx}",
                callback_data=f"diary_dialog_detail_{session_id}"
            )]
        )
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 Назад к датам", callback_data="diary_dates")
    ])
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 В меню", callback_data="diary_back_to_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "diary_back_to_today")
async def diary_back_to_today(callback: CallbackQuery, db_session: AsyncSession):
    """Возврат к сегодняшним событиям."""
    await callback.answer()
    
    telegram_id = callback.from_user.id
    
    result = await db_session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.message.edit_text("⚠️ Пожалуйста, отправьте /start", reply_markup=None)
        return
    
    user_tz = get_user_timezone(user)
    today = datetime.now(user_tz).date()
    
    diary_repo = DiaryRepository(db_session)
    events = await diary_repo.get_events_by_date(user.id, today)
    
    if not events:
        await callback.message.edit_text(
            f"📔 {today.strftime('%d.%m.%Y')} — записей нет.",
            reply_markup=get_diary_menu_keyboard(),
        )
        return
    
    text = f"📔 <b>Сегодня ({today.strftime('%d.%m.%Y')})</b>\n\n"
    
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
    
    keyboard_buttons = []
    idx = 0
    for session_id, session_events in sessions.items():
        idx += 1
        preview, _ = format_dialog_preview(session_events, user_tz)
        text += preview + "\n\n"
        keyboard_buttons.append(
            [InlineKeyboardButton(
                text=f"📖 Подробнее #{idx}",
                callback_data=f"diary_dialog_detail_{session_id}"
            )]
        )
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="📅 Другие дни", callback_data="diary_dates")
    ])
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 В меню", callback_data="diary_back_to_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "diary_back_to_menu")
async def diary_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await callback.answer()
    await state.clear()
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text="Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


def get_diary_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 История", callback_data="diary_history")],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="diary_back_to_menu")]
        ]
    )