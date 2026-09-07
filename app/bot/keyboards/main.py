"""
Главное меню бота.
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает главное меню с кнопками (новый порядок)."""
    builder = ReplyKeyboardBuilder()
    
    builder.add(
        # === ИНФО ===
        KeyboardButton(text="📖 Как это работает?"),
        
        # === ГЛАВНЫЙ РАЗДЕЛ ===
        KeyboardButton(text="📝 Описать состояние"),
        
        # === АНАЛИТИКА ===
        KeyboardButton(text="📊 Моя динамика"),
        
        # === ИНСТРУМЕНТЫ ===
        KeyboardButton(text="📔 Дневник"),
        
        # === ПРОФИЛЬ И ПРОДУКТЫ ===
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="💎 PRO"),
        
        # === ПОДДЕРЖКА ===
        KeyboardButton(text="🆘 Поддержка"),
    )
    
    # 7 кнопок → 4 ряда (1,2,2,2)
    builder.adjust(1, 1, 2, 1, 2)
    
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