"""
Инициализация клавиатур.
"""
from .main import get_main_menu_keyboard, get_back_menu_keyboard
from .cancel import get_cancel_keyboard
from .profile import get_profile_menu_keyboard, get_profile_back_keyboard
from .support import get_support_menu_keyboard, get_support_cancel_keyboard
from .pro import (
    get_pro_menu_keyboard,
    get_pro_features_keyboard,
    get_pro_payment_keyboard,
    get_pro_success_keyboard,
    get_pro_locked_keyboard,
)
from .reminders import (
    get_reminders_menu_keyboard,
    get_time_preset_keyboard,
    get_days_keyboard,
)
from .timezone import get_timezone_keyboard, get_timezone_skip_keyboard
from .surveys import (
    get_survey_cancel_keyboard,
    get_survey_skip_keyboard,
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
from .dynamics import (
    get_dynamics_period_keyboard,
    get_dynamics_cancel_keyboard,
    get_dynamics_actions_keyboard,
)
from .admin import get_admin_menu_keyboard