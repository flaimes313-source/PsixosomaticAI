"""
Сервисы приложения.

Здесь находятся внешние интеграции и бизнес-логика,
не относящаяся напрямую к Telegram handlers.
"""
from .yandex_gpt import YandexGPTClient, YandexGPTError
from .ai_service import AIService, ai_service