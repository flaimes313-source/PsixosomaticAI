"""
Главный файл приложения.
Запускает Telegram бота и FastAPI сервер.
"""
import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
import uvicorn

from app.config import settings
from app.utils.logging import setup_logging, logger
from app.bot.middlewares import DBSessionMiddleware
from app.bot.handlers import start, menu, help, privacy, symptom, cancel, history, stress, settings
from app.bot.errors import router as errors_router
from app.api.server import app as fastapi_app
from app.db.database import check_db_connection, engine


# Настройка логирования
logger = setup_logging(settings.LOG_LEVEL)


async def setup_bot_commands(bot: Bot) -> None:
    """Настраивает команды для меню Telegram бота."""
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="privacy", description="Конфиденциальность"),
        BotCommand(command="cancel", description="Отменить текущий диалог"),
        BotCommand(command="history", description="История анализов"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands configured")


async def main() -> None:
    """Главная функция запуска приложения."""
    logger.info("Starting Psychosomatic Bot...")
    
    # Проверяем подключение к базе данных
    logger.info("Checking database connection...")
    if not await check_db_connection():
        logger.error("Database connection failed! Exiting...")
        sys.exit(1)
    logger.info("Database connection OK")
    
    # Создаем экземпляр бота
    bot = Bot(token=settings.BOT_TOKEN)
    
    # Создаем диспетчер
    dp = Dispatcher()
    
    # Регистрируем middleware
    dp.update.middleware(DBSessionMiddleware())
    logger.info("Middleware registered")
    
    # Регистрируем обработчики (порядок важен!)
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(help.router)
    dp.include_router(privacy.router)
    dp.include_router(symptom.router)   # Сценарий "Разобрать симптом"
    dp.include_router(stress.router)    # Сценарий "Проверить стресс"
    dp.include_router(settings.router)  # Сценарий "Настройки"
    dp.include_router(cancel.router)    # Команда /cancel
    dp.include_router(history.router)   # История анализов
    dp.include_router(errors_router)    # Глобальный обработчик ошибок
    logger.info("Handlers registered")
    
    # Настраиваем команды
    await setup_bot_commands(bot)
    
    # Запускаем FastAPI сервер в фоне
    logger.info(f"Starting FastAPI server on {settings.API_HOST}:{settings.API_PORT}")
    config = uvicorn.Config(
        fastapi_app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    fastapi_task = asyncio.create_task(server.serve())
    
    try:
        # Запускаем бота (поллинг)
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    finally:
        # Graceful shutdown
        fastapi_task.cancel()
        await bot.session.close()
        await engine.dispose()
        logger.info("Application stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)