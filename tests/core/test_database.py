import pytest
from unittest.mock import Mock, patch, MagicMock
from app.core.database import DatabaseManager, DatabaseConnection, db_manager


class TestDatabaseManager:

    def test_singleton_pattern(self):
        """Test that DatabaseManager is singleton"""
        manager1 = DatabaseManager()
        manager2 = DatabaseManager()

        assert manager1 is manager2
        assert manager1 is db_manager

    @patch("app.core.database.psycopg2.pool.SimpleConnectionPool")
    @patch("app.core.database.settings")
    def test_initialize_pool_success(self, mock_settings, mock_pool_class):
        """Test successful pool initialization"""
        mock_settings.db_host.return_value = "localhost"
        mock_settings.db_port.return_value = 5432
        mock_settings.db_name.return_value = "testdb"
        mock_settings.db_user.return_value = "user"
        mock_settings.db_password.return_value = "pass"

        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        mock_pool.getconn.return_value = mock_conn

        manager = DatabaseManager()
        manager._connection_pool = None

        manager.initialize_pool()

        assert manager._connection_pool == mock_pool
        mock_pool_class.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT 1")

    @patch("app.core.database.psycopg2.pool.SimpleConnectionPool")
    def test_initialize_pool_failure(self, mock_pool_class):
        """Test pool initialization failure"""
        mock_pool_class.side_effect = Exception("Connection failed")

        manager = DatabaseManager()
        manager._connection_pool = None

        with pytest.raises(Exception, match="Connection failed"):
            manager.initialize_pool()

    def test_get_connection_not_initialized(self):
        """Test getting connection when pool not initialized"""
        manager = DatabaseManager()
        manager._connection_pool = None

        with pytest.raises(RuntimeError, match="Connection pool not initialized"):
            manager.get_connection()

    def test_get_and_return_connection(self):
        """Test getting and returning connection"""
        manager = DatabaseManager()
        mock_pool = Mock()
        mock_conn = Mock()
        mock_pool.getconn.return_value = mock_conn
        manager._connection_pool = mock_pool

        conn = manager.get_connection()
        assert conn == mock_conn
        mock_pool.getconn.assert_called_once()

        manager.return_connection(conn)
        mock_pool.putconn.assert_called_once_with(conn)

    def test_close_connection_pool(self):
        """Test closing connection pool"""
        manager = DatabaseManager()
        mock_pool = Mock()
        manager._connection_pool = mock_pool

        manager.close_connection_pool()

        mock_pool.closeall.assert_called_once()
        assert manager._connection_pool is None


class TestDatabaseConnection:

    @patch.object(db_manager, "get_connection")
    @patch.object(db_manager, "return_connection")
    def test_context_manager_success(self, mock_return, mock_get):
        """Test context manager normal flow"""
        mock_conn = Mock()
        mock_get.return_value = mock_conn

        with DatabaseConnection() as conn:
            assert conn == mock_conn

        mock_get.assert_called_once()
        mock_return.assert_called_once_with(mock_conn)

    @patch.object(db_manager, "get_connection")
    @patch.object(db_manager, "return_connection")
    def test_context_manager_with_exception(self, mock_return, mock_get):
        """Test context manager with exception (rollback)"""
        mock_conn = Mock()
        mock_get.return_value = mock_conn

        with pytest.raises(ValueError):
            with DatabaseConnection() as conn:
                raise ValueError("Test error")

        mock_conn.rollback.assert_called_once()
        mock_return.assert_called_once_with(mock_conn)
