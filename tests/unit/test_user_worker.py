from mysql.connector import Error

FIND_FOR_CREATE = "SELECT clerk_user_id FROM users"
FIND_FOR_DELETE = "SELECT user_id FROM users"


def test_create_user_skips_existing_users(user_worker, db):  # U-USER-1
    db.on(FIND_FOR_CREATE, rows=[{"clerk_user_id": "clerk_1"}])
    result = user_worker.create_user("clerk_1", "name")
    assert result["passed"] and result["already_exists"]
    assert db.executed("INSERT") == []


def test_create_user_inserts_new_users(user_worker, db):  # U-USER-2
    result = user_worker.create_user("clerk_1", "name", "msg_1")
    assert result["passed"] and not result["already_exists"]
    assert db.params("INSERT INTO users") == [("clerk_1", "name")]
    assert db.count("commit") == 1


def test_create_user_reports_db_errors_without_logging_the_id(user_worker, db, caplog):  # U-USER-3
    db.fail_on("INSERT INTO users", Error(msg="boom", errno=1205, sqlstate="HY000"))
    result = user_worker.create_user("clerk_secret_id", "name")
    assert result["passed"] is False
    assert result["step_failed"] == "insert_user"
    assert result["exception"]["context"] == {
        "function": "create_user", "step": "insert_user", "clerk_user_id": "clerk_secret_id"
    }
    assert "errno=1205" in caplog.text
    assert "clerk_secret_id" not in caplog.text


def test_delete_user_tolerates_unknown_users(user_worker, db):  # U-USER-4
    assert user_worker.delete_user("clerk_1")["passed"] is True
    assert db.executed("DELETE") == []
    assert db.count("commit") == 0


def test_delete_user_deletes_in_foreign_key_order_then_commits(user_worker, db):  # U-USER-5
    db.on(FIND_FOR_DELETE, rows=[(9,)])
    assert user_worker.delete_user("clerk_1")["passed"] is True

    statements = ["DELETE li FROM list_items", "DELETE FROM user_lists", "DELETE FROM collection_items", "DELETE FROM users"]
    positions = [db.index_of(statement) for statement in statements]
    assert positions == sorted(positions)
    assert positions[-1] < db.events.index("commit")
    for statement in statements:
        assert db.params(statement) == [(9,)]


def test_delete_user_does_not_commit_a_partial_delete(user_worker, db):  # U-USER-6
    db.on(FIND_FOR_DELETE, rows=[(9,)])
    db.fail_on("DELETE FROM collection_items", Error(msg="boom", errno=1205))
    result = user_worker.delete_user("clerk_1")
    assert result["passed"] is False
    assert db.count("commit") == 0
    assert db.count("close") == 1
