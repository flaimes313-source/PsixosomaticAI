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
    from app.db.models.diary_event import DiaryEvent


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

    # ==================== СЧЁТЧИКИ (СТАРЫЕ) ====================
    body_analysis_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    body_analysis_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    help_analysis_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    help_analysis_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    diary_entries_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ==================== НОВОЕ: TRIAL И FREE-ДИАЛОГ ====================
    # trial_used: TRUE, если пользователь уже запускал 3-дневный пробный PRO.
    # Повторно trial не даётся.
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # trial_started_at: когда начался пробный PRO.
    trial_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # trial_ends_at: когда закончится пробный PRO (started_at + 3 дня).
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # free_dialog_used: TRUE, если пользователь уже использовал
    # свой единственный бесплатный диалог «Описать состояние» после trial.
    free_dialog_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # free_dialog_questions_count: сколько уточняющих вопросов Сома задала
    # в текущем бесплатном диалоге (максимум 3).
    free_dialog_questions_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # ==================== СВЯЗИ ====================
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

    diary_events: Mapped[List["DiaryEvent"]] = relationship(
        "DiaryEvent",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="DiaryEvent.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"