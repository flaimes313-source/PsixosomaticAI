"""
Клавиатуры для раздела "Профиль".
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_profile_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню профиля."""
    buttons = [
        [
            InlineKeyboardButton(text="💳 Подписка", callback_data="profile_subscription"),
            InlineKeyboardButton(text="🔔 Напоминания", callback_data="profile_reminders"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="profile_settings"),
            InlineKeyboardButton(text="🔐 Конфиденциальность", callback_data="profile_privacy"),
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="profile_help"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в меню", callback_data="profile_back"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_profile_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой возврата в профиль."""
    buttons = [
        [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="profile_back_to_profile")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)