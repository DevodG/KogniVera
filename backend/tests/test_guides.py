from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_match_guides():
    response = client.get("/api/guides/match?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert "guides" in data
    assert len(data["guides"]) <= 2

def test_get_guide():
    # Attempt to fetch a non-existent guide
    response = client.get("/api/guides/guid_fake123")
    assert response.status_code == 404
