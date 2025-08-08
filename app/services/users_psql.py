import logging
from typing import List, Optional, Dict, Any
import psycopg2
from app.core.database import DatabaseConnection
from app.core.logging import log_debug, log_error
from app.models.users import User

logger = logging.getLogger(__name__)

USERS_TABLE_NAME = "users"


class UserPsql:
    """Data access layer for user operations"""

    @staticmethod
    async def get_all_users() -> List[User]:
        """Get all users"""
        try:
            log_debug(logger, "Fetching users")
            with DatabaseConnection() as conn:
                with conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            f"""
                            SELECT id, username, email, first_name, last_name, created_at::date
                            FROM {USERS_TABLE_NAME}
                            ORDER BY created_at DESC
                        """
                        )
                        rows = cursor.fetchall()

                        users = [
                            User(
                                id=row[0],
                                username=row[1],
                                email=row[2],
                                first_name=row[3],
                                last_name=row[4],
                                created_at=row[5],
                            )
                            for row in rows
                        ]

                        log_debug(logger, f"Retrieved {len(users)} users")
                        return users
        except Exception as e:
            log_error(logger, f"Failed to fetch users: {e}", exc_info=e)
            raise

    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            log_debug(logger, f"Fetching user {user_id}")
            with DatabaseConnection() as conn:
                with conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            f"""
                            SELECT id, username, email, first_name, last_name, created_at::date
                            FROM {USERS_TABLE_NAME} WHERE id = %s
                        """,
                            (user_id,),
                        )
                        row = cursor.fetchone()

                        if row:
                            user = User(
                                id=row[0],
                                username=row[1],
                                email=row[2],
                                first_name=row[3],
                                last_name=row[4],
                                created_at=row[5],
                            )
                            log_debug(logger, f"Found user: {user.username}")
                            return user

                        return None
        except Exception as e:
            log_error(logger, f"Failed to fetch user {user_id}: {e}", exc_info=e)
            raise

    @staticmethod
    async def create_user(user_data: Dict[str, Any]) -> User:
        """Create new user from dict data"""
        try:
            log_debug(logger, f"Creating user: {user_data.get('username')}")
            with DatabaseConnection() as conn:
                with conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            f"""
                            INSERT INTO {USERS_TABLE_NAME} (username, email, first_name, last_name)
                            VALUES (%s, %s, %s, %s)
                            RETURNING id, username, email, first_name, last_name, created_at::date
                        """,
                            (
                                user_data["username"],
                                user_data["email"],
                                user_data["first_name"],
                                user_data["last_name"],
                            ),
                        )

                        row = cursor.fetchone()
                        user = User(
                            id=row[0],
                            username=row[1],
                            email=row[2],
                            first_name=row[3],
                            last_name=row[4],
                            created_at=row[5],
                        )

                        log_debug(
                            logger, f"Created user: {user.username} with ID {user.id}"
                        )
                        return user

        except psycopg2.IntegrityError as e:
            error_detail = str(e).lower()
            if "ix_users_username" in error_detail or "username" in error_detail:
                raise ValueError(
                    f"Username '{user_data.get('username')}' already exists"
                )
            elif "ix_users_email" in error_detail or "email" in error_detail:
                raise ValueError(f"Email '{user_data.get('email')}' already exists")
            else:
                raise ValueError(f"User data violates database constraint: {e}")
        except Exception as e:
            log_error(logger, f"Failed to create user: {e}", exc_info=e)
            raise
