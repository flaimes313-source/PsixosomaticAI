"""
Главное меню бота.
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает главное меню с кнопками."""
    builder = ReplyKeyboardBuilder()
    
    builder.add(
        KeyboardButton(text="🧠 Разобрать симптом"),
        KeyboardButton(text="📔 Дневник"),
        KeyboardButton(text="📊 Моя динамика"),      # ← НОВАЯ КНОПКА
        KeyboardButton(text="🧠 Проверить стресс"),
        KeyboardButton(text="📋 История"),
        KeyboardButton(text="🔔 Напоминания"),       # ← НОВАЯ КНОПКА
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="❓ Помощь"),
        KeyboardButton(text="🔐 Конфиденциальность"),
    )
    
    # Располагаем кнопки по 2 в ряд
    # Получается: 9 кнопок → 5 рядов (2, 2, 2, 2, 1)
    builder.adjust(2, 2, 2, 2, 1)
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_back_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопкой 'Назад'."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔙 Назад"))
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False,
    )