from fastapi.testclient import TestClient
from ..main import app
from fastapi import status

client = TestClient(app)


def test_read():
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data.get("status_code") == status.HTTP_200_OK
    assert data.get("detail") == "ok"
    assert data.get("result") == "working"

    assert "db_postgres" in data
    assert "redis_pings_count" in data