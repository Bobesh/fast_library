import logging
from functools import lru_cache
from app.services.library_manager import LibraryManager
from app.core.logging import log_debug
from app.services.library_psql import LibraryPsql
from app.services.users_manager import UserManager
from app.services.users_psql import UserPsql

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

async def library_manager_dependency() -> LibraryManager:
    """FastAPI dependency for LibraryManager"""
    return get_library_manager()

@lru_cache()
def get_user_psql() -> UserPsql:
    """Get UserPsql instance (singleton)"""
    log_debug(logger, "Creating UserPsql instance")
    return UserPsql()

@lru_cache()
def get_user_manager() -> UserManager:
    """Get UserManager instance (singleton)"""
    log_debug(logger, "Creating UserManager instance")
    psql = get_user_psql()
    return UserManager(psql)

async def user_manager_dependency() -> UserManager:
    """FastAPI dependency for UserManager"""
    return get_user_manager()