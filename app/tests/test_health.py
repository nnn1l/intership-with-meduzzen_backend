from http.client import responses
from fastapi import status
from fastapi.testclient import TestClient
from ..main import get_application

app = get_application()
client = TestClient(app)

def test_read():
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status_code": status.HTTP_200_OK,
        "detail": "ok",
        "result": "working"
    }