from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status, HTTPException

from ..models.company import company_members
from ..models.notification import Notification
from ..models.user import User
from ..schemas.notification import NotificationCreate
from ..logger import logger

if TYPE_CHECKING:
    from .company import CompanyService
    from ..utils.dependencies import check_admin_role

class NotificationService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    # CREATING NOTIFICATION(S) FOR 1+ USERS
    async def create_notifications(self, notification_data: NotificationCreate, current_user: User, receiver_ids: list[int], company_id: int) -> list[Notification]:
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id) # ensures that company exists & gets company

        admin_role = await check_admin_role(company_id, current_user.id)

        if not admin_role and company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You aren't an admin/owner of this company to create notifications")

        user_in_company = select(company_members.c.user_id).where(
            company_members.c.user_id.in_(receiver_ids),
            company_members.c.company_id == company_id)
        result = await self.db.execute(user_in_company)
        valid_ids = [row[0] for row in result.all()]
        if not valid_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't send notifications to user that isn't a member of your company")

        logger.info(f"Attempting to create notifications to user(s) with ID {valid_ids}...")
        try:
            notifications = [Notification(
                user_id = receiver_id,
                message = notification_data.message
            ) for receiver_id in valid_ids]

            self.db.add_all(notifications)
            await self.db.commit()
            for notification in notifications: await self.db.refresh(notification)
            return notifications

        except Exception as e:
            await self.db.rollback()
            logger.error('Error appeared during creating a notification')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Internal server error during notification creation: {str(e)}")


    # GET NOTIFICATION BY ID
    async def get_notification_by_id(self, notification_id: int) -> Notification:
        query = select(Notification).where(Notification.id == notification_id)
        result = await self.db.execute(query)
        notification = result.scalar_one_or_none()

        if not notification:
            logger.error(f"Notification with ID {notification_id} wasn't found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification with this ID doesn't exist")

        return notification


    # GET USER'S NOTIFICATION LIST
    async def get_users_notifications(self, current_user: User) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == current_user.id)
        result = await self.db.execute(query)

        return list(result.scalars().all())


    # CHANGE NOTIFICATION STATUS -> TRUE
    async def change_notification_status(self, notification_id: int, current_user: User) -> bool:
        notification = await self.get_notification_by_id(notification_id) # ensures that notification exists & return notification

        if notification.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You can't change notification status if you're not a receiver of it")

        if notification.status:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't change notification read status back to False")

        notification.status = True
        return True
