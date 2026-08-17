"""
Схемы для структурированного ответа YandexGPT.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class AnalysisResult(BaseModel):
    """
    Структурированный результат анализа симптома.
    """
    summary: str = Field(
        description="Краткое резюме симптома и его возможной связи"
    )
    possible_factors: List[str] = Field(
        default_factory=list,
        description="Список возможных факторов, влияющих на симптом"
    )
    possible_patterns: List[str] = Field(
        default_factory=list,
        description="Список возможных паттернов (когда усиливается/уменьшается)"
    )
    check_question: Optional[str] = Field(
        default=None,
        description="Вопрос для самопроверки пользователя"
    )
    micro_action: Optional[str] = Field(
        default=None,
        description="Маленькое практическое действие на ближайшие дни"
    )
    things_to_observe: List[str] = Field(
        default_factory=list,
        description="Список за чем понаблюдать в ближайшие дни"
    )
    medical_warning: Optional[str] = Field(
        default=None,
        description="Медицинское предупреждение (если нужно)"
    )

    def has_medical_warning(self) -> bool:
        """Проверяет, есть ли медицинское предупреждение."""
        return self.medical_warning is not None and len(self.medical_warning) > 0