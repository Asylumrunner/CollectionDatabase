import json
import logging
from types import SimpleNamespace
from unittest import mock

import pytest
from mysql.connector import Error
from mysql.connector.errors import PoolError

import Workers.BaseWorker as base_worker_module
from Workers.BaseWorker import BaseWorker
from Workers.ItemWorker import ItemWorker
from Workers.ListWorker import ListWorker

from tests.helpers import FAKE_SECRETS, FakeDB

MEDIA_ROWS = [{"id": 1, "type_name": "book"}, {"id": 2, "type_name": "movie"}]


def fake_pool():
    return FakeDB().on("FROM media_types", rows=MEDIA_ROWS)


@pytest.fixture
def pool_class(monkeypatch):
    """Replaces the real pool class; each construction yields a new FakeDB-backed pool."""
    pool_constructor = mock.Mock(side_effect=lambda **kwargs: fake_pool())
    monkeypatch.setattr(base_worker_module.pooling, "MySQLConnectionPool", pool_constructor)
    return pool_constructor


@pytest.fixture
def local_config(monkeypatch, tmp_path):
    def write(**overrides):
        config = {"host": "local-host", "port": 3307, "database": "local_db",
                  "username": "local_user", "password": "local_password", **overrides}
        config = {k: v for k, v in config.items() if v is not None}
        path = tmp_path / "local_db_config.json"
        path.write_text(json.dumps(config))
        monkeypatch.setattr(base_worker_module, "_LOCAL_CONFIG_PATH", str(path))
    return write


def initialized_worker(pool):
    worker = ItemWorker()
    worker._pool_initialized = True
    worker._connection_pool = pool
    return worker


def fake_clock(monkeypatch, *ticks):
    monkeypatch.setattr(base_worker_module, "time", SimpleNamespace(perf_counter=mock.Mock(side_effect=list(ticks))))


def test_local_config_takes_precedence_over_secrets(pool_class, local_config):  # U-BASE-1
    local_config()
    ItemWorker().get_connection()
    kwargs = pool_class.call_args.kwargs
    assert (kwargs["host"], kwargs["port"], kwargs["database"], kwargs["user"], kwargs["password"]) == (
        "local-host", 3307, "local_db", "local_user", "local_password")


@pytest.mark.parametrize("configured, expected", [("3308", 3308), (None, 3306)])
def test_port_is_cast_and_defaulted(pool_class, local_config, configured, expected):  # U-BASE-2
    local_config(port=configured)
    ItemWorker().get_connection()
    assert pool_class.call_args.kwargs["port"] == expected


def test_secrets_are_used_without_a_local_config(pool_class):  # U-BASE-3
    ItemWorker().get_connection()
    kwargs = pool_class.call_args.kwargs
    assert kwargs["host"] == FAKE_SECRETS["database_endpoint"]
    assert kwargs["database"] == FAKE_SECRETS["collection_database_name"]
    assert kwargs["user"] == FAKE_SECRETS["database_username"]
    assert kwargs["password"] == FAKE_SECRETS["database_password"]
    assert kwargs["port"] == 3306


def test_incomplete_local_config_raises_and_leaves_pool_uninitialized(pool_class, local_config):  # U-BASE-4
    local_config(password=None)
    with pytest.raises(KeyError):
        ItemWorker().get_connection()
    assert not ItemWorker._pool_initialized


def test_failed_pool_creation_is_retried(pool_class):  # U-BASE-5
    pool_class.side_effect = [Error(msg="db down"), fake_pool()]
    worker = ItemWorker()
    with pytest.raises(Error):
        worker.get_connection()
    assert worker.get_connection() is not None
    assert pool_class.call_count == 2


def test_pool_is_only_created_once(pool_class):  # U-BASE-6
    worker = ItemWorker()
    worker.get_connection()
    worker.get_connection()
    assert pool_class.call_count == 1


def test_media_type_mappings_are_loaded_and_resources_released(pool_class):  # U-BASE-7
    pool = fake_pool()
    pool_class.side_effect = [pool]
    ItemWorker().get_connection()
    assert BaseWorker.media_type_mappings == {"book": 1, "movie": 2}
    assert pool.events.index("cursor_close") < pool.events.index("close")


@pytest.mark.xfail(reason="B3: pool is marked initialized before mappings load, so a failed load never retries")
def test_failed_mapping_load_is_retried(pool_class):  # U-BASE-8
    failing = FakeDB().fail_on("FROM media_types", Error(msg="transient"))
    pool_class.side_effect = [failing, fake_pool()]
    worker = ItemWorker()
    with pytest.raises(Error):
        worker.get_connection()
    worker.get_connection()
    assert BaseWorker.media_type_mappings == {"book": 1, "movie": 2}


@pytest.mark.xfail(reason="B14: pool state is assigned to cls, so each worker subclass builds its own pool")
def test_workers_share_one_pool(pool_class):  # U-BASE-9
    ItemWorker().get_connection()
    ListWorker().get_connection()
    assert ItemWorker._connection_pool is ListWorker._connection_pool


def test_pool_exhaustion_is_logged_and_reraised(caplog):  # U-BASE-10
    pool = mock.Mock()
    pool.get_connection.side_effect = PoolError(msg="exhausted")
    with pytest.raises(PoolError):
        initialized_worker(pool).get_connection()
    assert "Connection pool exhausted" in caplog.text
    assert "pool_size=5" in caplog.text
    assert "caller=" in caplog.text


def test_other_connection_errors_are_logged_and_reraised(caplog):  # U-BASE-11
    pool = mock.Mock()
    pool.get_connection.side_effect = Error(msg="lost connection")
    with pytest.raises(Error):
        initialized_worker(pool).get_connection()
    assert "Failed to get connection from pool" in caplog.text


@pytest.mark.parametrize("context_name", ["get_connection_context", "get_cursor_context"])
def test_connection_is_closed_on_normal_exit(db, context_name):  # U-BASE-12
    worker = ItemWorker()
    worker.get_connection = db.get_connection
    with getattr(worker, context_name)():
        assert db.count("close") == 0
    assert db.count("close") == 1


@pytest.mark.parametrize("context_name", ["get_connection_context", "get_cursor_context"])
def test_connection_is_closed_when_the_body_raises(db, context_name):  # U-BASE-12
    worker = ItemWorker()
    worker.get_connection = db.get_connection
    with pytest.raises(Error):
        with getattr(worker, context_name)():
            raise Error(msg="query failed")
    assert db.count("close") == 1


@pytest.mark.parametrize("seconds, warns", [(0.5, True), (0.01, False)])
def test_slow_acquire_warning(db, monkeypatch, caplog, seconds, warns):  # U-BASE-13
    worker = ItemWorker()
    worker.get_connection = db.get_connection
    fake_clock(monkeypatch, 0, seconds, seconds)
    with worker.get_connection_context():
        pass
    assert ("Slow connection acquire" in caplog.text) is warns


@pytest.mark.parametrize("seconds, warns", [(2.0, True), (0.5, False)])
def test_long_hold_warning(db, monkeypatch, caplog, seconds, warns):  # U-BASE-14
    worker = ItemWorker()
    worker.get_connection = db.get_connection
    fake_clock(monkeypatch, 0, 0, seconds)
    with worker.get_connection_context():
        pass
    assert ("Connection held a long time" in caplog.text) is warns


@pytest.mark.parametrize("dictionary", [True, False])
def test_cursor_context_passes_dictionary_flag(db, dictionary):  # U-BASE-15
    worker = ItemWorker()
    worker.get_connection = db.get_connection
    with worker.get_cursor_context(dictionary=dictionary):
        pass
    assert f"cursor:dictionary={dictionary}" in db.events


def test_cursor_is_closed_before_connection_even_on_exception(db):  # U-BASE-15
    worker = ItemWorker()
    worker.get_connection = db.get_connection
    with pytest.raises(ValueError):
        with worker.get_cursor_context():
            raise ValueError("boom")
    assert db.events.index("cursor_close") < db.events.index("close")


def test_non_database_errors_still_close_the_connection(db, caplog):  # U-BASE-16
    worker = ItemWorker()
    worker.get_connection = db.get_connection
    with pytest.raises(ValueError):
        with worker.get_connection_context():
            raise ValueError("boom")
    assert db.count("close") == 1
    assert "Database error" not in caplog.text


@pytest.mark.xfail(reason="B13: context managers log the raw DB message, which can echo identifiers")
@pytest.mark.parametrize("context_name", ["get_connection_context", "get_cursor_context"])
def test_raw_database_messages_are_not_logged(db, caplog, context_name):  # U-BASE-17
    worker = ItemWorker()
    worker.get_connection = db.get_connection
    with pytest.raises(Error):
        with getattr(worker, context_name)():
            raise Error(msg="Duplicate entry 'user_123' for key 'clerk_user_id'", errno=1062)
    assert "user_123" not in caplog.text


def test_error_log_fields_formats_database_errors():  # U-BASE-18
    fields = ItemWorker()._error_log_fields(Error(msg="secret value", errno=1062, sqlstate="23000"))
    assert fields == "error_type=Error errno=1062 sqlstate=23000"


def test_error_log_fields_handles_errors_without_codes():  # U-BASE-18
    assert ItemWorker()._error_log_fields(ValueError("x")) == "error_type=ValueError errno=None sqlstate=None"


def test_find_caller_reports_the_worker_method(db, monkeypatch, caplog):  # U-BASE-19
    class ProbeWorker(ItemWorker):
        def probing_method(self):
            with self.get_cursor_context():
                pass

    worker = ProbeWorker()
    worker.get_connection = db.get_connection
    fake_clock(monkeypatch, 0, 0.5, 0.5)
    caplog.set_level(logging.WARNING)
    worker.probing_method()
    assert "caller=test_base_worker.py:probing_method:" in caplog.text
