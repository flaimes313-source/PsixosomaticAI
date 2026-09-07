"""
Обработчик для запуска опросов по кнопке из шедулера.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.surveys.morning import start_morning_survey
from app.bot.handlers.surveys.day import start_day_survey
from app.bot.handlers.surveys.evening import start_evening_survey
from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


@router.callback_query(F.data.startswith("survey_start_"))
async def start_survey_from_callback(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Запускает опрос по нажатию кнопки."""
    survey_type = callback.data.replace("survey_start_", "")
    
    await callback.answer("Запускаю опрос...")
    await callback.message.delete()
    
    if survey_type == "morning":
        await start_morning_survey(callback.message, state, db_session)
    elif survey_type == "day":
        await start_day_survey(callback.message, state, db_session)
    elif survey_type == "evening":
        await start_evening_survey(callback.message, state, db_session)
    else:
        await callback.message.answer(
            "❌ Неизвестный тип опроса.",
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
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )