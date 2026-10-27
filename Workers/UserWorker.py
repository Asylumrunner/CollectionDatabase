from Workers.BaseWorker import BaseWorker
from mysql.connector import Error
import sys
import traceback
import logging
import time

logger = logging.getLogger(__name__)


class UserWorker(BaseWorker):
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

    def create_user(self, clerk_user_id: str, username: str, webhook_id: str = None) -> dict:
        start = time.perf_counter()
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
                        logger.info(f"User already exists, skipping creation: webhook_id={webhook_id} duration_ms={(time.perf_counter() - start) * 1000:.0f}")
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

                    logger.info(f"Successfully created user: webhook_id={webhook_id} duration_ms={(time.perf_counter() - start) * 1000:.0f}")
                    return {
                        'passed': True,
                        'clerk_user_id': clerk_user_id,
                        'already_exists': False,
                        'message': 'User created successfully'
                    }
                finally:
                    cursor.close()

        except Error as e:
            # Log error codes only; MySQL error messages can echo row values back
            logger.error(f"Failed to create user: webhook_id={webhook_id} duration_ms={(time.perf_counter() - start) * 1000:.0f} error_type={type(e).__name__} errno={e.errno} sqlstate={e.sqlstate}")
            return {
                'passed': False,
                'exception': self._build_exception_dict(e, {'clerk_user_id': clerk_user_id})
            }

    def delete_user(self, clerk_user_id: str, webhook_id: str = None) -> dict:
        start = time.perf_counter()
        try:
            with self.get_connection_context() as connection:
                cursor = connection.cursor()
                try:
                    # Resolve clerk_user_id to internal user_id
                    cursor.execute(
                        "SELECT user_id FROM users WHERE clerk_user_id = %s",
                        (clerk_user_id,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        logger.warning(f"User not found for deletion: webhook_id={webhook_id} duration_ms={(time.perf_counter() - start) * 1000:.0f}")
                        return {
                            'passed': True,
                            'message': 'User not found (may have already been deleted)'
                        }
                    user_id = row[0]

                    # Delete in order respecting foreign key constraints:
                    # 1. Delete list_items for user's lists
                    cursor.execute(
                        """
                        DELETE li FROM list_items li
                        INNER JOIN user_lists ul ON li.list_id = ul.list_id
                        WHERE ul.user_id = %s
                        """,
                        (user_id,)
                    )
                    list_items_deleted = cursor.rowcount

                    # 2. Delete user's lists
                    cursor.execute(
                        "DELETE FROM user_lists WHERE user_id = %s",
                        (user_id,)
                    )
                    lists_deleted = cursor.rowcount

                    # 3. Delete user's collection items
                    cursor.execute(
                        "DELETE FROM collection_items WHERE user_id = %s",
                        (user_id,)
                    )
                    collection_items_deleted = cursor.rowcount

                    # 4. Delete the user
                    cursor.execute(
                        "DELETE FROM users WHERE user_id = %s",
                        (user_id,)
                    )

                    connection.commit()

                    logger.info(f"Successfully deleted user: webhook_id={webhook_id} lists={lists_deleted} list_items={list_items_deleted} collection_items={collection_items_deleted} duration_ms={(time.perf_counter() - start) * 1000:.0f}")
                    return {
                        'passed': True,
                        'message': 'User deleted successfully'
                    }
                finally:
                    cursor.close()

        except Error as e:
            logger.error(f"Failed to delete user: webhook_id={webhook_id} duration_ms={(time.perf_counter() - start) * 1000:.0f} error_type={type(e).__name__} errno={e.errno} sqlstate={e.sqlstate}")
            return {
                'passed': False,
                'exception': self._build_exception_dict(e, {'clerk_user_id': clerk_user_id})
            }
