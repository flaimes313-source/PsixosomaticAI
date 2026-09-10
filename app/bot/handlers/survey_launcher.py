"""
Обработчик для запуска опросов по кнопке из шедулера.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


@router.callback_query(F.data.startswith("survey_start_"))
async def start_survey_from_callback(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Запускает опрос по нажатию кнопки."""
    survey_type = callback.data.replace("survey_start_", "")
    
    await callback.answer("Запускаю опрос...")
    
    # ==================== УДАЛЯЕМ СООБЩЕНИЕ ====================
    try:
        await callback.message.delete()
    except Exception:
        pass
    # =========================================================
    
    # ==================== ЗАПУСКАЕМ ОПРОС ЧЕРЕЗ MESSAGE ====================
    # Создаём фейковое сообщение, чтобы передать его в handler
    class FakeUser:
        def __init__(self, user_id, first_name=None, username=None, language_code=None):
            self.id = user_id
            self.first_name = first_name or "User"
            self.username = username
            self.language_code = language_code or "ru"
    
    class FakeChat:
        def __init__(self, chat_id):
            self.id = chat_id
            self.type = "private"
    
    class FakeMessage:
        def __init__(self, callback: CallbackQuery):
            self.from_user = FakeUser(
                user_id=callback.from_user.id,
                first_name=callback.from_user.first_name,
                username=callback.from_user.username,
                language_code=callback.from_user.language_code,
            )
            self.chat = FakeChat(callback.from_user.id)
            self.text = ""
            self.message_id = callback.message.message_id if callback.message else 0
            self.bot = callback.bot
        
        async def answer(self, text, reply_markup=None, parse_mode=None):
            return await self.bot.send_message(
                chat_id=self.from_user.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
    
    fake_message = FakeMessage(callback)
    
    try:
        if survey_type == "morning":
            from app.bot.handlers.surveys.morning import start_morning_survey
            await start_morning_survey(fake_message, state, db_session)
        elif survey_type == "day":
            from app.bot.handlers.surveys.day import start_day_survey
            await start_day_survey(fake_message, state, db_session)
        elif survey_type == "evening":
            from app.bot.handlers.surveys.evening import start_evening_survey
            await start_evening_survey(fake_message, state, db_session)
        else:
            await callback.message.answer(
                "❌ Неизвестный тип опроса.",
                reply_markup=get_main_menu_keyboard(),
            )
    except Exception as e:
        logger.error(f"Error starting survey {survey_type}: {e}", exc_info=True)
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text="⚠️ Произошла ошибка при запуске опроса. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard(),
        )


@router.callback_query(F.data.startswith("survey_skip_"))
async def skip_survey(callback: CallbackQuery):
    """Пропускает опрос."""
    survey_type = callback.data.replace("survey_skip_", "")
    survey_names = {
        "morning": "утренний",
        "day": "дневной",
        "evening": "вечерний",
    }
    
    await callback.answer(f"{survey_names.get(survey_type, '')} опрос пропущен")
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text="Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )