from unittest import mock

import pytest
import pytest_socket
import responses as responses_lib

import Workers.BaseWorker as base_worker_module
from Workers.BaseWorker import BaseWorker
from Workers.ItemWorker import ItemWorker
from Workers.ListWorker import ListWorker
from Workers.SearchWorker import SearchWorker
from Workers.UserWorker import UserWorker

from tests.conftest import fake_twitch_token
from tests.helpers import MEDIA_TYPE_IDS, FakeDB, reset_pool_state


@pytest.fixture(autouse=True)
def isolate_from_outside_world(monkeypatch, tmp_path):
    pytest_socket.disable_socket()
    monkeypatch.setattr(base_worker_module, "_LOCAL_CONFIG_PATH", str(tmp_path / "no_such_config.json"))
    reset_pool_state()
    yield
    reset_pool_state()
    pytest_socket.enable_socket()


@pytest.fixture
def loaded_mappings():
    BaseWorker.media_type_mappings.update(MEDIA_TYPE_IDS)


@pytest.fixture
def db():
    return FakeDB()


def _with_db(worker, db):
    worker.get_connection = db.get_connection
    return worker


@pytest.fixture
def item_worker(db, loaded_mappings):
    db.on("SELECT user_id FROM users", rows=[{"user_id": 7}])
    db.on("SELECT creator_id", rows=[{"creator_id": 5}])
    db.on("SELECT genre_id", rows=[{"genre_id": 6}])
    db.on("SELECT platform_id", rows=[{"platform_id": 8}])
    return _with_db(ItemWorker(), db)


@pytest.fixture
def list_worker(db):
    db.on("SELECT user_id FROM users", rows=[{"user_id": 7}])
    return _with_db(ListWorker(), db)


@pytest.fixture
def user_worker(db):
    return _with_db(UserWorker(), db)


@pytest.fixture
def search_worker():
    with mock.patch("requests.post", return_value=fake_twitch_token()):
        return SearchWorker()


@pytest.fixture
def rsps():
    with responses_lib.RequestsMock(assert_all_requests_are_fired=False) as requests_mock:
        yield requests_mock


@pytest.fixture
def mock_workers(api_module, monkeypatch):
    workers = {name: mock.MagicMock() for name in ("SEARCH", "ITEM", "USER", "LIST")}
    monkeypatch.setattr(api_module, "workers", workers)
    return workers


@pytest.fixture
def client(api_module, mock_workers, monkeypatch):
    """Test client with mocked workers, signed in as user_1."""
    monkeypatch.setenv("SKIP_AUTH", "true")
    monkeypatch.setenv("DEV_USER_ID", "user_1")
    return api_module.app.test_client()
