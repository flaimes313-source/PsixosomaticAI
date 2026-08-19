"""
Pydantic-схемы для анализа динамики.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class PeriodType(str, Enum):
    """Типы периодов для анализа."""
    DAYS_7 = "7_days"
    DAYS_14 = "14_days"
    DAYS_30 = "30_days"
    DAYS_90 = "90_days"


class SymptomStats(BaseModel):
    """Статистика по одному симптому."""
    symptom: str = Field(..., description="Название симптома")
    count: int = Field(..., description="Количество упоминаний")
    average_intensity: float = Field(..., description="Средняя интенсивность")
    min_intensity: int = Field(..., description="Минимальная интенсивность")
    max_intensity: int = Field(..., description="Максимальная интенсивность")


class PeriodStats(BaseModel):
    """Статистика за один период (для сравнения)."""
    start_date: datetime
    end_date: datetime
    entries_count: int
    average_intensity: float
    average_stress: float
    average_mood: float
    average_sleep: float


class DynamicsStatistics(BaseModel):
    """Полная статистика для анализа динамики."""
    # Общие данные
    period_type: PeriodType
    period_days: int
    entries_count: int
    start_date: datetime
    end_date: datetime
    
    # Общая статистика
    average_intensity: float
    min_intensity: int
    max_intensity: int
    
    average_stress: float
    min_stress: int
    max_stress: int
    
    average_mood: float
    min_mood: int
    max_mood: int
    
    average_sleep: float
    min_sleep: float
    max_sleep: float
    
    # Топ симптомов
    top_symptoms: List[SymptomStats] = Field(default_factory=list)
    
    # Сравнение первой и последней части периода
    first_period: Optional[PeriodStats] = None
    last_period: Optional[PeriodStats] = None
    
    # Сравнения (корреляции)
    stress_symptom_comparison: Optional[Dict[str, Any]] = None
    sleep_symptom_comparison: Optional[Dict[str, Any]] = None
    mood_symptom_comparison: Optional[Dict[str, Any]] = None
    
    # Контексты
    relevant_contexts: List[str] = Field(default_factory=list)
    frequent_contexts: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Предыдущие анализы (кратко)
    previous_analyses_summary: Optional[str] = None


class DynamicsReport(BaseModel):
    """Ответ от YandexGPT с анализом динамики."""
    summary: str = Field(..., description="Общая картина за период")
    main_patterns: List[str] = Field(default_factory=list, description="Основные закономерности")
    possible_connections: List[str] = Field(default_factory=list, description="Возможные связи")
    positive_changes: List[str] = Field(default_factory=list, description="Положительные изменения")
    areas_to_watch: List[str] = Field(default_factory=list, description="На что обратить внимание")
    next_steps: List[str] = Field(default_factory=list, description="Что можно попробовать")
    medical_note: str = Field(default="", description="Медицинское предостережение")