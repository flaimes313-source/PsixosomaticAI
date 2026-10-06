"""
Модель дневника.
ВНИМАНИЕ: модель DiaryEntry устарела.
Актуальная модель — DiaryEvent (app.db.models.diary_event).
Оставлена для обратной совместимости, но БЕЗ связи с User.
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
    from app.db.models.analysis import Analysis


class DiaryEntry(Base):
    """Модель записи в дневнике (УСТАРЕЛО)."""
    __tablename__ = "diary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # ==================== ОСНОВНЫЕ ПОЛЯ ====================
    symptom: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    symptom_intensity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=5)
    mood: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=3)
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
    morning_q1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    morning_q2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    morning_q3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    morning_q4: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    morning_q5: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    morning_clarification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    day_q1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    day_q2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    day_q3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

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

    # ==================== «ОПИСАТЬ СОСТОЯНИЕ» ====================
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ==================== УТОЧНЕНИЯ ====================
    clarification_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clarification_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ==================== СВЯЗИ ====================
    # ВАЖНО: связь с User УБРАНА (back_populates="diary_entries" удалён),
    # потому что в User больше нет relationship diary_entries.
    # Связь с Analysis оставлена.
    analysis: Mapped[Optional["Analysis"]] = relationship(
        "Analysis",
        foreign_keys=[analysis_id],
    )

    def __repr__(self) -> str:
        return f"<DiaryEntry(id={self.id}, user_id={self.user_id}, date={self.entry_date})>"