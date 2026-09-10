"""
Инициализация обработчиков.
"""
from . import start
from . import menu
from . import help
from . import privacy
from . import cancel
from . import history
from . import settings as settings_handler
from . import dynamics as dynamics_handler
from . import reminders as reminders_handler
from . import pro as pro_handler
from . import admin as admin_handler
from . import support as support_handler
from . import profile as profile_handler
from . import how_it_works as how_it_works_handler
from . import describe_state as describe_state_handler
from . import diary as diary_handler
from . import survey_launcher

# Опросники
from .surveys import morning as morning_survey_handler
from .surveys import day as day_survey_handler
from .surveys import evening as evening_survey_handler