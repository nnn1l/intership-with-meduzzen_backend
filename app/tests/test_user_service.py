import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock
from ..main import app
from ..database import engine

@pytest.fixture
def mock_db_session():  # imitation of db
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
async def async_client(mock_db_session):
    app.dependency_overrides[engine] = lambda: mock_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
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

    assert response.status_code == 201

    response_data = response.json()
    assert "user" in response_data
    assert response_data["user"]["username"] == "viktoriia_dev"
    assert response_data["user"]["email"] == "viktoriia@example.com"