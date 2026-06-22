from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

class NotificationBase(BaseModel):
    message: str

class NotificationCreate(NotificationBase):
    user_id: Optional[int] = None

class NotificationUpdate(NotificationBase):
    status: Optional[bool] = True

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    status: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)