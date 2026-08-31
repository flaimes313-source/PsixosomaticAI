"""
Enum для фич и ограничений + числовые лимиты FREE/PRO.
"""
from enum import Enum, auto
from typing import Optional


class Feature(str, Enum):
    """Фичи, доступ к которым можно ограничить."""
    # Анализ симптомов
    SYMPTOM_ANALYSIS = "symptom_analysis"
    SYMPTOM_CLARIFICATION = "symptom_clarification"  # Уточняющие вопросы
    
    # Дневник
    DIARY_ENTRY = "diary_entry"
    DIARY_UNLIMITED = "diary_unlimited"
    
    # Динамика
    DYNAMICS_7_DAYS = "dynamics_7_days"
    DYNAMICS_30_DAYS = "dynamics_30_days"
    DYNAMICS_90_DAYS = "dynamics_90_days"
    DYNAMICS_ADVANCED = "dynamics_advanced"
    
    # Напоминания
    REMINDERS = "reminders"
    REMINDERS_ADVANCED = "reminders_advanced"  # Расширенные настройки


class AccessLevel(str, Enum):
    """Уровни доступа."""
    FREE = "free"
    PRO = "pro"


# Права доступа для фич
FEATURE_ACCESS = {
    # FREE фичи
    Feature.SYMPTOM_ANALYSIS: AccessLevel.FREE,
    Feature.SYMPTOM_CLARIFICATION: AccessLevel.FREE,
    Feature.DIARY_ENTRY: AccessLevel.FREE,
    Feature.DYNAMICS_7_DAYS: AccessLevel.FREE,
    Feature.REMINDERS: AccessLevel.FREE,
    
    # PRO фичи
    Feature.DIARY_UNLIMITED: AccessLevel.PRO,
    Feature.DYNAMICS_30_DAYS: AccessLevel.PRO,
    Feature.DYNAMICS_90_DAYS: AccessLevel.PRO,
    Feature.DYNAMICS_ADVANCED: AccessLevel.PRO,
    Feature.REMINDERS_ADVANCED: AccessLevel.PRO,
}


def get_feature_access(feature: Feature) -> AccessLevel:
    """Получить уровень доступа для фичи."""
    return FEATURE_ACCESS.get(feature, AccessLevel.FREE)


# ==================== НОВЫЕ ЧИСЛОВЫЕ ЛИМИТЫ ====================
# Эти лимиты используются для счётчиков в AccessService

class FreeLimits:
    """Числовые лимиты для FREE-пользователей."""
    
    # "Что я чувствую в теле" — 1 анализ в месяц
    BODY_ANALYSES_PER_MONTH: int = 1
    
    # "Помогите разобраться" — 1 сессия в месяц
    HELP_SESSIONS_PER_MONTH: int = 1
    
    # Дневник — всего 10 записей (не сбрасывается ежемесячно)
    DIARY_ENTRIES_TOTAL: int = 10
    
    # Уточняющие вопросы после анализа — 3 штуки
    CLARIFICATIONS_PER_BODY: int = 3


class ProLimits:
    """Числовые лимиты для PRO-пользователей (None = безлимит)."""
    
    BODY_ANALYSES_PER_MONTH: Optional[int] = None
    HELP_SESSIONS_PER_MONTH: Optional[int] = None
    DIARY_ENTRIES_TOTAL: Optional[int] = None
    CLARIFICATIONS_PER_BODY: Optional[int] = None