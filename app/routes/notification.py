from fastapi import status, APIRouter
from fastapi.params import Depends

from ..models.user import User
from ..schemas.notification import NotificationCreate, NotificationResponse
from ..services.notification import NotificationService
from ..utils.dependencies import get_current_user, get_notification_service

router = APIRouter()

@router.post('/create-notfications', response_model=NotificationCreate, status_code=status.HTTP_201_CREATED)
async def create_notifications(notification_data: NotificationCreate,
                               company_id: int,
                               receiver_ids: list[int],
                               current_user: User = Depends(get_current_user),
                               service: NotificationService = Depends(get_notification_service)):
    return await service.create_notifications(notification_data, current_user,receiver_ids, company_id)

@router.get('/{notification_id}/get', response_model=NotificationResponse)
async def get_notification_by_id(notification_id: int,
                                 service: NotificationService = Depends(get_notification_service)):
    return await service.get_notification_by_id(notification_id)

@router.get('/{user_id}/get-notifications', response_model=list)
async def get_users_notifications(current_user: User = Depends(get_current_user),
                                  service: NotificationService = Depends(get_notification_service)):
    return await service.get_users_notifications(current_user)

@router.patch('{notification_id}/change-status', response_model=bool)
async def change_notification_status(notification_id: int,
                                     current_user: User = Depends(get_current_user),
                                     service: NotificationService = Depends(get_notification_service)):
    return await service.change_notification_status(notification_id, current_user)