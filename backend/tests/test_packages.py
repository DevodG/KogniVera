from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_search_packages():
    response = client.get("/api/packages?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert "packages" in data
    assert len(data["packages"]) <= 2

def test_get_components():
    # Attempt to fetch a non-existent package's components
    response = client.get("/api/packages/pkg_fake123/components")
    assert response.status_code == 404
