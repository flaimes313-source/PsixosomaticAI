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


# Сколько записей показывать на одной странице
PAGE_SIZE = 12


def get_user_timezone(user) -> ZoneInfo:
    user_tz_str = user.timezone or "UTC"
    try:
        return ZoneInfo(user_tz_str)
    except:
        return ZoneInfo("UTC")


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def _truncate(text: str, limit: int = 40) -> str:
    """Аккуратно обрезает текст до limit символов, добавляя «...» при необходимости."""
    if not text:
        return ""

    text = text.strip().replace("\n", " ")

    if len(text) <= limit:
        return text

    return text[:limit].rstrip() + "..."


def _get_user_preview_text(events: list) -> str:
    """Возвращает текст первого сообщения пользователя в сессии."""
    for event in events:
        if event.event_type == "describe_user" and event.content:
            return event.content
    return ""


def _get_session_time(events: list, user_tz: ZoneInfo) -> str:
    """Возвращает время первого события в сессии (HH:MM)."""
    if not events:
        return "—:—"
    return events[0].created_at.astimezone(user_tz).strftime("%H:%M")


def _build_compact_button_label(session_events: list, user_tz: ZoneInfo) -> str:
    """
    Строит компактную метку для кнопки записи.
    Формат: 🕐 HH:MM · <начало сообщения пользователя>
    """
    time_str = _get_session_time(session_events, user_tz)
    user_text = _get_user_preview_text(session_events)

    if user_text:
        preview = _truncate(user_text, limit=40)
    else:
        # Если пользовательского текста нет (например, только AI-ответ)
        preview = "(без текста)"

    return f"🕐 {time_str} · {preview}"


def _group_by_sessions(events: list) -> dict:
    """Группирует события по session_id."""
    sessions = {}
    for event in events:
        if event.event_type in [
            "describe_user", "describe_ai",
            "clarification_question", "clarification_answer",
            "survey_morning", "survey_day", "survey_evening",
            "analysis",
        ]:
            session_id = event.session_id or f"single_{event.id}"
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(event)
    return sessions


def _build_sessions_keyboard(
    sessions: dict,
    user_tz: ZoneInfo,
    page: int = 0,
    date_iso: str = None,
    is_today: bool = False,
) -> tuple:
    """
    Строит клавиатуру с записями и пагинацией.

    Returns:
        (keyboard, total_pages, sessions_count)
    """
    sessions_list = list(sessions.items())  # [(session_id, events), ...]

    total = len(sessions_list)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    # Ограничиваем page
    page = max(0, min(page, total_pages - 1))

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_sessions = sessions_list[start:end]

    buttons = []

    # Компактные кнопки записей
    for session_id, session_events in page_sessions:
        label = _build_compact_button_label(session_events, user_tz)
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"diary_dialog_detail_{session_id}"
            )
        ])

    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Предыдущие",
            callback_data=f"diary_page_{'today' if is_today else date_iso}_{page - 1}"
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️ Следующие записи",
            callback_data=f"diary_page_{'today' if is_today else date_iso}_{page + 1}"
        ))
    if nav_buttons:
        buttons.append(nav_buttons)

    # Навигация по разделам
    if is_today:
        buttons.append([
            InlineKeyboardButton(text="📅 Другие дни", callback_data="diary_dates")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="🔙 Назад к датам", callback_data="diary_dates")
        ])
    buttons.append([
        InlineKeyboardButton(text="🔙 В меню", callback_data="diary_back_to_menu")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard, total_pages, total


# ==================== ФОРМАТИРОВАНИЕ ПОЛНОГО ДИАЛОГА ====================

def format_dialog_full(events: list, user_tz) -> str:
    """Форматирует полный диалог/опрос для отображения."""
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


# ==================== ГЛАВНЫЙ ЭКРАН ДНЕВНИКА ====================

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
    user_tz_str = user.timezone or "UTC"
    today = datetime.now(user_tz).date()

    diary_repo = DiaryRepository(db_session)
    events = await diary_repo.get_events_by_date(user.id, today, user_tz_str)

    if not events:
        await message.answer(
            "📔 Сегодня записей пока нет\n"
            "Начни с кнопки 📝 Описать состояние\n"
            "и расскажи, что сейчас происходит.",
            reply_markup=get_diary_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    sessions = _group_by_sessions(events)
    sessions_count = len(sessions)

    keyboard, total_pages, total = _build_sessions_keyboard(
        sessions, user_tz, page=0, is_today=True
    )

    text = (
        f"📔 <b>Сегодня ({today.strftime('%d.%m.%Y')})</b>\n\n"
        f"Записей: <b>{total}</b>"
    )
    if total_pages > 1:
        text += f"\nСтраница: <b>1</b> / <b>{total_pages}</b>"

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"User opened diary: {telegram_id}, sessions={sessions_count}")


# ==================== ПАГИНАЦИЯ ====================

@router.callback_query(F.data.startswith("diary_page_"))
async def diary_page_navigate(callback: CallbackQuery, db_session: AsyncSession):
    """
    Обрабатывает пагинацию.
    callback_data: diary_page_{'today'|<ISO-date>}_{page}
    """
    await callback.answer()

    data_parts = callback.data.replace("diary_page_", "").rsplit("_", 1)
    date_key = data_parts[0]
    page = int(data_parts[1])

    telegram_id = callback.from_user.id

    result = await db_session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await callback.message.edit_text("⚠️ Пожалуйста, отправьте /start", reply_markup=None)
        return

    user_tz = get_user_timezone(user)
    user_tz_str = user.timezone or "UTC"

    if date_key == "today":
        event_date = datetime.now(user_tz).date()
        is_today = True
        title = f"📔 <b>Сегодня ({event_date.strftime('%d.%m.%Y')})</b>"
    else:
        event_date = date.fromisoformat(date_key)
        is_today = False
        title = f"📔 <b>{event_date.strftime('%d.%m.%Y')}</b>"

    diary_repo = DiaryRepository(db_session)
    events = await diary_repo.get_events_by_date(user.id, event_date, user_tz_str)

    if not events:
        await callback.message.edit_text(
            f"{title}\n\nЗаписей нет.",
            reply_markup=get_diary_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    sessions = _group_by_sessions(events)

    keyboard, total_pages, total = _build_sessions_keyboard(
        sessions, user_tz, page=page,
        date_iso=None if is_today else event_date.isoformat(),
        is_today=is_today,
    )

    text = f"{title}\n\nЗаписей: <b>{total}</b>"
    if total_pages > 1:
        text += f"\nСтраница: <b>{page + 1}</b> / <b>{total_pages}</b>"

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== ПОЛНЫЙ ДИАЛОГ ====================

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

    # Определяем, куда вернуться
    first_event = events[0]
    event_date = first_event.created_at.astimezone(user_tz).date()
    today = datetime.now(user_tz).date()

    if event_date == today:
        back_callback = "diary_back_to_today"
        back_label = "🔙 Назад к дневнику"
    else:
        back_callback = f"diary_date_{event_date.isoformat()}"
        back_label = "🔙 Назад к дате"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=back_label, callback_data=back_callback)]
        ]
    )

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== СПИСОК ДАТ ====================

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


# ==================== ЗАПИСИ ЗА КОНКРЕТНУЮ ДАТУ ====================

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
    user_tz_str = user.timezone or "UTC"
    diary_repo = DiaryRepository(db_session)
    events = await diary_repo.get_events_by_date(user.id, event_date, user_tz_str)

    if not events:
        await callback.message.edit_text(
            f"📅 {event_date.strftime('%d.%m.%Y')} — записей нет.",
            reply_markup=get_diary_menu_keyboard(),
        )
        return

    sessions = _group_by_sessions(events)

    keyboard, total_pages, total = _build_sessions_keyboard(
        sessions, user_tz, page=0,
        date_iso=event_date.isoformat(),
        is_today=False,
    )

    text = f"📔 <b>{event_date.strftime('%d.%m.%Y')}</b>\n\nЗаписей: <b>{total}</b>"
    if total_pages > 1:
        text += f"\nСтраница: <b>1</b> / <b>{total_pages}</b>"

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== ВОЗВРАТ К СЕГОДНЯ ====================

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
    user_tz_str = user.timezone or "UTC"
    today = datetime.now(user_tz).date()

    diary_repo = DiaryRepository(db_session)
    events = await diary_repo.get_events_by_date(user.id, today, user_tz_str)

    if not events:
        await callback.message.edit_text(
            f"📔 {today.strftime('%d.%m.%Y')} — записей нет.",
            reply_markup=get_diary_menu_keyboard(),
        )
        return

    sessions = _group_by_sessions(events)

    keyboard, total_pages, total = _build_sessions_keyboard(
        sessions, user_tz, page=0, is_today=True
    )

    text = f"📔 <b>Сегодня ({today.strftime('%d.%m.%Y')})</b>\n\nЗаписей: <b>{total}</b>"
    if total_pages > 1:
        text += f"\nСтраница: <b>1</b> / <b>{total_pages}</b>"

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== ЗАКРЫТИЕ ====================

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