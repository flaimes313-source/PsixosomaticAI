"""
Клавиатуры для раздела поддержки.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_support_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню поддержки."""
    buttons = [
        [InlineKeyboardButton(text="📩 Написать в поддержку", callback_data="support_write")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="support_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_support_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="support_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)