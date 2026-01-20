from Workers.BaseWorker import BaseWorker
from DataClasses.item import Item
import sys
import traceback
import json

class ItemWorker(BaseWorker):
    def __init__(self):
        print("Placeholder for the init function!")

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

    def check_item(self, media_type, original_api_id):
        with self.get_cursor_context(dictionary=True) as cursor:
            query = "SELECT id FROM items WHERE media_type = %s AND original_api_id = %s"
            cursor.execute(query, (media_type, original_api_id))
            result = cursor.fetchone()
            return result['id'] if result else None

    def get_item_by_id(self, item_id):
        with self.get_cursor_context(dictionary=True) as cursor:
            query = "SELECT * FROM items_complete_view WHERE id = %s"
            cursor.execute(query, (item_id,))
            row = cursor.fetchone()

            if not row:
                return None

            creators = json.loads(row['creators']) if row['creators'] else []
            genres = json.loads(row['genres']) if row['genres'] else []
            platforms = json.loads(row['videogame_platforms']) if row['videogame_platforms'] else None
            tracklist = json.loads(row['album_tracks']) if row['album_tracks'] else None

            media_type = row['media_type']
            isbn = None
            printing_year = None
            lang = None
            duration = None
            min_players = None
            max_players = None
            episodes = None

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
            # video_game uses platforms (already parsed)
            # album uses tracklist (already parsed)

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

    def get_item(self, media_type, original_api_id):
        item_id = self.check_item(media_type, original_api_id)
        if item_id:
            return self.get_item_by_id(item_id)
        return None

    def add_item(self, item):
        response = {"passed": True, "Item": None, "already_exists": False}

        try:
            existing_item_id = self.check_item(item.media_type, item.original_api_id)
            if existing_item_id:
                response["Item"] = self.get_item_by_id(existing_item_id)
                response["already_exists"] = True
                return response

            with self.get_connection_context() as connection:
                cursor = connection.cursor(dictionary=True)
                try:
                    item_query = """
                        INSERT INTO items (title, media_type, release_year, img_link, original_api_id, summary)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    media_type_id = self.media_type_mappings.get(item.media_type)
                    if media_type_id is None:
                        raise ValueError(f"Unknown media type: {item.media_type}")

                    cursor.execute(item_query, (
                        item.title,
                        media_type_id,
                        item.release_year,
                        item.img_link,
                        item.original_api_id,
                        item.summary
                    ))
                    item_id = cursor.lastrowid

                    if item.created_by:
                        for creator_name in item.created_by:
                            creator_insert = """
                                INSERT IGNORE INTO creators (creator_name) VALUES (%s)
                            """
                            cursor.execute(creator_insert, (creator_name,))

                            cursor.execute("SELECT creator_id FROM creators WHERE creator_name = %s", (creator_name,))
                            creator_id = cursor.fetchone()['creator_id']

                            cursor.execute(
                                "INSERT INTO item_creators (item_id, creator_id) VALUES (%s, %s)",
                                (item_id, creator_id)
                            )

                    if item.genres:
                        for genre_name in item.genres:
                            genre_insert = """
                                INSERT IGNORE INTO genres (genre_name) VALUES (%s)
                            """
                            cursor.execute(genre_insert, (genre_name,))

                            cursor.execute("SELECT genre_id FROM genres WHERE genre_name = %s", (genre_name,))
                            genre_id = cursor.fetchone()['genre_id']

                            cursor.execute(
                                "INSERT INTO item_genres (item_id, genre_id) VALUES (%s, %s)",
                                (item_id, genre_id)
                            )

                    media_type_lower = item.media_type.lower()

                    if media_type_lower == 'book':
                        cursor.execute(
                            "INSERT INTO books (id, isbn, printing_year) VALUES (%s, %s, %s)",
                            (item_id, item.isbn, item.printing_year)
                        )

                    elif media_type_lower == 'movie':
                        cursor.execute(
                            "INSERT INTO movies (id, lang, duration) VALUES (%s, %s, %s)",
                            (item_id, item.lang, item.duration)
                        )

                    elif media_type_lower == 'video_game':
                        cursor.execute(
                            "INSERT INTO video_games (id) VALUES (%s)",
                            (item_id,)
                        )

                        if item.platforms:
                            for platform_name in item.platforms:
                                cursor.execute(
                                    "INSERT IGNORE INTO video_game_platforms (platform_name) VALUES (%s)",
                                    (platform_name,)
                                )

                                cursor.execute(
                                    "SELECT platform_id FROM video_game_platforms WHERE platform_name = %s",
                                    (platform_name,)
                                )
                                platform_id = cursor.fetchone()['platform_id']

                                cursor.execute(
                                    "INSERT INTO game_platform_availabilities (game_id, platform_id) VALUES (%s, %s)",
                                    (item_id, platform_id)
                                )

                    elif media_type_lower == 'board_game':
                        cursor.execute(
                            "INSERT INTO board_games (id, min_players, max_players, duration) VALUES (%s, %s, %s, %s)",
                            (item_id, item.min_players, item.max_players, item.duration)
                        )

                    elif media_type_lower == 'rpg':
                        cursor.execute(
                            "INSERT INTO rpgs (id, isbn) VALUES (%s, %s)",
                            (item_id, item.isbn)
                        )

                    elif media_type_lower == 'anime':
                        cursor.execute(
                            "INSERT INTO anime (id, episodes) VALUES (%s, %s)",
                            (item_id, item.episodes)
                        )

                    elif media_type_lower == 'album':
                        cursor.execute(
                            "INSERT INTO albums (id) VALUES (%s)",
                            (item_id,)
                        )

                        if item.tracklist:
                            for track_number, track_name in enumerate(item.tracklist, start=1):
                                cursor.execute(
                                    "INSERT INTO album_tracks (album_id, track_number, track_name) VALUES (%s, %s, %s)",
                                    (item_id, track_number, track_name)
                                )

                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
                finally:
                    cursor.close()

            # Fetch complete item AFTER releasing the connection to avoid pool exhaustion
            response["Item"] = self.get_item_by_id(item_id)
            return response

        except Exception as e:
            response["passed"] = False
            response["exception"] = self._build_exception_dict(e, {
                "function": "add_item",
                "media_type": item.media_type,
                "original_api_id": item.original_api_id,
                "title": item.title
            })
            return response

    def add_item_to_collection(self, user_id, item):
        add_item_response = self.add_item(item)
        if not add_item_response["passed"]:
            return {
                "passed": False,
                "step_failed": "add_item",
                "step_status": add_item_response
            }

        item_id = add_item_response["Item"].id

        current_step = None
        try:
            with self.get_connection_context() as connection:
                cursor = connection.cursor(dictionary=True)
                try:
                    # Check if item/user pairing already exists in collection_items
                    current_step = "check_collection_item_exists"
                    query = "SELECT * FROM collection_items WHERE item_id = %s AND user_id = %s"
                    cursor.execute(query, (item_id, user_id))
                    result = cursor.fetchone()

                    if result:
                        return {
                            "passed": True,
                            "already_exists": True,
                            "Item": add_item_response["Item"]
                        }

                    # Add item/user pairing to collection_items
                    current_step = "add_collection_item"
                    insert_query = "INSERT INTO collection_items (item_id, user_id) VALUES (%s, %s)"
                    cursor.execute(insert_query, (item_id, user_id))
                    connection.commit()

                    return {
                        "passed": True,
                        "already_exists": False,
                        "item_id": item_id,
                        "user_id": user_id
                    }
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
                    "function": "add_item_to_collection",
                    "step": current_step,
                    "item_id": item_id,
                    "user_id": user_id
                })
            }

