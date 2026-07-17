from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status, HTTPException

from ..models.notification import Notification
from ..models.user import User
from ..repositories.base import get_by_filter, refresh_data_in_db
from ..repositories.notification import send_notifications
from ..schemas.notification import NotificationCreate
from ..logger import logger

if TYPE_CHECKING:
    from .company import CompanyService
    from ..repositories.company import check_admin_role, filter_company_members


class NotificationService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    # CREATING NOTIFICATION(S) FOR 1+ USERS
    async def create_notifications(self, notification_data: NotificationCreate, current_user: User, receiver_ids: list[int], company_id: int) -> list[Notification]:
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id) # ensures that company exists & gets company

        admin_role = await check_admin_role(company_id, current_user.id, self.db)

        if not admin_role and company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You aren't an admin/owner of this company to create notifications")

        valid_ids = await filter_company_members(company_id, receiver_ids, self.db)
        if len(valid_ids) != len(receiver_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't send notifications to users that aren't members of your company")

        logger.info(f"Attempting to create notifications to user(s) with ID {valid_ids}...")
        return await send_notifications(notification_data, valid_ids, self.db)


    # GET NOTIFICATION BY ID
    async def get_notification_by_id(self, notification_id: int) -> Notification:
        notification = await get_by_filter(Notification, self.db, id=notification_id)

        if not notification:
            logger.error(f"Notification with ID {notification_id} wasn't found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification with this ID doesn't exist")

        return notification


    # GET USER'S NOTIFICATION LIST
    async def get_users_notifications(self, current_user: User) -> list[Notification]:
        result = await get_by_filter(Notification, self.db, user_id=current_user.id)

        return list(result.scalars().all())


    # CHANGE NOTIFICATION STATUS -> TRUE
    async def change_notification_status(self, notification_id: int, current_user: User) -> Notification:
        notification = await self.get_notification_by_id(notification_id) # ensures that notification exists & return notification

        if notification.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You can't change notification status if you're not a receiver of it")

        if notification.status:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't change notification read status back to False")

        notification.status = True
        await refresh_data_in_db(notification, self.db)
        return notification
