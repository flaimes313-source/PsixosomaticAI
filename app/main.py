"""
Главный файл приложения.
Запускает Telegram бота и FastAPI сервер.
"""
import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
import uvicorn

from app.config import settings as config_settings
from app.utils.logging import setup_logging, logger
from app.bot.middlewares import DBSessionMiddleware
from app.bot.handlers import (
    start, menu, help, privacy, symptom, cancel, history, stress,
    settings as settings_handler, diary,
    dynamics_handler, reminders_handler, pro_handler,
    admin_handler, support_handler, profile_handler,
    how_it_works_handler, symptom_choice_handler, quick_start_handler  # ← ДОБАВЛЕН quick_start_handler
)
from app.bot.errors import router as errors_router
from app.api.server import app as fastapi_app
from app.db.database import check_db_connection, engine, async_session_maker
from app.services.reminder_service import ReminderService
from app.services.subscription_service import SubscriptionService
from app.services.payment_reconciliation_service import PaymentReconciliationService
from app.webhooks.yookassa import router as yookassa_webhook_router
from app.db.repositories.subscription import SubscriptionRepository


# Настройка логирования
logger = setup_logging(config_settings.LOG_LEVEL)


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


async def check_expired_subscriptions() -> None:
    """Проверяет истекшие подписки при запуске."""
    try:
        async with async_session_maker() as session:
            subscription_service = SubscriptionService(session)
            expired_count = await subscription_service.check_expired_subscriptions()
            if expired_count > 0:
                logger.info(f"Checked and expired {expired_count} subscriptions")
    except Exception as e:
        logger.error(f"Failed to check expired subscriptions on startup: {e}")


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
    bot = Bot(token=config_settings.BOT_TOKEN)
    
    # Создаем диспетчер
    dp = Dispatcher()
    
    # Регистрируем middleware
    dp.update.middleware(DBSessionMiddleware())
    logger.info("Middleware registered")
    
    # ==================== РЕГИСТРИРУЕМ ОБРАБОТЧИКИ ====================
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(help.router)
    dp.include_router(privacy.router)
    dp.include_router(symptom.router)          # Сценарий "Разобрать симптом"
    dp.include_router(stress.router)           # Сценарий "Проверить стресс"
    dp.include_router(settings_handler.router) # Сценарий "Настройки"
    dp.include_router(diary.router)            # Сценарий "Дневник"
    dp.include_router(dynamics_handler.router) # Сценарий "Моя динамика"
    dp.include_router(reminders_handler.router)# Сценарий "Напоминания"
    dp.include_router(pro_handler.router)      # Сценарий "PRO"
    dp.include_router(admin_handler.router)    # Админ-панель
    dp.include_router(support_handler.router)  # Поддержка
    dp.include_router(profile_handler.router)  # Профиль
    dp.include_router(how_it_works_handler.router)  # "Как это работает?"
    dp.include_router(symptom_choice_handler.router)  # "Что я чувствую в теле?"
    dp.include_router(quick_start_handler.router)  # ← НОВЫЙ: "Помогите разобраться"
    dp.include_router(cancel.router)           # Команда /cancel
    dp.include_router(history.router)          # История анализов
    dp.include_router(errors_router)           # Глобальный обработчик ошибок
    logger.info("Handlers registered")
    
    # Настраиваем команды
    await setup_bot_commands(bot)
    
    # Проверяем истекшие подписки при запуске
    await check_expired_subscriptions()
    
    # Запускаем шедулер напоминаний
    logger.info("Starting ReminderService...")
    reminder_service = ReminderService(async_session_maker, bot)
    await reminder_service.start()
    logger.info("ReminderService started")
    
    # Запуск реконсиляции платежей
    logger.info("Starting PaymentReconciliationService...")
    reconciliation_service = PaymentReconciliationService(async_session_maker)
    await reconciliation_service.start()
    logger.info("PaymentReconciliationService started")

    # Подключение webhook
    fastapi_app.include_router(yookassa_webhook_router)
    logger.info("YooKassa webhook router registered")
    
    # Запускаем FastAPI сервер в фоне
    logger.info(f"Starting FastAPI server on {config_settings.API_HOST}:{config_settings.API_PORT}")
    config = uvicorn.Config(
        fastapi_app,
        host=config_settings.API_HOST,
        port=config_settings.API_PORT,
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
        logger.info("Shutting down...")
        fastapi_task.cancel()
        await reminder_service.stop()
        await reconciliation_service.stop()
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