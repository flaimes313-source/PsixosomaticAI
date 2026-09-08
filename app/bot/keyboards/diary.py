"""
Клавиатуры для дневника.
"""
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_diary_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура главного меню дневника."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="➕ Новая запись"),
        KeyboardButton(text="📅 Сегодня"),
        KeyboardButton(text="📖 История"),
        KeyboardButton(text="🔙 Назад"),
    )
    builder.adjust(2, 1, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_intensity_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора интенсивности."""
    builder = ReplyKeyboardBuilder()
    for i in range(11):
        builder.add(KeyboardButton(text=str(i)))
    builder.adjust(4, 4, 3)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_mood_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора настроения."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="1 😞"),
        KeyboardButton(text="2 🙁"),
        KeyboardButton(text="3 😐"),
        KeyboardButton(text="4 🙂"),
        KeyboardButton(text="5 😄"),
    )
    builder.adjust(3, 2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_stress_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора уровня стресса."""
    builder = ReplyKeyboardBuilder()
    for i in range(11):
        builder.add(KeyboardButton(text=str(i)))
    builder.adjust(4, 4, 3)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_sleep_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора часов сна."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="4"),
        KeyboardButton(text="5"),
        KeyboardButton(text="6"),
        KeyboardButton(text="7"),
        KeyboardButton(text="8"),
        KeyboardButton(text="9"),
        KeyboardButton(text="10"),
        KeyboardButton(text="⏭ Пропустить"),
    )
    builder.adjust(3, 3, 2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой 'Пропустить'."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="⏭ Пропустить"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой 'Отмена'."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Сохранить", callback_data="diary_save"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="diary_edit"),
            ],
            [
                InlineKeyboardButton(text="❌ Отменить", callback_data="diary_cancel"),
            ]
        ]
    )


def get_entry_detail_keyboard(entry_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра записи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"diary_edit_entry_{entry_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"diary_delete_entry_{entry_id}"),
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="diary_back_to_menu"),
            ]
        ]
    )


def get_confirm_delete_keyboard(entry_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения удаления."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"diary_confirm_delete_{entry_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="diary_cancel_delete"),
            ]
        ]
    )


def get_date_navigation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для навигации по датам."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="diary_prev_day"),
                InlineKeyboardButton(text="▶️ Вперёд", callback_data="diary_next_day"),
            ],
            [
                InlineKeyboardButton(text="🔙 Назад в меню", callback_data="diary_back_to_menu"),
            ]
        ]
    )