"""
Инициализация обработчиков.
"""
from . import start, menu, help, privacy, symptom, cancel, history, stress, settings, diary
from . import dynamics as dynamics_handler
from . import reminders as reminders_handler
from . import pro as pro_handler
from . import admin as admin_handler
from . import support as support_handler
from . import profile as profile_handler  # ← НОВОЕ
from . import how_it_works as how_it_works_handler
from . import symptom_choice as symptom_choice_handler
from . import quick_start as quick_start_handler