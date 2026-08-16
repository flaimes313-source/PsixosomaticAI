from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    APP_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    YANDEX_API_KEY: str
    YANDEX_FOLDER_ID: str
    YANDEX_MODEL: str = "yandexgpt/latest"
    YANDEX_TIMEOUT: int = 60
    YANDEX_MAX_RETRIES: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",          # Пробует прочитать из файла (для локальной разработки)
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        # ГЛАВНОЕ: если переменной нет в файле, он всё равно посмотрит в переменные ОС (хостинга)
    )

settings = Settings()
