from unittest import mock

import pytest
from tests.functional_support import assert_test_database, truncate_all

from tests.helpers import MEDIA_TYPES


def test_schema_loads_with_seed_data_and_view(db):  # F-DB-1
    types = {row["type_name"] for row in db.rows("SELECT type_name FROM media_types")}
    assert types == set(MEDIA_TYPES)
    assert db.rows("SELECT * FROM items_complete_view") == []


def _connection_to(database_name):
    connection = mock.Mock()
    connection.cursor.return_value.fetchone.return_value = (database_name,)
    return connection


@pytest.mark.parametrize("name", ["collectionDB", "production", None])
def test_truncate_refuses_any_other_database(name):  # F-DB-2
    connection = _connection_to(name)
    with pytest.raises(RuntimeError, match="Refusing to truncate"):
        truncate_all(connection)
    executed = [call.args[0] for call in connection.cursor.return_value.execute.call_args_list]
    assert executed == ["SELECT DATABASE()"]


def test_guard_accepts_the_test_database():  # F-DB-2
    assert_test_database(_connection_to("collection_test"))
