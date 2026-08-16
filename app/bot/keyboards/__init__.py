"""
Инициализация клавиатур.
"""
from .main import get_main_menu_keyboard, get_back_menu_keyboard
from .symptom import (
    get_duration_keyboard,
    get_cancel_keyboard,
    get_cancel_inline_keyboard,
    get_analysis_complete_keyboard,
    get_clarification_keyboard,
    get_question_keyboard,
)
from .stress import (
    get_stress_question_1_keyboard,
    get_stress_question_2_keyboard,
    get_stress_question_3_keyboard,
    get_stress_question_4_keyboard,
    get_stress_question_5_keyboard,
    get_stress_cancel_keyboard,
    get_stress_result_keyboard,
)