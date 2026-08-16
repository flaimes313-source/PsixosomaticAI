"""
Конфигурация приложения.

Все секретные значения загружаются из .env.
Реальные API-ключи не должны храниться в исходном коде.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Основные настройки приложения."""

    # ==========================================
    # Telegram
    # ==========================================

    BOT_TOKEN: str

    # ==========================================
    # Database
    # ==========================================

    DATABASE_URL: str

    # ==========================================
    # Logging
    # ==========================================

    LOG_LEVEL: str = "INFO"
    APP_ENV: str = "development"

    # ==========================================
    # FastAPI
    # ==========================================

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # ==========================================
    # YandexGPT
    # ==========================================

    YANDEX_API_KEY: str
    YANDEX_FOLDER_ID: str

    # Например: yandexgpt/latest
    YANDEX_MODEL: str = "yandexgpt/latest"

    # Таймаут HTTP-запроса к Yandex Cloud
    YANDEX_TIMEOUT: int = 60

    # Количество повторных попыток при временной ошибке API
    YANDEX_MAX_RETRIES: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Глобальный объект конфигурации
settings = Settings()