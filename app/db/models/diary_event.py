"""
Модель центрального события дневника.
Единое хранилище всех событий пользователя.
"""
from sqlalchemy import (
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING, Any, Dict

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class DiaryEvent(Base):
    """
    Единая модель события в дневнике пользователя.
    
    Хранит ВСЕ события:
    - Описать состояние (user_message, ai_response)
    - Опросы (утро/день/вечер)
    - Анализы
    - Уточняющие вопросы
    - Микродействия
    - Отчёты динамики
    """
    __tablename__ = "diary_events"

    # ==================== ОСНОВНЫЕ ПОЛЯ ====================
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # ==================== ТИП СОБЫТИЯ ====================
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # ==================== ИСТОЧНИК ====================
    source: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    
    # ==================== СЕССИЯ ====================
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    
    # ==================== РОЛЬ ====================
    role: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    # ==================== СОДЕРЖИМОЕ ====================
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ==================== СТРУКТУРИРОВАННЫЕ ДАННЫЕ ====================
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    
    # ==================== ДАТЫ ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    event_date: Mapped[date] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    
    # ==================== СВЯЗИ ====================
    analysis_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    parent_event_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    # ==================== СВЯЗИ ORM ====================
    user: Mapped["User"] = relationship("User", back_populates="diary_events")

    # ==================== ИНДЕКСЫ ====================
    __table_args__ = (
        Index("idx_diary_events_user_created", "user_id", "created_at"),
        Index("idx_diary_events_user_date", "user_id", "event_date"),
        Index("idx_diary_events_session", "session_id"),
        Index("idx_diary_events_type", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<DiaryEvent(id={self.id}, user_id={self.user_id}, type={self.event_type})>"