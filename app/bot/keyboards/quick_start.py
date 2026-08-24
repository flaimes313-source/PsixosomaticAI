"""
Клавиатуры для экспресс-диагностики "Помогите разобраться".
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_quick_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для начала диагностики."""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="quick_start_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quick_start_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="quick_start_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)