import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.config import settings
from app.core.logging import initialize_logging, log_info, log_debug, log_warning
from app.core.database import db_manager
from app.routers import health

# Initialize logging first
initialize_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(api: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    log_debug(logger, "Application lifespan startup initiated")

    log_debug(logger, "Initializing database connection pool")
    await db_manager.initialize_pool()

    log_info(logger, f"Application {settings.app_name} v{settings.version} startup completed")

    yield

    # Shutdown
    log_debug(logger, "Application lifespan shutdown initiated")

    log_debug(logger, "Closing database connection pool")
    await db_manager.close_connection_pool()

    log_info(logger, "Application shutdown completed")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="REST API pro knihovnický systém",
    openapi_tags=[
        {"name": "knihy", "description": "Operace s knihami"},
        {"name": "health", "description": "Health check endpoints"},
    ],
    lifespan=lifespan,
)

log_info(
    logger,
    f"Starting {settings.app_name} version {settings.version} on {settings.app_host()}:{settings.app_port()}"
)

# Include routers
app.include_router(health.router, tags=["health"])


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, ex: HTTPException) -> JSONResponse:
    log_warning(
        logger,
        f"HTTP exception: {ex.status_code} - {ex.detail}",
        status_code=ex.status_code,
        path=str(request.url.path),
        method=request.method
    )

    message = f"HTTP {ex.status_code}: {ex.detail}"
    if ex.status_code == status.HTTP_404_NOT_FOUND:
        message = f"Resource not found: {request.url.path}"

    return JSONResponse(
        status_code=ex.status_code,
        content={"message": message, "status_code": ex.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, ex: Exception) -> JSONResponse:
    log_warning(
        logger,
        f"Unhandled exception occurred: {type(ex).__name__}",
        exc_info=ex,
        path=str(request.url.path),
        method=request.method
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": f"Internal server error: {type(ex).__name__}",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "path": str(request.url.path)
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.app_host(),
        port=settings.app_port(),
        log_config=None,
        log_level=None,
    )
