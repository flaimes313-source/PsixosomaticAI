"""
Клавиатура с кнопкой 'Отмена'.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой 'Отмена'."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_cancel_inline_keyboard() -> ReplyKeyboardMarkup:
    """Алиас для get_cancel_keyboard."""
    return get_cancel_keyboard()