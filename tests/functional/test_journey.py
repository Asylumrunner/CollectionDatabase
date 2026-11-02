from tests.functional_support import load_json_fixture
from tests.helpers import signed_webhook

CLERK_ID = "clerk_journey"


def webhook(anonymous, event_type, data):
    body, headers = signed_webhook({"type": event_type, "data": data})
    return anonymous.post("/webhooks/clerk", data=body, headers=headers)


def test_a_users_whole_lifecycle(anonymous, client_as, db, rsps):  # F-E2E-1
    # Clerk tells us about a new user
    created = webhook(anonymous, "user.created", {"id": CLERK_ID, "email_addresses": [{"email_address": "new@example.test"}]})
    assert created.status_code == 200
    client = client_as(CLERK_ID)

    # They search for a book and add it to their collection
    rsps.get("https://openlibrary.org/search.json", json=load_json_fixture("openlibrary/search.json"))
    found = client.get("/search/dune?media_type=book").get_json()["data"][0]
    assert client.put("/collection/item", json=found).status_code == 200

    # They organize it into a list
    list_id = client.post("/lists", json={"list_name": "To reread"}).get_json()["data"]["list_id"]
    added = client.put(f"/lists/{list_id}/item", json=found)
    assert added.status_code == 200
    assert added.get_json()["data"]["already_exists"] is False
    item_id = added.get_json()["data"]["item_id"]

    # Both views show it
    assert [item["id"] for item in client.get("/collection").get_json()["data"]] == [item_id]
    assert [item["id"] for item in client.get(f"/lists/{list_id}").get_json()["data"]] == [item_id]

    # They tidy up
    assert client.delete(f"/lists/{list_id}/item", json={"id": item_id}).status_code == 200
    assert client.get(f"/lists/{list_id}").get_json()["data"] == []
    assert client.delete(f"/lists/{list_id}").status_code == 200

    # They delete their account, with the book still in their collection
    assert webhook(anonymous, "user.deleted", {"id": CLERK_ID}).status_code == 200
    for table in ("users", "user_lists", "list_items", "collection_items"):
        assert db.count(table) == 0, table
    assert db.count("items") == 1
