"""
Модель анализа симптома в базе данных.
"""
from sqlalchemy import (
    Integer,
    BigInteger,  # ← ДОБАВЛЕНО
    String,
    Text,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.clarification import Clarification
    from app.db.models.diary import DiaryEntry
    from app.db.models.user import User


class Analysis(Base):
    """Модель анализа симптома"""
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 🔥 ИСПРАВЛЕНО: Integer → BigInteger
    user_id: Mapped[int] = mapped_column(
        BigInteger,  # ← ИЗМЕНЕНО
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    symptom: Mapped[str] = mapped_column(String(500), nullable=False)
    duration: Mapped[str] = mapped_column(String(100), nullable=False)
    intensity: Mapped[int] = mapped_column(Integer, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    analysis: Mapped[str] = mapped_column(Text, nullable=False)
    
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
    user: Mapped["User"] = relationship("User", back_populates="analyses")
    
    clarifications: Mapped[List["Clarification"]] = relationship(
        "Clarification",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="Clarification.created_at",
    )
    
    diary_entries: Mapped[List["DiaryEntry"]] = relationship(
        "DiaryEntry",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="DiaryEntry.created_at",
    )

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, user_id={self.user_id}, symptom={self.symptom[:30]})>"