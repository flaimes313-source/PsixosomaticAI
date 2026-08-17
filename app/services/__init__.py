"""
Сервисы приложения.
"""
from .yandex_gpt import YandexGPTClient, YandexGPTError
from .ai_service import AIService, ai_service
from .safety import SafetyService, safety_service, SafetyLevel, SafetyResult