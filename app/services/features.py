"""
Enum для фич и ограничений.
"""
from enum import Enum, auto


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