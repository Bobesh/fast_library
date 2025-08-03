import asyncio
import logging
from typing import Optional
import psycopg2
from psycopg2 import pool

from app.core.config import settings
from app.core.logging import log_debug, log_info, log_error

logger = logging.getLogger(__name__)


class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
    _connection_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    async def initialize_pool(self) -> None:
        """Initialize database connection pool"""
        if self._connection_pool is None:
            try:
                log_debug(logger, "Initializing database connection pool")
                self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=settings.db_host(),
                    port=settings.db_port(),
                    database=settings.db_name(),
                    user=settings.db_user(),
                    password=settings.db_password()
                )
                log_info(logger, "Database connection pool initialized successfully")

                # Test connection
                await self._test_connection()

            except Exception as e:
                log_error(logger, f"Failed to initialize database connection pool: {e}", exc_info=e)
                raise

    async def _test_connection(self) -> None:
        """Test database connection"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                log_debug(logger, f"Database connection test successful: {result}")
            self.return_connection(conn)
        except Exception as e:
            log_error(logger, f"Database connection test failed: {e}", exc_info=e)
            raise

    def get_connection(self):
        """Get connection from pool"""
        if self._connection_pool is None:
            raise RuntimeError("Connection pool not initialized")
        return self._connection_pool.getconn()

    def return_connection(self, connection) -> None:
        """Return connection to pool"""
        if self._connection_pool:
            self._connection_pool.putconn(connection)

    async def close_connection_pool(self) -> None:
        """Close all connections in pool"""
        if self._connection_pool:
            log_debug(logger, "Closing database connection pool")
            self._connection_pool.closeall()
            self._connection_pool = None
            log_info(logger, "Database connection pool closed")


# Singleton instance
db_manager = DatabaseManager()


class DatabaseConnection:
    """Context manager for database connections"""

    def __init__(self):
        self.connection = None

    def __enter__(self):
        self.connection = db_manager.get_connection()
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            if exc_type:
                self.connection.rollback()
            db_manager.return_connection(self.connection)