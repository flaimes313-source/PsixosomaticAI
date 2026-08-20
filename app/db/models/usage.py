"""
Модель использования (счётчики для FREE).
"""
from sqlalchemy import Column, Integer, BigInteger, DateTime, Date
from sqlalchemy.sql import func

from app.db.base import Base


class UserUsage(Base):
    """Счётчики использования для пользователя."""
    __tablename__ = "user_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, unique=True, index=True)  # Telegram ID
    
    # Счётчики за текущий период (месяц)
    analyses_count = Column(Integer, default=0, nullable=False)  # AI-анализы
    dynamics_count = Column(Integer, default=0, nullable=False)  # Запуски динамики
    
    # Период (месяц)
    period_start = Column(Date, server_default=func.current_date(), nullable=False)
    period_end = Column(Date, nullable=True)  # NULL = бессрочно
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self):
        return f"<UserUsage user_id={self.user_id} analyses={self.analyses_count} dynamics={self.dynamics_count}>"