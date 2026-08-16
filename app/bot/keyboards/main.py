"""
Главное меню бота.
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.add(
        KeyboardButton(text="🧠 Разобрать симптом"),
        KeyboardButton(text="🧠 Проверить стресс"),
        KeyboardButton(text="📋 История"),
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="❓ Помощь"),
        KeyboardButton(text="🔐 Конфиденциальность"),
    )
    
    builder.adjust(2, 2, 2)
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_back_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔙 Назад"))
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False,
    )