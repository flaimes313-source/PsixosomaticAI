"""
Инициализация обработчиков.
"""
from . import start, menu, help, privacy, symptom, cancel, history, stress, settings, diary
from . import dynamics as dynamics_handler   # ← ЯВНО УКАЗЫВАЕМ, что это из handlers
from . import reminders as reminders_handler  # ← И для reminders тоже