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

    def get_user_lists(self, user_id):
        current_step = None
        try:
            with self.get_cursor_context(dictionary=True) as cursor:
                current_step = "resolve_user_id"
                internal_user_id = resolve_user_id(cursor, user_id)

                current_step = "fetch_lists"
                query = """
                    SELECT * FROM (
                        SELECT
                            ul.list_id,
                            ul.list_name,
                            v.id,
                            v.img_link,
                            ROW_NUMBER() OVER (
                                PARTITION BY ul.list_id ORDER BY li.date_added DESC
                            ) AS rn
                        FROM user_lists ul
                        LEFT JOIN list_items li ON ul.list_id = li.list_id
                        LEFT JOIN items i ON li.item_id = i.id
                        LEFT JOIN items_complete_view v ON li.item_id = v.id
                        WHERE ul.user_id = %s
                    ) ranked
                    WHERE rn <= 10
                    ORDER BY list_id, rn
                """
                cursor.execute(query, (internal_user_id,))
                rows = cursor.fetchall()

            lists = {}
            list_order = []
            for row in rows:
                list_id = row['list_id']
                if list_id not in lists:
                    lists[list_id] = {
                        "list_id": list_id,
                        "list_name": row['list_name'],
                        "img_links": []
                    }
                    list_order.append(list_id)
                if row['id'] is not None:
                    lists[list_id]["img_links"].append(row['img_link'])

            return {
                "passed": True,
                "lists": [lists[lid] for lid in list_order]
            }

        except Exception as e:
            return {
                "passed": False,
                "step_failed": current_step,
                "exception": self._build_exception_dict(e, {
                    "function": "get_user_lists",
                    "step": current_step,
                    "user_id": user_id
                })
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
