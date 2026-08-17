"""
Клавиатуры для выбора часового пояса.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_timezone_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с популярными часовыми поясами."""
    builder = ReplyKeyboardBuilder()
    
    timezones = [
        "UTC-12:00 (Камчатка)",
        "UTC-11:00 (Магадан)",
        "UTC-10:00 (Владивосток)",
        "UTC-09:00 (Якутск)",
        "UTC-08:00 (Иркутск)",
        "UTC-07:00 (Красноярск)",
        "UTC-06:00 (Новосибирск)",
        "UTC-05:00 (Екатеринбург)",
        "UTC-04:00 (Самара)",
        "UTC-03:00 (Москва)",
        "UTC-02:00 (Калининград)",
        "UTC-01:00 (Азорские острова)",
        "UTC+00:00 (Лондон)",
        "UTC+01:00 (Париж)",
        "UTC+02:00 (Киев)",
        "UTC+03:00 (Москва, лето)",
        "UTC+04:00 (Дубай)",
        "UTC+05:00 (Екатеринбург, лето)",
        "UTC+06:00 (Омск)",
        "UTC+07:00 (Красноярск, лето)",
        "UTC+08:00 (Иркутск, лето)",
        "UTC+09:00 (Якутск, лето)",
        "UTC+10:00 (Владивосток, лето)",
        "UTC+11:00 (Магадан, лето)",
        "UTC+12:00 (Камчатка, лето)",
    ]
    
    for tz in timezones:
        builder.add(KeyboardButton(text=tz))
    
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