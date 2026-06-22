from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..models import Base

class Notification(Base):
    __tablename__ = 'notifications'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, default=False) # read status
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc))

