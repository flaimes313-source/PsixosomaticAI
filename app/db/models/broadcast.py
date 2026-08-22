"""
Модель для рассылок.
"""
from sqlalchemy import Column, Integer, BigInteger, Text, String, DateTime, Boolean  # ← ДОБАВЛЕН BigInteger
from sqlalchemy.sql import func

from app.db.base import Base


class Broadcast(Base):
    """Рассылка для пользователей."""
    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    
    # Опционально: ссылка на картинку
    image_url = Column(String(500), nullable=True)
    
    # Статус
    is_sent = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Кто создал
    created_by = Column(BigInteger, nullable=False)  # Telegram ID админа
    
    # Количество отправленных
    recipients_count = Column(Integer, default=0, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Broadcast id={self.id} title={self.title} is_sent={self.is_sent}>"