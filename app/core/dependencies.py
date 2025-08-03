import logging
from functools import lru_cache
from app.services.library_manager import LibraryManager
from app.core.logging import log_debug
from app.services.library_psql import LibraryPsql

logger = logging.getLogger(__name__)

@lru_cache()
def get_library_psql() -> LibraryPsql:
    """Get LibraryPsql instance (singleton)"""
    log_debug(logger, "Creating LibraryPsql instance")
    return LibraryPsql()

@lru_cache()
def get_library_manager() -> LibraryManager:
    """Get LibraryManager instance (singleton)"""
    log_debug(logger, "Creating LibraryManager instance")
    psql = get_library_psql()
    return LibraryManager(psql)

# FastAPI dependency
async def library_manager_dependency() -> LibraryManager:
    """FastAPI dependency for LibraryManager"""
    return get_library_manager()