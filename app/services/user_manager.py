import logging
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from app.core.logging import log_debug, log_error
from app.models.users import User
from app.services.users_psql import UserPsql

logger = logging.getLogger(__name__)


class UserManager:
    """Business logic layer for user operations"""

    def __init__(self, data_access: UserPsql):
        self.data_access = data_access
        log_debug(logger, "UserManager initialized")

    async def get_all_users(self) -> List[User]:
        """Get all users"""
        log_debug(logger, "UserManager: Getting all users")
        try:
            return await self.data_access.get_all_users()
        except Exception as e:
            log_error(logger, f"UserManager: Failed to get all users - {e}", exc_info=e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve users",
            )

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        log_debug(logger, f"UserManager: Getting user {user_id}")
        try:
            return await self.data_access.get_user_by_id(user_id)
        except Exception as e:
            log_error(
                logger, f"UserManager: Failed to get user {user_id} - {e}", exc_info=e
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user",
            )

    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user"""
        log_debug(logger, f"UserManager: Creating user {user_data.get('username')}")
        try:
            user = await self.data_access.create_user(user_data)
            log_debug(
                logger,
                f"UserManager: Successfully created user {user.username} with ID {user.id}",
            )
            return user
        except ValueError as e:
            log_error(logger, f"UserManager: Failed to create user - {e}")
            raise
        except Exception as e:
            log_error(
                logger, f"UserManager: Unexpected error creating user - {e}", exc_info=e
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )
