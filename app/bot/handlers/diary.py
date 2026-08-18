"""
Обработчик для сценария "Дневник".
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.bot.states import DiaryStates
from app.bot.keyboards.diary import (
    get_diary_menu_keyboard,
    get_intensity_keyboard,
    get_mood_keyboard,
    get_stress_keyboard,
    get_sleep_keyboard,
    get_skip_keyboard,
    get_cancel_keyboard,
    get_confirm_keyboard,
    get_entry_detail_keyboard,
    get_confirm_delete_keyboard,
    get_date_navigation_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.db.repositories.diary import DiaryRepository
from app.db.models.user import User
from app.utils.logging import logger

router = Router()
MAX_SYMPTOM_LENGTH = 500
MAX_TEXT_LENGTH = 2000


def get_user_timezone(user) -> ZoneInfo:
    """Возвращает часовой пояс пользователя."""
    user_tz_str = user.timezone or "UTC"
    try:
        return ZoneInfo(user_tz_str)
    except:
        return ZoneInfo("UTC")


# ==================== ГЛАВНОЕ МЕНЮ ДНЕВНИКА ====================

@router.message(F.text == "📔 Дневник")
async def show_diary_menu(message: types.Message, state: FSMContext):
    """Показывает главное меню дневника."""
    await state.clear()
    
    await message.answer(
        "📔 Мой дневник\n\n"
        "Выбери действие:",
        reply_markup=get_diary_menu_keyboard(),
    )
    logger.info(f"User opened diary menu: telegram_id={message.from_user.id}")


@router.message(F.text == "🔙 Назад")
async def back_to_main_menu_from_diary(message: types.Message, state: FSMContext):
    """Возврат в главное меню из дневника (без FSM)."""
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


# ==================== НОВАЯ ЗАПИСЬ ====================

@router.message(F.text == "➕ Новая запись")
async def start_new_diary_entry(message: types.Message, state: FSMContext):
    """Начинает создание новой дневниковой записи."""
    await state.clear()
    await state.set_state(DiaryStates.waiting_for_symptom)
    
    await message.answer(
        "📝 Новая запись в дневнике\n\n"
        "1/7: Опишите ваш симптом или состояние.\n\n"
        "Например: головная боль, усталость, тревога...",
        reply_markup=get_cancel_keyboard(),
    )
    logger.info(f"User started new diary entry: telegram_id={message.from_user.id}")


# ==================== ШАГ 1: СИМПТОМ ====================

@router.message(DiaryStates.waiting_for_symptom, F.text)
async def process_diary_symptom(message: types.Message, state: FSMContext):
    """Обработка симптома."""
    symptom = message.text.strip()
    
    if symptom.startswith('/'):
        return
    
    if len(symptom) < 2:
        await message.answer(
            "Пожалуйста, опишите симптом более подробно.\n"
            "Минимум 2 символа.",
            reply_markup=get_cancel_keyboard(),
        )
        return
    
    if len(symptom) > MAX_SYMPTOM_LENGTH:
        await message.answer(
            f"Симптом слишком длинный. Пожалуйста, сократите до {MAX_SYMPTOM_LENGTH} символов.",
            reply_markup=get_cancel_keyboard(),
        )
        return
    
    await state.update_data(symptom=symptom)
    await state.set_state(DiaryStates.waiting_for_intensity)
    
    await message.answer(
        "2/7: Оцените интенсивность симптома по шкале от 0 до 10.\n\n"
        "0 — нет симптома\n"
        "1-3 — слабый\n"
        "4-6 — средний\n"
        "7-9 — сильный\n"
        "10 — максимальный\n\n"
        "Выберите число:",
        reply_markup=get_intensity_keyboard(),
    )


@router.message(DiaryStates.waiting_for_symptom)
async def process_diary_symptom_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод симптома."""
    await message.answer(
        "Пожалуйста, опишите ваш симптом текстом.",
        reply_markup=get_cancel_keyboard(),
    )


# ==================== ШАГ 2: ИНТЕНСИВНОСТЬ ====================

@router.message(DiaryStates.waiting_for_intensity, F.text)
async def process_diary_intensity(message: types.Message, state: FSMContext):
    """Обработка интенсивности."""
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    try:
        intensity = int(text)
        if intensity < 0 or intensity > 10:
            raise ValueError
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число от 0 до 10.",
            reply_markup=get_intensity_keyboard(),
        )
        return
    
    await state.update_data(symptom_intensity=intensity)
    await state.set_state(DiaryStates.waiting_for_mood)
    
    await message.answer(
        "3/7: Как ваше настроение сегодня?\n\n"
        "1 😞 — очень плохое\n"
        "2 🙁 — плохое\n"
        "3 😐 — нормальное\n"
        "4 🙂 — хорошее\n"
        "5 😄 — отличное\n\n"
        "Выберите:",
        reply_markup=get_mood_keyboard(),
    )


@router.message(DiaryStates.waiting_for_intensity)
async def process_diary_intensity_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод интенсивности."""
    await message.answer(
        "Пожалуйста, введите число от 0 до 10.",
        reply_markup=get_intensity_keyboard(),
    )


# ==================== ШАГ 3: НАСТРОЕНИЕ ====================

@router.message(DiaryStates.waiting_for_mood, F.text)
async def process_diary_mood(message: types.Message, state: FSMContext):
    """Обработка настроения."""
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    # Извлекаем число из текста (например "3 😐" -> 3)
    try:
        if text[0].isdigit():
            mood = int(text[0])
        else:
            mood = int(text)
        if mood < 1 or mood > 5:
            raise ValueError
    except ValueError:
        await message.answer(
            "Пожалуйста, выберите число от 1 до 5.",
            reply_markup=get_mood_keyboard(),
        )
        return
    
    await state.update_data(mood=mood)
    await state.set_state(DiaryStates.waiting_for_stress)
    
    await message.answer(
        "4/7: Оцените уровень стресса сегодня по шкале от 0 до 10.\n\n"
        "0 — полное спокойствие\n"
        "5 — средний уровень\n"
        "10 — максимальный стресс\n\n"
        "Выберите число:",
        reply_markup=get_stress_keyboard(),
    )


@router.message(DiaryStates.waiting_for_mood)
async def process_diary_mood_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод настроения."""
    await message.answer(
        "Пожалуйста, выберите число от 1 до 5.",
        reply_markup=get_mood_keyboard(),
    )


# ==================== ШАГ 4: СТРЕСС ====================

@router.message(DiaryStates.waiting_for_stress, F.text)
async def process_diary_stress(message: types.Message, state: FSMContext):
    """Обработка уровня стресса."""
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    try:
        stress = int(text)
        if stress < 0 or stress > 10:
            raise ValueError
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число от 0 до 10.",
            reply_markup=get_stress_keyboard(),
        )
        return
    
    await state.update_data(stress=stress)
    await state.set_state(DiaryStates.waiting_for_sleep)
    
    await message.answer(
        "5/7: Сколько часов вы спали прошлой ночью?\n\n"
        "Напишите число (например: 7, 7.5, 6,5):",
        reply_markup=get_sleep_keyboard(),
    )


@router.message(DiaryStates.waiting_for_stress)
async def process_diary_stress_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод стресса."""
    await message.answer(
        "Пожалуйста, введите число от 0 до 10.",
        reply_markup=get_stress_keyboard(),
    )


# ==================== ШАГ 5: СОН ====================

@router.message(DiaryStates.waiting_for_sleep, F.text)
async def process_diary_sleep(message: types.Message, state: FSMContext):
    """Обработка часов сна."""
    text = message.text.strip().replace(',', '.')
    
    if text.startswith('/'):
        return
    
    try:
        sleep_hours = float(text)
        if sleep_hours < 0 or sleep_hours > 24:
            raise ValueError
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число от 0 до 24.\n"
            "Например: 7, 7.5, 8",
            reply_markup=get_sleep_keyboard(),
        )
        return
    
    await state.update_data(sleep_hours=sleep_hours)
    await state.set_state(DiaryStates.waiting_for_context)
    
    await message.answer(
        "6/7: Что происходило сегодня или непосредственно перед появлением симптома?\n\n"
        "Опишите контекст или события.\n"
        "Можно пропустить.",
        reply_markup=get_skip_keyboard(),
    )


@router.message(DiaryStates.waiting_for_sleep)
async def process_diary_sleep_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод сна."""
    await message.answer(
        "Пожалуйста, введите число от 0 до 24.\n"
        "Например: 7, 7.5, 8",
        reply_markup=get_sleep_keyboard(),
    )


# ==================== ШАГ 6: КОНТЕКСТ ====================

@router.message(DiaryStates.waiting_for_context, F.text)
async def process_diary_context(message: types.Message, state: FSMContext):
    """Обработка контекста."""
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    if text == "⏭ Пропустить":
        await state.update_data(context=None)
    else:
        if len(text) > MAX_TEXT_LENGTH:
            await message.answer(
                f"Текст слишком длинный. Пожалуйста, сократите до {MAX_TEXT_LENGTH} символов.",
                reply_markup=get_skip_keyboard(),
            )
            return
        await state.update_data(context=text)
    
    await state.set_state(DiaryStates.waiting_for_note)
    
    await message.answer(
        "7/7: Есть ли что-нибудь ещё, что вы хотите отметить?\n\n"
        "Дополнительная заметка.\n"
        "Можно пропустить.",
        reply_markup=get_skip_keyboard(),
    )


@router.message(DiaryStates.waiting_for_context)
async def process_diary_context_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод контекста."""
    await message.answer(
        "Пожалуйста, опишите контекст текстом или нажмите 'Пропустить'.",
        reply_markup=get_skip_keyboard(),
    )


# ==================== ШАГ 7: ЗАМЕТКА ====================

@router.message(DiaryStates.waiting_for_note, F.text)
async def process_diary_note(message: types.Message, state: FSMContext):
    """Обработка заметки."""
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    if text == "⏭ Пропустить":
        await state.update_data(note=None)
    else:
        if len(text) > MAX_TEXT_LENGTH:
            await message.answer(
                f"Текст слишком длинный. Пожалуйста, сократите до {MAX_TEXT_LENGTH} символов.",
                reply_markup=get_skip_keyboard(),
            )
            return
        await state.update_data(note=text)
    
    # Показываем предпросмотр
    await show_preview(message, state)


@router.message(DiaryStates.waiting_for_note)
async def process_diary_note_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод заметки."""
    await message.answer(
        "Пожалуйста, напишите заметку текстом или нажмите 'Пропустить'.",
        reply_markup=get_skip_keyboard(),
    )


# ==================== ПРЕДПРОСМОТР ====================

async def show_preview(message: types.Message, state: FSMContext):
    """Показывает предпросмотр записи."""
    data = await state.get_data()
    
    today = date.today()
    
    preview_text = (
        "📔 Проверь запись\n\n"
        f"📅 Дата: {today.strftime('%d.%m.%Y')}\n\n"
        f"🩺 Симптом: {data.get('symptom', 'Не указано')}\n"
        f"📊 Интенсивность: {data.get('symptom_intensity', 'Не указано')}/10\n"
        f"🙂 Настроение: {data.get('mood', 'Не указано')}/5\n"
        f"😰 Стресс: {data.get('stress', 'Не указано')}/10\n"
        f"😴 Сон: {data.get('sleep_hours', 'Не указано')} ч\n"
    )
    
    if data.get('context'):
        preview_text += f"📝 Контекст: {data.get('context')}\n"
    
    if data.get('note'):
        preview_text += f"💬 Заметка: {data.get('note')}\n"
    
    preview_text += "\nСохранить запись?"
    
    await state.set_state(DiaryStates.confirming)
    
    await message.answer(
        preview_text,
        reply_markup=get_confirm_keyboard(),
    )


# ==================== СОХРАНЕНИЕ ====================

@router.callback_query(F.data == "diary_save")
async def save_diary_entry(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Сохраняет дневниковую запись."""
    await callback.answer()
    
    data = await state.get_data()
    
    try:
        # Находим пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "⚠️ Пользователь не найден. Отправьте /start",
                reply_markup=None,
            )
            return
        
        # Создаем запись
        diary_repo = DiaryRepository(db_session)
        
        entry = await diary_repo.create_entry(
            user_id=user.id,
            symptom=data.get('symptom', 'Не указано'),
            symptom_intensity=data.get('symptom_intensity', 0),
            mood=data.get('mood', 3),
            stress=data.get('stress', 5),
            sleep_hours=data.get('sleep_hours', 0.0),
            context=data.get('context'),
            note=data.get('note'),
            analysis_id=data.get('analysis_id'),
        )
        
        await state.clear()
        
        # Получаем часовой пояс пользователя
        user_tz = get_user_timezone(user)
        created_at_local = entry.created_at.astimezone(user_tz)
        time_str = created_at_local.strftime("%H:%M")
        
        await callback.message.edit_text(
            f"✅ Запись сохранена!\n\n"
            f"📅 {entry.entry_date.strftime('%d.%m.%Y')} {time_str}\n"
            f"🩺 {entry.symptom} — {entry.symptom_intensity}/10\n"
            f"🙂 Настроение: {entry.mood}/5\n"
            f"😰 Стресс: {entry.stress}/10\n"
            f"😴 Сон: {entry.sleep_hours} ч",
            reply_markup=None,
        )
        
        await callback.message.answer(
            "📔 Мой дневник\n\n"
            "Выбери действие:",
            reply_markup=get_diary_menu_keyboard(),
        )
        
        logger.info(f"Diary entry saved: user_id={user.id}, id={entry.id}")
        
    except Exception as e:
        logger.error(f"Error saving diary entry: {e}")
        await callback.message.edit_text(
            "⚠️ Не удалось сохранить запись. Попробуй ещё раз позже.",
            reply_markup=None,
        )
        await callback.message.answer(
            "📔 Мой дневник",
            reply_markup=get_diary_menu_keyboard(),
        )


# ==================== КНОПКА "ИЗМЕНИТЬ" НА ПРЕДПРОСМОТРЕ ====================

@router.callback_query(F.data == "diary_edit")
async def edit_diary_entry(callback: CallbackQuery, state: FSMContext):
    """Возврат к редактированию."""
    await callback.answer("Возвращаемся к редактированию...")
    
    # Очищаем состояние confirming
    await state.set_state(DiaryStates.waiting_for_symptom)
    
    # ❗ УДАЛЯЕМ сообщение с inline-клавиатурой
    await callback.message.delete()
    
    # ❗ ОТПРАВЛЯЕМ новое сообщение с обычной клавиатурой
    await callback.message.answer(
        "✏️ Давайте исправим запись.\n\n"
        "1/7: Опишите ваш симптом или состояние.",
        reply_markup=get_cancel_keyboard(),
    )


@router.callback_query(F.data == "diary_cancel")
async def cancel_diary_entry(callback: CallbackQuery, state: FSMContext):
    """Отмена создания записи."""
    await callback.answer("Отменяем...")
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Создание записи отменено.",
        reply_markup=None,
    )
    await callback.message.answer(
        "📔 Мой дневник\n\n"
        "Выбери действие:",
        reply_markup=get_diary_menu_keyboard(),
    )


# ==================== ОТМЕНА FSM ====================

@router.message(F.text == "❌ Отмена")
async def cancel_diary_fsm(message: types.Message, state: FSMContext):
    """Отмена FSM через текстовую кнопку."""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer(
            "У вас нет активного диалога.",
            reply_markup=get_diary_menu_keyboard(),
        )
        return
    
    await state.clear()
    await message.answer(
        "❌ Диалог отменён.",
        reply_markup=get_diary_menu_keyboard(),
    )


# ==================== ВОЗВРАТ НАЗАД ИЗ РЕДАКТИРОВАНИЯ ====================

@router.message(F.text == "🔙 Назад")
async def back_from_edit(message: types.Message, state: FSMContext):
    """Возврат в меню дневника из режима редактирования (FSM)."""
    current_state = await state.get_state()
    
    # Если есть активное FSM состояние
    if current_state is not None:
        await state.clear()
        await message.answer(
            "📔 Мой дневник\n\n"
            "Выбери действие:",
            reply_markup=get_diary_menu_keyboard(),
        )
        logger.info(f"User returned from edit mode: telegram_id={message.from_user.id}")
    else:
        # Если FSM нет, просто показываем меню
        await message.answer(
            "📔 Мой дневник\n\n"
            "Выбери действие:",
            reply_markup=get_diary_menu_keyboard(),
        )


# ==================== ПРОСМОТР СЕГОДНЯШНИХ ЗАПИСЕЙ ====================

@router.message(F.text == "📅 Сегодня")
async def show_today_entries(message: types.Message, db_session: AsyncSession):
    """Показывает записи за сегодня."""
    telegram_id = message.from_user.id
    
    try:
        # Находим пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(
                "⚠️ Вы еще не зарегистрированы.\nОтправьте /start",
                reply_markup=get_diary_menu_keyboard(),
            )
            return
        
        # Получаем записи за сегодня
        diary_repo = DiaryRepository(db_session)
        entries = await diary_repo.get_today_entries(user.id)
        
        if not entries:
            await message.answer(
                "📅 Сегодня записей пока нет.\n\n"
                "Нажмите ➕ Новая запись, чтобы создать первую.",
                reply_markup=get_diary_menu_keyboard(),
            )
            return
        
        today = date.today()
        user_tz = get_user_timezone(user)
        
        text = f"📅 Сегодня ({today.strftime('%d.%m.%Y')})\n\n"
        
        for entry in entries:
            time_str = entry.created_at.astimezone(user_tz).strftime("%H:%M")
            text += (
                f"🕐 {time_str}\n"
                f"🩺 {entry.symptom} — {entry.symptom_intensity}/10\n"
                f"🙂 Настроение: {entry.mood}/5\n"
                f"😰 Стресс: {entry.stress}/10\n"
                f"😴 Сон: {entry.sleep_hours} ч\n"
                f"🆔 #{entry.id}\n\n"
            )
        
        # Добавляем кнопки для просмотра записей
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"📖 Запись #{entry.id}",
                    callback_data=f"diary_view_{entry.id}"
                )]
                for entry in entries[:5]
            ] + [
                [InlineKeyboardButton(
                    text="🔙 Назад в меню",
                    callback_data="diary_back_to_menu"
                )]
            ]
        )
        
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing today entries: {e}")
        await message.answer(
            "⚠️ Не удалось загрузить записи.",
            reply_markup=get_diary_menu_keyboard(),
        )


# ==================== ИСТОРИЯ ДНЕВНИКА ====================

@router.message(F.text == "📖 История")
async def show_diary_history(message: types.Message, db_session: AsyncSession):
    """Показывает историю дневника (список дат)."""
    telegram_id = message.from_user.id
    
    try:
        # Находим пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(
                "⚠️ Вы еще не зарегистрированы.\nОтправьте /start",
                reply_markup=get_diary_menu_keyboard(),
            )
            return
        
        # Получаем даты с записями
        diary_repo = DiaryRepository(db_session)
        dates = await diary_repo.get_dates_with_entries(user.id, limit=15)
        
        if not dates:
            await message.answer(
                "📖 История дневника пуста.\n\n"
                "Начните вести дневник с кнопки ➕ Новая запись.",
                reply_markup=get_diary_menu_keyboard(),
            )
            return
        
        text = "📖 История дневника\n\n"
        
        for entry_date, count in dates:
            text += f"{entry_date.strftime('%d.%m.%Y')} — {count} записей\n"
        
        text += "\nНажмите на дату ниже, чтобы посмотреть записи."
        
        # Создаем инлайн-кнопки для дат
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=entry_date.strftime('%d.%m.%Y'),
                    callback_data=f"diary_date_{entry_date.isoformat()}"
                )]
                for entry_date, count in dates[:10]
            ] + [
                [InlineKeyboardButton(
                    text="🔙 Назад в меню",
                    callback_data="diary_back_to_menu"
                )]
            ]
        )
        
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing diary history: {e}")
        await message.answer(
            "⚠️ Не удалось загрузить историю.",
            reply_markup=get_diary_menu_keyboard(),
        )


@router.callback_query(F.data.startswith("diary_date_"))
async def show_entries_for_date(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает записи за конкретную дату."""
    await callback.answer()
    
    date_str = callback.data.replace("diary_date_", "")
    entry_date = date.fromisoformat(date_str)
    
    try:
        # Находим пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "⚠️ Пожалуйста, отправьте /start",
                reply_markup=None,
            )
            return
        
        # Получаем записи за дату
        diary_repo = DiaryRepository(db_session)
        entries = await diary_repo.get_entries_by_date(user.id, entry_date)
        
        if not entries:
            await callback.message.edit_text(
                f"📅 {entry_date.strftime('%d.%m.%Y')} — записей нет.",
                reply_markup=None,
            )
            return
        
        user_tz = get_user_timezone(user)
        text = f"📅 {entry_date.strftime('%d.%m.%Y')}\n\n"
        
        for entry in entries:
            time_str = entry.created_at.astimezone(user_tz).strftime("%H:%M")
            text += (
                f"🕐 {time_str}\n"
                f"🩺 {entry.symptom} — {entry.symptom_intensity}/10\n"
                f"🙂 Настроение: {entry.mood}/5\n"
                f"😰 Стресс: {entry.stress}/10\n"
                f"😴 Сон: {entry.sleep_hours} ч\n"
                f"🆔 #{entry.id}\n\n"
            )
        
        # Кнопки для просмотра записей и возврата
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"📖 Запись #{entry.id}",
                    callback_data=f"diary_view_{entry.id}"
                )]
                for entry in entries[:5]
            ] + [
                [InlineKeyboardButton(
                    text="🔙 Назад к истории",
                    callback_data="diary_back_to_history"
                )]
            ]
        )
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing entries for date: {e}")
        await callback.message.edit_text(
            "⚠️ Не удалось загрузить записи.",
            reply_markup=None,
        )


# ==================== ВОЗВРАТ К ИСТОРИИ ====================

@router.callback_query(F.data == "diary_back_to_history")
async def back_to_diary_history(callback: CallbackQuery, db_session: AsyncSession):
    """Возврат к списку дат."""
    await callback.answer()
    
    telegram_id = callback.from_user.id
    
    try:
        # Находим пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "⚠️ Вы еще не зарегистрированы.\nОтправьте /start",
                reply_markup=None,
            )
            return
        
        # Получаем даты с записями
        diary_repo = DiaryRepository(db_session)
        dates = await diary_repo.get_dates_with_entries(user.id, limit=15)
        
        if not dates:
            await callback.message.edit_text(
                "📖 История дневника пуста.",
                reply_markup=None,
            )
            await callback.message.answer(
                "📔 Мой дневник",
                reply_markup=get_diary_menu_keyboard(),
            )
            return
        
        text = "📖 История дневника\n\n"
        for entry_date, count in dates:
            text += f"{entry_date.strftime('%d.%m.%Y')} — {count} записей\n"
        text += "\nНажмите на дату ниже, чтобы посмотреть записи."
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=entry_date.strftime('%d.%m.%Y'),
                    callback_data=f"diary_date_{entry_date.isoformat()}"
                )]
                for entry_date, count in dates[:10]
            ] + [
                [InlineKeyboardButton(
                    text="🔙 Назад в меню",
                    callback_data="diary_back_to_menu"
                )]
            ]
        )
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in back_to_diary_history: {e}")
        await callback.message.edit_text(
            "⚠️ Не удалось загрузить историю.",
            reply_markup=None,
        )


@router.callback_query(F.data == "diary_back_to_menu")
async def back_to_diary_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню дневника."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "📔 Мой дневник\n\n"
        "Выбери действие:",
        reply_markup=get_diary_menu_keyboard(),
    )


# ==================== ПРОСМОТР КОНКРЕТНОЙ ЗАПИСИ ====================

@router.callback_query(F.data.startswith("diary_view_"))
async def view_diary_entry(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает детали конкретной записи."""
    await callback.answer()
    
    entry_id = int(callback.data.split("_")[2])
    
    try:
        # Находим пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "⚠️ Пожалуйста, отправьте /start",
                reply_markup=None,
            )
            return
        
        # Получаем запись
        diary_repo = DiaryRepository(db_session)
        entry = await diary_repo.get_entry(entry_id, user.id)
        
        if not entry:
            await callback.message.edit_text(
                "❌ Запись не найдена.",
                reply_markup=None,
            )
            return
        
        user_tz = get_user_timezone(user)
        created_at_local = entry.created_at.astimezone(user_tz)
        time_str = created_at_local.strftime("%H:%M")
        
        text = (
            f"📔 Запись #{entry.id}\n\n"
            f"📅 {entry.entry_date.strftime('%d.%m.%Y')} {time_str}\n\n"
            f"🩺 Симптом: {entry.symptom}\n"
            f"📊 Интенсивность: {entry.symptom_intensity}/10\n"
            f"🙂 Настроение: {entry.mood}/5\n"
            f"😰 Стресс: {entry.stress}/10\n"
            f"😴 Сон: {entry.sleep_hours} ч\n"
        )
        
        if entry.context:
            text += f"📝 Контекст: {entry.context}\n"
        if entry.note:
            text += f"💬 Заметка: {entry.note}\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_entry_detail_keyboard(entry_id),
        )
        
    except Exception as e:
        logger.error(f"Error viewing diary entry: {e}")
        await callback.message.edit_text(
            "⚠️ Не удалось загрузить запись.",
            reply_markup=None,
        )


# ==================== РЕДАКТИРОВАНИЕ ЗАПИСИ (ПОСЛЕ СОХРАНЕНИЯ) ====================

@router.callback_query(F.data.startswith("diary_edit_entry_"))
async def edit_diary_entry_by_id(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Редактирование уже сохранённой записи."""
    await callback.answer()
    
    entry_id = int(callback.data.split("_")[3])
    
    try:
        # Находим пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "⚠️ Пожалуйста, отправьте /start",
                reply_markup=None,
            )
            return
        
        # Получаем запись
        diary_repo = DiaryRepository(db_session)
        entry = await diary_repo.get_entry(entry_id, user.id)
        
        if not entry:
            await callback.message.edit_text(
                "❌ Запись не найдена.",
                reply_markup=None,
            )
            return
        
        # Сохраняем ID записи для редактирования в FSM
        await state.update_data(edit_entry_id=entry_id)
        await state.set_state(DiaryStates.waiting_for_symptom)
        
        # Заполняем данными из записи
        await state.update_data(
            symptom=entry.symptom,
            symptom_intensity=entry.symptom_intensity,
            mood=entry.mood,
            stress=entry.stress,
            sleep_hours=entry.sleep_hours,
            context=entry.context,
            note=entry.note,
        )
        
        # Удаляем старое сообщение с inline-клавиатурой
        await callback.message.delete()
        
        # Отправляем новое сообщение с обычной клавиатурой
        await callback.message.answer(
            f"✏️ Редактируем запись #{entry_id}\n\n"
            "1/7: Опишите симптом\n\n"
            f"Было: {entry.symptom}\n\n"
            "Напишите новый симптом или оставьте тот же:",
            reply_markup=get_cancel_keyboard(),
        )
        
    except Exception as e:
        logger.error(f"Error editing diary entry: {e}")
        await callback.message.answer(
            "⚠️ Не удалось загрузить запись для редактирования.",
            reply_markup=get_cancel_keyboard(),
        )


# ==================== УДАЛЕНИЕ ====================

@router.callback_query(F.data.startswith("diary_delete_entry_"))
async def confirm_delete_diary_entry(callback: CallbackQuery):
    """Подтверждение удаления записи."""
    await callback.answer()
    
    entry_id = int(callback.data.split("_")[3])
    
    await callback.message.edit_text(
        "🗑 Удалить эту запись?\n\n"
        "Это действие нельзя отменить.",
        reply_markup=get_confirm_delete_keyboard(entry_id),
    )


@router.callback_query(F.data == "diary_cancel_delete")
async def cancel_delete_diary_entry(callback: CallbackQuery):
    """Отмена удаления."""
    await callback.answer("Удаление отменено")
    
    # Возвращаемся к деталям записи
    entry_id = int(callback.message.text.split("#")[1].split()[0])
    await callback.message.edit_text(
        callback.message.text,
        reply_markup=get_entry_detail_keyboard(entry_id),
    )


@router.callback_query(F.data.startswith("diary_confirm_delete_"))
async def delete_diary_entry(callback: CallbackQuery, db_session: AsyncSession):
    """Удаление записи."""
    await callback.answer("Запись удалена")
    
    entry_id = int(callback.data.split("_")[3])
    
    try:
        # Находим пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "⚠️ Пожалуйста, отправьте /start",
                reply_markup=None,
            )
            return
        
        # Удаляем запись
        diary_repo = DiaryRepository(db_session)
        success = await diary_repo.delete_entry(entry_id, user.id)
        
        if success:
            await callback.message.edit_text(
                "✅ Запись удалена.",
                reply_markup=None,
            )
            await callback.message.answer(
                "📔 Мой дневник\n\n"
                "Выбери действие:",
                reply_markup=get_diary_menu_keyboard(),
            )
            logger.info(f"Diary entry deleted: id={entry_id}, user_id={user.id}")
        else:
            await callback.message.edit_text(
                "❌ Не удалось удалить запись.",
                reply_markup=None,
            )
            
    except Exception as e:
        logger.error(f"Error deleting diary entry: {e}")
        await callback.message.edit_text(
            "⚠️ Не удалось удалить запись.",
            reply_markup=None,
        )