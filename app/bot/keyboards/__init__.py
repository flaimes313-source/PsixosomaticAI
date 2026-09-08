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
    get_dynamics_cancel_keyboard,
)
from .reminders import (
    get_reminders_menu_keyboard,
    get_time_preset_keyboard,
    get_days_keyboard,
    get_cancel_keyboard as get_reminder_cancel_keyboard,
)
from .pro import (
    get_pro_menu_keyboard,
    get_pro_features_keyboard,
    get_pro_payment_keyboard,
    get_pro_success_keyboard,
    get_pro_locked_keyboard,
    get_pro_menu_keyboard_with_back_to_profile,
)
from .profile import (
    get_profile_menu_keyboard,
    get_profile_back_keyboard,
)
from .support import (
    get_support_menu_keyboard,
    get_support_cancel_keyboard,
)
from .symptom_choice import (
    get_symptom_categories_keyboard,
    get_symptoms_by_category_keyboard,
    get_symptom_choice_back_keyboard,
)
from .quick_start import (
    get_quick_start_keyboard,
    get_quick_start_cancel_keyboard,
)
from .surveys import (
    get_survey_cancel_keyboard,
    get_survey_skip_keyboard,
    get_survey_finish_keyboard,
    get_morning_question_1_keyboard,
    get_morning_question_2_keyboard,
    get_morning_question_3_keyboard,
    get_morning_question_4_keyboard,
    get_morning_question_5_keyboard,
    get_morning_reminder_keyboard,
    get_day_question_1_keyboard,
    get_day_question_2_keyboard,
    get_day_question_3_keyboard,
    get_day_finish_keyboard,
    get_evening_question_1_keyboard,
    get_evening_question_2_keyboard,
    get_evening_question_3_keyboard,
    get_evening_question_4_keyboard,
    get_evening_question_5_keyboard,
    get_evening_reminder_keyboard,
)