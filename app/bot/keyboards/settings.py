"""
Клавиатуры для сценария "Настройки".
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для настроек."""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(
            text="🗑️ Удалить все данные",
            callback_data="delete_all_data"
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="🔙 Назад в меню",
            callback_data="back_to_menu_from_settings"
        )
    )
    
    builder.adjust(1)
    
    return builder.as_markup()


def get_confirm_delete_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения удаления."""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(
            text="✅ Да, удалить всё",
            callback_data="confirm_delete_all"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_delete"
        )
    )
    
    builder.adjust(2)
    
    return builder.as_markup()