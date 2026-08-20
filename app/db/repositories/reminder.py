"""
Репозиторий для работы с настройками напоминаний.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.sql import func
from datetime import time, datetime
from typing import Optional, List, Dict, Any

from app.db.models.reminder import ReminderSettings
from app.db.models.user import User
from app.utils.logging import logger


class ReminderRepository:
    """Репозиторий для управления настройками напоминаний."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, user_id: int) -> ReminderSettings:
        """Получить настройки пользователя или создать новые."""
        result = await self.session.execute(
            select(ReminderSettings).where(ReminderSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            # 🔥 БЕРЁМ ЧАСОВОЙ ПОЯС ИЗ ТАБЛИЦЫ USERS
            user_result = await self.session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = user_result.scalar_one_or_none()
            user_timezone = user.timezone if user and user.timezone else "UTC"
            
            settings = ReminderSettings(
                user_id=user_id,
                enabled=False,
                reminder_time=None,
                timezone=user_timezone,  # ← АВТОМАТИЧЕСКИ СТАВИМ ТОТ ЖЕ, ЧТО У ПОЛЬЗОВАТЕЛЯ
                days_of_week=None,
                last_reminder_sent_at=None
            )
            self.session.add(settings)
            await self.session.commit()
            await self.session.refresh(settings)
            logger.info(f"Created reminder settings for user {user_id} with timezone {user_timezone}")
        
        return settings

    async def get_by_user_id(self, user_id: int) -> Optional[ReminderSettings]:
        """Получить настройки пользователя."""
        result = await self.session.execute(
            select(ReminderSettings).where(ReminderSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        user_id: int,
        enabled: Optional[bool] = None,
        reminder_time: Optional[time] = None,
        timezone: Optional[str] = None,
        days_of_week: Optional[List[int]] = None,
    ) -> Optional[ReminderSettings]:
        """Обновить настройки пользователя."""
        settings = await self.get_by_user_id(user_id)
        if not settings:
            settings = await self.get_or_create(user_id)
        
        if enabled is not None:
            settings.enabled = enabled
        if reminder_time is not None:
            settings.reminder_time = reminder_time
        if timezone is not None:
            settings.timezone = timezone
        if days_of_week is not None:
            settings.days_of_week = days_of_week
        
        settings.updated_at = func.now()
        await self.session.commit()
        await self.session.refresh(settings)
        
        logger.info(f"Updated reminder settings for user {user_id}")
        return settings

    async def update_last_sent(self, user_id: int) -> None:
        """Обновить время последнего отправленного напоминания."""
        await self.session.execute(
            update(ReminderSettings)
            .where(ReminderSettings.user_id == user_id)
            .values(last_reminder_sent_at=func.now())
        )
        await self.session.commit()
        logger.debug(f"Updated last_reminder_sent_at for user {user_id}")

    async def get_active_reminders(self) -> List[ReminderSettings]:
        """Получить все активные настройки (включены)."""
        result = await self.session.execute(
            select(ReminderSettings).where(ReminderSettings.enabled == True)
        )
        return result.scalars().all()

    async def delete_settings(self, user_id: int) -> bool:
        """Удалить настройки пользователя."""
        result = await self.session.execute(
            delete(ReminderSettings).where(ReminderSettings.user_id == user_id)
        )
        await self.session.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted reminder settings for user {user_id}")
        return deleted

    async def is_reminder_sent_today(self, user_id: int) -> bool:
        """Проверить, было ли отправлено напоминание сегодня."""
        settings = await self.get_by_user_id(user_id)
        if not settings or not settings.last_reminder_sent_at:
            return False
        
        # Используем timezone пользователя для определения "сегодня"
        try:
            from zoneinfo import ZoneInfo
            user_tz = ZoneInfo(settings.timezone if settings.timezone else "UTC")
            today = datetime.now(user_tz).date()
            last_sent_date = settings.last_reminder_sent_at.astimezone(user_tz).date()
            return last_sent_date == today
        except Exception:
            # Fallback: сравниваем по UTC
            today = datetime.now().date()
            last_sent_date = settings.last_reminder_sent_at.date()
            return last_sent_date == today