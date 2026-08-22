"""
Клавиатуры для раздела PRO.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import settings


def get_pro_menu_keyboard(is_pro: bool) -> InlineKeyboardMarkup:
    """Главное меню PRO."""
    buttons = [
        [InlineKeyboardButton(text="📋 Что входит в PRO", callback_data="pro_features")],
    ]
    
    if is_pro:
        buttons.append([
            InlineKeyboardButton(text="💎 Продлить PRO", callback_data="pro_pay"),
        ])
        buttons.append([
            InlineKeyboardButton(text="💳 Мои платежи", callback_data="pro_payments_history"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text=f"💳 Оплатить {settings.PRO_PRICE_RUB} ₽", callback_data="pro_pay"),
        ])
    
    buttons.append([
        InlineKeyboardButton(text="↩️ Назад", callback_data="pro_close"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pro_features_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с подробностями PRO."""
    buttons = [
        [InlineKeyboardButton(text=f"💳 Оплатить {settings.PRO_PRICE_RUB} ₽", callback_data="pro_pay")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="pro_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pro_payment_keyboard(confirmation_url: str = None) -> InlineKeyboardMarkup:
    """Клавиатура для оплаты."""
    buttons = []
    
    if confirmation_url:
        buttons.append([
            InlineKeyboardButton(
                text="💳 Перейти к оплате",
                url=confirmation_url
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="pro_check_payment"),
    ])
    buttons.append([
        InlineKeyboardButton(text="↩️ Назад", callback_data="pro_back"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pro_success_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после успешной оплаты."""
    buttons = [
        [InlineKeyboardButton(text="🚀 Перейти к PRO", callback_data="pro_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pro_locked_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для заблокированной PRO-функции."""
    buttons = [
        [InlineKeyboardButton(text=f"💳 Оплатить {settings.PRO_PRICE_RUB} ₽", callback_data="pro_pay")],
        [InlineKeyboardButton(text="ℹ️ Подробнее", callback_data="pro_features")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="pro_close")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)