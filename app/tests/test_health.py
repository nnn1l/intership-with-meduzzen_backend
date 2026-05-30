from http.client import responses

from fastapi.testclient import TestClient
from ..main import get_application

app = get_application()
client = TestClient(app)

def test_read():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status_code": 200,
        "detail": "ok",
        "result": "working"
    }