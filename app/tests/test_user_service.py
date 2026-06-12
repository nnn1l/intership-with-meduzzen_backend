from datetime import datetime, timezone, timedelta

import pytest
import jwt
from fastapi import status
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock
from ..main import app
from ..database import engine
from ..models.user import User
from ..schemas.config import settings
from ..services.auth import AuthService
from ..utils.dependencies import validate_profile_owner


@pytest.fixture
def mock_db_session():  # imitation of db
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
async def async_client(mock_db_session):
    app.dependency_overrides[engine] = lambda: mock_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest.fixture
def mock_auth_user_1():
    async def override_validate_profile_owner(user_id: int):
        if user_id != 1:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="You're able to manage only your own profile"
            )
        return MOCK_USER_1

    app.dependency_overrides[validate_profile_owner] = override_validate_profile_owner
    yield
    app.dependency_overrides.clear()

MOCK_USER_1 = User(id=1, username="alex", email="alex@example.com")

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_signup_endpoint_success(async_client, mock_db_session):

    payload = {
        "username": "viktoriia_dev",
        "email": "viktoriia@example.com",
        "password": "securepassword123"
    }

    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    response = await async_client.post("/api/v1/users/", json=payload)

    assert response.status_code == status.HTTP_201_CREATED

    response_data = response.json()

    assert response_data["username"] == "viktoriia_dev"
    assert response_data["email"] == "viktoriia@example.com"


@pytest.mark.asyncio
async def test_get_current_user_by_token(mock_db_session):
    test_email = "viktoriia@example.com"

    mock_user = User(
        id=1,
        username="viktoriia_dev",
        email=test_email,
        hashed_password="some_hashed_password"
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session.execute.return_value = mock_result

    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    payload = {
        "email": test_email,
        "exp": expire
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    service = AuthService(mock_db_session)

    user = await service.get_current_user_by_token(token)

    assert user is not None
    assert user.email == test_email
    assert user.username == "viktoriia_dev"


async def test_update_own_profile_success(mock_auth_user_1):  # noqa
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {"name": "New name"}
        response = await ac.patch("/users/1", json=payload)

        assert response.status_code == status.HTTP_200_OK


async def test_update_someone_profile_forbidden(mock_auth_user_1):  # noqa
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {"name": "Hacker attack"}
        response = await ac.patch("/users/2", json=payload)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "You're able to manage only your own profile"


async def test_delete_someone_profile_forbidden(mock_auth_user_1):  # noqa
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.delete("/users/2")

        assert response.status_code == status.HTTP_403_FORBIDDEN