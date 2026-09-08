"""
Схемы для динамики.
"""
from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional, Any


class DynamicsStatistics(BaseModel):
    """Статистика для анализа динамики."""
    period_days: int
    entries_count: int
    start_date: date
    end_date: date
    
    average_mood: Optional[float] = None
    min_mood: Optional[float] = None
    max_mood: Optional[float] = None
    
    average_stress: Optional[float] = None
    min_stress: Optional[float] = None
    max_stress: Optional[float] = None
    
    average_sleep: Optional[float] = None
    min_sleep: Optional[float] = None
    max_sleep: Optional[float] = None
    
    top_symptoms: List[Any] = []
    relevant_contexts: List[str] = []


class DynamicsReport(BaseModel):
    """Отчёт динамики от AI."""
    summary: str
    main_patterns: List[str]
    possible_connections: List[str]
    positive_changes: List[str]
    areas_to_watch: List[str]
    next_steps: List[str]
    medical_note: str