import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import psycopg2

from app.models.users import User
from app.services.users_psql import UserPsql


class TestUserPsql:

    @pytest.fixture
    def user_psql(self):
        """Create UserPsql instance"""
        return UserPsql()

    @pytest.fixture
    def mock_cursor(self):
        """Mock database cursor"""
        cursor = Mock()
        cursor.fetchall = Mock()
        cursor.fetchone = Mock()
        cursor.execute = Mock()
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Mock database connection with cursor"""
        conn = Mock()
        conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        conn.cursor.return_value.__exit__ = Mock(return_value=None)
        conn.__enter__ = Mock(return_value=conn)
        conn.__exit__ = Mock(return_value=None)
        return conn

    @pytest.fixture
    def sample_users_data(self):
        """Sample users data from database"""
        return [
            (1, "john_doe", "john@example.com", "John", "Doe", date(2024, 1, 1)),
            (2, "jane_smith", "jane@example.com", "Jane", "Smith", date(2024, 1, 2)),
            (3, "bob_wilson", "bob@example.com", "Bob", "Wilson", date(2024, 1, 3)),
        ]

    @pytest.fixture
    def sample_user_data(self):
        """Sample single user data from database"""
        return (1, "john_doe", "john@example.com", "John", "Doe", date(2024, 1, 1))

    @pytest.fixture
    def sample_user_dict(self):
        """Sample user data as dictionary for creation"""
        return {
            "username": "new_user",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
        }

    @pytest.fixture
    def created_user_data(self):
        """Sample data returned from database after user creation"""
        return (5, "new_user", "new@example.com", "New", "User", date(2024, 1, 5))

    @patch("app.services.users_psql.DatabaseConnection")
    @patch("app.services.users_psql.log_debug")
    @patch("app.services.users_psql.logger")
    @pytest.mark.asyncio
    async def test_get_all_users_success(
        self,
        mock_logger,
        mock_log_debug,
        mock_db_connection,
        mock_connection,
        mock_cursor,
        sample_users_data,
    ):
        """Test successfully getting all users"""
        mock_db_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = sample_users_data

        result = await UserPsql.get_all_users()

        assert len(result) == 3
        assert all(isinstance(user, User) for user in result)

        assert result[0].id == 1
        assert result[0].username == "john_doe"
        assert result[0].email == "john@example.com"
        assert result[0].first_name == "John"
        assert result[0].last_name == "Doe"
        assert result[0].created_at == date(2024, 1, 1)

        mock_cursor.execute.assert_called_once_with(
            """
                            SELECT id, username, email, first_name, last_name, created_at::date
                            FROM users
                            ORDER BY created_at DESC
                        """
        )
        mock_cursor.fetchall.assert_called_once()

        mock_log_debug.assert_any_call(mock_logger, "Fetching users")
        mock_log_debug.assert_any_call(mock_logger, "Retrieved 3 users")

    @patch("app.services.users_psql.DatabaseConnection")
    @patch("app.services.users_psql.log_debug")
    @patch("app.services.users_psql.logger")
    @pytest.mark.asyncio
    async def test_get_all_users_empty_result(
        self,
        mock_logger,
        mock_log_debug,
        mock_db_connection,
        mock_connection,
        mock_cursor,
    ):
        """Test getting all users when no users exist"""
        mock_db_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = []

        result = await UserPsql.get_all_users()

        assert result == []
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchall.assert_called_once()
        mock_log_debug.assert_any_call(mock_logger, "Retrieved 0 users")

    @patch("app.services.users_psql.DatabaseConnection")
    @patch("app.services.users_psql.log_error")
    @patch("app.services.users_psql.logger")
    @pytest.mark.asyncio
    async def test_get_all_users_database_error(
        self,
        mock_logger,
        mock_log_error,
        mock_db_connection,
        mock_connection,
        mock_cursor,
    ):
        """Test handling database error when getting all users"""
        mock_db_connection.return_value = mock_connection
        error = Exception("Database connection failed")
        mock_cursor.execute.side_effect = error

        with pytest.raises(Exception, match="Database connection failed"):
            await UserPsql.get_all_users()

        mock_log_error.assert_called_once_with(
            mock_logger, f"Failed to fetch users: {error}", exc_info=error
        )

    @patch("app.services.users_psql.DatabaseConnection")
    @patch("app.services.users_psql.log_debug")
    @patch("app.services.users_psql.logger")
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(
        self,
        mock_logger,
        mock_log_debug,
        mock_db_connection,
        mock_connection,
        mock_cursor,
        sample_user_data,
    ):
        """Test successfully getting user by ID"""
        user_id = 1
        mock_db_connection.return_value = mock_connection
        mock_cursor.fetchone.return_value = sample_user_data

        result = await UserPsql.get_user_by_id(user_id)

        assert isinstance(result, User)
        assert result.id == 1
        assert result.username == "john_doe"
        assert result.email == "john@example.com"
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.created_at == date(2024, 1, 1)

        mock_cursor.execute.assert_called_once_with(
            """
                            SELECT id, username, email, first_name, last_name, created_at::date
                            FROM users WHERE id = %s
                        """,
            (user_id,),
        )
        mock_cursor.fetchone.assert_called_once()

        mock_log_debug.assert_any_call(mock_logger, f"Fetching user {user_id}")
        mock_log_debug.assert_any_call(mock_logger, "Found user: john_doe")

    @patch("app.services.users_psql.DatabaseConnection")
    @patch("app.services.users_psql.log_debug")
    @patch("app.services.users_psql.logger")
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(
        self,
        mock_logger,
        mock_log_debug,
        mock_db_connection,
        mock_connection,
        mock_cursor,
    ):
        """Test getting user by ID when user doesn't exist"""
        user_id = 999
        mock_db_connection.return_value = mock_connection
        mock_cursor.fetchone.return_value = None

        result = await UserPsql.get_user_by_id(user_id)

        assert result is None
        mock_cursor.execute.assert_called_once_with(
            """
                            SELECT id, username, email, first_name, last_name, created_at::date
                            FROM users WHERE id = %s
                        """,
            (user_id,),
        )
        mock_cursor.fetchone.assert_called_once()
        mock_log_debug.assert_any_call(mock_logger, f"Fetching user {user_id}")

    @patch("app.services.users_psql.DatabaseConnection")
    @patch("app.services.users_psql.log_error")
    @patch("app.services.users_psql.logger")
    @pytest.mark.asyncio
    async def test_get_user_by_id_database_error(
        self,
        mock_logger,
        mock_log_error,
        mock_db_connection,
        mock_connection,
        mock_cursor,
    ):
        """Test handling database error when getting user by ID"""
        user_id = 1
        mock_db_connection.return_value = mock_connection
        error = Exception("Database error")
        mock_cursor.execute.side_effect = error

        with pytest.raises(Exception, match="Database error"):
            await UserPsql.get_user_by_id(user_id)

        mock_log_error.assert_called_once_with(
            mock_logger, f"Failed to fetch user {user_id}: {error}", exc_info=error
        )

    @patch("app.services.users_psql.DatabaseConnection")
    @patch("app.services.users_psql.log_debug")
    @patch("app.services.users_psql.logger")
    @pytest.mark.asyncio
    async def test_create_user_success(
        self,
        mock_logger,
        mock_log_debug,
        mock_db_connection,
        mock_connection,
        mock_cursor,
        sample_user_dict,
        created_user_data,
    ):
        """Test successfully creating a user"""
        mock_db_connection.return_value = mock_connection
        mock_cursor.fetchone.return_value = created_user_data

        result = await UserPsql.create_user(sample_user_dict)

        assert isinstance(result, User)
        assert result.id == 5
        assert result.username == "new_user"
        assert result.email == "new@example.com"
        assert result.first_name == "New"
        assert result.last_name == "User"
        assert result.created_at == date(2024, 1, 5)

        mock_cursor.execute.assert_called_once_with(
            """
                            INSERT INTO users (username, email, first_name, last_name)
                            VALUES (%s, %s, %s, %s)
                            RETURNING id, username, email, first_name, last_name, created_at::date
                        """,
            (
                sample_user_dict["username"],
                sample_user_dict["email"],
                sample_user_dict["first_name"],
                sample_user_dict["last_name"],
            ),
        )
        mock_cursor.fetchone.assert_called_once()

        mock_log_debug.assert_any_call(
            mock_logger, f"Creating user: {sample_user_dict['username']}"
        )
        mock_log_debug.assert_any_call(mock_logger, f"Created user: new_user with ID 5")

    @patch("app.services.users_psql.DatabaseConnection")
    @pytest.mark.asyncio
    async def test_create_user_username_already_exists(
        self, mock_db_connection, mock_connection, mock_cursor, sample_user_dict
    ):
        """Test creating user with existing username"""
        mock_db_connection.return_value = mock_connection
        integrity_error = psycopg2.IntegrityError(
            'duplicate key value violates unique constraint "ix_users_username"'
        )
        mock_cursor.execute.side_effect = integrity_error

        with pytest.raises(ValueError, match="Username 'new_user' already exists"):
            await UserPsql.create_user(sample_user_dict)

    @patch("app.services.users_psql.DatabaseConnection")
    @pytest.mark.asyncio
    async def test_create_user_username_already_exists_alternative_format(
        self, mock_db_connection, mock_connection, mock_cursor, sample_user_dict
    ):
        """Test creating user with existing username (alternative error message format)"""
        mock_db_connection.return_value = mock_connection
        integrity_error = psycopg2.IntegrityError("username constraint violation")
        mock_cursor.execute.side_effect = integrity_error

        with pytest.raises(ValueError, match="Username 'new_user' already exists"):
            await UserPsql.create_user(sample_user_dict)

    @patch("app.services.users_psql.DatabaseConnection")
    @pytest.mark.asyncio
    async def test_create_user_email_already_exists(
        self, mock_db_connection, mock_connection, mock_cursor, sample_user_dict
    ):
        """Test creating user with existing email"""
        mock_db_connection.return_value = mock_connection
        integrity_error = psycopg2.IntegrityError(
            'duplicate key value violates unique constraint "ix_users_email"'
        )
        mock_cursor.execute.side_effect = integrity_error

        with pytest.raises(ValueError, match="Email 'new@example.com' already exists"):
            await UserPsql.create_user(sample_user_dict)

    @patch("app.services.users_psql.DatabaseConnection")
    @pytest.mark.asyncio
    async def test_create_user_email_already_exists_alternative_format(
        self, mock_db_connection, mock_connection, mock_cursor, sample_user_dict
    ):
        """Test creating user with existing email (alternative error message format)"""
        mock_db_connection.return_value = mock_connection
        integrity_error = psycopg2.IntegrityError("email constraint violation")
        mock_cursor.execute.side_effect = integrity_error

        with pytest.raises(ValueError, match="Email 'new@example.com' already exists"):
            await UserPsql.create_user(sample_user_dict)

    @patch("app.services.users_psql.DatabaseConnection")
    @patch("app.services.users_psql.log_error")
    @patch("app.services.users_psql.logger")
    @pytest.mark.asyncio
    async def test_create_user_database_error(
        self,
        mock_logger,
        mock_log_error,
        mock_db_connection,
        mock_connection,
        mock_cursor,
        sample_user_dict,
    ):
        """Test handling general database error when creating user"""
        mock_db_connection.return_value = mock_connection
        error = Exception("Database connection failed")
        mock_cursor.execute.side_effect = error

        with pytest.raises(Exception, match="Database connection failed"):
            await UserPsql.create_user(sample_user_dict)

        assert mock_log_error.called
        call_args = mock_log_error.call_args
        assert call_args[0][0] == mock_logger
        assert "Failed to create user:" in call_args[0][1]
        assert call_args[1]["exc_info"] == error

    @patch("app.services.users_psql.DatabaseConnection")
    @pytest.mark.asyncio
    async def test_create_user_missing_required_fields(
        self, mock_db_connection, mock_connection, mock_cursor
    ):
        """Test creating user with missing required fields"""
        mock_db_connection.return_value = mock_connection
        incomplete_user_data = {"username": "test_user", "email": "test@example.com"}

        with pytest.raises(KeyError):
            await UserPsql.create_user(incomplete_user_data)

    @patch("app.services.users_psql.DatabaseConnection")
    @pytest.mark.asyncio
    async def test_create_user_empty_values(
        self, mock_db_connection, mock_connection, mock_cursor
    ):
        """Test creating user with empty values"""
        mock_db_connection.return_value = mock_connection
        empty_user_data = {
            "username": "",
            "email": "",
            "first_name": "",
            "last_name": "",
        }
        created_user_data = (1, "", "", "", "", date(2024, 1, 1))
        mock_cursor.fetchone.return_value = created_user_data

        result = await UserPsql.create_user(empty_user_data)

        assert isinstance(result, User)
        assert result.username == ""
        assert result.email == ""
        assert result.first_name == ""
        assert result.last_name == ""

    @patch("app.services.users_psql.DatabaseConnection")
    @patch("app.services.users_psql.log_debug")
    @patch("app.services.users_psql.logger")
    @pytest.mark.asyncio
    async def test_create_and_retrieve_user_flow(
        self,
        mock_logger,
        mock_log_debug,
        mock_db_connection,
        mock_connection,
        mock_cursor,
    ):
        """Test creating and then retrieving a user"""
        mock_db_connection.return_value = mock_connection
        user_data = {
            "username": "lifecycle_user",
            "email": "lifecycle@example.com",
            "first_name": "Life",
            "last_name": "Cycle",
        }
        created_user_data = (
            10,
            "lifecycle_user",
            "lifecycle@example.com",
            "Life",
            "Cycle",
            date(2024, 1, 10),
        )

        mock_cursor.fetchone.side_effect = [created_user_data, created_user_data]

        created_user = await UserPsql.create_user(user_data)

        retrieved_user = await UserPsql.get_user_by_id(created_user.id)

        assert created_user.id == retrieved_user.id
        assert created_user.username == retrieved_user.username
        assert created_user.email == retrieved_user.email
        assert created_user.first_name == retrieved_user.first_name
        assert created_user.last_name == retrieved_user.last_name

    @patch("app.services.users_psql.DatabaseConnection")
    @pytest.mark.asyncio
    async def test_get_user_by_id_zero_id(
        self, mock_db_connection, mock_connection, mock_cursor
    ):
        """Test getting user with zero ID"""
        user_id = 0
        mock_db_connection.return_value = mock_connection
        mock_cursor.fetchone.return_value = None

        result = await UserPsql.get_user_by_id(user_id)

        assert result is None

    @patch("app.services.users_psql.DatabaseConnection")
    @pytest.mark.asyncio
    async def test_create_user_with_special_characters(
        self, mock_db_connection, mock_connection, mock_cursor
    ):
        """Test creating user with special characters"""
        mock_db_connection.return_value = mock_connection
        special_user_data = {
            "username": "user_ñáme_123",
            "email": "test+special@example.com",
            "first_name": "José María",
            "last_name": "González-Pérez",
        }
        created_user_data = (
            20,
            "user_ñáme_123",
            "test+special@example.com",
            "José María",
            "González-Pérez",
            date(2024, 1, 20),
        )
        mock_cursor.fetchone.return_value = created_user_data

        result = await UserPsql.create_user(special_user_data)

        assert result.username == "user_ñáme_123"
        assert result.email == "test+special@example.com"
        assert result.first_name == "José María"
        assert result.last_name == "González-Pérez"

    @patch("app.services.users_psql.DatabaseConnection")
    @pytest.mark.asyncio
    async def test_database_connection_context_manager(
        self, mock_db_connection, mock_connection, mock_cursor
    ):
        """Test that database connection is properly used as context manager"""
        mock_db_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = []

        await UserPsql.get_all_users()

        mock_db_connection.assert_called_once()
        assert mock_connection.__enter__.called
        assert mock_connection.__exit__.called
        mock_connection.cursor.assert_called_once()

    @patch("app.services.users_psql.DatabaseConnection")
    @pytest.mark.asyncio
    async def test_sql_injection_protection_get_user(
        self, mock_db_connection, mock_connection, mock_cursor
    ):
        """Test that parameterized queries protect against SQL injection"""
        malicious_id = "1; DROP TABLE users; --"
        mock_db_connection.return_value = mock_connection
        mock_cursor.fetchone.return_value = None

        result = await UserPsql.get_user_by_id(malicious_id)

        assert result is None
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1] == (malicious_id,)
        assert "%s" in call_args[0][0]

        @patch("app.services.users_psql.DatabaseConnection")
        @pytest.mark.asyncio
        async def test_sql_injection_protection_create_user(
            self, mock_db_connection, mock_connection, mock_cursor
        ):
            """Test that parameterized queries protect against SQL injection in user creation"""
            mock_db_connection.return_value = mock_connection
            malicious_user_data = {
                "username": "admin'; DROP TABLE users; --",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
            }
            created_user_data = (
                1,
                "admin'; DROP TABLE users; --",
                "test@example.com",
                "Test",
                "User",
                date(2024, 1, 1),
            )
            mock_cursor.fetchone.return_value = created_user_data

            result = await UserPsql.create_user(malicious_user_data)

            assert isinstance(result, User)
            assert mock_cursor.execute.called
            call_args = mock_cursor.execute.call_args
            expected_params = (
                malicious_user_data["username"],
                malicious_user_data["email"],
                malicious_user_data["first_name"],
                malicious_user_data["last_name"],
            )
            assert call_args[0][1] == expected_params
            assert "%s" in call_args[0][0]

    @patch("app.services.users_psql.DatabaseConnection")
    @pytest.mark.asyncio
    async def test_create_user_constraint_error_variations(
        self, mock_db_connection, mock_connection, mock_cursor
    ):
        """Test various constraint error message formats"""
        user_data = {
            "username": "test",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
        }

        test_cases = [
            (
                'duplicate key value violates unique constraint "ix_users_username"',
                "Username 'test' already exists",
            ),
            (
                "UNIQUE constraint failed: users.username",
                "Username 'test' already exists",
            ),
            (
                'duplicate key value violates unique constraint "ix_users_email"',
                "Email 'test@example.com' already exists",
            ),
            (
                "UNIQUE constraint failed: users.email",
                "Email 'test@example.com' already exists",
            ),
            ("some random constraint error", "User data violates database constraint"),
        ]

        for error_msg, expected_msg in test_cases:
            mock_db_connection.return_value = mock_connection
            mock_cursor.reset_mock()
            integrity_error = psycopg2.IntegrityError(error_msg)
            mock_cursor.execute.side_effect = integrity_error

            with pytest.raises(ValueError) as exc_info:
                await UserPsql.create_user(user_data)

            assert expected_msg in str(
                exc_info.value
            ) or "User data violates database constraint" in str(exc_info.value)
