"""
Модель для хранения истории диалогов «Помогите разобраться».
"""
from sqlalchemy import (
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional

from app.db.base import Base


class HelpDialogMessage(Base):
    """Модель сообщения в диалоге «Помогите разобраться»."""
    __tablename__ = "help_dialog_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="Уникальный ID сессии (UUID)"
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="user или assistant"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текст сообщения"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<HelpDialogMessage(id={self.id}, session={self.session_id}, role={self.role})>"