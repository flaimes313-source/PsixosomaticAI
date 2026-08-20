"""
Клавиатуры для раздела "Моя динамика".
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_dynamics_period_keyboard(is_pro: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура выбора периода с учётом PRO."""
    buttons = []
    
    # 7 дней — всегда доступно
    buttons.append([
        InlineKeyboardButton(text="📅 7 дней ✅", callback_data="dynamics_period_7_days"),
    ])
    
    # 30 дней — только PRO
    if is_pro:
        buttons.append([
            InlineKeyboardButton(text="📅 30 дней ⭐", callback_data="dynamics_period_30_days"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="📅 30 дней 🔒", callback_data="dynamics_period_30_days_locked"),
        ])
    
    # 90 дней — только PRO
    if is_pro:
        buttons.append([
            InlineKeyboardButton(text="📅 90 дней ⭐", callback_data="dynamics_period_90_days"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="📅 90 дней 🔒", callback_data="dynamics_period_90_days_locked"),
        ])
    
    buttons.append([
        InlineKeyboardButton(text="↩️ Назад", callback_data="dynamics_close"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dynamics_actions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура действий после отчёта."""
    buttons = [
        [
            InlineKeyboardButton(text="📊 Другой период", callback_data="dynamics_back_to_menu"),
        ],
        [
            InlineKeyboardButton(text="📔 Открыть дневник", callback_data="dynamics_open_diary"),
            InlineKeyboardButton(text="🧠 Новый анализ", callback_data="dynamics_new_analysis"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="dynamics_close"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dynamics_locked_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для заблокированной PRO-функции динамики."""
    buttons = [
        [InlineKeyboardButton(text="💎 Подключить PRO", callback_data="pro_upgrade")],
        [InlineKeyboardButton(text="ℹ️ Подробнее", callback_data="pro_features")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="dynamics_close")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)