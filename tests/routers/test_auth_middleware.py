import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.routers.auth_middleware import APIKeyMiddleware


@pytest.fixture
def app():
    app = FastAPI()
    with patch(
        "app.routers.auth_middleware.settings.api_key", return_value="test-api-key-123"
    ):
        app.add_middleware(APIKeyMiddleware)

    @app.get("/protected")
    async def protected_endpoint():
        return {"message": "success"}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestAPIKeyMiddleware:

    def test_health_endpoint_bypassed(self, client):
        """Test that /health endpoint bypasses API key check"""
        response = client.get("/health")
        assert response.status_code != 401

    def test_docs_endpoints_bypassed(self, client):
        """Test that docs endpoints bypass API key check"""
        endpoints = ["/docs", "/redoc", "/openapi.json"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should not be 401 (API key error)
            assert response.status_code != 401

    def test_root_endpoint_bypassed(self, client):
        """Test that root endpoint bypasses API key check"""
        response = client.get("/")
        assert response.status_code != 401

    def test_missing_api_key(self, client):
        """Test request without API key returns 401"""
        response = client.get("/protected")

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "API Key required"
        assert "X-API-Key header" in data["message"]

    def test_invalid_api_key(self, client):
        """Test request with invalid API key returns 401"""
        response = client.get("/protected", headers={"X-API-Key": "wrong-key"})

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "Invalid API Key"
        assert "not valid" in data["message"]

    @patch(
        "app.routers.auth_middleware.settings.api_key", return_value="test-api-key-123"
    )
    def test_valid_api_key_uppercase_header(self, mock_settings):
        """Test request with valid API key (uppercase header) succeeds"""
        from app.routers.auth_middleware import APIKeyMiddleware

        app = FastAPI()
        app.add_middleware(APIKeyMiddleware)

        @app.get("/protected")
        async def protected_endpoint():
            return {"message": "success"}

        client = TestClient(app)
        response = client.get("/protected", headers={"X-API-Key": "test-api-key-123"})

        assert response.status_code == 200
        assert response.json() == {"message": "success"}

    @patch(
        "app.routers.auth_middleware.settings.api_key", return_value="test-api-key-123"
    )
    def test_valid_api_key_lowercase_header(self, mock_settings):
        """Test request with valid API key (lowercase header) succeeds"""
        from app.routers.auth_middleware import APIKeyMiddleware

        app = FastAPI()
        app.add_middleware(APIKeyMiddleware)

        @app.get("/protected")
        async def protected_endpoint():
            return {"message": "success"}

        client = TestClient(app)
        response = client.get("/protected", headers={"x-api-key": "test-api-key-123"})

        assert response.status_code == 200
        assert response.json() == {"message": "success"}

    def test_missing_api_key(self):
        """Test request without API key returns 401"""
        from app.routers.auth_middleware import APIKeyMiddleware

        app = FastAPI()
        app.add_middleware(APIKeyMiddleware)

        @app.get("/protected")
        async def protected_endpoint():
            return {"message": "success"}

        client = TestClient(app)
        response = client.get("/protected")

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "API Key required"
        assert "X-API-Key header" in data["message"]

    @patch("app.routers.auth_middleware.log_warning")
    def test_logging_invalid_key(self, mock_log_warning, client):
        """Test that invalid API key is logged"""
        client.get("/protected", headers={"X-API-Key": "wrong-key"})

        mock_log_warning.assert_called_once()
        call_args = mock_log_warning.call_args
        assert "Invalid API Key" in call_args[0][1]
