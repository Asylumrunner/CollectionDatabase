import pytest

from tests.helpers import MEDIA_TYPES, item_payload


def add(client, media_type="book", original_api_id="api-1", **overrides):
    return client.put("/collection/item", json=item_payload(media_type, original_api_id, **overrides))


def collection(client, page=1):
    return client.get(f"/collection?page={page}").get_json()


def bulk_payload(count, prefix="bulk"):
    return [item_payload(original_api_id=f"{prefix}-{i}", title=f"Item {i}") for i in range(count)]


@pytest.mark.parametrize("media_type", MEDIA_TYPES)
def test_every_field_survives_a_round_trip(user_a, media_type):  # F-COL-1 to 7
    payload = item_payload(media_type, created_by=["Zed", "Amy"])
    response = user_a.put("/collection/item", json=payload)
    assert response.status_code == 200
    assert response.get_json()["data"]["already_exists"] is False

    stored = collection(user_a)["data"][0]
    for field, expected in payload.items():
        if field in ("created_by", "platforms", "genres"):
            # JSON_ARRAYAGG doesn't promise an order for these
            assert sorted(stored[field]) == sorted(expected), field
        else:
            assert stored[field] == expected, field


def test_adding_twice_is_idempotent(user_a, db):  # F-COL-8
    assert add(user_a).get_json()["data"]["already_exists"] is False
    second = add(user_a)
    assert second.status_code == 200
    assert second.get_json()["data"]["already_exists"] is True
    assert db.count("items") == 1
    assert db.count("collection_items") == 1


def test_two_users_share_one_catalog_row(user_a, user_b, db):  # F-COL-9
    assert add(user_a).status_code == 200
    assert add(user_b).status_code == 200
    assert db.count("items") == 1
    assert db.count("collection_items") == 2


def test_collections_are_isolated_between_users(user_a, user_b):  # F-COL-10
    add(user_a, original_api_id="a-only", title="Alice's item")
    add(user_b, original_api_id="b-only", title="Bob's item")
    assert [item["title"] for item in collection(user_a)["data"]] == ["Alice's item"]
    assert [item["title"] for item in collection(user_b)["data"]] == ["Bob's item"]


def test_delete_removes_only_the_callers_pairing(user_a, user_b, db):  # F-COL-11
    add(user_a)
    add(user_b)
    item_id = collection(user_a)["data"][0]["id"]
    response = user_a.delete("/collection/item", json={"id": item_id})
    assert response.status_code == 200
    assert response.get_json()["data"]["rows_deleted"] == 1
    assert collection(user_a)["data"] == []
    assert len(collection(user_b)["data"]) == 1
    assert db.count("items") == 1


def test_deleting_an_item_you_dont_have_changes_nothing(user_a, user_b, db):  # F-COL-12
    add(user_b)
    item_id = collection(user_b)["data"][0]["id"]
    response = user_a.delete("/collection/item", json={"id": item_id})
    assert response.status_code == 200
    assert response.get_json()["data"]["rows_deleted"] == 0
    assert db.count("collection_items") == 1


def test_pagination_across_the_page_boundary(user_a):  # F-COL-13
    assert user_a.put("/collection/items", json=bulk_payload(26)).status_code == 200
    first, second, third = collection(user_a, 1), collection(user_a, 2), collection(user_a, 3)
    assert (len(first["data"]), first["next_page"]) == (25, 2)
    assert (len(second["data"]), second["next_page"]) == (1, None)
    assert (third["data"], third["next_page"]) == ([], None)
    ids = [item["id"] for item in first["data"] + second["data"]]
    assert len(set(ids)) == 26


def test_exactly_one_full_page_has_no_next_page(user_a):  # F-COL-13
    user_a.put("/collection/items", json=bulk_payload(25))
    page = collection(user_a)
    assert (len(page["data"]), page["next_page"]) == (25, None)


def test_bulk_add_sorts_items_into_buckets(user_a, db):  # F-COL-14
    add(user_a, original_api_id="existing")
    existing_id = int(collection(user_a)["data"][0]["id"])
    response = user_a.put("/collection/items", json=[
        item_payload(original_api_id="new"),
        item_payload(original_api_id="existing"),
        item_payload(original_api_id="invalid", media_type="book", **{"title": "Bad"}) | {"media_type": "not_a_type"},
    ])
    data = response.get_json()["data"]
    assert response.status_code == 200
    assert data["already_existed"] == [existing_id]
    assert len(data["added"]) == 1
    assert [failure["item"]["original_api_id"] for failure in data["failed"]] == ["invalid"]
    assert db.count("collection_items") == 2


def test_bulk_delete_removes_only_the_callers_listed_items(user_a, user_b):  # F-COL-15
    user_a.put("/collection/items", json=bulk_payload(3))
    user_b.put("/collection/items", json=bulk_payload(3))
    ids = [item["id"] for item in collection(user_a)["data"]]
    response = user_a.delete("/collection/items", json={"ids": ids[:2]})
    assert response.get_json()["data"]["rows_deleted"] == 2
    assert [item["id"] for item in collection(user_a)["data"]] == ids[2:]
    assert len(collection(user_b)["data"]) == 3


@pytest.mark.xfail(reason="B11: the same item twice in one request violates the primary key")
def test_bulk_add_with_a_repeated_item(user_a, db):  # F-COL-16
    payload = item_payload(original_api_id="same")
    assert user_a.put("/collection/items", json=[payload, payload]).status_code == 200
    assert db.count("collection_items") == 1


def test_shared_creators_and_genres_get_one_row(user_a, db):  # F-COL-17
    add(user_a, original_api_id="one", created_by=["Shared"], genres=["Jazz"])
    add(user_a, original_api_id="two", created_by=["Shared"], genres=["Jazz"])
    assert db.count("creators") == 1
    assert db.count("genres") == 1
    assert db.count("item_creators") == 2
    assert db.count("item_genres") == 2


def test_shared_platforms_get_one_row(user_a, db):  # F-COL-18
    add(user_a, "video_game", original_api_id="one", platforms=["PC"])
    add(user_a, "video_game", original_api_id="two", platforms=["PC"])
    assert db.count("video_game_platforms") == 1
    assert db.count("game_platform_availabilities") == 2


def test_platform_igdb_ids_round_trip(user_a, db):  # F-COL-18
    add(user_a, "video_game", original_api_id="one", platforms=["PC (Microsoft Windows)", "PS5", "Homebrew"],
        platform_igdb_ids={"PC (Microsoft Windows)": 6})
    stored = collection(user_a)["data"][0]
    assert stored["platform_igdb_ids"] == {"PC (Microsoft Windows)": 6, "PS5": 167, "Homebrew": None}


def test_later_save_fills_in_a_missing_igdb_platform_id(user_a, db):  # F-COL-18
    add(user_a, "video_game", original_api_id="one", platforms=["Homebrew"])
    add(user_a, "video_game", original_api_id="two", platforms=["Homebrew"], platform_igdb_ids={"Homebrew": 999})
    assert db.rows("SELECT igdb_platform_id FROM video_game_platforms") == [{"igdb_platform_id": 999}]


def test_repeated_platform_in_one_item(user_a, db):  # F-COL-19
    assert add(user_a, "video_game", platforms=["PC", "PC"]).status_code == 200
    assert db.count("game_platform_availabilities") == 1


def test_repeated_creator_in_one_item(user_a, db):  # F-COL-19
    assert add(user_a, created_by=["Same", "Same"]).status_code == 200
    assert db.count("item_creators") == 1


def test_repeated_genre_in_one_item(user_a, db):  # F-COL-19
    assert add(user_a, genres=["Jazz", "Jazz"]).status_code == 200
    assert db.count("item_genres") == 1


def test_album_tracks_come_back_in_track_order(user_a):  # F-COL-20
    tracks = [f"{chr(ord('Z') - i)} track" for i in range(20)]
    add(user_a, "album", tracklist=tracks)
    assert collection(user_a)["data"][0]["tracklist"] == tracks


def test_failure_partway_leaves_no_rows_and_retry_succeeds(user_a, db):  # F-COL-21
    too_long_genre = "g" * 65
    response = add(user_a, genres=["Fine", too_long_genre])
    assert response.status_code == 500
    for table in ("items", "books", "creators", "item_creators", "genres", "item_genres", "collection_items"):
        assert db.count(table) == 0, table

    assert add(user_a, genres=["Fine"]).status_code == 200
    assert db.count("books") == 1


@pytest.mark.parametrize("title", ["進撃の巨人", "Café 🎲 Noir"])
def test_unicode_round_trips(user_a, title):  # F-COL-22
    add(user_a, title=title, created_by=[title])
    stored = collection(user_a)["data"][0]
    assert stored["title"] == title
    assert stored["created_by"] == [title]


def test_sql_in_a_title_is_stored_literally(user_a, db):  # F-COL-23
    title = "'; DROP TABLE items; --"
    assert add(user_a, title=title).status_code == 200
    assert collection(user_a)["data"][0]["title"] == title
    assert db.count("items") == 1


@pytest.mark.xfail(reason="B17: summaries over 1024 characters fail with a 500")
def test_long_summary_is_accepted(user_a):  # F-COL-24
    assert add(user_a, "movie", summary="s" * 5000).status_code == 200


@pytest.mark.xfail(reason="B18: a token with no users row is a 500")
def test_user_without_a_row_gets_a_404(client_as, db):  # F-COL-25
    response = add(client_as("not_in_users"))
    assert response.status_code == 404
    assert db.count("collection_items") == 0


@pytest.mark.xfail(reason="B4: 500 responses return the traceback to the client")
def test_db_failure_doesnt_leak_a_traceback(user_a):  # F-COL-26
    response = add(user_a, release_year="not a year")
    assert response.status_code == 500
    assert "Traceback" not in response.get_data(as_text=True)
