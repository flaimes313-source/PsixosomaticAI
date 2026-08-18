"""
Схемы для дневниковых записей.
"""
from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from typing import Optional


class DiaryEntryCreate(BaseModel):
    """Схема для создания дневниковой записи."""
    symptom: str = Field(..., max_length=500, description="Симптом")
    symptom_intensity: int = Field(..., ge=0, le=10, description="Интенсивность симптома (0-10)")
    mood: int = Field(..., ge=1, le=5, description="Настроение (1-5)")
    stress: int = Field(..., ge=0, le=10, description="Уровень стресса (0-10)")
    sleep_hours: float = Field(..., ge=0, le=24, description="Часы сна (0-24)")
    context: Optional[str] = Field(None, max_length=2000, description="Контекст")
    note: Optional[str] = Field(None, max_length=2000, description="Дополнительная заметка")
    analysis_id: Optional[int] = Field(None, description="ID связанного анализа")
    entry_date: Optional[date] = Field(None, description="Дата записи")

    @validator('symptom')
    def validate_symptom(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Симптом должен содержать хотя бы 2 символа')
        return v.strip()

    @validator('sleep_hours')
    def validate_sleep(cls, v):
        if v < 0 or v > 24:
            raise ValueError('Количество часов сна должно быть от 0 до 24')
        return v


class DiaryEntryResponse(BaseModel):
    """Схема для ответа с дневниковой записью."""
    id: int
    user_id: int
    analysis_id: Optional[int]
    symptom: str
    symptom_intensity: int
    mood: int
    stress: int
    sleep_hours: float
    context: Optional[str]
    note: Optional[str]
    entry_date: date
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiaryEntryUpdate(BaseModel):
    """Схема для обновления дневниковой записи."""
    symptom: Optional[str] = Field(None, max_length=500)
    symptom_intensity: Optional[int] = Field(None, ge=0, le=10)
    mood: Optional[int] = Field(None, ge=1, le=5)
    stress: Optional[int] = Field(None, ge=0, le=10)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    context: Optional[str] = Field(None, max_length=2000)
    note: Optional[str] = Field(None, max_length=2000)


class DiaryDatesResponse(BaseModel):
    """Схема для списка дат с записями."""
    date: date
    count: int