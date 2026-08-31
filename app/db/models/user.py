"""
Модель пользователя в базе данных.
"""
from sqlalchemy import (
    Integer,
    BigInteger,
    String,
    DateTime,
    Boolean,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.analysis import Analysis
    from app.db.models.diary import DiaryEntry


class User(Base):
    """Модель пользователя бота"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True
    )
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    consent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="UTC")

    # ==================== НОВЫЕ ПОЛЯ ДЛЯ СЧЁТЧИКОВ ====================
    # Счётчик для "Что я чувствую в теле" (месячный)
    body_analysis_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    body_analysis_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Формат: YYYY-MM
    
    # Счётчик для "Помогите разобраться" (месячный)
    help_analysis_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    help_analysis_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Формат: YYYY-MM
    
    # Счётчик для дневника (общий, не сбрасывается)
    diary_entries_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # ================================================================

    # Связи
    analyses: Mapped[List["Analysis"]] = relationship(
        "Analysis",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Analysis.created_at.desc()",
    )
    diary_entries: Mapped[List["DiaryEntry"]] = relationship(
        "DiaryEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="DiaryEntry.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"