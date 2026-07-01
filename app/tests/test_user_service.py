import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserSignUp, UserUpdate
from app.services.user import UserService
from ..models.quiz import Quiz, Question
from app.models.user import User
from fastapi import HTTPException, status

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=AsyncSession)

@pytest.fixture
def user_service(mock_db_session):
    return UserService(db_session=mock_db_session)


@pytest.mark.asyncio
async def test_create_user_success(user_service, mocker):
    user_data = UserSignUp(username="test_user", email="test@example.com", password="secure_password")

    mock_hash = mocker.patch("app.services.auth.AuthService.hash_password", return_value="hashed_str")

    fake_user = MagicMock()
    fake_user.username = "test_user"
    fake_user.email = "test@example.com"
    fake_user.hashed_password = "hashed_str"

    mocker.patch("app.services.user.User", return_value=fake_user)

    mock_add_to_db = mocker.patch("app.services.user.add_to_db", new_callable=AsyncMock)

    result = await user_service.create_user(user_data)

    assert result.username == "test_user"
    assert result.email == "test@example.com"
    assert result.hashed_password == "hashed_str"
    mock_add_to_db.assert_called_once_with(fake_user, user_service.db)


async def test_get_all_users_success(user_service, mocker):
    fake_user_1 = MagicMock()
    fake_user_2 = MagicMock()
    mock_users_list = [fake_user_1, fake_user_2]

    mock_async_func = AsyncMock(return_value=mock_users_list)

    mock_pagination = mocker.patch("app.services.user.get_with_pagination", new_callable=lambda: mock_async_func)

    result = await user_service.get_all_users(limit=10, offset=0)

    assert result == mock_users_list
    assert len(result) == 2

    mock_pagination.assert_called_once()


async def test_get_user_by_id_success(user_service, mocker):
    fake_user = MagicMock()
    fake_user.id = 1

    mock_filter = mocker.patch("app.services.user.get_by_filter", new_callable=AsyncMock, return_value=fake_user)

    result = await user_service.get_user_by_id(user_id=1)

    assert result == fake_user
    mock_filter.assert_called_once()


async def test_get_user_by_id_not_found(user_service, mocker):
    mocker.patch("app.services.user.get_by_filter", new_callable=AsyncMock, return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await user_service.get_user_by_id(user_id=999)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "User not found"


async def test_user_update_success(user_service, mocker):
    class FakeUser:
        def __init__(self):
            self.username = "Old Name"
            self.description = "Old Desc"

    fake_user = FakeUser()

    mocker.patch.object(user_service, "get_user_by_id", new_callable=AsyncMock, return_value=fake_user)

    mock_refresh = mocker.patch("app.services.user.refresh_data_in_db", new_callable=AsyncMock)

    update_data_mock = MagicMock()

    update_data_mock.model_dump.return_value = {
        "username": "New Name",
        "description": "New Desc"
    }

    result = await user_service.user_update(user_id=1, update_data=update_data_mock)

    assert result.username == "New Name"
    assert result.description == "New Desc"

    update_data_mock.model_dump.assert_called_once_with(exclude_unset=True)
    mock_refresh.assert_called_once_with(fake_user, user_service.db)


async def test_delete_user_success(user_service, mocker):
    fake_user = MagicMock()

    mocker.patch.object(user_service, "get_user_by_id", new_callable=AsyncMock, return_value=fake_user)
    mock_delete_from_db = mocker.patch("app.services.user.delete_from_db", new_callable=AsyncMock)

    result = await user_service.delete_user(user_id=1)

    assert result is True
    mock_delete_from_db.assert_called_once_with(fake_user, user_service.db)


async def test_get_user_by_email_success(user_service, mocker):
    fake_user = MagicMock()
    fake_user.email = "test@example.com"

    mock_filter = mocker.patch("app.services.user.get_by_filter", new_callable=AsyncMock, return_value=fake_user)

    result = await user_service.get_user_by_email(email="test@example.com")

    assert result == fake_user
    mock_filter.assert_called_once()


async def test_get_user_by_email_not_found(user_service, mocker):
    mocker.patch("app.services.user.get_by_filter", new_callable=AsyncMock, return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await user_service.get_user_by_email(email="wrong@example.com")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "User not found or incorrect e-mail"