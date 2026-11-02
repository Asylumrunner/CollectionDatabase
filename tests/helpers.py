"""Shared test doubles and factories. Importing this never touches a DB or the network."""
import base64
import datetime
import json
import re

from svix.webhooks import Webhook

from DataClasses.item import Item

WEBHOOK_SECRET = "whsec_" + base64.b64encode(b"collection-database-test-secret!").decode()

FAKE_SECRETS = {
    "database_endpoint": "secrets-db-host",
    "collection_database_name": "secrets_db_name",
    "database_username": "secrets_db_user",
    "database_password": "secrets_db_password",
    "BGG_API_Key": "fake-bgg-key",
    "MovieDB_Key": "fake-tmdb-key",
    "Discogs_Token": "fake-discogs-token",
    "IGDB_Client_ID": "fake-igdb-id",
    "IGDB_Client_Secret": "fake-igdb-secret",
    "CLERK_SECRET_KEY": "sk_test_fake",
    "CLERK_WEBHOOK_SECRET": WEBHOOK_SECRET,
}

MEDIA_TYPE_IDS = {
    "book": 1,
    "movie": 2,
    "video_game": 3,
    "board_game": 4,
    "rpg": 5,
    "anime": 6,
    "album": 7,
}
MEDIA_TYPES = list(MEDIA_TYPE_IDS)

# Fields each media type stores beyond the ones every item shares
SUBTYPE_FIELDS = {
    "book": {"isbn": "9780441013593", "printing_year": 1990},
    "movie": {"lang": "en", "duration": 155, "summary": "A movie summary"},
    "video_game": {"platforms": ["PC", "Dreamcast"], "summary": "A game summary"},
    "board_game": {"min_players": 3, "max_players": 4, "duration": 90, "summary": "A game summary"},
    "rpg": {"isbn": "1234567890", "summary": "An RPG summary"},
    "anime": {"episodes": 26, "summary": "An anime summary"},
    "album": {"tracklist": ["Zebra", "Apple", "Mango"], "genres": ["Jazz", "Funk"], "summary": "An album summary"},
}


def item_payload(media_type="book", original_api_id="api-1", **overrides):
    """A JSON body accepted by the item-adding routes."""
    payload = {
        "title": f"A {media_type}",
        "media_type": media_type,
        "release_year": 1999,
        "img_link": "https://example.test/cover.jpg",
        "original_api_id": original_api_id,
        "created_by": ["Some Creator"],
        **SUBTYPE_FIELDS[media_type],
    }
    payload.update(overrides)
    return payload


def make_item(media_type="book", original_api_id="api-1", **overrides):
    return Item(id="", **item_payload(media_type, original_api_id, **overrides))


def view_row(item_id=42, media_type="book", **overrides):
    """A row shaped like items_complete_view."""
    row = {
        "id": item_id,
        "title": "A title",
        "media_type": media_type,
        "release_year": 1999,
        "img_link": "https://example.test/cover.jpg",
        "original_api_id": "api-1",
        "summary": "A summary",
        "creators": None,
        "genres": None,
        "book_isbn": None,
        "book_printing_year": None,
        "movie_lang": None,
        "movie_duration": None,
        "boardgame_min_players": None,
        "boardgame_max_players": None,
        "boardgame_duration": None,
        "rpg_isbn": None,
        "anime_episodes": None,
        "videogame_platforms": None,
        "album_tracks": None,
    }
    row.update(overrides)
    return row


def _normalize_sql(sql):
    return re.sub(r"\s+", " ", sql).strip()


class FakeDB:
    """Stands in for a connection pool, recording everything the code under test does.

    Rules match on a substring of the whitespace-normalized SQL. Unit tests use them to
    script results and failures without asserting on full SQL text.
    """

    def __init__(self):
        self.rules = []
        self.calls = []
        self.events = []
        self.acquired = 0
        self.lastrowid = 42

    def on(self, sql_fragment, rows=None, rowcount=None):
        self.rules.append({"fragment": sql_fragment, "rows": rows or [], "rowcount": rowcount, "error": None})
        return self

    def fail_on(self, sql_fragment, error=None):
        # Failures win over any result rule registered for the same statement
        self.rules.insert(0, {"fragment": sql_fragment, "rows": [], "rowcount": None,
                              "error": error or RuntimeError(f"failed on {sql_fragment}")})
        return self

    def get_connection(self):
        self.acquired += 1
        self.events.append("acquire")
        return FakeConnection(self)

    # Query helpers for assertions
    def executed(self, sql_fragment):
        return [call for call in self.calls if sql_fragment in call["sql"]]

    def params(self, sql_fragment):
        return [call["params"] for call in self.executed(sql_fragment)]

    def count(self, event):
        return self.events.count(event)

    def index_of(self, sql_fragment):
        for i, event in enumerate(self.events):
            if event.startswith("execute:") and sql_fragment in event:
                return i
        raise AssertionError(f"{sql_fragment!r} was never executed; saw {self.events}")


class FakeConnection:
    connection_id = 1

    def __init__(self, db):
        self.db = db

    def cursor(self, dictionary=False):
        self.db.events.append(f"cursor:dictionary={dictionary}")
        return FakeCursor(self.db)

    def commit(self):
        self.db.events.append("commit")

    def rollback(self):
        self.db.events.append("rollback")

    def close(self):
        self.db.events.append("close")


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self._rows = []
        self.rowcount = -1
        self.lastrowid = db.lastrowid

    def _run(self, sql, params):
        sql = _normalize_sql(sql)
        self.db.calls.append({"sql": sql, "params": params})
        self.db.events.append(f"execute:{sql}")
        self._rows = []
        self.rowcount = -1
        for rule in self.db.rules:
            if rule["fragment"] in sql:
                if rule["error"]:
                    raise rule["error"]
                self._rows = list(rule["rows"])
                self.rowcount = rule["rowcount"] if rule["rowcount"] is not None else len(rule["rows"])
                return

    def execute(self, sql, params=None):
        self._run(sql, params)

    def executemany(self, sql, seq_params):
        self._run(sql, list(seq_params))

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows

    def close(self):
        self.db.events.append("cursor_close")


def reset_pool_state():
    """Put every worker class back to its just-imported state.

    `_initialize_pool` assigns to `cls`, so pool state lands on each subclass. Resetting
    BaseWorker alone would leave the subclasses' pools in place.
    """
    from Workers.BaseWorker import BaseWorker
    from Workers.ItemWorker import ItemWorker
    from Workers.ListWorker import ListWorker
    from Workers.SearchWorker import SearchWorker
    from Workers.UserWorker import UserWorker

    for cls in (ItemWorker, ListWorker, UserWorker, SearchWorker):
        for attr in ("_connection_pool", "_pool_initialized"):
            if attr in cls.__dict__:
                delattr(cls, attr)
    BaseWorker._connection_pool = None
    BaseWorker._pool_initialized = False
    BaseWorker.media_type_mappings.clear()


def signed_webhook(payload, secret=WEBHOOK_SECRET, msg_id="msg_test_1", timestamp=None):
    """Returns (body, headers) carrying a real Svix signature."""
    timestamp = timestamp or datetime.datetime.now(datetime.timezone.utc)
    body = payload if isinstance(payload, str) else json.dumps(payload)
    signature = Webhook(secret).sign(msg_id, timestamp, body)
    return body, {
        "svix-id": msg_id,
        "svix-timestamp": str(int(timestamp.timestamp())),
        "svix-signature": signature,
    }
