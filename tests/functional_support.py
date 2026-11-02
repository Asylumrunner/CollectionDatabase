"""Helpers for functional tests that test modules import directly."""
import json
import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"

TEST_DATABASE = "collection_test"
# Everything except media_types, which the schema seeds and the app only reads
DATA_TABLES = [
    "album_tracks", "albums", "anime", "board_games", "books", "movies", "rpgs",
    "game_platform_availabilities", "video_game_platforms", "video_games",
    "item_creators", "creators", "item_genres", "genres",
    "list_items", "user_lists", "collection_items", "items", "users",
]


def assert_test_database(connection):
    """Refuses to go further unless connected to the disposable test database."""
    cursor = connection.cursor()
    cursor.execute("SELECT DATABASE()")
    name = cursor.fetchone()[0]
    cursor.close()
    if name != TEST_DATABASE:
        raise RuntimeError(f"Refusing to truncate database {name!r}; expected {TEST_DATABASE!r}")


def truncate_all(connection):
    assert_test_database(connection)
    cursor = connection.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in DATA_TABLES:
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    cursor.close()


def load_fixture(relative_path):
    return (FIXTURES / relative_path).read_text()


def load_json_fixture(relative_path):
    return json.loads(load_fixture(relative_path))
