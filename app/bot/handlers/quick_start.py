"""
Обработчик для кнопки "💡 Помогите разобраться".
Экспресс-диагностика: пользователь описывает состояние → запуск психоблока.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession  # ← ДОБАВЛЕНО

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
        "💡 <b>Помогите разобраться</b>\n\n"
        "Я помогу тебе исследовать твоё состояние.\n\n"
        "📝 <b>Опиши, что ты чувствуешь</b>\n"
        "Расскажи своими словами:\n"
        "• Что тебя беспокоит?\n"
        "• Где ты это чувствуешь?\n"
        "• Что происходит в жизни?\n\n"
        "Например:\n"
        "«Последние дни чувствую тяжесть в груди, "
        "особенно когда волнуюсь на работе.»\n\n"
        "Или начни с простого: «Мне тревожно».",
        reply_markup=get_quick_start_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"User opened quick start: {message.from_user.id}")


@router.message(QuickStartStates.waiting_for_description, F.text)
async def process_quick_start_description(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает описание состояния пользователя."""
    description = message.text.strip()
    
    if len(description) < 5:
        await message.answer(
            "⚠️ Пожалуйста, опиши своё состояние подробнее (минимум 5 символов).",
            reply_markup=get_quick_start_cancel_keyboard(),
        )
        return
    
    await state.update_data(symptom=description)
    await state.update_data(symptom_source="quick_start")
    
    await start_psychoblock(message, state, db_session, description)


@router.message(QuickStartStates.waiting_for_description)
async def process_quick_start_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод."""
    await message.answer(
        "Пожалуйста, опиши своё состояние текстом.",
        reply_markup=get_quick_start_cancel_keyboard(),
    )


@router.callback_query(F.data == "quick_start_cancel")
async def cancel_quick_start(callback: CallbackQuery, state: FSMContext):
    """Отмена экспресс-диагностики."""
    await callback.answer("Возвращаемся в меню")
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


# ==================== ПСИХОБЛОК (заглушка) ====================

async def start_psychoblock(message: types.Message, state: FSMContext, db_session: AsyncSession, description: str):
    """
    🟡 ВРЕМЕННАЯ ЗАГЛУШКА: перенаправляет в существующий анализ симптома.
    🔥 ПОЗЖЕ: здесь будет полноценный психоблок с уточняющими вопросами и AI.
    """
    await state.update_data(symptom=description)
    await state.set_state(SymptomAnalysisStates.waiting_for_duration)
    
    await message.answer(
        f"💡 <b>Я тебя слышу</b>\n\n"
        f"📝 Ты написал:\n«{description[:200]}»\n\n"
        "Теперь давай уточним.\n\n"
        "Как долго это продолжается?",
        reply_markup=get_duration_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"Quick start psychoblock started for: {description[:50]}...")