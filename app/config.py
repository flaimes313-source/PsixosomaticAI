from pydantic_settings import BaseSettings, SettingsConfigDict
from decimal import Decimal
import os


class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str
    
    # Database
    DATABASE_URL: str
    
    # Logging
    LOG_LEVEL: str = "INFO"
    APP_ENV: str = "development"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # YandexGPT
    YANDEX_API_KEY: str
    YANDEX_FOLDER_ID: str
    YANDEX_MODEL: str = "yandexgpt/latest"
    YANDEX_TIMEOUT: int = 60
    YANDEX_MAX_RETRIES: int = 2
    
    # ==================== ЮKASSA ====================
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    YOOKASSA_RETURN_URL: str = "https://your-domain.ru/payment/success"
    
    # ==================== PRO ====================
    PRO_PRICE_RUB: Decimal = Decimal("490.00")
    PRO_DURATION_DAYS: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()