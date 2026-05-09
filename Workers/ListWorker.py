from Workers.BaseWorker import BaseWorker
from DataClasses.item import Item
from Utilities.ResolveUserId import resolve_user_id
import sys
import traceback
import json
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

    def _row_to_item(self, row):
        creators = json.loads(row['creators']) if row['creators'] else []
        genres = json.loads(row['genres']) if row['genres'] else []
        platforms = json.loads(row['videogame_platforms']) if row['videogame_platforms'] else None
        tracklist = json.loads(row['album_tracks']) if row['album_tracks'] else None

        media_type = row['media_type']
        isbn = printing_year = lang = duration = min_players = max_players = episodes = None

        if media_type == 'book':
            isbn = row['book_isbn']
            printing_year = row['book_printing_year']
        elif media_type == 'movie':
            lang = row['movie_lang']
            duration = row['movie_duration']
        elif media_type == 'board_game':
            min_players = row['boardgame_min_players']
            max_players = row['boardgame_max_players']
            duration = row['boardgame_duration']
        elif media_type == 'rpg':
            isbn = row['rpg_isbn']
        elif media_type == 'anime':
            episodes = row['anime_episodes']

        return Item(
            id=str(row['id']),
            title=row['title'],
            media_type=row['media_type'],
            release_year=row['release_year'],
            img_link=row['img_link'],
            original_api_id=row['original_api_id'],
            created_by=creators,
            isbn=isbn,
            printing_year=printing_year,
            lang=lang,
            summary=row['summary'],
            duration=duration,
            min_players=min_players,
            max_players=max_players,
            episodes=episodes,
            platforms=platforms,
            tracklist=tracklist,
            genres=genres
        )

    PAGE_SIZE = 25

    def get_list(self, user_id, list_id, page):
        current_step = None
        try:
            with self.get_cursor_context(dictionary=True) as cursor:
                current_step = "resolve_user_id"
                internal_user_id = resolve_user_id(cursor, user_id)

                current_step = "verify_list_ownership"
                cursor.execute(
                    "SELECT list_name FROM user_lists WHERE list_id = %s AND user_id = %s",
                    (list_id, internal_user_id)
                )
                list_row = cursor.fetchone()
                if not list_row:
                    return {"passed": True, "not_found": True}

                current_step = "fetch_list_items"
                offset = (page - 1) * self.PAGE_SIZE
                cursor.execute(
                    """
                    SELECT v.* FROM items_complete_view v
                    INNER JOIN list_items li ON li.item_id = v.id
                    WHERE li.list_id = %s
                    ORDER BY li.date_added DESC
                    LIMIT %s OFFSET %s
                    """,
                    (list_id, self.PAGE_SIZE + 1, offset)
                )
                rows = cursor.fetchall()

            has_more = len(rows) > self.PAGE_SIZE
            items = [self._row_to_item(row) for row in rows[:self.PAGE_SIZE]]

            return {
                "passed": True,
                "not_found": False,
                "list_name": list_row['list_name'],
                "items": items,
                "next_page": page + 1 if has_more else None
            }

        except Exception as e:
            return {
                "passed": False,
                "step_failed": current_step,
                "exception": self._build_exception_dict(e, {
                    "function": "get_list",
                    "step": current_step,
                    "user_id": user_id,
                    "list_id": list_id,
                    "page": page
                })
            }

    def get_list_names(self, user_id):
        current_step = None
        try:
            with self.get_cursor_context(dictionary=True) as cursor:
                current_step = "resolve_user_id"
                internal_user_id = resolve_user_id(cursor, user_id)

                current_step = "fetch_list_names"
                cursor.execute(
                    "SELECT list_id, list_name FROM user_lists WHERE user_id = %s ORDER BY date_added",
                    (internal_user_id,)
                )
                rows = cursor.fetchall()

            return {"passed": True, "lists": rows}

        except Exception as e:
            return {
                "passed": False,
                "step_failed": current_step,
                "exception": self._build_exception_dict(e, {
                    "function": "get_list_names",
                    "step": current_step,
                    "user_id": user_id
                })
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

    def add_item_to_list(self, user_id, list_id, item_id):
        current_step = None
        try:
            with self.get_connection_context() as connection:
                cursor = connection.cursor(dictionary=True)
                try:
                    current_step = "resolve_user_id"
                    internal_user_id = resolve_user_id(cursor, user_id)

                    current_step = "verify_list_ownership"
                    cursor.execute(
                        "SELECT list_id FROM user_lists WHERE list_id = %s AND user_id = %s",
                        (list_id, internal_user_id)
                    )
                    if not cursor.fetchone():
                        return {"passed": True, "not_found": True}

                    current_step = "check_item_in_list"
                    cursor.execute(
                        "SELECT item_id FROM list_items WHERE list_id = %s AND item_id = %s",
                        (list_id, item_id)
                    )
                    if cursor.fetchone():
                        return {"passed": True, "not_found": False, "already_exists": True}

                    current_step = "insert_list_item"
                    cursor.execute(
                        "INSERT INTO list_items (item_id, list_id) VALUES (%s, %s)",
                        (item_id, list_id)
                    )
                    connection.commit()

                    return {"passed": True, "not_found": False, "already_exists": False}
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
                    "function": "add_item_to_list",
                    "step": current_step,
                    "user_id": user_id,
                    "list_id": list_id,
                    "item_id": item_id
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
