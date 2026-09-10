"""
Главный файл приложения.
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
    start,
    menu,
    help,
    privacy,
    cancel,
    history,
    settings as settings_handler,
    dynamics_handler,
    reminders_handler,
    pro_handler,
    admin_handler,
    support_handler,
    profile_handler,
    how_it_works_handler,
    describe_state_handler,
    diary_handler,
    survey_launcher,  # ← ДОБАВЛЕНО
)
from app.bot.handlers.surveys import morning as morning_survey_handler
from app.bot.handlers.surveys import day as day_survey_handler
from app.bot.handlers.surveys import evening as evening_survey_handler
from app.bot.errors import router as errors_router
from app.api.server import app as fastapi_app
from app.db.database import check_db_connection, engine, async_session_maker
from app.services.reminder_service import ReminderService
from app.services.subscription_service import SubscriptionService
from app.services.payment_reconciliation_service import PaymentReconciliationService
from app.services.survey_scheduler import SurveyScheduler
from app.webhooks.yookassa import router as yookassa_webhook_router


logger = setup_logging(config_settings.LOG_LEVEL)


async def setup_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="privacy", description="Конфиденциальность"),
        BotCommand(command="cancel", description="Отменить текущий диалог"),
        BotCommand(command="history", description="История"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands configured")


async def main() -> None:
    logger.info("Starting Soma Bot...")
    
    if not await check_db_connection():
        logger.error("Database connection failed! Exiting...")
        sys.exit(1)
    
    bot = Bot(token=config_settings.BOT_TOKEN)
    dp = Dispatcher()
    
    dp.update.middleware(DBSessionMiddleware())
    
    # ==================== РЕГИСТРАЦИЯ РОУТЕРОВ ====================
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(help.router)
    dp.include_router(privacy.router)
    dp.include_router(settings_handler.router)
    dp.include_router(dynamics_handler.router)
    dp.include_router(reminders_handler.router)
    dp.include_router(pro_handler.router)
    dp.include_router(admin_handler.router)
    dp.include_router(support_handler.router)
    dp.include_router(profile_handler.router)
    dp.include_router(how_it_works_handler.router)
    dp.include_router(describe_state_handler.router)
    dp.include_router(diary_handler.router)
    dp.include_router(morning_survey_handler.router)
    dp.include_router(day_survey_handler.router)
    dp.include_router(evening_survey_handler.router)
    dp.include_router(survey_launcher.router)  # ← ДОБАВЛЕНО
    dp.include_router(cancel.router)
    dp.include_router(history.router)
    dp.include_router(errors_router)
    
    await setup_bot_commands(bot)
    
    reminder_service = ReminderService(async_session_maker, bot)
    await reminder_service.start()
    
    reconciliation_service = PaymentReconciliationService(async_session_maker)
    await reconciliation_service.start()
    
    survey_scheduler = SurveyScheduler(async_session_maker, bot)
    await survey_scheduler.start()
    
    fastapi_app.include_router(yookassa_webhook_router)
    
    config = uvicorn.Config(
        fastapi_app,
        host=config_settings.API_HOST,
        port=config_settings.API_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    fastapi_task = asyncio.create_task(server.serve())
    
    try:
        await dp.start_polling(bot)
    finally:
        fastapi_task.cancel()
        await reminder_service.stop()
        await reconciliation_service.stop()
        await survey_scheduler.stop()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)