"""
Клавиатуры для админ-панели.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    buttons = [
        [InlineKeyboardButton(text="📋 Белый список PRO", callback_data="admin_whitelist")],
        [InlineKeyboardButton(text="📢 Создать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📩 Обращения в поддержку", callback_data="admin_support_requests")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены рассылки."""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_broadcast_options_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора картинки."""
    buttons = [
        [InlineKeyboardButton(text="📨 Отправить без картинки", callback_data="broadcast_skip_image")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения рассылки."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_broadcast_recipients_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора получателей."""
    buttons = [
        [InlineKeyboardButton(text="📨 Все пользователи", callback_data="broadcast_recipients_all")],
        [InlineKeyboardButton(text="📨 Только PRO", callback_data="broadcast_recipients_pro")],
        [InlineKeyboardButton(text="📨 Только FREE", callback_data="broadcast_recipients_free")],
        [InlineKeyboardButton(text="📨 По ID (через запятую)", callback_data="broadcast_recipients_ids")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)