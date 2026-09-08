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
    ForeignKey,
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
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    
    # ==================== ОСНОВНЫЕ ПОЛЯ ====================
    symptom: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # ← СДЕЛАЛИ NULLABLE
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
    
    # ==================== ТИП ЗАПИСИ ====================
    entry_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
    )
    
    # ==================== СВЯЗЬ С АНАЛИЗОМ ====================
    analysis_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("analyses.id"),
        nullable=True,
        index=True,
    )
    
    # ==================== ПОЛЯ ДЛЯ ОПРОСОВ ====================
    # Утренний опрос
    morning_q1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    morning_q2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    morning_q3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    morning_q4: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    morning_q5: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    morning_clarification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Дневной опрос
    day_q1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    day_q2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    day_q3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Вечерний опрос
    evening_q1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    evening_q2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    evening_q3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    evening_q4: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    evening_q5: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    evening_clarification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ==================== ПОЛЯ ДЛЯ РАЗБОРА ====================
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    micro_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medical_warning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ==================== ПОЛЯ ДЛЯ «ОПИСАТЬ СОСТОЯНИЕ» ====================
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ==================== УТОЧНЯЮЩИЕ ВОПРОСЫ ====================
    clarification_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clarification_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ==================== СВЯЗИ ====================
    user: Mapped["User"] = relationship(
        "User",
        back_populates="diary_entries",
    )
    analysis: Mapped[Optional["Analysis"]] = relationship(
        "Analysis",
        foreign_keys=[analysis_id],
        back_populates="diary_entry",
    )

    def __repr__(self) -> str:
        return f"<DiaryEntry(id={self.id}, user_id={self.user_id}, date={self.entry_date})>"