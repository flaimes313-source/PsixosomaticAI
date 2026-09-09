"""
Инициализация моделей базы данных.
"""
from app.db.models.user import User
from app.db.models.diary_event import DiaryEvent
from app.db.models.analysis import Analysis
from app.db.models.clarification import Clarification
from app.db.models.subscription import Subscription
from app.db.models.whitelist import ProWhitelist
from app.db.models.support import SupportRequest
from app.db.models.broadcast import Broadcast
from app.db.models.reminder import ReminderSettings
from app.db.models.payment import Payment
from app.db.models.help_dialog import HelpDialogMessage

# Обновляем User с связью с DiaryEvent
# Добавляем в User модель:
# diary_events: Mapped[List["DiaryEvent"]] = relationship(
#     "DiaryEvent",
#     back_populates="user",
#     cascade="all, delete-orphan",
#     order_by="DiaryEvent.created_at.desc()",
# )