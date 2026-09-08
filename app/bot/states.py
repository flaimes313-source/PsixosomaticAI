"""
Состояния FSM для всех сценариев бота.
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


class DiaryStates(StatesGroup):
    """
    Состояния для сценария "Дневник".
    """
    waiting_for_symptom = State()      # 1/7: Симптом
    waiting_for_intensity = State()    # 2/7: Интенсивность (0-10)
    waiting_for_mood = State()         # 3/7: Настроение (1-5)
    waiting_for_stress = State()       # 4/7: Стресс (0-10)
    waiting_for_sleep = State()        # 5/7: Сон (0-24)
    waiting_for_context = State()      # 6/7: Контекст
    waiting_for_note = State()         # 7/7: Заметка
    confirming = State()               # Предпросмотр


class DynamicsStates(StatesGroup):
    """
    Состояния для раздела "Моя динамика".
    """
    choosing_period = State()          # Выбор периода (7/14/30/90 дней)
    waiting_for_custom_period = State()  # Ожидание ввода своего периода
    viewing_report = State()           # Просмотр отчёта


class ReminderStates(StatesGroup):
    """
    Состояния для раздела "Напоминания".
    """
    waiting_for_time = State()         # Ожидание выбора времени
    waiting_for_custom_time = State()  # Ожидание ввода своего времени
    waiting_for_days = State()         # Ожидание выбора дней недели


class ProStates(StatesGroup):
    """
    Состояния для раздела PRO и оплаты.
    """
    waiting_for_payment = State()      # Ожидание подтверждения оплаты


# ==================== АДМИН-ПАНЕЛЬ ====================

class AdminStates(StatesGroup):
    """
    Состояния для админ-панели.
    """
    waiting_for_broadcast_recipients = State()  # Выбор получателей
    waiting_for_broadcast_ids = State()         # Ожидание ввода ID
    waiting_for_broadcast_text = State()        # Ожидание текста для рассылки
    waiting_for_broadcast_image = State()       # Ожидание картинки для рассылки
    waiting_for_broadcast_confirm = State()     # Подтверждение рассылки


# ==================== ПОДДЕРЖКА ====================

class SupportStates(StatesGroup):
    """
    Состояния для раздела поддержки.
    """
    waiting_for_question = State()         # Ожидание вопроса от пользователя


# ==================== ВЫБОР СИМПТОМА ====================

class SymptomChoiceStates(StatesGroup):
    """
    Состояния для выбора симптома из списка.
    """
    choosing_category = State()           # Выбор категории симптома
    choosing_symptom = State()            # Выбор конкретного симптома из категории
    waiting_for_custom_symptom = State()  # Свободный ввод симптома


# ==================== ЭКСПРЕСС-ДИАГНОСТИКА «ПОМОГИТЕ РАЗОБРАТЬСЯ» ====================

class QuickStartStates(StatesGroup):
    """
    Состояния для экспресс-диагностики "Помогите разобраться".
    """
    waiting_for_description = State()  # Ожидание описания состояния


# ==================== СВОБОДНЫЙ ДИАЛОГ «ПОМОГИТЕ РАЗОБРАТЬСЯ» ====================

class HelpDialogStates(StatesGroup):
    """
    Состояния для свободного AI-диалога «Помогите разобраться».
    """
    waiting_for_message = State()      # Ожидание сообщения от пользователя (продолжение диалога)


# ==================== СЦЕНАРИЙ «ОПИСАТЬ СОСТОЯНИЕ» ====================

class DescribeStateStates(StatesGroup):
    """
    Состояния для сценария «Описать состояние».
    """
    waiting_for_description = State()  # Ожидание первого описания
    waiting_for_continue = State()     # Продолжение диалога


# ==================== ОПРОСНИКИ (УТРО/ДЕНЬ/ВЕЧЕР) ====================

class MorningSurveyStates(StatesGroup):
    """
    Состояния для утреннего опроса.
    """
    waiting_for_question_1 = State()  # Как проснулся?
    waiting_for_question_2 = State()  # Что чувствуешь в теле?
    waiting_for_question_3 = State()  # Какое настроение?
    waiting_for_question_4 = State()  # Что в мыслях?
    waiting_for_question_5 = State()  # Как спал?
    waiting_for_clarification = State()  # Уточняющие вопросы
    waiting_for_reminder = State()  # Интерактив (напоминание)


class DaySurveyStates(StatesGroup):
    """
    Состояния для дневного опроса.
    """
    waiting_for_question_1 = State()  # Как ты сейчас?
    waiting_for_question_2 = State()  # Что изменилось с утра?
    waiting_for_question_3 = State()  # Что повлияло?
    waiting_for_finish = State()      # Завершение


class EveningSurveyStates(StatesGroup):
    """
    Состояния для вечернего опроса.
    """
    waiting_for_question_1 = State()  # Как себя чувствуешь?
    waiting_for_question_2 = State()  # Что повлияло на состояние?
    waiting_for_question_3 = State()  # Что дало энергию?
    waiting_for_question_4 = State()  # Что забрало силы?
    waiting_for_question_5 = State()  # Как с едой, сном, движением?
    waiting_for_clarification = State()  # Уточняющие вопросы
    waiting_for_reminder = State()  # Интерактив (напоминание)