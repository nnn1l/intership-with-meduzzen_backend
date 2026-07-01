import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, status

from app.schemas.notification import NotificationCreate
from app.services.notification import NotificationService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def notification_service(mock_db_session):
    return NotificationService(db_session=mock_db_session)


async def test_create_notifications_success(notification_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.notification.CompanyService", return_value=mock_company_service, create=True)

    mocker.patch("app.services.notification.check_admin_role", new_callable=AsyncMock, return_value=False, create=True)
    mocker.patch("app.services.notification.filter_company_members", new_callable=AsyncMock, return_value=[2, 3],
                 create=True)

    mock_notifications_list = [MagicMock(), MagicMock()]
    mock_send = mocker.patch("app.services.notification.send_notifications", new_callable=AsyncMock,
                             return_value=mock_notifications_list)

    notification_data = NotificationCreate(title="Test", message="Hello")
    result = await notification_service.create_notifications(
        notification_data=notification_data,
        current_user=current_user,
        receiver_ids=[2, 3],
        company_id=10)

    assert result == mock_notifications_list
    mock_send.assert_called_once_with(notification_data, [2, 3], notification_service.db)


async def test_create_notifications_forbidden(notification_service, mocker):
    current_user = MagicMock()
    current_user.id = 5

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.notification.CompanyService", return_value=mock_company_service, create=True)

    mocker.patch("app.services.notification.check_admin_role", new_callable=AsyncMock, return_value=False, create=True)
    mocker.patch("app.services.notification.filter_company_members", new_callable=AsyncMock, return_value=[],
                 create=True)
    mocker.patch("app.services.notification.send_notifications", new_callable=AsyncMock, create=True)

    notification_data = NotificationCreate(title="Test", message="Hello")

    with pytest.raises(HTTPException) as exc_info:
        await notification_service.create_notifications(
            notification_data=notification_data,
            current_user=current_user,
            receiver_ids=[2, 3],
            company_id=10)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


async def test_get_notification_by_id_success(notification_service, mocker):
    fake_notification = MagicMock()
    mock_get = mocker.patch("app.services.notification.get_by_filter", new_callable=AsyncMock,
                            return_value=fake_notification)

    result = await notification_service.get_notification_by_id(notification_id=100)

    assert result == fake_notification
    mock_get.assert_called_once()


async def test_get_notification_by_id_not_found(notification_service, mocker):
    mocker.patch("app.services.notification.get_by_filter", new_callable=AsyncMock, return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await notification_service.get_notification_by_id(notification_id=999)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_get_users_notifications_success(notification_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    mock_notification_1 = MagicMock()
    mock_notification_2 = MagicMock()
    expected_list = [mock_notification_1, mock_notification_2]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = expected_list

    mocker.patch("app.services.notification.get_by_filter", new_callable=AsyncMock, return_value=mock_result)

    result = await notification_service.get_users_notifications(current_user=current_user)

    assert result == expected_list
    assert len(result) == 2


async def test_change_notification_status_success(notification_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    class FakeNotification:
        def __init__(self):
            self.id = 100
            self.user_id = 1
            self.status = False

    fake_notification = FakeNotification()
    mocker.patch.object(notification_service, "get_notification_by_id", new_callable=AsyncMock,
                        return_value=fake_notification)
    mock_refresh = mocker.patch("app.services.notification.refresh_data_in_db", new_callable=AsyncMock)

    result = await notification_service.change_notification_status(notification_id=100, current_user=current_user)

    assert result.status is True
    mock_refresh.assert_called_once_with(fake_notification, notification_service.db)


async def test_change_notification_status_already_read(notification_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    class FakeNotification:
        def __init__(self):
            self.id = 100
            self.user_id = 1
            self.status = True

    fake_notification = FakeNotification()
    mocker.patch.object(notification_service, "get_notification_by_id", new_callable=AsyncMock,
                        return_value=fake_notification)

    with pytest.raises(HTTPException) as exc_info:
        await notification_service.change_notification_status(notification_id=100, current_user=current_user)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST