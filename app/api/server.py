"""
FastAPI сервер для health checks и мониторинга.
"""
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any

from app.db.database import get_db, check_db_connection
from app.config import settings
from app.utils.logging import logger

# Создаем FastAPI приложение
app = FastAPI(
    title="Psychosomatic Bot API",
    description="Health checks и мониторинг для Telegram бота",
    version="1.0.0",
)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Базовый health check.
    
    Returns:
        Статус "ok"
    """
    logger.info("Health check requested")
    return {"status": "ok"}


@app.get("/health/db")
async def db_health_check(session: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Health check с проверкой базы данных.
    
    Выполняет SELECT 1 для проверки подключения к PostgreSQL.
    
    Args:
        session: Сессия базы данных (из dependency)
        
    Returns:
        Статус и информация о базе данных
    """
    try:
        # Выполняем простой запрос для проверки подключения
        await session.execute(text("SELECT 1"))
        logger.info("Database health check passed")
        return {
            "status": "ok",
            "database": "connected",
            "message": "Database connection is working"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "database": "disconnected",
            "message": f"Database connection failed: {str(e)}"
        }


@app.get("/health/version")
async def version_check() -> Dict[str, str]:
    """
    Получить информацию о версии приложения.
    
    Returns:
        Информация о версии и окружении
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }