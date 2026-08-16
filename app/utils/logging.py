"""
Настройка логирования для проекта.
"""
import logging
import sys
from datetime import datetime


def setup_logging(level: str = "INFO"):
    """
    Настраивает логирование с единым форматом.
    
    Формат: 2026-08-11 12:30:01 | INFO | message
    """
    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Настройка корневого логгера
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Отключаем лишние логи от библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    logger = logging.getLogger("psychosomatic_bot")
    logger.info(f"Logging initialized with level: {level}")
    
    return logger


# Создаем глобальный логгер
logger = logging.getLogger("psychosomatic_bot")