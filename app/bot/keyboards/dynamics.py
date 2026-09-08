"""
Клавиатуры для раздела «Моя динамика».
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_dynamics_period_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора периода."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 3 дня", callback_data="dynamics_period_3"),
                InlineKeyboardButton(text="📅 7 дней", callback_data="dynamics_period_7"),
            ],
            [
                InlineKeyboardButton(text="📅 14 дней", callback_data="dynamics_period_14"),
                InlineKeyboardButton(text="📅 30 дней", callback_data="dynamics_period_30"),
            ],
            [
                InlineKeyboardButton(text="📅 90 дней", callback_data="dynamics_period_90"),
                InlineKeyboardButton(text="📝 Свой период", callback_data="dynamics_period_custom"),
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="dynamics_back_to_menu"),
            ]
        ]
    )


def get_dynamics_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой 'Отмена'."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)