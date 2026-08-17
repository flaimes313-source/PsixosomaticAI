"""
Состояния FSM для сценария "Разобрать симптом".
"""
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """
    Состояния для регистрации пользователя.
    """
    waiting_for_timezone = State()


class SymptomAnalysisStates(StatesGroup):
    """
    Состояния для анализа симптома.
    """
    waiting_for_symptom = State()
    waiting_for_duration = State()
    waiting_for_intensity = State()
    waiting_for_context = State()
    waiting_for_clarification = State()


class StressCheckStates(StatesGroup):
    """
    Состояния для сценария "Проверить стресс".
    """
    waiting_for_question_1 = State()
    waiting_for_question_2 = State()
    waiting_for_question_3 = State()
    waiting_for_question_4 = State()
    waiting_for_question_5 = State()