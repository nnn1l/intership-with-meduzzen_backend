from fastapi.testclient import TestClient
from ..main import app
from fastapi import status

client = TestClient(app)

def test_read():
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status_code": status.HTTP_200_OK,
        "detail": "ok",
        "result": "working"
    }