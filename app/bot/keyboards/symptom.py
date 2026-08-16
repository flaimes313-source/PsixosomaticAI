"""
Клавиатуры для сценария "Разобрать симптом".
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_duration_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    buttons = [
        "Сегодня",
        "Несколько дней",
        "Несколько недель",
        "Больше месяца",
        "Не знаю",
    ]
    
    for button in buttons:
        builder.add(KeyboardButton(text=button))
    
    builder.adjust(2, 2, 1)
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_cancel_inline_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="❌ Отменить анализ",
        callback_data="cancel_analysis"
    ))
    return builder.as_markup()


def get_analysis_complete_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="🧠 Разобрать симптом"),
        KeyboardButton(text="🧠 Проверить стресс"),
        KeyboardButton(text="📋 История"),
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="❓ Помощь"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_clarification_keyboard(questions_asked: int = 0, max_questions: int = 3) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if questions_asked < max_questions:
        builder.add(InlineKeyboardButton(
            text=f"❓ Задать вопрос ({questions_asked}/{max_questions})",
            callback_data="ask_clarification"
        ))
    
    builder.add(InlineKeyboardButton(
        text="✅ Закончить",
        callback_data="finish_clarification"
    ))
    
    builder.adjust(1)
    return builder.as_markup()


def get_question_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False,
    )