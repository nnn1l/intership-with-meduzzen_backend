from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from ..logger import logger
from ..models import Notification
from ..schemas.notification import NotificationCreate


async def send_notifications(notification_data: NotificationCreate, valid_ids: list[int], db: AsyncSession) -> list[Notification]:
    try:
        notifications = [Notification(
            user_id=receiver_id,
            message=notification_data.message
        ) for receiver_id in valid_ids]

        db.add_all(notifications)
        await db.commit()
        for notification in notifications: await db.refresh(notification)
        return notifications

    except Exception as e:
        await db.rollback()
        logger.error('Error appeared during creating a notification')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during notification creation: {str(e)}")