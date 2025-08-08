import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


def create_test_app():
    """Helper to create test app with middleware"""
    from app.routers.auth_middleware import APIKeyMiddleware

    app = FastAPI()
    app.add_middleware(APIKeyMiddleware)

    @app.get("/protected")
    async def protected():
        return {"message": "success"}

    return TestClient(app)


class TestAPIKeyMiddleware:

    @patch("app.routers.auth_middleware.settings.api_key", return_value="test-key")
    def test_valid_api_key(self, mock_settings):
        """Test valid API key works"""
        client = create_test_app()
        response = client.get("/protected", headers={"X-API-Key": "test-key"})

        assert response.status_code == 200
        assert response.json() == {"message": "success"}

    @patch("app.routers.auth_middleware.settings.api_key", return_value="test-key")
    def test_valid_api_key_lowercase(self, mock_settings):
        """Test valid API key with lowercase header"""
        client = create_test_app()
        response = client.get("/protected", headers={"x-api-key": "test-key"})

        assert response.status_code == 200

    def test_missing_api_key(self):
        """Test missing API key returns 401"""
        client = create_test_app()
        response = client.get("/protected")

        assert response.status_code == 401
        assert response.json()["error"] == "API Key required"

    def test_invalid_api_key(self):
        """Test invalid API key returns 401"""
        client = create_test_app()
        response = client.get("/protected", headers={"X-API-Key": "wrong"})

        assert response.status_code == 401
        assert response.json()["error"] == "Invalid API Key"

    def test_health_bypass(self):
        """Test health endpoint bypasses middleware"""
        client = create_test_app()
        response = client.get("/health")

        assert response.status_code == 404
