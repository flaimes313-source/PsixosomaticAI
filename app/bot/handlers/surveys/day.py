"""
Обработчик дневного опроса.
Сохраняет каждый ответ в DiaryEvent.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.bot.states import DaySurveyStates
from app.bot.keyboards.surveys import (
    get_survey_cancel_keyboard,
    get_day_question_1_keyboard,
    get_day_question_2_keyboard,
    get_day_question_3_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.services.diary_event_service import DiaryEventService
from app.services.safety import safety_service, SafetyLevel
from app.db.models.user import User
from app.utils.logging import logger

router = Router()


@router.message(F.text == "☀️ Дневной опрос")
async def start_day_survey(message: types.Message, state: FSMContext, db_session: AsyncSession = None):
    """Запускает дневной опрос."""
    await state.clear()
    
    session_id = str(uuid.uuid4())
    await state.update_data(session_id=session_id)
    
    await message.answer(
        "☀️ <b>Добрый день!</b>\n\n"
        "Давай проверим, как проходит твой день.\n"
        "Ответь на несколько коротких вопросов.\n\n"
        "Если передумаешь, нажми ❌ Отмена",
        reply_markup=get_survey_cancel_keyboard(),
        parse_mode="HTML",
    )
    
    await state.set_state(DaySurveyStates.waiting_for_question_1)
    
    await message.answer(
        "1️⃣ <b>Как ты сейчас себя чувствуешь?</b>\n"
        "Выбери вариант:",
        reply_markup=get_day_question_1_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"Day survey started: user={message.from_user.id}, session={session_id}")


@router.message(DaySurveyStates.waiting_for_question_1, F.text)
async def process_day_q1(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 1."""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    data = await state.get_data()
    session_id = data.get("session_id")
    
    await state.update_data(q1=answer)
    await state.set_state(DaySurveyStates.waiting_for_question_2)
    
    diary_service = DiaryEventService(db_session)
    await diary_service.record_survey_answer(
        telegram_id=message.from_user.id,
        question="Как ты сейчас себя чувствуешь?",
        answer=answer,
        survey_type="day",
        session_id=session_id,
        payload={"question_number": 1},
    )
    
    await message.answer(
        "2️⃣ <b>Что изменилось с утра?</b>\n"
        "Выбери вариант:",
        reply_markup=get_day_question_2_keyboard(),
        parse_mode="HTML",
    )


@router.message(DaySurveyStates.waiting_for_question_2, F.text)
async def process_day_q2(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 2."""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    data = await state.get_data()
    session_id = data.get("session_id")
    
    await state.update_data(q2=answer)
    await state.set_state(DaySurveyStates.waiting_for_question_3)
    
    diary_service = DiaryEventService(db_session)
    await diary_service.record_survey_answer(
        telegram_id=message.from_user.id,
        question="Что изменилось с утра?",
        answer=answer,
        survey_type="day",
        session_id=session_id,
        payload={"question_number": 2},
    )
    
    await message.answer(
        "3️⃣ <b>Что повлияло на твоё состояние?</b>\n"
        "Выбери вариант или напиши свой:",
        reply_markup=get_day_question_3_keyboard(),
        parse_mode="HTML",
    )


@router.message(DaySurveyStates.waiting_for_question_3, F.text)
async def process_day_q3(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 3."""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    data = await state.get_data()
    session_id = data.get("session_id")
    
    await state.update_data(q3=answer)
    
    diary_service = DiaryEventService(db_session)
    await diary_service.record_survey_answer(
        telegram_id=message.from_user.id,
        question="Что повлияло на твоё состояние?",
        answer=answer,
        survey_type="day",
        session_id=session_id,
        payload={"question_number": 3},
    )
    
    data = await state.get_data()
    survey_data = {
        "q1": data.get("q1"),
        "q2": data.get("q2"),
        "q3": answer,
    }
    
    support_text = "☀️ <b>Спасибо за ответы!</b>\n\n"
    support_text += f"📊 <b>Краткая сводка:</b>\n"
    support_text += f"• Состояние: {survey_data.get('q1', 'Не указано')}\n"
    support_text += f"• Изменения: {survey_data.get('q2', 'Не указано')}\n"
    support_text += f"• Влияние: {survey_data.get('q3', 'Не указано')}\n\n"
    
    state_text = survey_data.get('q1', '').lower()
    if 'тревожно' in state_text or 'устало' in state_text:
        support_text += (
            "🧠 <b>Поддержка:</b>\n"
            "Это нормально — чувствовать усталость или тревогу в течение дня. "
            "Ты уже делаешь важный шаг — замечаешь своё состояние.\n\n"
            "🌱 <b>Маленькое действие:</b>\n"
            "Попробуй сделать 3 глубоких вдоха и выдоха прямо сейчас."
        )
    elif 'хорошо' in state_text or 'нормально' in state_text:
        support_text += (
            "🧠 <b>Поддержка:</b>\n"
            "Отлично! Ты в хорошем состоянии. Это хороший знак.\n\n"
            "🌱 <b>Маленькое действие:</b>\n"
            "Продолжай в том же духе."
        )
    else:
        support_text += (
            "🧠 <b>Поддержка:</b>\n"
            "Спасибо, что поделился. Ты молодец, что отслеживаешь своё состояние.\n\n"
            "🌱 <b>Маленькое действие:</b>\n"
            "Сделай небольшой перерыв."
        )
    
    support_text += "\n\n✅ Все ответы сохранены в дневник."
    
    await state.clear()
    
    finish_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="day_finish"
            )]
        ]
    )
    
    await message.answer(
        support_text,
        reply_markup=finish_keyboard,
        parse_mode="HTML",
    )
    
    logger.info(f"Day survey completed: user={message.from_user.id}")


@router.callback_query(F.data == "day_finish")
async def day_finish(callback: CallbackQuery, state: FSMContext):
    """Завершение дневного опроса."""
    await callback.answer()
    await state.clear()
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text="Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )