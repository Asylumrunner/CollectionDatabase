import importlib.util
import json
import logging
import pathlib
from unittest import mock

import pytest
import requests

import Workers.BaseWorker as base_worker_module
from Workers.ItemWorker import ItemWorker

from tests.helpers import item_payload, reset_pool_state, signed_webhook

API_PATH = pathlib.Path(__file__).resolve().parents[2] / "api.py"


@pytest.fixture
def fresh_pools():
    """For tests that break or replace pools: start and finish with none."""
    reset_pool_state()
    yield
    reset_pool_state()


def import_api_with_twitch_down():
    spec = importlib.util.spec_from_file_location("api_twitch_down", API_PATH)
    module = importlib.util.module_from_spec(spec)
    with mock.patch("requests.post", side_effect=requests.exceptions.ConnectionError("twitch down")):
        spec.loader.exec_module(module)
    return module


def test_failing_requests_dont_leak_connections(user_a, client_as):  # F-RES-1
    no_such_user = client_as("not_in_users")
    bad_type = item_payload() | {"media_type": "not_a_type"}
    for _ in range(5):
        assert user_a.put("/collection/item", json=item_payload(release_year="not a year")).status_code == 500
        assert user_a.put("/collection/item", json=bad_type).status_code == 500
        assert no_such_user.get("/collection").status_code == 500
        assert user_a.get("/collection?page=0").status_code >= 400
    assert user_a.get("/collection").status_code == 200
    assert user_a.put("/collection/item", json=item_payload()).status_code == 200


def test_pool_exhaustion_fails_fast_and_recovers(user_a):  # F-RES-2
    assert user_a.get("/collection").status_code == 200  # ensures the pool exists
    held = [ItemWorker._connection_pool.get_connection() for _ in range(5)]
    try:
        response = user_a.get("/collection")
        assert response.status_code == 500
        assert response.get_json()["status"] == "FAILURE"
    finally:
        for connection in held:
            connection.close()
    assert user_a.get("/collection").status_code == 200


def test_unreachable_db_fails_cleanly_and_recovers(user_a, test_db_path, tmp_path, monkeypatch, fresh_pools):  # F-RES-3
    unreachable = tmp_path / "unreachable.json"
    unreachable.write_text(json.dumps({
        "host": "127.0.0.1", "port": 1, "database": "collection_test", "username": "x", "password": "x",
    }))
    monkeypatch.setattr(base_worker_module, "_LOCAL_CONFIG_PATH", str(unreachable))
    response = user_a.get("/collection")
    assert response.status_code == 500
    assert response.get_json()["status"] == "FAILURE"

    monkeypatch.setattr(base_worker_module, "_LOCAL_CONFIG_PATH", test_db_path)
    assert user_a.get("/collection").status_code == 200


@pytest.mark.xfail(reason="B2: on a cold pool, check_item can't see the mappings, so an existing item looks new")
def test_cold_start_re_adding_an_existing_item(user_a, fresh_pools):  # F-RES-4
    assert user_a.put("/collection/item", json=item_payload()).status_code == 200
    reset_pool_state()  # what a new process, such as a Lambda cold start, looks like
    response = user_a.put("/collection/item", json=item_payload())
    assert response.status_code == 200
    assert response.get_json()["data"]["already_exists"] is True


@pytest.mark.xfail(reason="B20: an IGDB token failure at import takes down the entire API")
def test_twitch_outage_at_startup_only_affects_search(monkeypatch):  # F-RES-5
    module = import_api_with_twitch_down()
    monkeypatch.setenv("SKIP_AUTH", "true")
    client = module.app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/search/dune?media_type=video_game").status_code == 500


@pytest.mark.xfail(reason="B20: an IGDB token failure at import takes down the entire API")
def test_twitch_outage_at_startup_leaves_db_routes_working(db, monkeypatch):  # F-RES-5
    module = import_api_with_twitch_down()
    db.add_user("user_a")
    monkeypatch.setenv("SKIP_AUTH", "true")
    monkeypatch.setenv("DEV_USER_ID", "user_a")
    assert module.app.test_client().get("/collection").status_code == 200


def test_logs_contain_no_user_identifiers(anonymous, client_as, db, caplog):  # F-RES-6
    # Unlike the plan's first draft this isn't an expected failure: B13 needs a duplicate-key
    # race to trigger through the API, so that case is pinned by U-BASE-17 instead.
    caplog.set_level(logging.DEBUG)
    clerk_id = "clerk_private_id_123"
    email = "private.person@example.test"
    list_name = "My Private List Name"

    body, headers = signed_webhook({"type": "user.created", "data": {"id": clerk_id, "email_addresses": [{"email_address": email}]}})
    assert anonymous.post("/webhooks/clerk", data=body, headers=headers).status_code == 200

    client = client_as(clerk_id)
    client.put("/collection/item", json=item_payload())
    client.get("/collection")
    list_id = client.post("/lists", json={"list_name": list_name}).get_json()["data"]["list_id"]
    client.put(f"/lists/{list_id}/item", json=item_payload())
    client.get(f"/lists/{list_id}")
    client.put("/collection/item", json=item_payload(release_year="not a year", original_api_id="fails"))
    client.get("/collection?page=0")
    client.post("/lists", json={"list_name": "n" * 65})
    client.get("/lists/999999")

    body, headers = signed_webhook({"type": "user.deleted", "data": {"id": clerk_id}})
    anonymous.post("/webhooks/clerk", data=body, headers=headers)

    for secret in (clerk_id, email, list_name):
        assert secret not in caplog.text
