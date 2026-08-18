"""
Клавиатуры для сценария "Дневник".
"""
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# ==================== МЕНЮ ДНЕВНИКА ====================

def get_diary_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура главного меню дневника."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="➕ Новая запись"),
        KeyboardButton(text="📅 Сегодня"),
        KeyboardButton(text="📖 История"),
        KeyboardButton(text="🔙 Назад"),
    )
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


# ==================== КЛАВИАТУРЫ ДЛЯ ПОЛЕЙ ====================

def get_intensity_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора интенсивности (0-10)."""
    builder = ReplyKeyboardBuilder()
    buttons = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    for btn in buttons:
        builder.add(KeyboardButton(text=btn))
    builder.adjust(4, 4, 3)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_mood_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора настроения (1-5)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="1 😞"),
        KeyboardButton(text="2 🙁"),
        KeyboardButton(text="3 😐"),
        KeyboardButton(text="4 🙂"),
        KeyboardButton(text="5 😄"),
    )
    builder.adjust(5)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_stress_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора уровня стресса (0-10)."""
    builder = ReplyKeyboardBuilder()
    buttons = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    for btn in buttons:
        builder.add(KeyboardButton(text=btn))
    builder.adjust(4, 4, 3)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_sleep_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для ввода часов сна (можно ввести вручную)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="4"),
        KeyboardButton(text="5"),
        KeyboardButton(text="6"),
        KeyboardButton(text="7"),
        KeyboardButton(text="8"),
    )
    builder.adjust(3, 2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой 'Пропустить'."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="⏭ Пропустить"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой '❌ Отмена'."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


# ==================== КЛАВИАТУРЫ ДЛЯ ПРЕДПРОСМОТРА ====================

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура для подтверждения записи."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Сохранить", callback_data="diary_save"),
        InlineKeyboardButton(text="✏️ Изменить", callback_data="diary_edit"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="diary_cancel"),
    )
    builder.adjust(3)
    return builder.as_markup()


def get_entry_detail_keyboard(entry_id: int) -> InlineKeyboardMarkup:
    """Inline-клавиатура для деталей записи."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✏️ Изменить", callback_data=f"diary_edit_entry_{entry_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"diary_delete_entry_{entry_id}"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="diary_back_to_history"),
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def get_confirm_delete_keyboard(entry_id: int) -> InlineKeyboardMarkup:
    """Inline-клавиатура для подтверждения удаления."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="❌ Отмена", callback_data="diary_cancel_delete"),
        InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"diary_confirm_delete_{entry_id}"),
    )
    builder.adjust(2)
    return builder.as_markup()


def get_date_navigation_keyboard(offset: int = 0) -> InlineKeyboardMarkup:
    """Inline-клавиатура для навигации по датам."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"diary_history_offset_{offset - 10}"),
        InlineKeyboardButton(text="➡️ Далее", callback_data=f"diary_history_offset_{offset + 10}"),
    )
    builder.adjust(2)
    return builder.as_markup()