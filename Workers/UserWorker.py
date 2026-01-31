from Workers.BaseWorker import BaseWorker
from mysql.connector import Error
import sys
import traceback
import logging

logger = logging.getLogger(__name__)


class UserWorker(BaseWorker):
    """Worker class for handling user-related database operations."""

    def __init__(self):
        pass

    def _build_exception_dict(self, exception, context_info):
        _exc_type, _exc_value, exc_traceback = sys.exc_info()

        return {
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "traceback": traceback.format_exc(),
            "traceback_lines": traceback.format_tb(exc_traceback),
            "context": context_info,
            "exception_args": exception.args if hasattr(exception, 'args') else None
        }

    def create_user(self, clerk_user_id: str, username: str) -> dict:
        """
        Create a new user in the database.

        Args:
            clerk_user_id: The Clerk-provided user ID (e.g., 'user_xxx')
            username: The user's display name or email

        Returns:
            dict with 'passed' boolean and either user info or 'exception'
        """
        try:
            with self.get_connection_context() as connection:
                cursor = connection.cursor(dictionary=True)
                try:
                    # Check if user already exists
                    cursor.execute(
                        "SELECT clerk_user_id FROM users WHERE clerk_user_id = %s",
                        (clerk_user_id,)
                    )
                    existing = cursor.fetchone()

                    if existing:
                        logger.info(f"User {clerk_user_id} already exists, skipping creation")
                        return {
                            'passed': True,
                            'clerk_user_id': clerk_user_id,
                            'already_exists': True,
                            'message': 'User already exists'
                        }

                    # Insert new user
                    cursor.execute(
                        """
                        INSERT INTO users (clerk_user_id, username)
                        VALUES (%s, %s)
                        """,
                        (clerk_user_id, username)
                    )
                    connection.commit()

                    logger.info(f"Successfully created user {clerk_user_id}")
                    return {
                        'passed': True,
                        'clerk_user_id': clerk_user_id,
                        'already_exists': False,
                        'message': 'User created successfully'
                    }
                finally:
                    cursor.close()

        except Error as e:
            logger.error(f"Failed to create user {clerk_user_id}: {e}")
            return {
                'passed': False,
                'exception': self._build_exception_dict(e, {'clerk_user_id': clerk_user_id})
            }

    def delete_user(self, clerk_user_id: str) -> dict:
        """
        Delete a user and all associated data from the database.

        Args:
            clerk_user_id: The Clerk-provided user ID

        Returns:
            dict with 'passed' boolean and status information
        """
        try:
            with self.get_connection_context() as connection:
                cursor = connection.cursor()
                try:
                    # Delete in order respecting foreign key constraints:
                    # 1. Delete list_items for user's lists
                    cursor.execute(
                        """
                        DELETE li FROM list_items li
                        INNER JOIN user_lists ul ON li.list_id = ul.list_id
                        WHERE ul.clerk_user_id = %s
                        """,
                        (clerk_user_id,)
                    )

                    # 2. Delete user's lists
                    cursor.execute(
                        "DELETE FROM user_lists WHERE clerk_user_id = %s",
                        (clerk_user_id,)
                    )

                    # 3. Delete user's collection items
                    cursor.execute(
                        "DELETE FROM collection_items WHERE clerk_user_id = %s",
                        (clerk_user_id,)
                    )

                    # 4. Delete the user
                    cursor.execute(
                        "DELETE FROM users WHERE clerk_user_id = %s",
                        (clerk_user_id,)
                    )

                    rows_deleted = cursor.rowcount
                    connection.commit()

                    if rows_deleted == 0:
                        logger.warning(f"User {clerk_user_id} not found for deletion")
                        return {
                            'passed': True,
                            'message': 'User not found (may have already been deleted)'
                        }

                    logger.info(f"Successfully deleted user {clerk_user_id}")
                    return {
                        'passed': True,
                        'message': 'User deleted successfully'
                    }
                finally:
                    cursor.close()

        except Error as e:
            logger.error(f"Failed to delete user {clerk_user_id}: {e}")
            return {
                'passed': False,
                'exception': self._build_exception_dict(e, {'clerk_user_id': clerk_user_id})
            }
