import logging
from typing import List, Optional, Dict, Any
from app.core.database import DatabaseConnection
from app.core.logging import log_debug, log_error
from app.models.users import User

logger = logging.getLogger(__name__)

# Table names as constants
USERS_TABLE_NAME = "users"
BORROWINGS_TABLE_NAME = "borrowings"
COPIES_TABLE_NAME = "copies"
BOOKS_TABLE_NAME = "books"


class UserPsql:
    """Data access layer for user operations"""

    async def get_all_users(self, active_only: bool = True) -> List[User]:
        """Get all users"""
        try:
            log_debug(logger, f"Fetching users (active_only={active_only})")
            with DatabaseConnection() as conn:
                with conn.cursor() as cursor:
                    query = f"""
                        SELECT id, username, email, first_name, last_name, phone, active, created_at::date
                        FROM {USERS_TABLE_NAME}
                    """
                    if active_only:
                        query += " WHERE active = true"
                    query += " ORDER BY created_at DESC"

                    cursor.execute(query)
                    rows = cursor.fetchall()

                    users = [
                        User(
                            id=row[0], username=row[1], email=row[2], first_name=row[3],
                            last_name=row[4], phone=row[5], active=row[6], created_at=row[7]
                        )
                        for row in rows
                    ]

                    log_debug(logger, f"Retrieved {len(users)} users")
                    return users
        except Exception as e:
            log_error(logger, f"Failed to fetch users: {e}", exc_info=e)
            raise

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            log_debug(logger, f"Fetching user {user_id}")
            with DatabaseConnection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT id, username, email, first_name, last_name, phone, active, created_at::date
                        FROM {USERS_TABLE_NAME} WHERE id = %s
                    """, (user_id,))
                    row = cursor.fetchone()

                    if row:
                        user = User(
                            id=row[0], username=row[1], email=row[2], first_name=row[3],
                            last_name=row[4], phone=row[5], active=row[6], created_at=row[7]
                        )
                        log_debug(logger, f"Found user: {user.username}")
                        return user

                    return None
        except Exception as e:
            log_error(logger, f"Failed to fetch user {user_id}: {e}", exc_info=e)
            raise

    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create new user from dict data"""
        try:
            log_debug(logger, f"Creating user: {user_data.get('username')}")
            with DatabaseConnection() as conn:
                with conn:  # Transaction
                    with conn.cursor() as cursor:
                        # Check if username or email already exists
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM {USERS_TABLE_NAME} 
                            WHERE username = %s OR email = %s
                        """, (user_data['username'], user_data['email']))

                        if cursor.fetchone()[0] > 0:
                            raise ValueError("Username or email already exists")

                        # Create user
                        cursor.execute(f"""
                            INSERT INTO {USERS_TABLE_NAME} (username, email, first_name, last_name, phone)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING id, username, email, first_name, last_name, phone, active, created_at::date
                        """, (
                            user_data['username'],
                            user_data['email'],
                            user_data['first_name'],
                            user_data['last_name'],
                            user_data.get('phone')
                        ))

                        row = cursor.fetchone()
                        user = User(
                            id=row[0], username=row[1], email=row[2], first_name=row[3],
                            last_name=row[4], phone=row[5], active=row[6], created_at=row[7]
                        )

                        log_debug(logger, f"Created user: {user.username} with ID {user.id}")
                        return user
        except Exception as e:
            log_error(logger, f"Failed to create user: {e}", exc_info=e)
            raise

    async def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Optional[User]:
        """Update user from dict data"""
        try:
            log_debug(logger, f"Updating user {user_id}")
            with DatabaseConnection() as conn:
                with conn:  # Transaction
                    with conn.cursor() as cursor:
                        # Build dynamic update query from dict
                        update_fields = []
                        values = []

                        # Map dict keys to database columns
                        field_mapping = {
                            'username': 'username',
                            'email': 'email',
                            'first_name': 'first_name',
                            'last_name': 'last_name',
                            'phone': 'phone',
                            'active': 'active'
                        }

                        for key, db_field in field_mapping.items():
                            if key in user_data:
                                update_fields.append(f"{db_field} = %s")
                                values.append(user_data[key])

                        if not update_fields:
                            # No fields to update, just return current user
                            return await self.get_user_by_id(user_id)

                        values.append(user_id)  # for WHERE clause

                        cursor.execute(f"""
                            UPDATE {USERS_TABLE_NAME} 
                            SET {', '.join(update_fields)}
                            WHERE id = %s
                            RETURNING id, username, email, first_name, last_name, phone, active, created_at::date
                        """, values)

                        row = cursor.fetchone()
                        if row:
                            user = User(
                                id=row[0], username=row[1], email=row[2], first_name=row[3],
                                last_name=row[4], phone=row[5], active=row[6], created_at=row[7]
                            )
                            log_debug(logger, f"Updated user: {user.username}")
                            return user

                        return None
        except Exception as e:
            log_error(logger, f"Failed to update user {user_id}: {e}", exc_info=e)
            raise

    async def get_user_active_borrowings_count(self, user_id: int) -> int:
        """Get count of active borrowings for user"""
        try:
            log_debug(logger, f"Checking active borrowings for user {user_id}")
            with DatabaseConnection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM {BORROWINGS_TABLE_NAME}
                        WHERE user_id = %s AND returned_at IS NULL
                    """, (user_id,))

                    count = cursor.fetchone()[0]
                    log_debug(logger, f"User {user_id} has {count} active borrowings")
                    return count
        except Exception as e:
            log_error(logger, f"Failed to check active borrowings for user {user_id}: {e}", exc_info=e)
            raise

    async def get_user_borrowing_history(self, user_id: int, include_active: bool = True) -> List[Dict[str, Any]]:
        """Get borrowing history for user"""
        try:
            log_debug(logger, f"Fetching borrowing history for user {user_id}")
            with DatabaseConnection() as conn:
                with conn.cursor() as cursor:
                    query = f"""
                        SELECT b.title, br.borrowed_at, br.due_date, br.returned_at,
                               CASE WHEN br.returned_at IS NULL THEN true ELSE false END as is_active,
                               CASE WHEN br.due_date < CURRENT_DATE AND br.returned_at IS NULL THEN true ELSE false END as is_overdue
                        FROM {BORROWINGS_TABLE_NAME} br
                        JOIN {COPIES_TABLE_NAME} c ON br.copy_id = c.id
                        JOIN {BOOKS_TABLE_NAME} b ON c.book_id = b.id
                        WHERE br.user_id = %s
                    """

                    if not include_active:
                        query += " AND br.returned_at IS NOT NULL"

                    query += " ORDER BY br.borrowed_at DESC"

                    cursor.execute(query, (user_id,))
                    rows = cursor.fetchall()

                    history = []
                    for row in rows:
                        history.append({
                            'book_title': row[0],
                            'borrowed_at': row[1],
                            'due_date': row[2],
                            'returned_at': row[3],
                            'is_active': row[4],
                            'is_overdue': row[5]
                        })

                    log_debug(logger, f"Retrieved {len(history)} borrowing records for user {user_id}")
                    return history
        except Exception as e:
            log_error(logger, f"Failed to fetch borrowing history for user {user_id}: {e}", exc_info=e)
            raise

    async def can_user_be_deactivated(self, user_id: int) -> tuple[bool, str]:
        """Check if user can be deactivated (no active borrowings)"""
        try:
            active_count = await self.get_user_active_borrowings_count(user_id)

            if active_count > 0:
                return False, f"User has {active_count} active borrowing(s). All books must be returned before deactivation."

            return True, "User can be deactivated"
        except Exception as e:
            log_error(logger, f"Failed to check if user {user_id} can be deactivated: {e}", exc_info=e)
            raise
