"""
Обработчик для кнопки "💡 Помогите разобраться".
Экспресс-диагностика: пользователь описывает состояние → запуск психоблока.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import QuickStartStates, SymptomAnalysisStates
from app.bot.keyboards.quick_start import (
    get_quick_start_keyboard,
    get_quick_start_cancel_keyboard,
)
from app.bot.keyboards.symptom import get_duration_keyboard
from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


@router.message(F.text == "💡 Помогите разобраться")
async def show_quick_start(message: types.Message, state: FSMContext):
    """Показывает приветствие и предлагает описать состояние."""
    await state.clear()
    await state.set_state(QuickStartStates.waiting_for_description)

    await message.answer(
        "📝 <b>Расскажи, как ты себя чувствуешь</b>\n\n"
        "Можешь написать всё, что сейчас кажется важным: ощущения в теле, эмоции, "
        "мысли, сон, питание, нагрузку или то, что происходило сегодня.\n\n"
        "Пиши своими словами. Не нужно подбирать правильные формулировки.\n\n"
        "Например:\n"
        "• «Чувствую тяжесть в груди и тревогу»\n"
        "• «Утром болела голова, сейчас стало легче»\n"
        "• «Не могу сосредоточиться, всё раздражает»\n"
        "• «После работы сильно напряглись плечи»\n\n"
        "Не знаешь, с чего начать? Это тоже нормально.\n"
        "Можешь просто написать:\n"
        "«Я не знаю, что со мной».\n\n"
        "Сома сама начнёт диалог и задаст несколько простых вопросов, "
        "чтобы помочь тебе разобраться.\n\n"
        "Я буду уточнять только то, что действительно важно для понимания твоего состояния, "
        "и вместе мы посмотрим, что могло на него повлиять.\n\n"
        "🌿 Просто напиши, что происходит сейчас. Начнём с этого.",
        reply_markup=get_quick_start_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"User opened quick start: {message.from_user.id}")