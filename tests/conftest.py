import asyncio
import logging
from typing import Generator
from unittest.mock import Mock, AsyncMock

import pytest
import os

from app.services.library_manager import LibraryManager

# Test database configuration
os.environ["API_KEY"] = "test-key"
os.environ["DB_HOST"] = "test-db"
os.environ["DEBUG"] = "True"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    import logging

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    logging.basicConfig(level=logging.INFO, force=True)


@pytest.fixture
def mock_library_manager():

    mock = Mock(spec=LibraryManager)
    mock.get_all_books = AsyncMock()
    mock.get_book_details = AsyncMock()
    mock.borrow_copy = AsyncMock()
    mock.return_book = AsyncMock()
    mock.create_book = AsyncMock()
    return mock


@pytest.fixture
async def auth_headers():
    """Authentication headers for API calls"""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture(scope="function")
async def db_transaction():
    """Database transaction that rolls back after test"""
    yield


@pytest.fixture
def caplog_setup(caplog):
    """Setup logging capture with custom format"""
    caplog.set_level(logging.DEBUG)
    return caplog
