"""
Состояния FSM для сценария "Разобрать симптом".
"""
from aiogram.fsm.state import State, StatesGroup


class SymptomAnalysisStates(StatesGroup):
    """
    Состояния для анализа симптома.
    
    Последовательность:
    1. waiting_for_symptom - ожидание описания симптома
    2. waiting_for_duration - ожидание ответа о длительности
    3. waiting_for_intensity - ожидание интенсивности (1-10)
    4. waiting_for_context - ожидание дополнительного контекста
    5. waiting_for_clarification - ожидание уточняющего вопроса
    """
    waiting_for_symptom = State()
    waiting_for_duration = State()
    waiting_for_intensity = State()
    waiting_for_context = State()
    waiting_for_clarification = State()


class StressCheckStates(StatesGroup):
    """
    Состояния для сценария "Проверить стресс".
    
    Последовательность:
    1. waiting_for_question_1 - Как часто чувствуете стресс?
    2. waiting_for_question_2 - Как вы справляетесь со стрессом?
    3. waiting_for_question_3 - Есть ли физические проявления?
    4. waiting_for_question_4 - Как вы отдыхаете?
    5. waiting_for_question_5 - Оцените уровень стресса (1-10)
    """
    waiting_for_question_1 = State()
    waiting_for_question_2 = State()
    waiting_for_question_3 = State()
    waiting_for_question_4 = State()
    waiting_for_question_5 = State()