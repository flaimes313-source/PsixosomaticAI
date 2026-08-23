"""
Клавиатуры для сценария "Настройки".
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_settings_keyboard(back_to: str = "menu") -> InlineKeyboardMarkup:
    """
    Клавиатура для настроек.
    
    Args:
        back_to: Куда возвращаться - "menu" или "profile"
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(
            text="🗑️ Удалить все данные",
            callback_data="delete_all_data"
        )
    )
    
    # Кнопка "Назад" с динамическим callback
    if back_to == "profile":
        builder.add(
            InlineKeyboardButton(
                text="🔙 Назад в профиль",
                callback_data="settings_back_to_profile"
            )
        )
    else:
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