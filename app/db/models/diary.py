"""
Модель дневниковой записи в базе данных.
"""
from sqlalchemy import (
    Integer,
    BigInteger,  # ← ДОБАВЛЕНО
    String,
    Text,
    Float,
    DateTime,
    Date,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.analysis import Analysis
    from app.db.models.user import User


class DiaryEntry(Base):
    """Модель дневниковой записи пользователя"""
    __tablename__ = "diary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 🔥 ИСПРАВЛЕНО: Integer → BigInteger
    user_id: Mapped[int] = mapped_column(
        BigInteger,  # ← ИЗМЕНЕНО
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    analysis_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Данные записи
    symptom: Mapped[str] = mapped_column(Text, nullable=False)
    symptom_intensity: Mapped[int] = mapped_column(Integer, nullable=False)
    mood: Mapped[int] = mapped_column(Integer, nullable=False)
    stress: Mapped[int] = mapped_column(Integer, nullable=False)
    sleep_hours: Mapped[float] = mapped_column(Float, nullable=False)
    
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Дата и время
    entry_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=func.current_date(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="diary_entries")
    analysis: Mapped[Optional["Analysis"]] = relationship("Analysis", back_populates="diary_entries")

    def __repr__(self) -> str:
        return f"<DiaryEntry(id={self.id}, user_id={self.user_id}, entry_date={self.entry_date})>"