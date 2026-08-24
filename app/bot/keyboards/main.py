"""
Главное меню бота.
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает главное меню с кнопками."""
    builder = ReplyKeyboardBuilder()
    
    builder.add(
        # === ПСИХОБЛОК ===
        KeyboardButton(text="🤔 Что я чувствую в теле?"),
        KeyboardButton(text="💡 Помогите разобраться"),
        
        # === ИНФО ===
        KeyboardButton(text="📖 Как это работает?"),
        
        # === КОММЕРЦИЯ ===
        KeyboardButton(text="⭐ PRO"),
        
        # === ИНСТРУМЕНТЫ ===
        KeyboardButton(text="📔 Дневник"),
        KeyboardButton(text="📊 Моя динамика"),
        
        # === ПРОФИЛЬ И ПОДДЕРЖКА ===
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="❓ Поддержка"),
    )
    
    # 8 кнопок → 4 ряда (2,2,2,2)
    builder.adjust(2, 2, 2, 2)
    
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