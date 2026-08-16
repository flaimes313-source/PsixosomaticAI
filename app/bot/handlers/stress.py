"""
Обработчики для сценария "Проверить стресс".
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import StressCheckStates
from app.bot.keyboards.stress import (
    get_stress_question_1_keyboard,
    get_stress_question_2_keyboard,
    get_stress_question_3_keyboard,
    get_stress_question_4_keyboard,
    get_stress_question_5_keyboard,
    get_stress_cancel_keyboard,
    get_stress_result_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


# ==================== ОТМЕНА ====================

@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cancel_stress_check(message: types.Message, state: FSMContext):
    """Отмена стресс-теста."""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer(
            "У вас нет активного диалога.",
            reply_markup=get_main_menu_keyboard(),
        )
        return
    
    await state.clear()
    await message.answer(
        "❌ Стресс-тест отменён.\n\nВозвращаемся в главное меню.",
        reply_markup=get_main_menu_keyboard(),
    )
    logger.info(f"Stress test cancelled: telegram_id={message.from_user.id}")


# ==================== ЗАПУСК СТРЕСС-ТЕСТА ====================

@router.message(F.text == "🧠 Проверить стресс")
async def start_stress_check(message: types.Message, state: FSMContext):
    """Запуск сценария 'Проверить стресс'."""
    logger.info(f"User started stress check: telegram_id={message.from_user.id}")
    
    await state.clear()
    await state.set_state(StressCheckStates.waiting_for_question_1)
    
    await message.answer(
        "🧠 Давайте проверим ваш уровень стресса.\n\n"
        "Ответьте на 5 простых вопросов.\n"
        "Это займёт не больше минуты.\n\n"
        "Вопрос 1/5:\n"
        "Как часто вы чувствуете стресс?",
        reply_markup=get_stress_question_1_keyboard(),
    )


# ==================== ВОПРОС 1 ====================

@router.message(StressCheckStates.waiting_for_question_1, F.text)
async def process_question_1(message: types.Message, state: FSMContext):
    """Обработка ответа на вопрос 1."""
    answer = message.text.strip()
    
    if answer.startswith('/'):
        return
    
    valid_answers = ["Почти никогда", "Иногда", "Часто", "Постоянно"]
    if answer not in valid_answers:
        await message.answer(
            "Пожалуйста, выберите один из вариантов ниже.",
            reply_markup=get_stress_question_1_keyboard(),
        )
        return
    
    # Сохраняем ответ
    await state.update_data(answer_1=answer)
    await state.set_state(StressCheckStates.waiting_for_question_2)
    
    await message.answer(
        "Вопрос 2/5:\n"
        "Как вы обычно справляетесь со стрессом?",
        reply_markup=get_stress_question_2_keyboard(),
    )


@router.message(StressCheckStates.waiting_for_question_1)
async def process_question_1_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод в вопросе 1."""
    await message.answer(
        "Пожалуйста, выберите один из вариантов ниже.",
        reply_markup=get_stress_question_1_keyboard(),
    )


# ==================== ВОПРОС 2 ====================

@router.message(StressCheckStates.waiting_for_question_2, F.text)
async def process_question_2(message: types.Message, state: FSMContext):
    """Обработка ответа на вопрос 2."""
    answer = message.text.strip()
    
    if answer.startswith('/'):
        return
    
    valid_answers = ["Отдыхаю", "Занимаюсь спортом", "Ем сладкое", "Сложно справляюсь"]
    if answer not in valid_answers:
        await message.answer(
            "Пожалуйста, выберите один из вариантов ниже.",
            reply_markup=get_stress_question_2_keyboard(),
        )
        return
    
    await state.update_data(answer_2=answer)
    await state.set_state(StressCheckStates.waiting_for_question_3)
    
    await message.answer(
        "Вопрос 3/5:\n"
        "Есть ли у вас физические проявления стресса?\n"
        "Выберите один или напишите свой вариант:",
        reply_markup=get_stress_question_3_keyboard(),
    )


@router.message(StressCheckStates.waiting_for_question_2)
async def process_question_2_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод в вопросе 2."""
    await message.answer(
        "Пожалуйста, выберите один из вариантов ниже.",
        reply_markup=get_stress_question_2_keyboard(),
    )


# ==================== ВОПРОС 3 ====================

@router.message(StressCheckStates.waiting_for_question_3, F.text)
async def process_question_3(message: types.Message, state: FSMContext):
    """Обработка ответа на вопрос 3."""
    answer = message.text.strip()
    
    if answer.startswith('/'):
        return
    
    if not answer or len(answer) < 2:
        await message.answer(
            "Пожалуйста, опишите подробнее или выберите вариант.",
            reply_markup=get_stress_question_3_keyboard(),
        )
        return
    
    await state.update_data(answer_3=answer)
    await state.set_state(StressCheckStates.waiting_for_question_4)
    
    await message.answer(
        "Вопрос 4/5:\n"
        "Как вы отдыхаете?",
        reply_markup=get_stress_question_4_keyboard(),
    )


@router.message(StressCheckStates.waiting_for_question_3)
async def process_question_3_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод в вопросе 3."""
    await message.answer(
        "Пожалуйста, выберите один из вариантов или напишите подробнее.",
        reply_markup=get_stress_question_3_keyboard(),
    )


# ==================== ВОПРОС 4 ====================

@router.message(StressCheckStates.waiting_for_question_4, F.text)
async def process_question_4(message: types.Message, state: FSMContext):
    """Обработка ответа на вопрос 4."""
    answer = message.text.strip()
    
    if answer.startswith('/'):
        return
    
    valid_answers = ["Сплю 8 часов", "Читаю/смотрю кино", "Мало отдыхаю", "Не знаю как отдыхать"]
    if answer not in valid_answers:
        await message.answer(
            "Пожалуйста, выберите один из вариантов ниже.",
            reply_markup=get_stress_question_4_keyboard(),
        )
        return
    
    await state.update_data(answer_4=answer)
    await state.set_state(StressCheckStates.waiting_for_question_5)
    
    await message.answer(
        "Вопрос 5/5:\n"
        "Оцените ваш уровень стресса по шкале от 1 до 10.\n"
        "1 - совсем нет стресса\n"
        "10 - максимальный стресс",
        reply_markup=get_stress_question_5_keyboard(),
    )


@router.message(StressCheckStates.waiting_for_question_4)
async def process_question_4_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод в вопросе 4."""
    await message.answer(
        "Пожалуйста, выберите один из вариантов.",
        reply_markup=get_stress_question_4_keyboard(),
    )


# ==================== ВОПРОС 5 ====================

@router.message(StressCheckStates.waiting_for_question_5, F.text)
async def process_question_5(message: types.Message, state: FSMContext):
    """Обработка ответа на вопрос 5 (оценка стресса)."""
    answer = message.text.strip()
    
    if answer.startswith('/'):
        return
    
    # Проверяем что ввели число от 1 до 10
    try:
        stress_level = int(answer)
        if stress_level < 1 or stress_level > 10:
            raise ValueError
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число от 1 до 10.",
            reply_markup=get_stress_question_5_keyboard(),
        )
        return
    
    await state.update_data(answer_5=str(stress_level))
    
    # Получаем все ответы
    data = await state.get_data()
    
    answers = {
        "answer_1": data.get("answer_1", "Не указано"),
        "answer_2": data.get("answer_2", "Не указано"),
        "answer_3": data.get("answer_3", "Не указано"),
        "answer_4": data.get("answer_4", "Не указано"),
        "answer_5": stress_level,
    }
    
    # Анализируем уровень стресса
    stress_result = analyze_stress_level(answers)
    
    # Формируем результат
    result_text = format_stress_result(answers, stress_result)
    
    await state.clear()
    
    await message.answer(
        result_text,
        reply_markup=get_stress_result_keyboard(),
    )
    
    logger.info(f"Stress check completed: telegram_id={message.from_user.id}, level={stress_result['level']}")


@router.message(StressCheckStates.waiting_for_question_5)
async def process_question_5_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод в вопросе 5."""
    await message.answer(
        "Пожалуйста, введите число от 1 до 10.",
        reply_markup=get_stress_question_5_keyboard(),
    )


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def analyze_stress_level(answers: dict) -> dict:
    """
    Анализирует уровень стресса на основе ответов.
    """
    stress_level = 0
    recommendations = []
    
    # Вопрос 1: Частота стресса
    q1 = answers.get("answer_1", "")
    if q1 == "Почти никогда":
        stress_level += 1
        recommendations.append("✅ У вас хорошая стрессоустойчивость.")
    elif q1 == "Иногда":
        stress_level += 2
        recommendations.append("🟡 Иногда стресс возникает, но вы с ним справляетесь.")
    elif q1 == "Часто":
        stress_level += 3
        recommendations.append("🔴 Стресс часто сопровождает вашу жизнь.")
    elif q1 == "Постоянно":
        stress_level += 4
        recommendations.append("🔴 Похоже, стресс стал вашим постоянным спутником.")
    
    # Вопрос 2: Способы борьбы со стрессом
    q2 = answers.get("answer_2", "")
    if q2 == "Отдыхаю":
        stress_level += 1
        recommendations.append("✅ Вы умеете отдыхать - это важно!")
    elif q2 == "Занимаюсь спортом":
        stress_level += 1
        recommendations.append("✅ Спорт помогает снижать стресс!")
    elif q2 == "Ем сладкое":
        stress_level += 2
        recommendations.append("🟡 Сладкое даёт временное облегчение, но не решает причину.")
    elif q2 == "Сложно справляюсь":
        stress_level += 3
        recommendations.append("🔴 Возможно, вам нужна помощь в управлении стрессом.")
    
    # Вопрос 3: Физические проявления
    q3 = answers.get("answer_3", "")
    if q3 == "Нет":
        stress_level += 1
        recommendations.append("✅ Хорошо, что нет физических симптомов.")
    elif q3 in ["Головная боль", "Бессонница", "Усталость", "Раздражительность"]:
        stress_level += 2
        recommendations.append(f"🔴 {q3} - частый симптом стресса.")
    else:
        stress_level += 2
        recommendations.append(f"🔴 {q3} - может быть связано со стрессом.")
    
    # Вопрос 4: Отдых
    q4 = answers.get("answer_4", "")
    if q4 == "Сплю 8 часов":
        stress_level += 1
        recommendations.append("✅ Отличный режим сна!")
    elif q4 == "Читаю/смотрю кино":
        stress_level += 2
        recommendations.append("🟡 Пассивный отдых полезен, но нужен и активный.")
    elif q4 == "Мало отдыхаю":
        stress_level += 3
        recommendations.append("🔴 Недостаток отдыха усиливает стресс.")
    elif q4 == "Не знаю как отдыхать":
        stress_level += 3
        recommendations.append("🔴 Попробуйте найти свой способ отдыха.")
    
    # Вопрос 5: Оценка стресса
    q5 = answers.get("answer_5", 0)
    if q5 <= 3:
        stress_level += 1
        recommendations.append("✅ Вы оцениваете свой стресс как низкий.")
    elif q5 <= 6:
        stress_level += 2
        recommendations.append("🟡 Уровень стресса средний.")
    else:
        stress_level += 3
        recommendations.append("🔴 Высокий уровень стресса требует внимания.")
    
    # Определяем итоговый уровень
    if stress_level <= 8:
        level = "Низкий"
        emoji = "🟢"
        color = "зелёный"
    elif stress_level <= 14:
        level = "Средний"
        emoji = "🟡"
        color = "жёлтый"
    else:
        level = "Высокий"
        emoji = "🔴"
        color = "красный"
    
    # Формируем общие рекомендации
    general_recommendations = []
    if level == "Высокий":
        general_recommendations = [
            "Рекомендуется обратиться к психологу",
            "Уделите больше времени отдыху",
            "Занимайтесь дыхательными практиками",
        ]
    elif level == "Средний":
        general_recommendations = [
            "Практикуйте медитацию или дыхательные упражнения",
            "Добавьте физическую активность",
            "Следите за режимом сна",
        ]
    else:
        general_recommendations = [
            "Продолжайте заботиться о себе",
            "Поддерживайте здоровый образ жизни",
        ]
    
    return {
        "level": level,
        "emoji": emoji,
        "color": color,
        "score": stress_level,
        "recommendations": recommendations,
        "general_recommendations": general_recommendations,
    }


def format_stress_result(answers: dict, result: dict) -> str:
    """
    Форматирует результат стресс-теста.
    """
    text = (
        f"🧠 Результат стресс-теста:\n\n"
        f"{result['emoji']} Уровень стресса: {result['level']}\n"
        f"📊 Баллы: {result['score']} из 24\n\n"
        "📝 Ваши ответы:\n"
        f"1. Частота стресса: {answers.get('answer_1', 'Не указано')}\n"
        f"2. Способы борьбы: {answers.get('answer_2', 'Не указано')}\n"
        f"3. Физические проявления: {answers.get('answer_3', 'Не указано')}\n"
        f"4. Отдых: {answers.get('answer_4', 'Не указано')}\n"
        f"5. Оценка стресса: {answers.get('answer_5', 'Не указано')}/10\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💡 Рекомендации:\n"
    )
    
    # Добавляем рекомендации
    for rec in result["recommendations"]:
        text += f"  {rec}\n"
    
    text += "\n📌 Общие рекомендации:\n"
    for rec in result["general_recommendations"]:
        text += f"  • {rec}\n"
    
    text += (
        "\n━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Это не медицинский диагноз.\n"
        "Если вы чувствуете, что стресс усиливается, обратитесь к специалисту."
    )
    
    return text