"""
Клавиатуры для раздела "Напоминания".
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_reminders_menu_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    """Главное меню напоминаний."""
    buttons = []
    
    if enabled:
        buttons.append(
            [InlineKeyboardButton(text="🔕 Отключить", callback_data="reminders_disable")]
        )
        buttons.append(
            [InlineKeyboardButton(text="⚙️ Изменить время", callback_data="reminders_enable")]
        )
    else:
        buttons.append(
            [InlineKeyboardButton(text="✅ Включить", callback_data="reminders_enable")]
        )
    
    buttons.append(
        [InlineKeyboardButton(text="↩️ Назад", callback_data="reminders_close")]
    )
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_time_preset_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора времени."""
    buttons = [
        [
            InlineKeyboardButton(text="08:00", callback_data="reminders_time_08:00"),
            InlineKeyboardButton(text="10:00", callback_data="reminders_time_10:00"),
            InlineKeyboardButton(text="12:00", callback_data="reminders_time_12:00"),
        ],
        [
            InlineKeyboardButton(text="18:00", callback_data="reminders_time_18:00"),
            InlineKeyboardButton(text="20:00", callback_data="reminders_time_20:00"),
            InlineKeyboardButton(text="22:00", callback_data="reminders_time_22:00"),
        ],
        [
            InlineKeyboardButton(text="⏰ Другое время", callback_data="reminders_time_custom"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="reminders_back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_days_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора дней недели."""
    buttons = [
        [
            InlineKeyboardButton(text="📅 Каждый день", callback_data="reminders_days_all"),
        ],
        [
            InlineKeyboardButton(text="📅 Будни (Пн-Пт)", callback_data="reminders_days_weekdays"),
        ],
        [
            InlineKeyboardButton(text="📅 Выходные (Сб-Вс)", callback_data="reminders_days_weekend"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="reminders_back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="reminders_back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)