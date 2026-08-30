"""
Обработчики для сценария "Разобрать симптом".
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.bot.states import SymptomAnalysisStates
from app.bot.keyboards import (
    get_duration_keyboard,
    get_cancel_keyboard,
    get_analysis_complete_keyboard,
    get_main_menu_keyboard,
    get_clarification_keyboard,
    get_question_keyboard,
)
from app.bot.keyboards.pro import get_pro_locked_keyboard
from app.services.ai_service import ai_service, AIService
from app.services.safety import safety_service, SafetyLevel
from app.services.access_service import AccessService
from app.services.usage_service import UsageService
from app.utils.logging import logger
from app.utils.formatter import format_analysis_for_telegram

router = Router()
MAX_CLARIFICATIONS = 3


# ==================== ОТМЕНА СЦЕНАРИЯ ====================

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Диалог отменён.\n\nВозвращаемся в главное меню.",
        reply_markup=get_main_menu_keyboard(),
    )
    logger.info(f"User cancelled: telegram_id={message.from_user.id}")


@router.message(F.text == "❌ Отмена")
async def cancel_analysis_text(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer(
            "У вас нет активного диалога.",
            reply_markup=get_main_menu_keyboard(),
        )
        return
    
    await state.clear()
    await message.answer(
        "❌ Диалог отменён.\n\nВозвращаемся в главное меню.",
        reply_markup=get_main_menu_keyboard(),
    )
    logger.info(f"User cancelled analysis: telegram_id={message.from_user.id}")


@router.callback_query(F.data == "cancel_analysis")
async def cancel_analysis_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Диалог отменён")
    await state.clear()
    await callback.message.edit_text(
        "❌ Диалог отменён.\n\nВозвращаемся в главное меню.",
        reply_markup=None,
    )
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )
    logger.info(f"User cancelled via callback: telegram_id={callback.from_user.id}")


# ==================== ЗАПУСК СЦЕНАРИЯ ====================

@router.message(F.text == "🧠 Разобрать симптом")
async def start_symptom_analysis(message: types.Message, state: FSMContext):
    logger.info(f"User started symptom analysis: telegram_id={message.from_user.id}")
    
    await state.clear()
    await state.set_state(SymptomAnalysisStates.waiting_for_symptom)
    
    await message.answer(
        "🧠 Давайте разберём ваш симптом.\n\n"
        "Опишите, что вас беспокоит своими словами.\n"
        "Например:\n"
        "«Последние несколько дней болит голова, особенно вечером».\n\n"
        "Если передумаете, нажмите ❌ Отмена",
        reply_markup=get_cancel_keyboard(),
    )


# ==================== ПОЛУЧЕНИЕ СИМПТОМА ====================

@router.message(SymptomAnalysisStates.waiting_for_symptom, F.text)
async def process_symptom(message: types.Message, state: FSMContext):
    symptom = message.text.strip()
    
    if symptom.startswith('/'):
        return
    
    if not symptom or len(symptom) < 2:
        await message.answer(
            "Пожалуйста, опишите ваш симптом более подробно.\n"
            "Напишите хотя бы 2-3 слова.",
            reply_markup=get_cancel_keyboard(),
        )
        return
    
    await state.update_data(symptom=symptom)
    await state.set_state(SymptomAnalysisStates.waiting_for_duration)
    
    await message.answer(
        "Понял. Как давно появился этот симптом?\n\n"
        "Выберите один из вариантов ниже или напишите свой ответ:",
        reply_markup=get_duration_keyboard(),
    )


@router.message(SymptomAnalysisStates.waiting_for_symptom)
async def process_symptom_invalid(message: types.Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, опишите ваш симптом текстом.\n"
        "Если передумали, нажмите ❌ Отмена",
        reply_markup=get_cancel_keyboard(),
    )


# ==================== ПОЛУЧЕНИЕ ДЛИТЕЛЬНОСТИ ====================

@router.message(SymptomAnalysisStates.waiting_for_duration, F.text)
async def process_duration(message: types.Message, state: FSMContext):
    duration = message.text.strip()
    
    if duration.startswith('/'):
        return
    
    if not duration or len(duration) < 1:
        await message.answer(
            "Пожалуйста, напишите или выберите вариант длительности.",
            reply_markup=get_duration_keyboard(),
        )
        return
    
    await state.update_data(duration=duration)
    await state.set_state(SymptomAnalysisStates.waiting_for_intensity)
    
    await message.answer(
        "Насколько сильно вы ощущаете этот симптом по шкале от 1 до 10?\n\n"
        "1 - очень слабо\n"
        "10 - очень сильно\n\n"
        "Напишите число от 1 до 10:",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(SymptomAnalysisStates.waiting_for_duration)
async def process_duration_invalid(message: types.Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, напишите или выберите вариант длительности.",
        reply_markup=get_duration_keyboard(),
    )


# ==================== ПОЛУЧЕНИЕ ИНТЕНСИВНОСТИ ====================

@router.message(SymptomAnalysisStates.waiting_for_intensity, F.text)
async def process_intensity(message: types.Message, state: FSMContext):
    intensity_text = message.text.strip()
    
    if intensity_text.startswith('/'):
        return
    
    try:
        intensity = int(intensity_text)
    except ValueError:
        await message.answer(
            "Пожалуйста, укажите число от 1 до 10.\nНапример: 7",
            reply_markup=get_cancel_keyboard(),
        )
        return
    
    if intensity < 1 or intensity > 10:
        await message.answer(
            f"Пожалуйста, укажите число от 1 до 10.\n\nВы ввели: {intensity}",
            reply_markup=get_cancel_keyboard(),
        )
        return
    
    await state.update_data(intensity=intensity)
    await state.set_state(SymptomAnalysisStates.waiting_for_context)
    
    await message.answer(
        "Есть ли обстоятельства, при которых симптом усиливается или уменьшается?\n\n"
        "Например:\n"
        "• Стресс\n"
        "• Работа\n"
        "• Сон\n"
        "• Физическая нагрузка\n"
        "• Питание\n\n"
        "Опишите подробнее:",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(SymptomAnalysisStates.waiting_for_intensity)
async def process_intensity_invalid(message: types.Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, укажите число от 1 до 10.\nНапример: 7",
        reply_markup=get_cancel_keyboard(),
    )


# ==================== ПОЛУЧЕНИЕ КОНТЕКСТА И ВЫЗОВ AI ====================

@router.message(SymptomAnalysisStates.waiting_for_context, F.text)
async def process_context(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обработка ввода контекста и вызов AI анализа."""
    context = message.text.strip()
    
    if context.startswith('/'):
        return
    
    if not context or len(context) < 2:
        await message.answer(
            "Пожалуйста, опишите контекст более подробно.\n"
            "Напишите хотя бы 2-3 слова.",
            reply_markup=get_cancel_keyboard(),
        )
        return
    
    await state.update_data(context=context)
    
    data = await state.get_data()
    
    symptom = data.get("symptom", "Не указано")
    duration = data.get("duration", "Не указано")
    intensity = data.get("intensity", 0)
    context_desc = data.get("context", "Не указано")
    telegram_id = message.from_user.id
    
    # ==================== SAFETY ПРОВЕРКА ПЕРЕД AI ====================
    safety_result = safety_service.check_context(
        symptom=symptom,
        duration=duration,
        intensity=intensity,
        context=context_desc
    )
    
    # Если CRITICAL — останавливаем AI
    if safety_result.level == SafetyLevel.CRITICAL:
        await message.answer(
            safety_result.warning or "⚠️ Обнаружены симптомы, требующие медицинского внимания.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()
        logger.info(f"Safety critical: {safety_result.reason}, user={telegram_id}")
        return
    
    # ==================== НОВАЯ ПРОВЕРКА ЛИМИТА AI-АНАЛИЗОВ ====================
    access_service = AccessService(db_session)
    can_use, limit_message = await access_service.check_and_increment_analysis(telegram_id)
    
    if not can_use:
        await message.answer(
            limit_message,
            reply_markup=get_pro_locked_keyboard(),
            parse_mode="HTML",
        )
        return
    # ========================================================================
    
    # Если WARNING — сохраняем предупреждение для финального ответа
    safety_warning = None
    if safety_result.level == SafetyLevel.WARNING:
        safety_warning = safety_result.warning
        await state.update_data(safety_warning=safety_warning)
    
    loading_message = await message.answer(
        "🧠 Анализирую ваш симптом...\n\n"
        "Это может занять несколько секунд.\n"
        "Пожалуйста, подождите.",
        reply_markup=get_cancel_keyboard(),
    )
    
    try:
        result = await ai_service.analyze_and_save(
            telegram_id=telegram_id,
            symptom=symptom,
            duration=duration,
            intensity=intensity,
            context=context_desc,
            db_session=db_session,
        )
        
        await loading_message.delete()
        
        if result["success"]:
            analysis = result["analysis"]
            
            # ==================== УВЕЛИЧИВАЕМ СЧЁТЧИК ИСПОЛЬЗОВАНИЯ ====================
            usage_service = UsageService(db_session)
            await usage_service.increment_analysis(telegram_id)
            # ========================================================================
            
            # ==================== SAFETY ПРОВЕРКА ПОСЛЕ AI ====================
            safety_output = safety_service.check_output(analysis.summary)
            
            # Сохраняем данные для уточнений в FSM
            await state.update_data(
                analysis=analysis.summary,
                analysis_id=result.get("analysis_id"),
                user_id=result.get("user_id"),
                clarifications_count=0,
                is_clarification_mode=True,
            )
            
            # Форматируем для Telegram
            result_text = format_analysis_for_telegram(analysis)
            
            # Добавляем предупреждение если есть
            if safety_warning:
                result_text += f"\n\n---\n\n{safety_warning}"
            
            if safety_output.level == SafetyLevel.WARNING and safety_output.warning:
                result_text += f"\n\n---\n\n{safety_output.warning}"
            
            save_status = "✅ Сохранено в историю" if result.get("saved") else "⚠️ Не сохранено в историю"
            result_text += f"\n\n{save_status}"
            
            keyboard = get_clarification_keyboard(
                questions_asked=0,
                max_questions=MAX_CLARIFICATIONS,
            )
            
            await message.answer(
                result_text,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
            
            logger.info(f"User completed analysis: telegram_id={telegram_id}")
            
        else:
            await state.clear()
            await message.answer(
                f"😔 Извините, не удалось выполнить анализ.\n\n"
                f"Ошибка: {result.get('error', 'Неизвестная ошибка')}\n\n"
                "Попробуйте позже.",
                reply_markup=get_main_menu_keyboard(),
            )
            
    except Exception as e:
        await loading_message.delete()
        await state.clear()
        logger.error(f"Unexpected error in symptom analysis: {e}")
        await message.answer(
            "😔 Произошла техническая ошибка.\n\n"
            "Попробуйте ещё раз через несколько секунд.",
            reply_markup=get_main_menu_keyboard(),
        )


@router.message(SymptomAnalysisStates.waiting_for_context)
async def process_context_invalid(message: types.Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, опишите контекст вашего симптома.\n"
        "Например: усиливается при стрессе",
        reply_markup=get_cancel_keyboard(),
    )


# ==================== УТОЧНЯЮЩИЕ ВОПРОСЫ ====================

@router.callback_query(F.data == "ask_clarification")
async def ask_clarification(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    clarifications_count = data.get("clarifications_count", 0)
    
    if clarifications_count >= MAX_CLARIFICATIONS:
        await callback.message.answer(
            "⚠️ Вы уже задали максимальное количество вопросов (3).\n"
            "Нажмите ✅ Закончить, чтобы завершить.",
            reply_markup=get_main_menu_keyboard(),
        )
        return
    
    await state.set_state(SymptomAnalysisStates.waiting_for_clarification)
    await state.update_data(is_clarification_mode=True)
    
    remaining = MAX_CLARIFICATIONS - clarifications_count
    
    await callback.message.answer(
        f"❓ Задайте ваш вопрос (осталось {remaining}):\n\n"
        "Напишите всё, что хотите уточнить по поводу анализа.\n"
        "Например: 'Что делать, если боль усиливается?'",
        reply_markup=get_question_keyboard(),
    )


@router.message(SymptomAnalysisStates.waiting_for_clarification, F.text)
async def process_clarification(
    message: types.Message,
    state: FSMContext,
    db_session: AsyncSession,
):
    question = message.text.strip()
    
    if question.startswith('/'):
        return
    
    if not question or len(question) < 3:
        await message.answer(
            "Пожалуйста, задайте более конкретный вопрос.",
            reply_markup=get_question_keyboard(),
        )
        return
    
    data = await state.get_data()
    
    symptom = data.get("symptom", "Не указано")
    duration = data.get("duration", "Не указано")
    intensity = data.get("intensity", 0)
    context = data.get("context", "Не указано")
    previous_analysis = data.get("analysis", "")
    analysis_id = data.get("analysis_id")
    telegram_id = message.from_user.id
    clarifications_count = data.get("clarifications_count", 0)
    
    # ==================== SAFETY ПРОВЕРКА УТОЧНЕНИЯ ====================
    safety_result = safety_service.check_input(question)
    
    if safety_result.level == SafetyLevel.CRITICAL:
        await message.answer(
            safety_result.warning or "⚠️ Обнаружены симптомы, требующие медицинского внимания.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()
        logger.info(f"Safety critical in clarification: {safety_result.reason}, user={telegram_id}")
        return
    
    if clarifications_count >= MAX_CLARIFICATIONS:
        await message.answer(
            "⚠️ Вы уже задали максимальное количество вопросов.\n"
            "Нажмите ✅ Закончить.",
            reply_markup=get_main_menu_keyboard(),
        )
        return
    
    loading_message = await message.answer(
        "🧠 Думаю над ответом...\n\nПожалуйста, подождите.",
        reply_markup=get_question_keyboard(),
    )
    
    try:
        result = await ai_service.clarify_symptom(
            symptom=symptom,
            duration=duration,
            intensity=intensity,
            context=context,
            previous_analysis=previous_analysis,
            question=question,
            analysis_id=analysis_id,
            telegram_id=telegram_id,
            db_session=db_session,
        )
        
        await loading_message.delete()
        
        if result["success"]:
            answer = result.get("answer", "Не удалось получить ответ")
            
            if hasattr(answer, 'summary'):
                answer = answer.summary
            elif not isinstance(answer, str):
                answer = str(answer)
            
            # ==================== SAFETY ПРОВЕРКА ОТВЕТА AI ====================
            safety_output = safety_service.check_output(answer)
            
            if safety_output.level == SafetyLevel.CRITICAL:
                await message.answer(
                    safety_output.warning or "⚠️ Не удалось безопасно сформировать ответ.",
                    reply_markup=get_main_menu_keyboard(),
                )
                await state.clear()
                logger.info(f"Safety critical in AI output: {safety_output.reason}, user={telegram_id}")
                return
            
            clarifications_count += 1
            
            await state.update_data(
                clarifications_count=clarifications_count,
            )
            
            save_status = "✅ Сохранено в историю" if result.get("saved") else "⚠️ Не сохранено"
            
            result_text = (
                f"❓ Ваш вопрос:\n{question}\n\n"
                f"📝 Ответ:\n{answer}\n\n"
            )
            
            if safety_output.level == SafetyLevel.WARNING and safety_output.warning:
                result_text += f"\n---\n\n{safety_output.warning}\n\n"
            
            result_text += (
                "━━━━━━━━━━━━━━━━━━━\n"
                f"💡 Задано вопросов: {clarifications_count}/{MAX_CLARIFICATIONS}\n"
                f"{save_status}\n"
                "Нажмите кнопку ниже для продолжения."
            )
            
            keyboard = get_clarification_keyboard(
                questions_asked=clarifications_count,
                max_questions=MAX_CLARIFICATIONS,
            )
            
            await message.answer(
                result_text,
                reply_markup=keyboard,
            )
            
            logger.info(
                f"Clarification processed: user={message.from_user.id}, "
                f"count={clarifications_count}"
            )
            
        else:
            await message.answer(
                f"😔 Извините, не удалось ответить на вопрос.\n\n"
                f"Ошибка: {result.get('error', 'Неизвестная ошибка')}\n\n"
                "Попробуйте переформулировать вопрос.",
                reply_markup=get_question_keyboard(),
            )
            
    except Exception as e:
        await loading_message.delete()
        logger.error(f"Unexpected error in clarification: {e}")
        await message.answer(
            "😔 Произошла техническая ошибка.\n\n"
            "Попробуйте ещё раз.",
            reply_markup=get_main_menu_keyboard(),
        )


@router.message(SymptomAnalysisStates.waiting_for_clarification)
async def process_clarification_invalid(message: types.Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, задайте вопрос текстом.\n"
        "Нажмите ❌ Отмена, чтобы выйти.",
        reply_markup=get_question_keyboard(),
    )


@router.callback_query(F.data == "finish_clarification")
async def finish_clarification(callback: CallbackQuery, state: FSMContext):
    """Завершение режима уточнений."""
    await callback.answer("Анализ завершён")
    
    await state.clear()
    
    # Создаем inline-кнопки для завершения
    finish_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🧠 Новый анализ",
                callback_data="new_analysis"
            )],
            [InlineKeyboardButton(
                text="📋 История",
                callback_data="history_back"
            )],
            [InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="back_to_menu"
            )]
        ]
    )
    
    await callback.message.edit_text(
        "✅ Анализ завершён.\n\n"
        "Спасибо за использование бота! 🙏\n\n"
        "Вы можете выбрать действие ниже:",
        reply_markup=finish_keyboard,
    )
    
    logger.info(f"User finished clarification: telegram_id={callback.from_user.id}")


@router.callback_query(F.data == "new_analysis")
async def new_analysis(callback: CallbackQuery, state: FSMContext):
    """Начать новый анализ."""
    await callback.answer("Начинаем новый анализ")
    await state.clear()
    
    await callback.message.delete()
    
    # Создаем фейковое сообщение для переиспользования
    class FakeMessage:
        def __init__(self, user_id):
            self.from_user = type('obj', (object,), {'id': user_id})
    
    fake_message = FakeMessage(callback.from_user.id)
    await start_symptom_analysis(fake_message, state)


# ==================== ИСПРАВЛЕНО: передаём callback, а не callback.message ====================

@router.callback_query(F.data == "history_back")
async def go_to_history(callback: CallbackQuery, state: FSMContext):
    """Переход к истории."""
    await callback.answer()
    await state.clear()
    
    from app.bot.handlers.history import show_history
    await show_history(callback, db_session=None)  # ← ИСПРАВЛЕНО: передаём callback


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )