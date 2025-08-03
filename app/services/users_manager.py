import logging
from typing import List, Optional, Dict, Any
from app.data.user_psql import UserPsql
from app.models.user_models import User
from app.core.logging import log_debug, log_info, log_error

logger = logging.getLogger(__name__)


class UserManager:
    """Business logic layer for user operations"""

    def __init__(self, data_access: UserPsql):
        self.data_access = data_access
        log_debug(logger, "UserManager initialized")

    async def get_all_users(self, active_only: bool = True) -> List[User]:
        """Get all users with optional filtering by active status"""
        log_debug(logger, f"UserManager: Getting all users (active_only={active_only})")
        return await self.data_access.get_all_users(active_only)

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        log_debug(logger, f"UserManager: Getting user {user_id}")
        return await self.data_access.get_user_by_id(user_id)

    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """
        Create a new user
        """
        log_info(logger, f"UserManager: Creating user {user_data.get('username')}")

        try:
            user = await self.data_access.create_user(user_data)
            log_info(logger, f"UserManager: Successfully created user {user.username} with ID {user.id}")
            return user
        except ValueError as e:
            log_error(logger, f"UserManager: Failed to create user - {e}")
            raise
        except Exception as e:
            log_error(logger, f"UserManager: Unexpected error creating user - {e}", exc_info=e)
            raise

    async def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Optional[User]:
        """
        Update user information
        """
        log_info(logger, f"UserManager: Updating user {user_id}")

        try:
            user = await self.data_access.update_user(user_id, user_data)
            if user:
                log_info(logger, f"UserManager: Successfully updated user {user.username}")
            else:
                log_debug(logger, f"UserManager: User {user_id} not found for update")
            return user
        except Exception as e:
            log_error(logger, f"UserManager: Failed to update user {user_id} - {e}", exc_info=e)
            raise

    async def deactivate_user(self, user_id: int) -> Optional[User]:
        """
        Deactivate user
        Business logic: check if user can be deactivated (no active borrowings)
        """
        log_info(logger, f"UserManager: Attempting to deactivate user {user_id}")

        try:
            # Check if user can be deactivated
            can_deactivate, reason = await self.data_access.can_user_be_deactivated(user_id)

            if not can_deactivate:
                log_info(logger, f"UserManager: Cannot deactivate user {user_id}: {reason}")
                raise ValueError(reason)

            # Deactivate user
            user_data = {'active': False}
            user = await self.data_access.update_user(user_id, user_data)

            if user:
                log_info(logger, f"UserManager: Successfully deactivated user {user.username}")

            return user
        except ValueError as e:
            log_error(logger, f"UserManager: Failed to deactivate user {user_id} - {e}")
            raise
        except Exception as e:
            log_error(logger, f"UserManager: Unexpected error deactivating user {user_id} - {e}", exc_info=e)
            raise

    async def activate_user(self, user_id: int) -> Optional[User]:
        """
        Activate user
        """
        log_info(logger, f"UserManager: Attempting to activate user {user_id}")

        try:
            user_data = {'active': True}
            user = await self.data_access.update_user(user_id, user_data)

            if user:
                log_info(logger, f"UserManager: Successfully activated user {user.username}")
            else:
                log_debug(logger, f"UserManager: User {user_id} not found for activation")

            return user
        except Exception as e:
            log_error(logger, f"UserManager: Unexpected error activating user {user_id} - {e}", exc_info=e)
            raise

    async def get_user_borrowing_history(self, user_id: int, include_active: bool = True) -> List[Dict[str, Any]]:
        """Get borrowing history for user"""
        log_debug(logger, f"UserManager: Getting borrowing history for user {user_id}")
        return await self.data_access.get_user_borrowing_history(user_id, include_active)
