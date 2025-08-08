import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import date

from fastapi import HTTPException

from app.models.users import User
from app.services.user_manager import UserManager
from app.services.users_psql import UserPsql


class TestUserManager:

    @pytest.fixture
    def mock_users_psql(self):
        """Mock UserPsql data access layer"""
        mock = Mock(spec=UserPsql)
        mock.get_all_users = AsyncMock()
        mock.get_user_by_id = AsyncMock()
        mock.create_user = AsyncMock()
        return mock

    @pytest.fixture
    def user_manager(self, mock_users_psql):
        """Create UserManager with mocked data access"""
        with patch("app.services.user_manager.log_debug"):
            return UserManager(mock_users_psql)

    @pytest.fixture
    def sample_user(self):
        """Sample User for testing"""
        return User(
            id=1,
            username="test_user",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            created_at=date.today(),
        )

    @pytest.fixture
    def sample_users_list(self):
        """Sample list of users for testing"""
        return [
            User(
                id=1,
                username="user1",
                email="user1@example.com",
                first_name="First",
                last_name="User",
                created_at=date.today(),
            ),
            User(
                id=2,
                username="user2",
                email="user2@example.com",
                first_name="Second",
                last_name="User",
                created_at=date.today(),
            ),
        ]

    @pytest.fixture
    def sample_user_data(self):
        """Sample user creation data"""
        return {
            "username": "new_user",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
        }

    @patch("app.services.user_manager.log_debug")
    @patch("app.services.user_manager.logger")
    def test_user_manager_initialization(
        self, mock_logger, mock_log_debug, mock_users_psql
    ):
        """Test UserManager initialization"""
        manager = UserManager(mock_users_psql)

        assert manager.data_access == mock_users_psql
        mock_log_debug.assert_called_once_with(mock_logger, "UserManager initialized")

    @patch("app.services.user_manager.log_debug")
    @patch("app.services.user_manager.logger")
    @pytest.mark.asyncio
    async def test_get_all_users_success(
        self,
        mock_logger,
        mock_log_debug,
        user_manager,
        mock_users_psql,
        sample_users_list,
    ):
        """Test successful retrieval of all users"""
        mock_users_psql.get_all_users.return_value = sample_users_list

        result = await user_manager.get_all_users()

        assert len(result) == 2
        assert result[0].username == "user1"
        assert result[1].username == "user2"
        mock_users_psql.get_all_users.assert_called_once()
        mock_log_debug.assert_any_call(mock_logger, "UserManager: Getting all users")

    @patch("app.services.user_manager.log_debug")
    @patch("app.services.user_manager.logger")
    @pytest.mark.asyncio
    async def test_get_all_users_empty_result(
        self, mock_logger, mock_log_debug, user_manager, mock_users_psql
    ):
        """Test getting all users when no users exist"""
        mock_users_psql.get_all_users.return_value = []

        result = await user_manager.get_all_users()

        assert result == []
        mock_users_psql.get_all_users.assert_called_once()
        mock_log_debug.assert_any_call(mock_logger, "UserManager: Getting all users")

    @pytest.mark.asyncio
    async def test_get_all_users_exception_propagation(
        self, user_manager, mock_users_psql
    ):
        """Test that exceptions from data layer are propagated"""
        from fastapi import HTTPException

        mock_users_psql.get_all_users.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await user_manager.get_all_users()

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to retrieve users"

    @patch("app.services.user_manager.log_debug")
    @patch("app.services.user_manager.logger")
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(
        self, mock_logger, mock_log_debug, user_manager, mock_users_psql, sample_user
    ):
        """Test successful retrieval of user by ID"""
        user_id = 1
        mock_users_psql.get_user_by_id.return_value = sample_user

        result = await user_manager.get_user_by_id(user_id)

        assert result == sample_user
        assert result.id == 1
        assert result.username == "test_user"
        mock_users_psql.get_user_by_id.assert_called_once_with(user_id)
        mock_log_debug.assert_any_call(
            mock_logger, f"UserManager: Getting user {user_id}"
        )

    @patch("app.services.user_manager.log_debug")
    @patch("app.services.user_manager.logger")
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(
        self, mock_logger, mock_log_debug, user_manager, mock_users_psql
    ):
        """Test getting user by ID when user doesn't exist"""
        user_id = 999
        mock_users_psql.get_user_by_id.return_value = None

        result = await user_manager.get_user_by_id(user_id)

        assert result is None
        mock_users_psql.get_user_by_id.assert_called_once_with(user_id)
        mock_log_debug.assert_any_call(
            mock_logger, f"UserManager: Getting user {user_id}"
        )

    @pytest.mark.asyncio
    async def test_get_user_by_id_exception_propagation(
        self, user_manager, mock_users_psql
    ):
        """Test that exceptions from data layer are propagated"""
        from fastapi import HTTPException

        user_id = 1
        mock_users_psql.get_user_by_id.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await user_manager.get_user_by_id(user_id)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to retrieve user"

    @patch("app.services.user_manager.log_debug")
    @patch("app.services.user_manager.logger")
    @pytest.mark.asyncio
    async def test_create_user_success(
        self,
        mock_logger,
        mock_log_debug,
        user_manager,
        mock_users_psql,
        sample_user_data,
        sample_user,
    ):
        """Test successful user creation"""
        mock_users_psql.create_user.return_value = sample_user

        result = await user_manager.create_user(sample_user_data)

        assert result == sample_user
        assert result.username == "test_user"
        mock_users_psql.create_user.assert_called_once_with(sample_user_data)
        mock_log_debug.assert_any_call(
            mock_logger,
            f"UserManager: Creating user {sample_user_data.get('username')}",
        )
        mock_log_debug.assert_any_call(
            mock_logger,
            f"UserManager: Successfully created user {sample_user.username} with ID {sample_user.id}",
        )

    @patch("app.services.user_manager.log_debug")
    @patch("app.services.user_manager.logger")
    @pytest.mark.asyncio
    async def test_create_user_success_with_none_username(
        self, mock_logger, mock_log_debug, user_manager, mock_users_psql, sample_user
    ):
        """Test successful user creation when username is None in input data"""
        user_data_no_username = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
        }
        mock_users_psql.create_user.return_value = sample_user

        result = await user_manager.create_user(user_data_no_username)

        assert result == sample_user
        mock_log_debug.assert_any_call(mock_logger, "UserManager: Creating user None")

    @patch("app.services.user_manager.log_error")
    @patch("app.services.user_manager.logger")
    @pytest.mark.asyncio
    async def test_create_user_value_error(
        self,
        mock_logger,
        mock_log_error,
        user_manager,
        mock_users_psql,
        sample_user_data,
    ):
        """Test handling ValueError during user creation"""
        error_message = "Username already exists"
        mock_users_psql.create_user.side_effect = ValueError(error_message)

        with pytest.raises(ValueError, match=error_message):
            await user_manager.create_user(sample_user_data)

        mock_log_error.assert_called_once_with(
            mock_logger, f"UserManager: Failed to create user - {error_message}"
        )

    @patch("app.services.user_manager.log_error")
    @patch("app.services.user_manager.logger")
    @pytest.mark.asyncio
    async def test_create_user_unexpected_error(
        self,
        mock_logger,
        mock_log_error,
        user_manager,
        mock_users_psql,
        sample_user_data,
    ):
        """Test handling unexpected error during user creation"""
        from fastapi import HTTPException

        error = Exception("Database connection failed")
        mock_users_psql.create_user.side_effect = error

        with pytest.raises(HTTPException) as exc_info:
            await user_manager.create_user(sample_user_data)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to create user"
        mock_log_error.assert_called_once_with(
            mock_logger,
            f"UserManager: Unexpected error creating user - {error}",
            exc_info=error,
        )

    @patch("app.services.user_manager.log_debug")
    @patch("app.services.user_manager.log_error")
    @patch("app.services.user_manager.logger")
    @pytest.mark.asyncio
    async def test_create_user_error_after_debug_log(
        self,
        mock_logger,
        mock_log_error,
        mock_log_debug,
        user_manager,
        mock_users_psql,
        sample_user_data,
    ):
        """Test that debug log is called before error occurs"""
        mock_users_psql.create_user.side_effect = ValueError("Test error")

        with pytest.raises(ValueError):
            await user_manager.create_user(sample_user_data)

        mock_log_debug.assert_any_call(
            mock_logger,
            f"UserManager: Creating user {sample_user_data.get('username')}",
        )
        mock_log_error.assert_called_once()

    @patch("app.services.user_manager.log_debug")
    @patch("app.services.user_manager.logger")
    @pytest.mark.asyncio
    async def test_create_and_retrieve_user_flow(
        self,
        mock_logger,
        mock_log_debug,
        user_manager,
        mock_users_psql,
        sample_user_data,
        sample_user,
    ):
        """Test creating and then retrieving a user"""
        mock_users_psql.create_user.return_value = sample_user
        mock_users_psql.get_user_by_id.return_value = sample_user

        created_user = await user_manager.create_user(sample_user_data)

        retrieved_user = await user_manager.get_user_by_id(created_user.id)

        assert created_user == retrieved_user
        assert created_user.id == retrieved_user.id
        mock_users_psql.create_user.assert_called_once_with(sample_user_data)
        mock_users_psql.get_user_by_id.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_get_user_by_id_with_zero(self, user_manager, mock_users_psql):
        """Test getting user with ID zero"""
        mock_users_psql.get_user_by_id.return_value = None

        result = await user_manager.get_user_by_id(0)

        assert result is None
        mock_users_psql.get_user_by_id.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_get_user_by_id_with_negative(self, user_manager, mock_users_psql):
        """Test getting user with negative ID"""
        mock_users_psql.get_user_by_id.return_value = None

        result = await user_manager.get_user_by_id(-1)

        assert result is None
        mock_users_psql.get_user_by_id.assert_called_once_with(-1)
