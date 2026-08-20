"""
Модель уточняющего вопроса в базе данных.
"""
from sqlalchemy import (
    Integer,
    BigInteger,  # ← ДОБАВЛЕНО
    Text,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.analysis import Analysis


class Clarification(Base):
    """Модель уточняющего вопроса пользователя"""
    __tablename__ = "clarifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 🔥 ИСПРАВЛЕНО: Integer → BigInteger
    analysis_id: Mapped[int] = mapped_column(
        BigInteger,  # ← ИЗМЕНЕНО
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # 🔥 ИСПРАВЛЕНО: Integer → BigInteger
    user_id: Mapped[int] = mapped_column(
        BigInteger,  # ← ИЗМЕНЕНО
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    analysis: Mapped["Analysis"] = relationship(
        "Analysis",
        back_populates="clarifications"
    )

    def __repr__(self) -> str:
        return f"<Clarification(id={self.id}, analysis_id={self.analysis_id})>"