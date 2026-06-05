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
from ..services.user import UserService


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

    service = UserService(mock_db_session)

    user = await service.get_current_user_by_token(token)

    assert user is not None
    assert user.email == test_email
    assert user.username == "viktoriia_dev"