"""
Клавиатуры для выбора часового пояса.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_timezone_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с популярными часовыми поясами."""
    builder = ReplyKeyboardBuilder()
    
    # Формат: (текст на кнопке, правильное tz название)
    timezones = [
        ("UTC-12:00 (Камчатка)", "Pacific/Midway"),
        ("UTC-11:00 (Магадан)", "Asia/Magadan"),
        ("UTC-10:00 (Владивосток)", "Asia/Vladivostok"),
        ("UTC-09:00 (Якутск)", "Asia/Yakutsk"),
        ("UTC-08:00 (Иркутск)", "Asia/Irkutsk"),
        ("UTC-07:00 (Красноярск)", "Asia/Krasnoyarsk"),
        ("UTC-06:00 (Новосибирск)", "Asia/Novosibirsk"),
        ("UTC-05:00 (Екатеринбург)", "Asia/Yekaterinburg"),
        ("UTC-04:00 (Самара)", "Europe/Samara"),
        ("UTC-03:00 (Москва)", "Europe/Moscow"),  # <-- ИСПРАВЛЕНО!
        ("UTC-02:00 (Калининград)", "Europe/Kaliningrad"),
        ("UTC-01:00 (Азорские острова)", "Atlantic/Azores"),
        ("UTC+00:00 (Лондон)", "Europe/London"),
        ("UTC+01:00 (Париж)", "Europe/Paris"),
        ("UTC+02:00 (Киев)", "Europe/Kiev"),
        ("UTC+03:00 (Москва, лето)", "Europe/Moscow"),
        ("UTC+04:00 (Дубай)", "Asia/Dubai"),
        ("UTC+05:00 (Екатеринбург, лето)", "Asia/Yekaterinburg"),
        ("UTC+06:00 (Омск)", "Asia/Omsk"),
        ("UTC+07:00 (Красноярск, лето)", "Asia/Krasnoyarsk"),
        ("UTC+08:00 (Иркутск, лето)", "Asia/Irkutsk"),
        ("UTC+09:00 (Якутск, лето)", "Asia/Yakutsk"),
        ("UTC+10:00 (Владивосток, лето)", "Asia/Vladivostok"),
        ("UTC+11:00 (Магадан, лето)", "Asia/Magadan"),
        ("UTC+12:00 (Камчатка, лето)", "Pacific/Kamchatka"),
    ]
    
    for text, tz_name in timezones:
        builder.add(KeyboardButton(text=text))
    
    builder.adjust(2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1)
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_timezone_skip_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой 'Пропустить'."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="⏭ Пропустить (UTC)"))
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )