"""Functional tests run the real app. Only third-party APIs are stubbed.

Tests that need MySQL ask for the `db` fixture. Everything else (auth rejections, search
against stubbed APIs) runs without one.

MySQL comes from a throwaway Docker container, or from the server named by TEST_DB_HOST
(with TEST_DB_PORT, TEST_DB_USER, TEST_DB_PASSWORD). Either way only the collection_test
database is touched.
"""
import json
import os
import pathlib
import time

import mysql.connector
import pytest
import pytest_socket
import responses as responses_lib

import Workers.BaseWorker as base_worker_module

from tests.functional_support import TEST_DATABASE, assert_test_database, truncate_all
from tests.helpers import signed_webhook

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "SQL" / "database.sql"

DB_READY_TIMEOUT_SECONDS = 180


def pytest_collection_modifyitems(items):
    for item in items:
        if "functional" in item.path.parts:
            item.add_marker(pytest.mark.functional)


def _connect(config, **overrides):
    return mysql.connector.connect(
        host=config["host"], port=config["port"], user=config["username"],
        password=config["password"], **overrides,
    )


def _wait_for_schema(config):
    # The image's init script restarts the server, so keep retrying until the seed data is visible
    deadline = time.monotonic() + DB_READY_TIMEOUT_SECONDS
    last_error = None
    while time.monotonic() < deadline:
        try:
            connection = _connect(config, database=TEST_DATABASE)
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM media_types")
            count = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            if count == 7:
                return
        except mysql.connector.Error as e:
            last_error = e
        time.sleep(1)
    raise RuntimeError(f"MySQL wasn't ready within {DB_READY_TIMEOUT_SECONDS}s: {last_error}")


def _load_schema_into_external_server(config):
    connection = _connect(config, autocommit=True)
    cursor = connection.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS {TEST_DATABASE}")
    cursor.execute(f"CREATE DATABASE {TEST_DATABASE}")
    cursor.execute(f"USE {TEST_DATABASE}")
    for statement in SCHEMA_PATH.read_text().split(";"):
        if statement.strip():
            cursor.execute(statement)
    cursor.close()
    connection.close()


def _allowed_hosts():
    hosts = ["127.0.0.1", "localhost"]
    if os.environ.get("TEST_DB_HOST"):
        hosts.append(os.environ["TEST_DB_HOST"])
    return hosts


@pytest.fixture(autouse=True)
def only_local_network():
    pytest_socket.socket_allow_hosts(_allowed_hosts(), allow_unix_socket=True)
    yield
    pytest_socket._remove_restrictions()


@pytest.fixture(autouse=True)
def never_touch_the_dev_database(monkeypatch, tmp_path):
    """Without this, any test reaching a worker would connect using local_db_config.json."""
    path = tmp_path / "unreachable_db_config.json"
    path.write_text(json.dumps({
        "host": "127.0.0.1", "port": 1, "database": TEST_DATABASE, "username": "nobody", "password": "nobody",
    }))
    monkeypatch.setattr(base_worker_module, "_LOCAL_CONFIG_PATH", str(path))


@pytest.fixture(scope="session")
def test_db_config():
    if os.environ.get("TEST_DB_HOST"):
        config = {
            "host": os.environ["TEST_DB_HOST"],
            "port": int(os.environ.get("TEST_DB_PORT", 3306)),
            "username": os.environ.get("TEST_DB_USER", "root"),
            "password": os.environ.get("TEST_DB_PASSWORD", ""),
            "database": TEST_DATABASE,
        }
        _load_schema_into_external_server(config)
        yield config
        return

    from testcontainers.core.container import DockerContainer

    password = "test-only-password"
    try:
        container = (
            DockerContainer("mysql:8.0")
            .with_env("MYSQL_ROOT_PASSWORD", password)
            .with_env("MYSQL_DATABASE", TEST_DATABASE)
            .with_exposed_ports(3306)
            .with_volume_mapping(str(SCHEMA_PATH), "/docker-entrypoint-initdb.d/database.sql", "ro")
        )
        container.start()
    except Exception as e:
        pytest.fail(f"Couldn't start MySQL in Docker ({e}). Fix Docker access or set TEST_DB_HOST.", pytrace=False)
    try:
        config = {
            "host": container.get_container_host_ip(),
            "port": int(container.get_exposed_port(3306)),
            "username": "root",
            "password": password,
            "database": TEST_DATABASE,
        }
        _wait_for_schema(config)
        yield config
    finally:
        container.stop()


class Database:
    """Direct DB access for arranging tests and asserting on rows, bypassing the app."""

    def __init__(self, connection):
        self.connection = connection

    def rows(self, sql, params=()):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def scalar(self, sql, params=()):
        return next(iter(self.rows(sql, params)[0].values()))

    def count(self, table):
        return self.scalar(f"SELECT COUNT(*) FROM {table}")

    def execute(self, sql, params=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        cursor.close()

    def add_user(self, clerk_user_id, username="someone"):
        self.execute("INSERT INTO users (clerk_user_id, username) VALUES (%s, %s)", (clerk_user_id, username))


@pytest.fixture(scope="session")
def _db_connection(test_db_config):
    connection = _connect(test_db_config, database=TEST_DATABASE, autocommit=True)
    assert_test_database(connection)
    yield connection
    connection.close()


@pytest.fixture
def test_db_path(test_db_config, tmp_path):
    path = tmp_path / "test_db_config.json"
    path.write_text(json.dumps(test_db_config))
    return str(path)


@pytest.fixture
def db(_db_connection, test_db_path, monkeypatch, never_touch_the_dev_database):
    """An empty test database, with the app configured to use it."""
    truncate_all(_db_connection)
    monkeypatch.setattr(base_worker_module, "_LOCAL_CONFIG_PATH", test_db_path)
    return Database(_db_connection)


class UserClient:
    """Test client signed in as one user. SKIP_AUTH and DEV_USER_ID are read per request,
    so tests can act as several users. Real tokens are covered in test_auth.py."""

    def __init__(self, app, monkeypatch, user_id):
        self.app = app
        self.monkeypatch = monkeypatch
        self.user_id = user_id

    def open(self, path, method, **kwargs):
        self.monkeypatch.setenv("SKIP_AUTH", "true")
        self.monkeypatch.setenv("DEV_USER_ID", self.user_id)
        return self.app.test_client().open(path, method=method, **kwargs)

    def get(self, path, **kwargs):
        return self.open(path, "GET", **kwargs)

    def put(self, path, **kwargs):
        return self.open(path, "PUT", **kwargs)

    def post(self, path, **kwargs):
        return self.open(path, "POST", **kwargs)

    def delete(self, path, **kwargs):
        return self.open(path, "DELETE", **kwargs)


@pytest.fixture
def client_as(api_module, monkeypatch):
    def build(user_id):
        return UserClient(api_module.app, monkeypatch, user_id)
    return build


@pytest.fixture
def user_a(db, client_as):
    db.add_user("user_a", "Alice Example")
    return client_as("user_a")


@pytest.fixture
def user_b(db, client_as):
    db.add_user("user_b", "Bob Example")
    return client_as("user_b")


@pytest.fixture
def anonymous(api_module):
    return api_module.app.test_client()


@pytest.fixture
def send_webhook(anonymous):
    """Posts a webhook with a real Svix signature."""
    counter = iter(range(1, 1000))

    def send(event_type, data, msg_id=None):
        payload = {"type": event_type, "data": data}
        body, headers = signed_webhook(payload, msg_id=msg_id or f"msg_{next(counter)}")
        return anonymous.post("/webhooks/clerk", data=body, headers=headers)
    return send


@pytest.fixture
def rsps():
    with responses_lib.RequestsMock(assert_all_requests_are_fired=False) as requests_mock:
        yield requests_mock
