"""
Модель для белого списка PRO (бесплатный доступ).
"""
from sqlalchemy import Column, Integer, BigInteger, DateTime
from sqlalchemy.sql import func

from app.db.base import Base


class ProWhitelist(Base):
    """Белый список пользователей с бесплатным PRO."""
    __tablename__ = "pro_whitelist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)  # Telegram ID
    added_by = Column(BigInteger, nullable=False)  # Кто добавил (ваш Telegram ID)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ProWhitelist user_id={self.user_id} added_by={self.added_by}>"