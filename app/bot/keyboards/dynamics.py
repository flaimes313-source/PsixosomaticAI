"""
Клавиатуры для раздела "Моя динамика".
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_dynamics_period_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода."""
    buttons = [
        [
            InlineKeyboardButton(text="📅 7 дней", callback_data="dynamics_period_7_days"),
            InlineKeyboardButton(text="📅 14 дней", callback_data="dynamics_period_14_days"),
        ],
        [
            InlineKeyboardButton(text="📅 30 дней", callback_data="dynamics_period_30_days"),
            InlineKeyboardButton(text="📅 90 дней", callback_data="dynamics_period_90_days"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="dynamics_close"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dynamics_actions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура действий после отчёта."""
    buttons = [
        [
            InlineKeyboardButton(text="📊 Другой период", callback_data="dynamics_back_to_menu"),
        ],
        [
            InlineKeyboardButton(text="📔 Открыть дневник", callback_data="dynamics_open_diary"),
            InlineKeyboardButton(text="🧠 Новый анализ", callback_data="dynamics_new_analysis"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="dynamics_close"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)