from types import SimpleNamespace
from unittest import mock

import pytest

import Workers.BaseWorker as base_worker_module
from Workers.BaseWorker import BaseWorker
from Workers.ItemWorker import ItemWorker

from tests.helpers import FakeDB, make_item, view_row

VIEW = "items_complete_view"
MEDIA_ROWS = [{"id": 1, "type_name": "book"}]


# check_item / get_item

def test_check_item_skips_the_db_for_unknown_types(item_worker, db):  # U-ITEM-1
    assert item_worker.check_item("not_a_type", "api-1") is None
    assert db.acquired == 0


def test_check_item_returns_the_id_when_found(item_worker, db):  # U-ITEM-2
    db.on("SELECT id FROM items", rows=[{"id": 42}])
    assert item_worker.check_item("book", "api-1") == 42
    assert db.params("SELECT id FROM items") == [(1, "api-1")]


def test_check_item_returns_none_when_missing(item_worker):  # U-ITEM-2
    assert item_worker.check_item("book", "api-1") is None


@pytest.mark.xfail(reason="B2: check_item reads the mappings before the pool has loaded them")
def test_check_item_finds_items_on_a_cold_pool(monkeypatch):  # U-ITEM-3
    pool = FakeDB().on("FROM media_types", rows=MEDIA_ROWS).on("SELECT id FROM items", rows=[{"id": 42}])
    monkeypatch.setattr(base_worker_module.pooling, "MySQLConnectionPool", mock.Mock(return_value=pool))
    assert BaseWorker.media_type_mappings == {}
    assert ItemWorker().check_item("book", "api-1") == 42


def test_get_item_by_id_returns_an_item(item_worker, db):  # U-ITEM-4
    db.on(VIEW, rows=[view_row(item_id=42)])
    assert item_worker.get_item_by_id(42).id == "42"


def test_get_item_by_id_returns_none_when_missing(item_worker):  # U-ITEM-4
    assert item_worker.get_item_by_id(42) is None


def test_get_item_fetches_when_found(item_worker, db):  # U-ITEM-4
    db.on("SELECT id FROM items", rows=[{"id": 42}]).on(VIEW, rows=[view_row(item_id=42)])
    assert item_worker.get_item("book", "api-1").id == "42"


def test_get_item_skips_the_fetch_when_missing(item_worker, db):  # U-ITEM-4
    assert item_worker.get_item("book", "api-1") is None
    assert db.executed(VIEW) == []


# add_item

def test_add_item_returns_an_existing_item_without_inserting(item_worker, db):  # U-ITEM-5
    db.on("SELECT id FROM items", rows=[{"id": 42}]).on(VIEW, rows=[view_row(item_id=42)])
    result = item_worker.add_item(make_item())
    assert result["passed"] and result["already_exists"]
    assert result["Item"].id == "42"
    assert db.executed("INSERT") == []


def test_add_item_rejects_unknown_media_types(item_worker, db):  # U-ITEM-6
    item = make_item()
    item.media_type = "not_a_type"
    result = item_worker.add_item(item)
    assert result["passed"] is False
    assert result["exception"]["error_type"] == "ValueError"
    assert db.count("rollback") == 1
    assert db.count("cursor_close") >= 1
    assert db.executed("INSERT") == []


@pytest.mark.parametrize("media_type, table, expected_params", [
    ("book", "INSERT INTO books", (42, "9780441013593", 1990)),
    ("movie", "INSERT INTO movies", (42, "en", 155)),
    ("video_game", "INSERT INTO video_games", (42,)),
    ("board_game", "INSERT INTO board_games", (42, 3, 4, 90)),
    ("rpg", "INSERT INTO rpgs", (42, "1234567890")),
    ("anime", "INSERT INTO anime", (42, 26)),
    ("album", "INSERT INTO albums", (42,)),
])
def test_add_item_writes_the_subtype_row(item_worker, db, media_type, table, expected_params):  # U-ITEM-7 to 13
    db.on(VIEW, rows=[view_row(item_id=42, media_type=media_type)])
    result = item_worker.add_item(make_item(media_type))
    assert result["passed"] and not result["already_exists"]
    assert db.params(table) == [expected_params]


def test_add_item_links_creators_and_genres(item_worker, db):  # U-ITEM-14
    item_worker.add_item(make_item(created_by=["A", "B"], genres=["Jazz", "Funk"]))
    assert db.params("INSERT IGNORE INTO creators") == [("A",), ("B",)]
    assert db.params("SELECT creator_id") == [("A",), ("B",)]
    assert db.params("INSERT INTO item_creators") == [(42, 5), (42, 5)]
    assert db.params("INSERT IGNORE INTO genres") == [("Jazz",), ("Funk",)]
    assert db.params("INSERT INTO item_genres") == [(42, 6), (42, 6)]


def test_add_item_links_platforms(item_worker, db):  # U-ITEM-15
    item_worker.add_item(make_item("video_game", platforms=["PC", "Dreamcast"]))
    assert db.params("INSERT INTO game_platform_availabilities") == [(42, 8), (42, 8)]


def test_add_item_ignores_repeated_platform_names(item_worker, db):  # U-ITEM-15
    result = item_worker.add_item(make_item("video_game", platforms=["PC", "PC", "Dreamcast"]))
    assert result["passed"]
    assert db.params("INSERT INTO video_game_platforms") == [("PC", 6), ("Dreamcast", 23)]
    assert len(db.params("INSERT INTO game_platform_availabilities")) == 2


def test_add_item_saves_igdb_platform_ids(item_worker, db):  # U-ITEM-15
    item_worker.add_item(make_item(
        "video_game", platforms=["PC (Microsoft Windows)", "PS5", "Homebrew Console"],
        platform_igdb_ids={"PC (Microsoft Windows)": 6},
    ))
    # IGDB's ID first, then the alias table, else NULL
    assert db.params("INSERT INTO video_game_platforms") == [
        ("PC (Microsoft Windows)", 6), ("PS5", 167), ("Homebrew Console", None),
    ]


@pytest.mark.parametrize("platforms", [None, []])
def test_add_item_without_platforms_makes_no_platform_queries(item_worker, db, platforms):  # U-ITEM-15
    item_worker.add_item(make_item("video_game", platforms=platforms))
    assert db.executed("video_game_platforms") == []


def test_add_item_numbers_tracks_from_one_in_list_order(item_worker, db):  # U-ITEM-16
    item_worker.add_item(make_item("album", tracklist=["Zebra", "Apple"]))
    assert db.params("INSERT INTO album_tracks") == [(42, 1, "Zebra"), (42, 2, "Apple")]


def test_add_item_skips_loops_when_lists_are_none(item_worker, db):  # U-ITEM-17
    result = item_worker.add_item(make_item(created_by=None, genres=None))
    assert result["passed"]
    assert db.executed("creators") == []
    assert db.executed("genres") == []


def test_add_item_commits_exactly_once(item_worker, db):  # U-ITEM-18
    item_worker.add_item(make_item(genres=["Jazz"]))
    assert db.count("commit") == 1
    assert db.count("rollback") == 0


@pytest.mark.parametrize("failing_statement", [
    "INSERT INTO items", "INSERT IGNORE INTO creators", "INSERT INTO item_creators",
    "INSERT INTO item_genres", "INSERT INTO books",
])
def test_add_item_rolls_back_on_failure_at_each_step(item_worker, db, failing_statement):  # U-ITEM-19
    db.fail_on(failing_statement)
    result = item_worker.add_item(make_item(genres=["Jazz"]))
    assert result["passed"] is False
    assert db.count("rollback") == 1
    assert db.count("commit") == 0
    assert result["exception"]["context"]["function"] == "add_item"
    assert result["exception"]["context"]["original_api_id"] == "api-1"


def test_add_item_releases_its_connection_before_refetching(item_worker, db):  # U-ITEM-20
    db.on(VIEW, rows=[view_row(item_id=42)])
    item_worker.add_item(make_item())
    commit = db.events.index("commit")
    close_after_commit = db.events.index("close", commit)
    assert close_after_commit < db.index_of(VIEW)


@pytest.mark.parametrize("media_type, field, link_table", [
    ("book", "created_by", "INSERT INTO item_creators"),
    ("book", "genres", "INSERT INTO item_genres"),
    ("video_game", "platforms", "INSERT INTO game_platform_availabilities"),
])
def test_add_item_deduplicates_repeated_names(item_worker, db, media_type, field, link_table):  # U-ITEM-21
    result = item_worker.add_item(make_item(media_type, **{field: ["Same", "Same"]}))
    assert result["passed"]
    assert len(db.params(link_table)) == 1


# get_user_collection

@pytest.mark.parametrize("page, offset", [(1, 0), (2, 25), (3, 50)])
def test_collection_paging_parameters(item_worker, db, page, offset):  # U-ITEM-22
    item_worker.get_user_collection("clerk_1", page)
    assert db.params(VIEW) == [(7, 26, offset)]


@pytest.mark.parametrize("row_count, returned, next_page", [(26, 25, 3), (25, 25, None), (0, 0, None)])
def test_collection_next_page_boundaries(item_worker, db, row_count, returned, next_page):  # U-ITEM-23
    db.on(VIEW, rows=[view_row(item_id=i) for i in range(row_count)])
    result = item_worker.get_user_collection("clerk_1", 2)
    assert len(result["items"]) == returned
    assert result["next_page"] == next_page


@pytest.mark.parametrize("failing_statement, step", [
    ("SELECT user_id FROM users", "resolve_user_id"),
    (VIEW, "fetch_collection"),
])
def test_collection_failures_report_their_step(item_worker, db, failing_statement, step):  # U-ITEM-24
    db.fail_on(failing_statement)
    result = item_worker.get_user_collection("clerk_1", 1)
    assert result["passed"] is False
    assert result["step_failed"] == step


# remove_item_from_collection

def test_remove_item_reports_rows_deleted(item_worker, db):  # U-ITEM-25
    db.on("DELETE FROM collection_items", rowcount=1)
    result = item_worker.remove_item_from_collection("clerk_1", 42)
    assert result == {"passed": True, "rows_deleted": 1}
    assert db.params("DELETE FROM collection_items") == [(42, 7)]
    assert db.count("commit") == 1


def test_remove_item_rolls_back_on_failure(item_worker, db):  # U-ITEM-25
    db.fail_on("DELETE FROM collection_items")
    result = item_worker.remove_item_from_collection("clerk_1", 42)
    assert result["passed"] is False
    assert result["step_failed"] == "delete_collection_item"
    assert db.count("rollback") == 1


# add_items_to_collection

def _stub_add_item(worker, *outcomes):
    """Each outcome is an item id, or None for a failed add."""
    def to_response(outcome):
        if outcome is None:
            return {"passed": False, "exception": {"error_type": "ValueError"}}
        return {"passed": True, "Item": SimpleNamespace(id=str(outcome))}
    worker.add_item = mock.Mock(side_effect=[to_response(o) for o in outcomes])
    return [make_item(original_api_id=f"api-{i}") for i in range(len(outcomes))]


def test_bulk_add_inserts_all_new_items(item_worker, db):  # U-ITEM-26
    items = _stub_add_item(item_worker, 1, 2)
    result = item_worker.add_items_to_collection("clerk_1", items)
    assert result["passed"]
    assert result["added"] == [1, 2]
    assert db.params("INSERT INTO collection_items") == [[(1, 7), (2, 7)]]
    assert db.count("commit") == 1


def test_bulk_add_separates_items_already_in_the_collection(item_worker, db):  # U-ITEM-27
    db.on("SELECT item_id FROM collection_items", rows=[{"item_id": 1}])
    items = _stub_add_item(item_worker, 1, 2)
    result = item_worker.add_items_to_collection("clerk_1", items)
    assert result["added"] == [2]
    assert result["already_existed"] == [1]
    assert db.params("INSERT INTO collection_items") == [[(2, 7)]]


def test_bulk_add_continues_past_a_failed_item(item_worker):  # U-ITEM-28
    items = _stub_add_item(item_worker, None, 2)
    result = item_worker.add_items_to_collection("clerk_1", items)
    assert result["passed"]
    assert result["added"] == [2]
    assert [f["item"]["original_api_id"] for f in result["failed"]] == ["api-0"]


def test_bulk_add_opens_no_connection_when_every_item_fails(item_worker, db):  # U-ITEM-29
    items = _stub_add_item(item_worker, None, None)
    item_worker.add_items_to_collection("clerk_1", items)
    assert db.acquired == 0


@pytest.mark.xfail(reason="B11: a bulk add where every item failed still reports passed=True")
def test_bulk_add_reports_failure_when_every_item_fails(item_worker):  # U-ITEM-29
    items = _stub_add_item(item_worker, None, None)
    assert item_worker.add_items_to_collection("clerk_1", items)["passed"] is False


@pytest.mark.xfail(reason="B11: the same item twice in one request violates the primary key")
def test_bulk_add_collapses_duplicates_in_one_request(item_worker, db):  # U-ITEM-30
    items = _stub_add_item(item_worker, 1, 1)
    result = item_worker.add_items_to_collection("clerk_1", items)
    assert result["added"] == [1]
    assert db.params("INSERT INTO collection_items") == [[(1, 7)]]


def test_bulk_add_writes_nothing_when_nothing_is_new(item_worker, db):  # U-ITEM-31
    db.on("SELECT item_id FROM collection_items", rows=[{"item_id": 1}])
    items = _stub_add_item(item_worker, 1)
    result = item_worker.add_items_to_collection("clerk_1", items)
    assert result["added"] == []
    assert db.executed("INSERT INTO collection_items") == []
    assert db.count("commit") == 0


def test_bulk_add_with_an_unknown_user_keeps_earlier_results(db, loaded_mappings):  # U-ITEM-32
    worker = ItemWorker()
    worker.get_connection = db.get_connection
    items = _stub_add_item(worker, None, 2)
    result = worker.add_items_to_collection("clerk_1", items)
    assert result["passed"] is False
    assert result["step_failed"] == "resolve_user_id"
    assert len(result["failed"]) == 1


# remove_items_from_collection

def test_bulk_remove_binds_every_id(item_worker, db):  # U-ITEM-33
    db.on("DELETE FROM collection_items", rowcount=3)
    result = item_worker.remove_items_from_collection("clerk_1", [1, 2, 3])
    assert result == {"passed": True, "rows_deleted": 3}
    call = db.executed("DELETE FROM collection_items")[0]
    assert call["sql"].count("%s") == 4
    assert call["params"] == (7, 1, 2, 3)
    assert db.count("commit") == 1


def test_bulk_remove_rolls_back_on_failure(item_worker, db):  # U-ITEM-33
    db.fail_on("DELETE FROM collection_items")
    result = item_worker.remove_items_from_collection("clerk_1", [1])
    assert result["passed"] is False
    assert result["step_failed"] == "delete_collection_items"
    assert db.count("rollback") == 1


# add_item_to_collection

def test_add_to_collection_stops_when_add_item_fails(item_worker, db):  # U-ITEM-34
    _stub_add_item(item_worker, None)
    result = item_worker.add_item_to_collection("clerk_1", make_item())
    assert result["passed"] is False
    assert result["step_failed"] == "add_item"
    assert db.acquired == 0


def test_add_to_collection_skips_an_existing_pair(item_worker, db):  # U-ITEM-35
    _stub_add_item(item_worker, 42)
    db.on("SELECT * FROM collection_items", rows=[{"item_id": 42, "user_id": 7}])
    result = item_worker.add_item_to_collection("clerk_1", make_item())
    assert result["passed"] and result["already_exists"]
    assert db.executed("INSERT INTO collection_items") == []


def test_add_to_collection_inserts_a_new_pair(item_worker, db):  # U-ITEM-36
    _stub_add_item(item_worker, 42)
    result = item_worker.add_item_to_collection("clerk_1", make_item())
    assert result == {"passed": True, "already_exists": False, "item_id": "42", "user_id": 7}
    assert db.params("INSERT INTO collection_items") == [("42", 7)]
    assert db.count("commit") == 1


@pytest.mark.parametrize("failing_statement, step", [
    ("SELECT user_id FROM users", "resolve_user_id"),
    ("SELECT * FROM collection_items", "check_collection_item_exists"),
    ("INSERT INTO collection_items", "add_collection_item"),
])
def test_add_to_collection_failures_report_their_step(item_worker, db, failing_statement, step):  # U-ITEM-37
    _stub_add_item(item_worker, 42)
    db.fail_on(failing_statement)
    result = item_worker.add_item_to_collection("clerk_1", make_item())
    assert result["passed"] is False
    assert result["step_failed"] == step
    assert db.count("rollback") == 1
