"""
Клавиатуры для раздела поддержки.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_support_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню поддержки."""
    buttons = [
        [InlineKeyboardButton(text="❓ Частые вопросы", callback_data="support_faq")],
        [InlineKeyboardButton(text="💬 Задать вопрос", callback_data="support_ask")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="support_close")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_support_faq_keyboard() -> InlineKeyboardMarkup:
    """Список частых вопросов."""
    buttons = [
        [InlineKeyboardButton(
            text="❓ Что такое Сома и как она работает?",
            callback_data="support_faq_about"
        )],
        [InlineKeyboardButton(
            text="❓ Что происходит с моими данными?",
            callback_data="support_faq_data"
        )],
        [InlineKeyboardButton(
            text="❓ Сома ставит диагнозы?",
            callback_data="support_faq_diagnoses"
        )],
        [InlineKeyboardButton(
            text="❓ Что входит в PRO?",
            callback_data="support_faq_pro"
        )],
        [InlineKeyboardButton(
            text="❓ Как отключить утренние напоминания?",
            callback_data="support_faq_reminders"
        )],
        [InlineKeyboardButton(
            text="❓ Как удалить свои данные?",
            callback_data="support_faq_delete"
        )],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="support_back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_support_faq_answer_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для ответа FAQ — возврат к списку вопросов."""
    buttons = [
        [InlineKeyboardButton(text="↩️ Назад к вопросам", callback_data="support_faq")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_support_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены (при ожидании вопроса)."""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="support_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)