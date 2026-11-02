import pytest

from tests.helpers import item_payload


def create_list(client, name="Favorites"):
    return client.post("/lists", json={"list_name": name}).get_json()["data"]["list_id"]


def add_to_list(client, list_id, original_api_id="api-1", **overrides):
    return client.put(f"/lists/{list_id}/item", json=item_payload(original_api_id=original_api_id, **overrides))


def fill_list(client, db, list_id, count):
    """Adds items with distinct date_added values: the column has one-second resolution,
    and ties would make `ORDER BY date_added` non-deterministic. Item 0 is the oldest."""
    item_ids = []
    for i in range(count):
        body = add_to_list(client, list_id, f"fill-{i}", title=f"Item {i}", img_link=f"https://example.test/{i}.jpg")
        item_id = body.get_json()["data"]["item_id"]
        db.execute(
            "UPDATE list_items SET date_added = %s + INTERVAL %s MINUTE WHERE list_id = %s AND item_id = %s",
            ("2020-01-01 00:00:00", i, list_id, item_id),
        )
        item_ids.append(item_id)
    return item_ids


def test_created_list_appears_everywhere(user_a):  # F-LST-1
    response = user_a.post("/lists", json={"list_name": "Favorites"})
    assert response.status_code == 200
    list_id = response.get_json()["data"]["list_id"]
    assert user_a.get("/lists/names").get_json()["data"] == [{"list_id": list_id, "list_name": "Favorites"}]
    assert user_a.get("/lists").get_json()["data"] == [{"list_id": list_id, "list_name": "Favorites", "img_links": []}]


def test_added_item_is_visible_from_both_directions(user_a):  # F-LST-2
    list_id = create_list(user_a)
    response = add_to_list(user_a, list_id, title="Dune")
    assert response.status_code == 200
    item_id = response.get_json()["data"]["item_id"]

    assert [item["title"] for item in user_a.get(f"/lists/{list_id}").get_json()["data"]] == ["Dune"]
    assert user_a.get(f"/lists/item/{item_id}").get_json()["data"] == [{"list_id": list_id, "list_name": "Favorites"}]


def test_adding_to_a_list_twice_is_idempotent(user_a, db):  # F-LST-3
    list_id = create_list(user_a)
    add_to_list(user_a, list_id)
    second = add_to_list(user_a, list_id)
    assert second.status_code == 200
    assert second.get_json()["data"]["already_exists"] is True
    assert db.count("list_items") == 1


def test_list_items_are_newest_first(user_a, db):  # F-LST-4
    list_id = create_list(user_a)
    fill_list(user_a, db, list_id, 3)
    titles = [item["title"] for item in user_a.get(f"/lists/{list_id}").get_json()["data"]]
    assert titles == ["Item 2", "Item 1", "Item 0"]


def test_list_pagination(user_a, db):  # F-LST-5
    list_id = create_list(user_a)
    fill_list(user_a, db, list_id, 26)
    first = user_a.get(f"/lists/{list_id}?page=1").get_json()
    second = user_a.get(f"/lists/{list_id}?page=2").get_json()
    assert (len(first["data"]), first["next_page"]) == (25, 2)
    assert (len(second["data"]), second["next_page"]) == (1, None)
    assert second["data"][0]["title"] == "Item 0"


def test_list_previews_are_capped_at_ten_newest(user_a, db):  # F-LST-6
    full = create_list(user_a, "Full")
    empty = create_list(user_a, "Empty")
    fill_list(user_a, db, full, 11)
    previews = {entry["list_id"]: entry["img_links"] for entry in user_a.get("/lists").get_json()["data"]}
    assert previews[full] == [f"https://example.test/{i}.jpg" for i in range(10, 0, -1)]
    assert previews[empty] == []


def test_rename_persists(user_a):  # F-LST-7
    list_id = create_list(user_a)
    assert user_a.put(f"/lists/{list_id}/rename", json={"list_name": "Renamed"}).status_code == 200
    assert user_a.get("/lists/names").get_json()["data"][0]["list_name"] == "Renamed"


def test_removing_from_a_list_keeps_catalog_and_collection(user_a, db):  # F-LST-8
    user_a.put("/collection/item", json=item_payload())
    list_id = create_list(user_a)
    item_id = add_to_list(user_a, list_id).get_json()["data"]["item_id"]

    assert user_a.delete(f"/lists/{list_id}/item", json={"id": item_id}).status_code == 200
    assert user_a.get(f"/lists/{list_id}").get_json()["data"] == []
    assert db.count("items") == 1
    assert db.count("collection_items") == 1


def test_deleting_a_list_keeps_items_and_other_lists(user_a, db):  # F-LST-9
    doomed = create_list(user_a, "Doomed")
    kept = create_list(user_a, "Kept")
    add_to_list(user_a, doomed)
    add_to_list(user_a, kept)

    assert user_a.delete(f"/lists/{doomed}").status_code == 200
    assert user_a.get(f"/lists/{doomed}").status_code == 404
    assert db.count("user_lists") == 1
    assert db.count("list_items") == 1
    assert db.count("items") == 1
    assert len(user_a.get(f"/lists/{kept}").get_json()["data"]) == 1


def test_item_in_two_lists_returns_both_sorted_by_name(user_a):  # F-LST-10
    second = create_list(user_a, "Zebra")
    first = create_list(user_a, "Apple")
    add_to_list(user_a, second)
    item_id = add_to_list(user_a, first).get_json()["data"]["item_id"]
    assert user_a.get(f"/lists/item/{item_id}").get_json()["data"] == [
        {"list_id": first, "list_name": "Apple"},
        {"list_id": second, "list_name": "Zebra"},
    ]


def test_removing_from_collection_leaves_lists_alone(user_a):  # F-LST-11
    # Documents current behaviour: collections and lists are independent
    user_a.put("/collection/item", json=item_payload())
    list_id = create_list(user_a)
    item_id = add_to_list(user_a, list_id).get_json()["data"]["item_id"]
    user_a.delete("/collection/item", json={"id": item_id})
    assert len(user_a.get(f"/lists/{list_id}").get_json()["data"]) == 1


def test_other_users_cant_touch_a_list(user_a, user_b, db):  # F-LST-12
    list_id = create_list(user_a)
    item_id = add_to_list(user_a, list_id, title="Alice's item").get_json()["data"]["item_id"]

    assert user_b.get(f"/lists/{list_id}").status_code == 404
    assert add_to_list(user_b, list_id, original_api_id="from-bob").status_code == 404
    assert user_b.delete(f"/lists/{list_id}/item", json={"id": item_id}).status_code == 404
    assert user_b.delete(f"/lists/{list_id}").status_code == 404

    assert db.count("user_lists") == 1
    assert db.count("list_items") == 1
    assert [item["title"] for item in user_a.get(f"/lists/{list_id}").get_json()["data"]] == ["Alice's item"]


def test_lists_containing_item_shows_only_the_callers(user_a, user_b):  # F-LST-13
    a_list = create_list(user_a, "Alice's list")
    b_list = create_list(user_b, "Bob's list")
    add_to_list(user_a, a_list)
    item_id = add_to_list(user_b, b_list).get_json()["data"]["item_id"]
    assert user_a.get(f"/lists/item/{item_id}").get_json()["data"] == [{"list_id": a_list, "list_name": "Alice's list"}]
    assert user_b.get(f"/lists/item/{item_id}").get_json()["data"] == [{"list_id": b_list, "list_name": "Bob's list"}]


@pytest.mark.xfail(reason="B9: renaming a list you don't own, or one that doesn't exist, returns 200")
def test_renaming_someone_elses_list_is_a_404(user_a, user_b):  # F-LST-14
    list_id = create_list(user_a, "Original")
    assert user_b.put(f"/lists/{list_id}/rename", json={"list_name": "Hijacked"}).status_code == 404


@pytest.mark.xfail(reason="B9: renaming a list you don't own, or one that doesn't exist, returns 200")
def test_renaming_a_missing_list_is_a_404(user_a):  # F-LST-14
    assert user_a.put("/lists/999999/rename", json={"list_name": "Nope"}).status_code == 404


def test_renaming_someone_elses_list_doesnt_change_it(user_a, user_b):  # F-LST-14
    list_id = create_list(user_a, "Original")
    user_b.put(f"/lists/{list_id}/rename", json={"list_name": "Hijacked"})
    assert user_a.get("/lists/names").get_json()["data"][0]["list_name"] == "Original"


@pytest.mark.xfail(reason="B16: the catalog item is created before list ownership is checked")
def test_adding_to_a_missing_list_creates_nothing(user_a, db):  # F-LST-15
    assert add_to_list(user_a, 999999).status_code == 404
    assert db.count("items") == 0


def test_list_name_at_the_limit_is_accepted(user_a):  # F-LST-16
    assert user_a.post("/lists", json={"list_name": "n" * 64}).status_code == 200


@pytest.mark.xfail(reason="B17: list names aren't validated; too long is a 500 and blank is accepted")
@pytest.mark.parametrize("name", ["n" * 65, "", "   "], ids=["too_long", "empty", "blank"])
def test_invalid_list_names_are_a_400(user_a, name):  # F-LST-17
    assert user_a.post("/lists", json={"list_name": name}).status_code == 400


@pytest.mark.xfail(reason="B10: page below 1 becomes a negative OFFSET and a SQL error")
@pytest.mark.parametrize("path", ["/collection", "/lists/{list_id}"])
def test_page_zero_is_a_400(user_a, path):  # F-LST-18
    list_id = create_list(user_a)
    assert user_a.get(path.format(list_id=list_id) + "?page=0").status_code == 400
