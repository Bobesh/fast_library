import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.routers.health import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint returns correct response"""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == "It is alive!"
