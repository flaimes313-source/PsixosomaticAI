"""
Клавиатуры для раздела PRO.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_pro_menu_keyboard(is_pro: bool) -> InlineKeyboardMarkup:
    """Главное меню PRO."""
    buttons = [
        [InlineKeyboardButton(text="📋 Что входит в PRO", callback_data="pro_features")],
    ]
    
    if is_pro:
        buttons.append([
            InlineKeyboardButton(text="✅ Уже PRO", callback_data="pro_upgrade"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="💎 Подключить PRO", callback_data="pro_upgrade"),
        ])
    
    buttons.append([
        InlineKeyboardButton(text="↩️ Назад", callback_data="pro_close"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pro_features_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с подробностями PRO."""
    buttons = [
        [InlineKeyboardButton(text="💎 Подключить PRO", callback_data="pro_upgrade")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="pro_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pro_upgrade_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подключения PRO."""
    buttons = [
        [InlineKeyboardButton(
            text="💳 Оплатить PRO (скоро)",
            callback_data="pro_payment_soon"
        )],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="pro_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pro_locked_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для заблокированной PRO-функции."""
    buttons = [
        [InlineKeyboardButton(text="💎 Подключить PRO", callback_data="pro_upgrade")],
        [InlineKeyboardButton(text="ℹ️ Подробнее", callback_data="pro_features")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="pro_close")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)