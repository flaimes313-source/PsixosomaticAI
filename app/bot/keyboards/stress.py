"""
Клавиатуры для сценария "Проверить стресс".
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_stress_question_1_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 1: Как часто вы чувствуете стресс?"""
    builder = ReplyKeyboardBuilder()
    buttons = [
        "Почти никогда",
        "Иногда",
        "Часто",
        "Постоянно",
    ]
    for button in buttons:
        builder.add(KeyboardButton(text=button))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_stress_question_2_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 2: Как вы справляетесь со стрессом?"""
    builder = ReplyKeyboardBuilder()
    buttons = [
        "Отдыхаю",
        "Занимаюсь спортом",
        "Ем сладкое",
        "Сложно справляюсь",
    ]
    for button in buttons:
        builder.add(KeyboardButton(text=button))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_stress_question_3_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 3: Есть ли физические проявления стресса?"""
    builder = ReplyKeyboardBuilder()
    buttons = [
        "Нет",
        "Головная боль",
        "Бессонница",
        "Усталость",
        "Раздражительность",
    ]
    for button in buttons:
        builder.add(KeyboardButton(text=button))
    builder.adjust(2, 3)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_stress_question_4_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 4: Как вы отдыхаете?"""
    builder = ReplyKeyboardBuilder()
    buttons = [
        "Сплю 8 часов",
        "Читаю/смотрю кино",
        "Мало отдыхаю",
        "Не знаю как отдыхать",
    ]
    for button in buttons:
        builder.add(KeyboardButton(text=button))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_stress_question_5_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 5: Оцените уровень стресса (1-10)."""
    builder = ReplyKeyboardBuilder()
    buttons = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    for button in buttons:
        builder.add(KeyboardButton(text=button))
    builder.adjust(5, 5)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_stress_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_stress_result_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура после завершения стресс-теста."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="🧠 Разобрать симптом"),
        KeyboardButton(text="🧠 Проверить стресс"),
        KeyboardButton(text="📋 История"),
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="❓ Помощь"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)