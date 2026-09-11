"""
Обработчик утреннего опроса.
Сохраняет каждый ответ в DiaryEvent.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.bot.states import MorningSurveyStates
from app.bot.keyboards.surveys import (
    get_survey_cancel_keyboard,
    get_morning_question_1_keyboard,
    get_morning_question_2_keyboard,
    get_morning_question_3_keyboard,
    get_morning_question_4_keyboard,
    get_morning_question_5_keyboard,
    get_morning_reminder_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.services.ai_service import ai_service
from app.services.diary_event_service import DiaryEventService
from app.services.safety import safety_service, SafetyLevel
from app.db.models.user import User
from app.utils.logging import logger
from app.utils.survey_formatter import format_morning_survey_analysis

router = Router()

AFFIRMATIONS = [
    "Моё тело — мой союзник. Я учусь слышать его сигналы.",
    "Сегодня я могу заметить больше, чем вчера.",
    "Я разрешаю себе чувствовать и быть в контакте с собой.",
    "Утро задаёт тон дню. Как ты начнёшь его?",
]

affirmation_index = 0


def get_next_affirmation() -> str:
    global affirmation_index
    aff = AFFIRMATIONS[affirmation_index % len(AFFIRMATIONS)]
    affirmation_index += 1
    return aff


@router.message(F.text == "🌅 Утренний опрос")
async def start_morning_survey(message: types.Message, state: FSMContext, db_session: AsyncSession = None):
    """Запускает утренний опрос."""
    await state.clear()
    
    affirmation = get_next_affirmation()
    await message.answer(
        f"🌅 <b>Доброе утро!</b>\n\n"
        f"✨ <i>«{affirmation}»</i>\n\n"
        "Давай начнём день с небольшого наблюдения за собой.\n"
        "Ответь на несколько вопросов — это поможет лучше понять своё состояние.\n\n"
        "Если передумаешь, нажми ❌ Отмена",
        reply_markup=get_survey_cancel_keyboard(),
        parse_mode="HTML",
    )
    
    await state.set_state(MorningSurveyStates.waiting_for_question_1)
    
    await message.answer(
        "1️⃣ <b>Как ты проснулся?</b>\n"
        "Выбери вариант:",
        reply_markup=get_morning_question_1_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"Morning survey started: user={message.from_user.id}")


@router.message(MorningSurveyStates.waiting_for_question_1, F.text)
async def process_morning_q1(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 1."""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(q1=answer)
    await state.set_state(MorningSurveyStates.waiting_for_question_2)
    
    diary_service = DiaryEventService(db_session)
    await diary_service.record_survey_answer(
        telegram_id=message.from_user.id,
        question="Как ты проснулся?",
        answer=answer,
        survey_type="morning",
        payload={"question_number": 1},
    )
    
    await message.answer(
        "2️⃣ <b>Что сейчас чувствуешь в теле?</b>\n"
        "Выбери вариант или напиши свой:",
        reply_markup=get_morning_question_2_keyboard(),
        parse_mode="HTML",
    )


@router.message(MorningSurveyStates.waiting_for_question_2, F.text)
async def process_morning_q2(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 2."""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(q2=answer)
    await state.set_state(MorningSurveyStates.waiting_for_question_3)
    
    diary_service = DiaryEventService(db_session)
    await diary_service.record_survey_answer(
        telegram_id=message.from_user.id,
        question="Что сейчас чувствуешь в теле?",
        answer=answer,
        survey_type="morning",
        payload={"question_number": 2},
    )
    
    await message.answer(
        "3️⃣ <b>Какое у тебя настроение?</b>\n"
        "Выбери вариант:",
        reply_markup=get_morning_question_3_keyboard(),
        parse_mode="HTML",
    )


@router.message(MorningSurveyStates.waiting_for_question_3, F.text)
async def process_morning_q3(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 3."""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(q3=answer)
    await state.set_state(MorningSurveyStates.waiting_for_question_4)
    
    diary_service = DiaryEventService(db_session)
    await diary_service.record_survey_answer(
        telegram_id=message.from_user.id,
        question="Какое у тебя настроение?",
        answer=answer,
        survey_type="morning",
        payload={"question_number": 3},
    )
    
    await message.answer(
        "4️⃣ <b>Что сейчас в мыслях?</b>\n"
        "Выбери вариант или напиши свой:",
        reply_markup=get_morning_question_4_keyboard(),
        parse_mode="HTML",
    )


@router.message(MorningSurveyStates.waiting_for_question_4, F.text)
async def process_morning_q4(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 4."""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(q4=answer)
    await state.set_state(MorningSurveyStates.waiting_for_question_5)
    
    diary_service = DiaryEventService(db_session)
    await diary_service.record_survey_answer(
        telegram_id=message.from_user.id,
        question="Что сейчас в мыслях?",
        answer=answer,
        survey_type="morning",
        payload={"question_number": 4},
    )
    
    await message.answer(
        "5️⃣ <b>Как спал прошлой ночью?</b>\n"
        "Выбери вариант:",
        reply_markup=get_morning_question_5_keyboard(),
        parse_mode="HTML",
    )


@router.message(MorningSurveyStates.waiting_for_question_5, F.text)
async def process_morning_q5(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 5."""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(q5=answer)
    
    diary_service = DiaryEventService(db_session)
    await diary_service.record_survey_answer(
        telegram_id=message.from_user.id,
        question="Как спал прошлой ночью?",
        answer=answer,
        survey_type="morning",
        payload={"question_number": 5},
    )
    
    data = await state.get_data()
    survey_data = {
        "q1": data.get("q1"),
        "q2": data.get("q2"),
        "q3": data.get("q3"),
        "q4": data.get("q4"),
        "q5": answer,
    }
    
    await state.update_data(survey_data=survey_data)
    await state.set_state(MorningSurveyStates.waiting_for_clarification)
    
    await message.answer(
        "📝 <b>Давай уточним</b>\n\n"
        "Где именно ты чувствуешь напряжение или дискомфорт?\n"
        "(Или напиши 'Пропустить', если не хочешь уточнять)",
        reply_markup=get_morning_question_2_keyboard(),
        parse_mode="HTML",
    )


@router.message(MorningSurveyStates.waiting_for_clarification, F.text)
async def process_morning_clarification(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка уточняющего вопроса."""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(clarification=answer)
    await state.set_state(MorningSurveyStates.waiting_for_reminder)
    
    diary_service = DiaryEventService(db_session)
    await diary_service.record_survey_answer(
        telegram_id=message.from_user.id,
        question="Где именно напряжение/дискомфорт?",
        answer=answer,
        survey_type="morning",
        payload={"type": "clarification"},
    )
    
    await message.answer(
        "📝 <b>Что сейчас сильнее всего влияет на твоё состояние?</b>\n"
        "(Или напиши 'Пропустить')",
        reply_markup=get_survey_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(MorningSurveyStates.waiting_for_reminder, F.text)
async def process_morning_second_clarification(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка второго уточняющего вопроса и запуск анализа."""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(second_clarification=answer)
    
    diary_service = DiaryEventService(db_session)
    await diary_service.record_survey_answer(
        telegram_id=message.from_user.id,
        question="Что сильнее всего влияет на состояние?",
        answer=answer,
        survey_type="morning",
        payload={"type": "clarification_2"},
    )
    
    data = await state.get_data()
    survey_data = data.get("survey_data", {})
    clarification = data.get("clarification", "Не указано")
    second_clarification = data.get("second_clarification", "Не указано")
    telegram_id = message.from_user.id
    
    symptom_text = (
        f"Утреннее состояние:\n"
        f"1. Как проснулся: {survey_data.get('q1', 'Не указано')}\n"
        f"2. Телесные ощущения: {survey_data.get('q2', 'Не указано')}\n"
        f"3. Настроение: {survey_data.get('q3', 'Не указано')}\n"
        f"4. Мысли: {survey_data.get('q4', 'Не указано')}\n"
        f"5. Сон: {survey_data.get('q5', 'Не указано')}\n"
        f"Уточнение 1 (дискомфорт): {clarification}\n"
        f"Уточнение 2 (влияние): {second_clarification}"
    )
    
    loading_message = await message.answer(
        "🧠 Анализирую твоё состояние...\n\nПожалуйста, подожди.",
        reply_markup=get_survey_cancel_keyboard(),
    )
    
    try:
        result = await ai_service.analyze_and_save(
            telegram_id=telegram_id,
            symptom=symptom_text[:200],
            duration="Утро",
            intensity=5,
            context="Утренний опрос",
            db_session=db_session,
        )
        
        await loading_message.delete()
        
        if result["success"]:
            analysis = result["analysis"]
            analysis_id = result.get("analysis_id")
            
            from app.services.access_service import AccessService
            access_service = AccessService(db_session)
            await access_service.increment_body_analysis(telegram_id)
            
            # Сохраняем анализ в DiaryEvent
            await diary_service.record_event(
                telegram_id=telegram_id,
                event_type="analysis",
                source="morning_survey",
                role="assistant",
                content=analysis.summary if hasattr(analysis, 'summary') else str(analysis),
                payload={
                    "summary": analysis.summary if hasattr(analysis, 'summary') else None,
                    "micro_action": analysis.micro_action if hasattr(analysis, 'micro_action') else None,
                    "survey_data": survey_data,
                },
                analysis_id=analysis_id,
            )
            
            result_text = format_morning_survey_analysis(analysis, survey_data)
            
            micro_action = analysis.micro_action or "Попробуй сделать 5 глубоких вдохов и выдохов."
            result_text += f"\n\n🌱 <b>Микродействие на сегодня:</b>\n{micro_action}\n\n"
            
            await state.clear()
            
            await message.answer(
                result_text,
                reply_markup=get_morning_reminder_keyboard(),
                parse_mode="HTML",
            )
            
            logger.info(f"Morning survey completed: user={telegram_id}")
            
        else:
            await message.answer(
                f"😔 Не удалось выполнить анализ.\n\n{result.get('error', 'Попробуйте позже.')}",
                reply_markup=get_main_menu_keyboard(),
            )
            
    except Exception as e:
        await loading_message.delete()
        logger.error(f"Error in morning survey: {e}")
        await message.answer(
            "😔 Произошла ошибка. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard(),
        )


@router.callback_query(F.data.startswith("morning_"))
async def morning_callback_actions(callback: CallbackQuery, state: FSMContext):
    """Обработка callback-действий."""
    action = callback.data.replace("morning_", "")
    
    if action == "remind_1h":
        await callback.answer("🔔 Напомню через час!")
        await callback.message.edit_text(
            "✅ Отлично! Я напомню тебе об этом через час.\n\n"
            "Если захочешь описать изменения — просто напиши мне.",
            reply_markup=None,
        )
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text="Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )
        
    elif action == "remind_2h":
        await callback.answer("🔔 Напомню через 2 часа!")
        await callback.message.edit_text(
            "✅ Отлично! Я напомню тебе об этом через 2 часа.\n\n"
            "Если захочешь описать изменения — просто напиши мне.",
            reply_markup=None,
        )
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text="Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )
        
    elif action == "track_next":
        await callback.answer("📝 Отлично, отследим в следующем опросе!")
        await callback.message.edit_text(
            "✅ Хорошо! Ты сможешь описать изменения в следующем опросе.\n\n"
            "Это поможет отследить твой прогресс!",
            reply_markup=None,
        )
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text="Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )
        
    elif action == "finish":
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