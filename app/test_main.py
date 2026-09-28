from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_item_success():
    response = client.get("/items/15")
    assert response.status_code == 200
    assert response.json() == {"item_id": 15, "status": "found"}

def test_read_item_validation_error():
    response = client.get("items/fluffy-dog")
    assert response.status_code == 422