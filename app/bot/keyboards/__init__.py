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
from .timezone import (
    get_timezone_keyboard,
    get_timezone_skip_keyboard,
)
from .settings import (
    get_settings_keyboard,
    get_confirm_delete_keyboard,
)
from .diary import (
    get_diary_menu_keyboard,
    get_intensity_keyboard,
    get_mood_keyboard,
    get_stress_keyboard,
    get_sleep_keyboard,
    get_skip_keyboard,
    get_cancel_keyboard as get_diary_cancel_keyboard,
    get_confirm_keyboard,
    get_entry_detail_keyboard,
    get_confirm_delete_keyboard as get_diary_confirm_delete_keyboard,
    get_date_navigation_keyboard,
)
from .dynamics import (
    get_dynamics_period_keyboard,
    get_dynamics_actions_keyboard,
)
from .reminders import (  # ← ПРАВИЛЬНО
    get_reminders_menu_keyboard,
    get_time_preset_keyboard,
    get_days_keyboard,
    get_cancel_keyboard as get_reminder_cancel_keyboard,
)
from .pro import (
    get_pro_menu_keyboard,
    get_pro_features_keyboard,
    get_pro_upgrade_keyboard,
    get_pro_locked_keyboard,
)