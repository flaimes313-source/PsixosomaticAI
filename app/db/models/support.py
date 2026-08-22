"""
Модель для обращений в поддержку.
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

from app.db.base import Base


class SupportRequest(Base):
    """Обращение пользователя в поддержку."""
    __tablename__ = "support_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram ID
    
    # Тема и текст
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    
    # Статус
    is_answered = Column(Boolean, default=False, nullable=False)
    is_closed = Column(Boolean, default=False, nullable=False)
    
    # Ответы
    answer = Column(Text, nullable=True)
    answered_by = Column(BigInteger, nullable=True)  # Telegram ID админа
    answered_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self):
        return f"<SupportRequest id={self.id} user_id={self.user_id} is_answered={self.is_answered}>"