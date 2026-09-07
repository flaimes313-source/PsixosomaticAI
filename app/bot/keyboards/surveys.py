"""
Клавиатуры для опросников (утро/день/вечер).
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


# ==================== ОБЩИЕ КЛАВИАТУРЫ ====================

def get_survey_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой 'Отмена' для опросников."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_survey_skip_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой 'Пропустить'."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="⏭ Пропустить"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_survey_finish_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для завершения опроса."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Завершить",
                callback_data="survey_finish"
            )]
        ]
    )


# ==================== УТРЕННИЙ ОПРОС ====================

def get_morning_question_1_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 1 (Как проснулся?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Бодро"),
        KeyboardButton(text="Тяжело"),
        KeyboardButton(text="Тревожно"),
        KeyboardButton(text="Спокойно"),
    )
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_morning_question_2_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 2 (Что чувствуешь в теле?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Напряжение"),
        KeyboardButton(text="Боль"),
        KeyboardButton(text="Лёгкость"),
        KeyboardButton(text="Усталость"),
        KeyboardButton(text="Другое (напишу)"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_morning_question_3_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 3 (Какое настроение?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Спокойное"),
        KeyboardButton(text="Тревожное"),
        KeyboardButton(text="Раздражённое"),
        KeyboardButton(text="Нейтральное"),
        KeyboardButton(text="Радостное"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_morning_question_4_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 4 (Что в мыслях?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Заботы"),
        KeyboardButton(text="Планы"),
        KeyboardButton(text="Тревоги"),
        KeyboardButton(text="Пустота"),
        KeyboardButton(text="Другое (напишу)"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_morning_question_5_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 5 (Как спал?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Отлично"),
        KeyboardButton(text="Плохо"),
        KeyboardButton(text="Часто просыпался"),
        KeyboardButton(text="Видел сны"),
    )
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_morning_reminder_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для интерактива после утреннего опроса."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="⏰ Напомнить через час",
                callback_data="morning_remind_1h"
            )],
            [InlineKeyboardButton(
                text="⏰ Напомнить через 2 часа",
                callback_data="morning_remind_2h"
            )],
            [InlineKeyboardButton(
                text="📝 Опишу в следующем опросе",
                callback_data="morning_track_next"
            )],
            [InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="morning_finish"
            )]
        ]
    )


# ==================== ДНЕВНОЙ ОПРОС ====================

def get_day_question_1_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 1 (Как ты сейчас?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Хорошо"),
        KeyboardButton(text="Нормально"),
        KeyboardButton(text="Тревожно"),
        KeyboardButton(text="Устало"),
        KeyboardButton(text="Другое (напишу)"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_day_question_2_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 2 (Что изменилось с утра?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Лучше"),
        KeyboardButton(text="Хуже"),
        KeyboardButton(text="Так же"),
        KeyboardButton(text="Не знаю"),
    )
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_day_question_3_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 3 (Что повлияло?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Работа"),
        KeyboardButton(text="Отдых"),
        KeyboardButton(text="Общение"),
        KeyboardButton(text="Еда"),
        KeyboardButton(text="Другое (напишу)"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_day_finish_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для завершения дневного опроса."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="day_finish"
            )]
        ]
    )


# ==================== ВЕЧЕРНИЙ ОПРОС ====================

def get_evening_question_1_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 1 (Как себя чувствуешь?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Хорошо"),
        KeyboardButton(text="Нормально"),
        KeyboardButton(text="Тревожно"),
        KeyboardButton(text="Устало"),
        KeyboardButton(text="Другое (напишу)"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_evening_question_2_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 2 (Что повлияло на состояние?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Работа"),
        KeyboardButton(text="Отдых"),
        KeyboardButton(text="Общение"),
        KeyboardButton(text="Стресс"),
        KeyboardButton(text="Другое (напишу)"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_evening_question_3_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 3 (Что дало энергию?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Еда"),
        KeyboardButton(text="Сон"),
        KeyboardButton(text="Движение"),
        KeyboardButton(text="Общение"),
        KeyboardButton(text="Другое (напишу)"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_evening_question_4_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 4 (Что забрало силы?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Работа"),
        KeyboardButton(text="Переживания"),
        KeyboardButton(text="Недосып"),
        KeyboardButton(text="Неправильное питание"),
        KeyboardButton(text="Другое (напишу)"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_evening_question_5_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса 5 (Как с едой, сном, движением?)."""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="Всё хорошо"),
        KeyboardButton(text="С едой проблемы"),
        KeyboardButton(text="Спал мало"),
        KeyboardButton(text="Двигался мало"),
        KeyboardButton(text="Другое (напишу)"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_evening_reminder_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для интерактива после вечернего опроса."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="⏰ Напомнить завтра утром",
                callback_data="evening_remind_tomorrow"
            )],
            [InlineKeyboardButton(
                text="📝 Опишу результат в следующем опросе",
                callback_data="evening_track_next"
            )],
            [InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="evening_finish"
            )]
        ]
    )