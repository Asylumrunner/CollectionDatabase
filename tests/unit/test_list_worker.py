import pytest

from tests.helpers import view_row

VIEW = "items_complete_view"
OWNS_LIST = "SELECT list_id FROM user_lists"
LIST_NAME = "SELECT list_name FROM user_lists"


def _owned(db):
    db.on(OWNS_LIST, rows=[{"list_id": 3}])
    db.on(LIST_NAME, rows=[{"list_name": "Favorites"}])
    return db


def test_get_list_not_owned(list_worker, db):  # U-LIST-1
    assert list_worker.get_list("clerk_1", 3, 1) == {"passed": True, "not_found": True}
    assert db.params(LIST_NAME) == [(3, 7)]
    assert db.executed(VIEW) == []


@pytest.mark.parametrize("page, row_count, offset, returned, next_page", [
    (1, 26, 0, 25, 2),
    (1, 25, 0, 25, None),
    (3, 26, 50, 25, 4),
    (2, 0, 25, 0, None),
])
def test_get_list_paging(list_worker, db, page, row_count, offset, returned, next_page):  # U-LIST-2
    _owned(db).on(VIEW, rows=[view_row(item_id=i) for i in range(row_count)])
    result = list_worker.get_list("clerk_1", 3, page)
    assert db.params(VIEW) == [(3, 26, offset)]
    assert len(result["items"]) == returned
    assert result["next_page"] == next_page
    assert result["list_name"] == "Favorites"
    assert result["not_found"] is False


def test_get_list_names_returns_rows(list_worker, db):  # U-LIST-3
    rows = [{"list_id": 3, "list_name": "Favorites"}]
    db.on("SELECT list_id, list_name FROM user_lists", rows=rows)
    assert list_worker.get_list_names("clerk_1") == {"passed": True, "lists": rows}
    assert db.params("SELECT list_id, list_name FROM user_lists") == [(7,)]


def _preview_row(list_id, name, item_id, img):
    return {"list_id": list_id, "list_name": name, "id": item_id, "img_link": img}


def test_get_user_lists_groups_rows_and_keeps_order(list_worker, db):  # U-LIST-4
    db.on(VIEW, rows=[
        _preview_row(2, "Second", 10, "a.jpg"),
        _preview_row(2, "Second", 11, "b.jpg"),
        _preview_row(1, "First", 12, "c.jpg"),
    ])
    assert list_worker.get_user_lists("clerk_1")["lists"] == [
        {"list_id": 2, "list_name": "Second", "img_links": ["a.jpg", "b.jpg"]},
        {"list_id": 1, "list_name": "First", "img_links": ["c.jpg"]},
    ]


def test_get_user_lists_handles_empty_lists(list_worker, db):  # U-LIST-5
    db.on(VIEW, rows=[_preview_row(1, "Empty", None, None)])
    assert list_worker.get_user_lists("clerk_1")["lists"] == [
        {"list_id": 1, "list_name": "Empty", "img_links": []},
    ]


def test_add_item_to_list_not_owned(list_worker, db):  # U-LIST-6
    assert list_worker.add_item_to_list("clerk_1", 3, 42) == {"passed": True, "not_found": True}
    assert db.executed("INSERT") == []


def test_add_item_to_list_already_present(list_worker, db):  # U-LIST-7
    _owned(db).on("SELECT item_id FROM list_items", rows=[{"item_id": 42}])
    result = list_worker.add_item_to_list("clerk_1", 3, 42)
    assert result["already_exists"] is True
    assert db.executed("INSERT") == []


def test_add_item_to_list_inserts_new_items(list_worker, db):  # U-LIST-8
    _owned(db)
    result = list_worker.add_item_to_list("clerk_1", 3, 42)
    assert result == {"passed": True, "not_found": False, "already_exists": False, "item_id": 42}
    assert db.params("INSERT INTO list_items") == [(42, 3)]
    assert db.count("commit") == 1


def test_get_lists_containing_item_is_scoped_to_user_and_item(list_worker, db):  # U-LIST-9
    rows = [{"list_id": 3, "list_name": "Favorites"}]
    db.on("FROM user_lists ul", rows=rows)
    assert list_worker.get_lists_containing_item("clerk_1", 42) == {"passed": True, "lists": rows}
    assert db.params("FROM user_lists ul") == [(7, 42)]


def test_remove_item_from_list_not_owned(list_worker, db):  # U-LIST-10
    assert list_worker.remove_item_from_list("clerk_1", 3, 42) == {"passed": True, "not_found": True}
    assert db.executed("DELETE") == []


def test_remove_item_from_list_deletes_and_commits(list_worker, db):  # U-LIST-10
    _owned(db)
    assert list_worker.remove_item_from_list("clerk_1", 3, 42) == {"passed": True, "not_found": False}
    assert db.params("DELETE FROM list_items") == [(3, 42)]
    assert db.count("commit") == 1


def test_create_list_returns_the_new_id(list_worker, db):  # U-LIST-11
    db.lastrowid = 99
    assert list_worker.create_list("clerk_1", "Favorites") == {"passed": True, "list_id": 99, "list_name": "Favorites"}
    assert db.params("INSERT INTO user_lists") == [("Favorites", 7)]
    assert db.count("commit") == 1


def test_delete_list_not_owned(list_worker, db):  # U-LIST-12
    assert list_worker.delete_list("clerk_1", 3) == {"passed": True, "not_found": True}
    assert db.executed("DELETE") == []


def test_delete_list_removes_items_before_the_list(list_worker, db):  # U-LIST-12
    _owned(db)
    assert list_worker.delete_list("clerk_1", 3) == {"passed": True, "not_found": False}
    assert db.index_of("DELETE FROM list_items") < db.index_of("DELETE FROM user_lists")
    assert db.params("DELETE FROM user_lists") == [(3, 7)]
    assert db.count("commit") == 1


def test_rename_reports_a_missing_list(list_worker, db):  # U-LIST-13
    db.on("UPDATE user_lists", rowcount=0)
    assert list_worker.change_list_name("clerk_1", 3, "New name").get("not_found") is True


def test_rename_to_the_current_name_still_succeeds(list_worker, db):  # U-LIST-13
    # MySQL reports 0 affected rows when the name doesn't change, so that alone isn't "not found"
    db.on("UPDATE user_lists", rowcount=0)
    _owned(db)
    result = list_worker.change_list_name("clerk_1", 3, "Favorites")
    assert result["passed"] and result["not_found"] is False


def test_rename_updates_only_the_callers_list(list_worker, db):  # U-LIST-14
    db.on("UPDATE user_lists", rowcount=1)
    result = list_worker.change_list_name("clerk_1", 3, "New name")
    assert result["passed"] and result["list_name"] == "New name"
    assert db.params("UPDATE user_lists") == [("New name", 3, 7)]
    assert db.count("commit") == 1


RESOLVE = "SELECT user_id FROM users"


@pytest.mark.parametrize("method, args, failing_statement, step, writes", [
    ("get_list", (3, 1), RESOLVE, "resolve_user_id", False),
    ("get_list", (3, 1), LIST_NAME, "verify_list_ownership", False),
    ("get_list", (3, 1), VIEW, "fetch_list_items", False),
    ("get_list_names", (), RESOLVE, "resolve_user_id", False),
    ("get_list_names", (), "SELECT list_id, list_name", "fetch_list_names", False),
    ("get_user_lists", (), RESOLVE, "resolve_user_id", False),
    ("get_user_lists", (), VIEW, "fetch_lists", False),
    ("add_item_to_list", (3, 42), RESOLVE, "resolve_user_id", True),
    ("add_item_to_list", (3, 42), OWNS_LIST, "verify_list_ownership", True),
    ("add_item_to_list", (3, 42), "SELECT item_id FROM list_items", "check_item_in_list", True),
    ("add_item_to_list", (3, 42), "INSERT INTO list_items", "insert_list_item", True),
    ("get_lists_containing_item", (42,), RESOLVE, "resolve_user_id", False),
    ("get_lists_containing_item", (42,), "FROM user_lists ul", "fetch_lists_containing_item", False),
    ("remove_item_from_list", (3, 42), RESOLVE, "resolve_user_id", True),
    ("remove_item_from_list", (3, 42), OWNS_LIST, "verify_list_ownership", True),
    ("remove_item_from_list", (3, 42), "DELETE FROM list_items", "delete_list_item", True),
    ("create_list", ("Name",), RESOLVE, "resolve_user_id", True),
    ("create_list", ("Name",), "INSERT INTO user_lists", "insert_list", True),
    ("delete_list", (3,), RESOLVE, "resolve_user_id", True),
    ("delete_list", (3,), OWNS_LIST, "verify_list_ownership", True),
    ("delete_list", (3,), "DELETE FROM list_items", "delete_list_items", True),
    ("delete_list", (3,), "DELETE FROM user_lists", "delete_list", True),
    ("change_list_name", (3, "Name"), RESOLVE, "resolve_user_id", True),
    ("change_list_name", (3, "Name"), "UPDATE user_lists", "rename_list", True),
])
def test_failures_report_their_step(list_worker, db, method, args, failing_statement, step, writes):  # U-LIST-15
    _owned(db)
    db.fail_on(failing_statement)
    result = getattr(list_worker, method)("clerk_1", *args)
    assert result["passed"] is False
    assert result["step_failed"] == step
    assert result["exception"]["context"]["function"] == method
    assert db.count("commit") == 0
    assert db.count("rollback") == (1 if writes else 0)
    assert db.count("close") == 1
