import secrets
import logging
from http.client import HTTPException

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.config import settings
from app.core.logging import log_warning, log_debug

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        if not settings.api_key():
            raise HTTPException("Auth api key is missing in app")
        self.api_key = settings.api_key()
        log_debug(logger, "APIKeyMiddleware initialized")

    async def dispatch(self, request: Request, call_next) -> Response:

        if request.url.path == "/health":
            return await call_next(request)

        if request.url.path == "/":
            return await call_next(request)

        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        provided_key = request.headers.get("X-API-Key") or request.headers.get(
            "x-api-key"
        )

        if not provided_key:
            log_warning(
                logger,
                f"API Key missing for {request.method} {request.url.path}",
                client_ip=request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": "API Key required",
                    "message": "Please provide API Key in X-API-Key header",
                },
            )

        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(provided_key, self.api_key): # type: ignore ## non existent api key is handled
            log_warning(
                logger,
                f"Invalid API Key for {request.method} {request.url.path}",
                client_ip=request.client.host if request.client else "unknown",
                provided_key_length=len(provided_key),
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Invalid API Key",
                    "message": "The provided API Key is not valid",
                },
            )

        log_debug(logger, f"Valid API Key for {request.method} {request.url.path}")

        # API Key is valid, continue with request
        response = await call_next(request)
        return response
