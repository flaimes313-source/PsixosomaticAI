"""
Модель дневника.
"""
from sqlalchemy import (
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    Float,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.analysis import Analysis


class DiaryEntry(Base):
    """Модель записи в дневнике."""
    __tablename__ = "diary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    
    # Основные поля
    entry_date: Mapped[date] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # ==================== НОВЫЕ ПОЛЯ ====================
    # Тип записи: "survey_morning", "survey_day", "survey_evening", "describe_state", "analysis", "clarification"
    entry_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
        comment="Тип записи: survey_morning, survey_day, survey_evening, describe_state, analysis, clarification"
    )
    
    # Связь с анализом (если есть)
    analysis_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    
    # ==================== ПОЛЯ ДЛЯ ОПРОСОВ ====================
    # Утренний опрос
    morning_q1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Как проснулся?
    morning_q2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Что в теле?
    morning_q3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Настроение?
    morning_q4: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Мысли?
    morning_q5: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Сон?
    morning_clarification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Уточнение
    
    # Дневной опрос
    day_q1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Как сейчас?
    day_q2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Что изменилось?
    day_q3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Что повлияло?
    
    # Вечерний опрос
    evening_q1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Как себя чувствуешь?
    evening_q2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Что повлияло?
    evening_q3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Что дало энергию?
    evening_q4: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Что забрало силы?
    evening_q5: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Еда/сон/движение?
    evening_clarification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Уточнение
    
    # ==================== ПОЛЯ ДЛЯ РАЗБОРА ====================
    # Разбор (гипотезы, выводы, микродействия)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Краткое резюме
    analysis_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Полный анализ
    micro_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Микродействие
    medical_warning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Медицинское предупреждение
    
    # ==================== ПОЛЯ ДЛЯ «ОПИСАТЬ СОСТОЯНИЕ» ====================
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Описание пользователя
    ai_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Ответ AI
    
    # ==================== УТОЧНЯЮЩИЕ ВОПРОСЫ ====================
    clarification_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Вопрос
    clarification_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Ответ

    # Связи
    user: Mapped["User"] = relationship(
        "User",
        back_populates="diary_entries",
    )
    analysis: Mapped[Optional["Analysis"]] = relationship(
        "Analysis",
        foreign_keys=[analysis_id],
        backref="diary_entries",
    )

    def __repr__(self) -> str:
        return f"<DiaryEntry(id={self.id}, user_id={self.user_id}, date={self.entry_date})>"