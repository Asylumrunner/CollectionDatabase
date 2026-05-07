from Workers.BaseWorker import BaseWorker
from Utilities.ResolveUserId import resolve_user_id
import sys
import traceback
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')


class ListWorker(BaseWorker):
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

    def create_list(self, user_id, list_name):
        current_step = None
        try:
            with self.get_connection_context() as connection:
                cursor = connection.cursor(dictionary=True)
                try:
                    current_step = "resolve_user_id"
                    internal_user_id = resolve_user_id(cursor, user_id)

                    current_step = "insert_list"
                    cursor.execute(
                        "INSERT INTO user_lists (list_name, user_id) VALUES (%s, %s)",
                        (list_name, internal_user_id)
                    )
                    list_id = cursor.lastrowid
                    connection.commit()

                    return {"passed": True, "list_id": list_id, "list_name": list_name}
                except Exception:
                    connection.rollback()
                    raise
                finally:
                    cursor.close()

        except Exception as e:
            return {
                "passed": False,
                "step_failed": current_step,
                "exception": self._build_exception_dict(e, {
                    "function": "create_list",
                    "step": current_step,
                    "user_id": user_id,
                    "list_name": list_name
                })
            }
