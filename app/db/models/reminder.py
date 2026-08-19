"""
Модель для настроек напоминаний.
"""
from sqlalchemy import Column, Integer, BigInteger, Boolean, String, Time, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class ReminderSettings(Base):
    """Настройки напоминаний для пользователя."""
    __tablename__ = "reminder_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)  # Telegram ID
    
    # Основные настройки
    enabled = Column(Boolean, default=False, nullable=False)
    reminder_time = Column(Time, nullable=True)  # Локальное время (без часового пояса)
    timezone = Column(String(50), default="UTC", nullable=False)  # Europe/Moscow и т.д.
    
    # Дни недели (JSON: [0,1,2,3,4,5,6] где 0 - понедельник, 6 - воскресенье)
    # NULL или [] означает "каждый день"
    days_of_week = Column(JSON, nullable=True, default=list)
    
    # Защита от спама
    last_reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self):
        return f"<ReminderSettings user_id={self.user_id} enabled={self.enabled} time={self.reminder_time}>"