"""
Обработчик для просмотра истории сессий (хронологическая лента).
Использует DiaryRepository.

Изменения:
- Компактный текст (без повторения «Диалог» перед каждой записью).
- Компактные кнопки: 🕐 HH:MM · <начало сообщения>.
- Пагинация по 12 записей.
- Убрана кнопка «🏠 В меню», оставлена «↩️ В профиль».
- ФИКС: разбиение длинных диалогов на части (Telegram: лимит 4096 символов).
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


# Сколько записей показывать на одной странице
PAGE_SIZE = 12

# Лимит Telegram на длину сообщения — 4096. Берём с запасом.
MAX_MESSAGE_LENGTH = 4000


# ==================== ВСПОМОГАТЕЛЬНЫЕ ====================

def get_user_timezone(user) -> ZoneInfo:
    user_tz_str = user.timezone or "UTC"
    try:
        return ZoneInfo(user_tz_str)
    except Exception:
        return ZoneInfo("UTC")


def _truncate(text: str, limit: int = 40) -> str:
    """Аккуратно обрезает текст до limit символов, добавляя «...» при необходимости."""
    if not text:
        return ""

    text = text.strip().replace("\n", " ")

    if len(text) <= limit:
        return text

    truncated = text[:limit]
    last_space = truncated.rfind(" ")

    if last_space > limit * 0.6:
        truncated = truncated[:last_space]

    return truncated.rstrip() + "..."


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


def _get_session_datetime(events: list, user_tz: ZoneInfo) -> str:
    """Возвращает дату+время первого события (DD.MM.YYYY HH:MM)."""
    if not events:
        return ""
    return events[0].created_at.astimezone(user_tz).strftime("%d.%m.%Y %H:%M")


def _build_compact_button_label(session_events: list, user_tz: ZoneInfo) -> str:
    """Строит компактную метку для кнопки записи."""
    time_str = _get_session_time(session_events, user_tz)
    user_text = _get_user_preview_text(session_events)

    if user_text:
        preview = _truncate(user_text, limit=40)
    else:
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


def _split_message(text: str, max_len: int = MAX_MESSAGE_LENGTH):
    """
    Разбивает длинный текст на части по max_len символов.
    Старается резать по переносам строк, чтобы не рвать слова.
    """
    if len(text) <= max_len:
        return [text]

    parts = []
    remaining = text

    while remaining:
        if len(remaining) <= max_len:
            parts.append(remaining)
            break

        # Ищем последний перенос строки в пределах max_len
        cut = remaining.rfind("\n", 0, max_len)

        # Если переносов нет или они слишком близко к началу — режем по пробелу
        if cut == -1 or cut < max_len * 0.5:
            cut = remaining.rfind(" ", 0, max_len)

        # Если и пробела нет — режем жёстко
        if cut == -1 or cut < max_len * 0.5:
            cut = max_len

        parts.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n ")

    return parts


async def _send_long_message(
    callback: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup = None,
):
    """
    Отправляет текст, разбивая его на части, если он длиннее лимита Telegram.
    Кнопки — на последней части.
    """
    parts = _split_message(text)

    # Если одна часть — пытаемся отредактировать, иначе отправляем
    if len(parts) == 1:
        try:
            await callback.message.edit_text(
                parts[0],
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return
        except Exception:
            await callback.message.answer(
                parts[0],
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return

    # Несколько частей: удаляем старое сообщение
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Отправляем все части, кроме последней — без кнопок
    for part in parts[:-1]:
        await callback.message.answer(part, parse_mode="HTML")

    # Последняя — с кнопками
    await callback.message.answer(
        parts[-1],
        reply_markup=keyboard,
        parse_mode="HTML",
    )


def _build_page_text_and_keyboard(
    sessions: dict,
    user_tz: ZoneInfo,
    page: int = 0,
):
    """Строит текст истории + клавиатуру с пагинацией."""
    sessions_list = list(sessions.items())

    total = len(sessions_list)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    page = max(0, min(page, total_pages - 1))

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_sessions = sessions_list[start:end]

    text = "📋 <b>История</b>\n\n"

    for session_id, session_events in page_sessions:
        dt_str = _get_session_datetime(session_events, user_tz)
        user_text = _get_user_preview_text(session_events)

        if user_text:
            preview = _truncate(user_text, limit=60)
        else:
            preview = "(без текста)"

        text += f"🕐 {dt_str}\n📝 {preview}\n\n"

    if total_pages > 1:
        text += f"📌 Страница {page + 1} из {total_pages}\n"
    else:
        text += f"📌 Показаны последние {total} диалогов"

    buttons = []

    for session_id, session_events in page_sessions:
        label = _build_compact_button_label(session_events, user_tz)
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"history_dialog_detail_{session_id}"
            )
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Предыдущие",
            callback_data=f"history_page_{page - 1}"
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️ Следующие записи",
            callback_data=f"history_page_{page + 1}"
        ))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="↩️ В профиль", callback_data="back_to_profile_from_history")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard, total_pages


# ==================== ФОРМАТ ПОЛНОГО ДИАЛОГА ====================

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


# ==================== ГЛАВНЫЙ ПОКАЗ ИСТОРИИ ====================

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
    events = await diary_repo.get_latest_events(user.id, limit=200)

    if not events:
        text = (
            "📋 <b>История пуста</b>\n\n"
            "Начни с кнопки 📝 Описать состояние\n"
            "и расскажи, что сейчас происходит."
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="↩️ В профиль", callback_data="back_to_profile_from_history")]
            ]
        )
        if isinstance(event, CallbackQuery):
            try:
                await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        return

    sessions = _group_by_sessions(events)

    text, keyboard, total_pages = _build_page_text_and_keyboard(sessions, user_tz, page=0)

    if isinstance(event, CallbackQuery):
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    logger.info(f"User opened history: {telegram_id}, sessions={len(sessions)}")


# ==================== ПАГИНАЦИЯ ====================

@router.callback_query(F.data.startswith("history_page_"))
async def history_page_navigate(callback: CallbackQuery, db_session: AsyncSession):
    """Обрабатывает пагинацию в истории."""
    await callback.answer()

    page = int(callback.data.replace("history_page_", ""))
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
    events = await diary_repo.get_latest_events(user.id, limit=200)

    if not events:
        await callback.message.edit_text(
            "📋 История пуста.",
            reply_markup=None,
        )
        return

    sessions = _group_by_sessions(events)

    text, keyboard, total_pages = _build_page_text_and_keyboard(sessions, user_tz, page=page)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== ПОЛНЫЙ ДИАЛОГ ====================

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
            [InlineKeyboardButton(text="↩️ Назад к истории", callback_data="diary_history")]
        ]
    )

    # ФИКС: если текст длинный — разбиваем на части
    await _send_long_message(callback, text, keyboard)


# ==================== ВОЗВРАТ В ПРОФИЛЬ ====================

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


# ==================== УДАЛЕНО: КНОПКА «В МЕНЮ» ====================