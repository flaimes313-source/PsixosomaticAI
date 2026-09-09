"""
Инициализация обработчиков.
"""
from . import start
from . import menu
from . import how_it_works as how_it_works_handler
from . import describe_state as describe_state_handler
from . import dynamics as dynamics_handler
from . import diary as diary_handler
from . import profile as profile_handler
from . import pro as pro_handler
from . import support as support_handler
from . import admin as admin_handler
from . import settings as settings_handler
from . import reminders as reminders_handler
from . import privacy as privacy_handler
from . import help as help_handler
from . import history as history_handler
from . import cancel as cancel_handler

# Опросники
from .surveys import morning as morning_survey_handler
from .surveys import day as day_survey_handler
from .surveys import evening as evening_survey_handler