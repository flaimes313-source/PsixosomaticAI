"""
Состояния FSM для сценария "Разобрать симптом".
"""
from aiogram.fsm.state import State, StatesGroup


class SymptomAnalysisStates(StatesGroup):
    """
    Состояния для анализа симптома.
    """
    waiting_for_symptom = State()
    waiting_for_duration = State()
    waiting_for_intensity = State()
    waiting_for_context = State()
    waiting_for_clarification = State()  # НОВОЕ: ожидание уточняющего вопроса