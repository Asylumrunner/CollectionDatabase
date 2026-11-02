"""Webhooks here carry real Svix signatures."""
import base64
import datetime

import pytest

from tests.helpers import item_payload, signed_webhook

EMAIL = [{"email_address": "new@example.test"}]


def created(send_webhook, clerk_id="clerk_new", **kwargs):
    return send_webhook("user.created", {"id": clerk_id, "email_addresses": EMAIL}, **kwargs)


def deleted(send_webhook, clerk_id="clerk_new"):
    return send_webhook("user.deleted", {"id": clerk_id})


def populate(client, api_id="shared-item"):
    """Gives a user a collection entry and a list containing an item."""
    client.put("/collection/item", json=item_payload(original_api_id=api_id))
    list_id = client.post("/lists", json={"list_name": "Favorites"}).get_json()["data"]["list_id"]
    client.put(f"/lists/{list_id}/item", json=item_payload(original_api_id=api_id))
    return list_id


def test_created_user_can_use_the_api_immediately(send_webhook, client_as, db):  # F-WH-1
    assert created(send_webhook).status_code == 200
    assert db.rows("SELECT username FROM users WHERE clerk_user_id = 'clerk_new'") == [{"username": "new@example.test"}]
    client = client_as("clerk_new")
    assert client.put("/collection/item", json=item_payload()).status_code == 200
    assert len(client.get("/collection").get_json()["data"]) == 1


def test_redelivery_is_idempotent(send_webhook, db):  # F-WH-2
    assert created(send_webhook, msg_id="msg_same").status_code == 200
    second = created(send_webhook, msg_id="msg_same")
    assert second.status_code == 200
    assert second.get_json()["data"]["already_exists"] is True
    assert db.count("users") == 1


def _bad_signature(body):
    other_secret = "whsec_" + base64.b64encode(b"a-completely-different-secret-!!").decode()
    return signed_webhook(body, secret=other_secret)


def _stale(body):
    ten_minutes_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10)
    return signed_webhook(body, timestamp=ten_minutes_ago)


def _tampered(body):
    _, headers = signed_webhook(body)
    return body.replace("clerk_new", "clerk_evil"), headers


@pytest.mark.parametrize("forge", [_bad_signature, _stale, _tampered], ids=["bad_signature", "stale", "tampered"])
def test_forged_webhooks_are_rejected_without_db_changes(anonymous, db, forge):  # F-WH-3
    original = '{"type": "user.created", "data": {"id": "clerk_new"}}'
    body, headers = forge(original)
    assert anonymous.post("/webhooks/clerk", data=body, headers=headers).status_code == 400
    assert db.count("users") == 0


def test_other_events_change_nothing(send_webhook, db):  # F-WH-4
    assert send_webhook("session.created", {"id": "clerk_new"}).status_code == 200
    assert db.count("users") == 0


def test_deleting_a_user_removes_their_data_and_keeps_the_catalog(send_webhook, client_as, db):  # F-WH-5
    created(send_webhook)
    populate(client_as("clerk_new"))
    assert deleted(send_webhook).status_code == 200
    for table in ("users", "user_lists", "list_items", "collection_items"):
        assert db.count(table) == 0, table
    assert db.count("items") == 1


def test_deleting_a_user_leaves_others_untouched(send_webhook, client_as, user_b, db):  # F-WH-6
    created(send_webhook)
    populate(client_as("clerk_new"))
    b_list = populate(user_b)
    deleted(send_webhook)
    assert len(user_b.get("/collection").get_json()["data"]) == 1
    assert len(user_b.get(f"/lists/{b_list}").get_json()["data"]) == 1
    assert db.count("users") == 1


def test_deleting_twice_succeeds_both_times(send_webhook, db):  # F-WH-7
    created(send_webhook)
    assert deleted(send_webhook).status_code == 200
    assert deleted(send_webhook).status_code == 200


def test_recreated_user_starts_empty(send_webhook, client_as, db):  # F-WH-8
    created(send_webhook)
    populate(client_as("clerk_new"))
    deleted(send_webhook)
    assert created(send_webhook).status_code == 200
    client = client_as("clerk_new")
    assert client.get("/collection").get_json()["data"] == []
    assert client.get("/lists").get_json()["data"] == []


@pytest.mark.xfail(reason="B12: null names produce the username 'None None'")
def test_null_names_become_unknown(send_webhook, db):  # F-WH-9
    send_webhook("user.created", {"id": "clerk_new", "email_addresses": [], "first_name": None, "last_name": None})
    assert db.scalar("SELECT username FROM users") == "Unknown"


@pytest.mark.xfail(reason="B4: 500 responses return the traceback to the client")
def test_created_event_without_an_id_fails_without_leaking(send_webhook, db):  # F-WH-10
    response = send_webhook("user.created", {"email_addresses": EMAIL})
    assert response.status_code >= 400
    assert "Traceback" not in response.get_data(as_text=True)
    assert db.count("users") == 0
