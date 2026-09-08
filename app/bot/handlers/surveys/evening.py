"""
Обработчик вечернего опроса.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.bot.states import EveningSurveyStates
from app.bot.keyboards.surveys import (
    get_survey_cancel_keyboard,
    get_evening_question_1_keyboard,
    get_evening_question_2_keyboard,
    get_evening_question_3_keyboard,
    get_evening_question_4_keyboard,
    get_evening_question_5_keyboard,
    get_evening_reminder_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.services.ai_service import ai_service
from app.services.safety import safety_service, SafetyLevel
from app.db.models.user import User
from app.db.repositories.analysis import AnalysisRepository
from app.db.repositories.diary import DiaryRepository
from app.utils.logging import logger

router = Router()


@router.message(F.text == "🌆 Вечерний опрос")
async def start_evening_survey(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Запускает вечерний опрос.
    """
    await state.clear()
    
    await message.answer(
        "🌆 <b>Добрый вечер!</b>\n\n"
        "Давай подведём итоги дня.\n"
        "Ответь на несколько вопросов — это поможет увидеть картину дня.\n\n"
        "Если передумаешь, нажми ❌ Отмена",
        reply_markup=get_survey_cancel_keyboard(),
        parse_mode="HTML",
    )
    
    await state.set_state(EveningSurveyStates.waiting_for_question_1)
    
    await message.answer(
        "1️⃣ <b>Как ты сейчас себя чувствуешь?</b>\n"
        "Выбери вариант:",
        reply_markup=get_evening_question_1_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"Evening survey started: user={message.from_user.id}")


@router.message(EveningSurveyStates.waiting_for_question_1, F.text)
async def process_evening_q1(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 1: Как себя чувствуешь?"""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(q1=answer)
    await state.set_state(EveningSurveyStates.waiting_for_question_2)
    
    await message.answer(
        "2️⃣ <b>Что сегодня сильнее всего повлияло на твоё состояние?</b>\n"
        "Выбери вариант или напиши свой:",
        reply_markup=get_evening_question_2_keyboard(),
        parse_mode="HTML",
    )


@router.message(EveningSurveyStates.waiting_for_question_2, F.text)
async def process_evening_q2(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 2: Что повлияло?"""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(q2=answer)
    await state.set_state(EveningSurveyStates.waiting_for_question_3)
    
    await message.answer(
        "3️⃣ <b>Что дало тебе энергию сегодня?</b>\n"
        "Выбери вариант или напиши свой:",
        reply_markup=get_evening_question_3_keyboard(),
        parse_mode="HTML",
    )


@router.message(EveningSurveyStates.waiting_for_question_3, F.text)
async def process_evening_q3(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 3: Что дало энергию?"""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(q3=answer)
    await state.set_state(EveningSurveyStates.waiting_for_question_4)
    
    await message.answer(
        "4️⃣ <b>Что забрало твои силы сегодня?</b>\n"
        "Выбери вариант или напиши свой:",
        reply_markup=get_evening_question_4_keyboard(),
        parse_mode="HTML",
    )


@router.message(EveningSurveyStates.waiting_for_question_4, F.text)
async def process_evening_q4(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 4: Что забрало силы?"""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(q4=answer)
    await state.set_state(EveningSurveyStates.waiting_for_question_5)
    
    await message.answer(
        "5️⃣ <b>Как прошёл день с точки зрения еды, сна и движения?</b>\n"
        "Выбери вариант или напиши свой:",
        reply_markup=get_evening_question_5_keyboard(),
        parse_mode="HTML",
    )


@router.message(EveningSurveyStates.waiting_for_question_5, F.text)
async def process_evening_q5(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка вопроса 5: Как с едой, сном, движением?"""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(q5=answer)
    
    data = await state.get_data()
    survey_data = {
        "q1": data.get("q1"),
        "q2": data.get("q2"),
        "q3": data.get("q3"),
        "q4": data.get("q4"),
        "q5": answer,
    }
    
    await state.update_data(survey_data=survey_data)
    await state.set_state(EveningSurveyStates.waiting_for_clarification)
    
    await message.answer(
        "📝 <b>Давай уточним</b>\n\n"
        "Что повторялось в твоём состоянии сегодня?\n"
        "(Или напиши 'Пропустить')",
        reply_markup=get_survey_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(EveningSurveyStates.waiting_for_clarification, F.text)
async def process_evening_clarification(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка уточняющего вопроса."""
    answer = message.text.strip()
    
    if answer == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Опрос отменён.", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(clarification=answer)
    await state.set_state(EveningSurveyStates.waiting_for_reminder)
    
    data = await state.get_data()
    survey_data = data.get("survey_data", {})
    clarification = data.get("clarification", "Не указано")
    telegram_id = message.from_user.id
    
    symptom_text = (
        f"Вечернее состояние:\n"
        f"1. Чувствую: {survey_data.get('q1', 'Не указано')}\n"
        f"2. Повлияло: {survey_data.get('q2', 'Не указано')}\n"
        f"3. Энергия от: {survey_data.get('q3', 'Не указано')}\n"
        f"4. Забрало силы: {survey_data.get('q4', 'Не указано')}\n"
        f"5. Еда/сон/движение: {survey_data.get('q5', 'Не указано')}\n"
        f"Уточнение (повторяемость): {clarification}"
    )
    
    loading_message = await message.answer(
        "🧠 Анализирую твой день...\n\nПожалуйста, подожди.",
        reply_markup=get_survey_cancel_keyboard(),
    )
    
    try:
        result = await ai_service.analyze_and_save(
            telegram_id=telegram_id,
            symptom=symptom_text[:200],
            duration="Вечер",
            intensity=5,
            context="Вечерний опрос",
            db_session=db_session,
        )
        
        await loading_message.delete()
        
        if result["success"]:
            analysis = result["analysis"]
            analysis_id = result.get("analysis_id")
            
            from app.services.access_service import AccessService
            access_service = AccessService(db_session)
            await access_service.increment_body_analysis(telegram_id)
            
            # ==================== СОХРАНЯЕМ В ДНЕВНИК ====================
            user_result = await db_session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                diary_repo = DiaryRepository(db_session)
                await diary_repo.save_survey_evening(
                    user_id=user.id,
                    answers=survey_data,
                    analysis_text=analysis.summary if hasattr(analysis, 'summary') else str(analysis),
                    micro_action=analysis.micro_action if hasattr(analysis, 'micro_action') else None,
                    summary=analysis.summary if hasattr(analysis, 'summary') else None,
                    medical_warning=analysis.medical_warning if hasattr(analysis, 'medical_warning') else None,
                    analysis_id=analysis_id,
                )
                logger.info(f"Evening survey saved to diary for user {telegram_id}")
            # ==============================================================
            
            result_text = format_evening_survey_analysis(analysis, survey_data)
            
            micro_action = analysis.micro_action or "Попробуй завтра утром сделать 5-минутную зарядку."
            result_text += f"\n\n🌱 <b>Микродействие на завтра:</b>\n{micro_action}\n\n"
            
            await state.clear()
            
            await message.answer(
                result_text,
                reply_markup=get_evening_reminder_keyboard(),
                parse_mode="HTML",
            )
            
            logger.info(f"Evening survey completed: user={telegram_id}")
            
        else:
            await message.answer(
                f"😔 Не удалось выполнить анализ.\n\n{result.get('error', 'Попробуйте позже.')}",
                reply_markup=get_main_menu_keyboard(),
            )
            
    except Exception as e:
        await loading_message.delete()
        logger.error(f"Error in evening survey: {e}")
        await message.answer(
            "😔 Произошла ошибка. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard(),
        )


@router.callback_query(F.data.startswith("evening_"))
async def evening_callback_actions(callback: CallbackQuery, state: FSMContext):
    """Обработка callback-действий после вечернего опроса."""
    action = callback.data.replace("evening_", "")
    
    if action == "remind_tomorrow":
        await callback.answer("🔔 Напомню завтра утром!")
        await callback.message.edit_text(
            "✅ Отлично! Я напомню тебе об этом завтра утром.\n\n"
            "Спокойной ночи! 🌙",
            reply_markup=None,
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )
        
    elif action == "track_next":
        await callback.answer("📝 Отлично, отследим в следующем опросе!")
        await callback.message.edit_text(
            "✅ Хорошо! Ты сможешь описать изменения в следующем опросе.\n\n"
            "Спокойной ночи! 🌙",
            reply_markup=None,
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )
        
    elif action == "finish":
        await callback.answer()
        await state.clear()
        await callback.message.delete()
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )


# ==================== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ====================

def format_evening_survey_analysis(analysis, survey_data: dict) -> str:
    """
    Форматирует результат вечернего опроса с двумя подходами.
    """
    text = f"🌆 <b>Итоги дня</b>\n\n"
    
    text += f"📊 <b>Краткая сводка</b>\n"
    text += f"• Состояние: {survey_data.get('q1', 'Не указано')}\n"
    text += f"• Повлияло: {survey_data.get('q2', 'Не указано')}\n"
    text += f"• Энергия от: {survey_data.get('q3', 'Не указано')}\n"
    text += f"• Забрало силы: {survey_data.get('q4', 'Не указано')}\n"
    text += f"• Еда/сон/движение: {survey_data.get('q5', 'Не указано')}\n\n"
    
    text += f"{analysis.summary}\n\n"
    
    if analysis.possible_factors:
        text += "📌 <b>Возможные факторы:</b>\n"
        for factor in analysis.possible_factors:
            text += f"• {factor}\n"
        text += "\n"
    
    if analysis.possible_patterns:
        text += "🔄 <b>Возможные паттерны:</b>\n"
        for pattern in analysis.possible_patterns:
            text += f"• {pattern}\n"
        text += "\n"
    
    text += "🧠 <b>Тело говорит подсознанию</b> (по Синельникову)\n"
    text += "Тело может отражать внутренние конфликты, невыраженные эмоции и бессознательные установки.\n"
    
    energy_source = survey_data.get('q3', '')
    if 'общение' in energy_source.lower():
        text += "• Общение может быть источником энергии, если оно приносит радость и поддержку.\n"
    if 'еда' in energy_source.lower():
        text += "• Еда — не только топливо, но и эмоциональный ресурс. Обрати внимание на качество питания.\n"
    text += "Важно: это возможная интерпретация для самонаблюдения, а не диагноз.\n\n"
    
    text += "🔬 <b>Современный подход</b>\n"
    text += "Современные исследования показывают, что вечернее состояние связано с накопленным стрессом "
    text += "и качеством восстановления. Регулярное наблюдение помогает снижать тревогу "
    text += "и повышать осознанность.\n"
    
    if analysis.check_question:
        text += f"\n❓ <b>Вопрос для самопроверки:</b>\n{analysis.check_question}\n"
    
    if analysis.medical_warning:
        text += f"\n⚠️ {analysis.medical_warning}\n"
    
    return text