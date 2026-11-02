"""U-RES, U-PLAT and U-GIF: small functions with no collaborators."""
import pytest

from DataClasses.igdb_platforms import get_platform_id, get_supported_platforms
from Utilities.ResolveUserId import resolve_user_id
from Workers.SearchWorker import getIfUseful

from tests.helpers import FakeDB


def _cursor(rows):
    return FakeDB().on("FROM users", rows=rows).get_connection().cursor()


def test_resolve_user_id_reads_dict_rows():  # U-RES-1
    assert resolve_user_id(_cursor([{"user_id": 7}]), "clerk_1") == 7


def test_resolve_user_id_reads_tuple_rows():  # U-RES-2
    assert resolve_user_id(_cursor([(9,)]), "clerk_1") == 9


def test_resolve_user_id_raises_when_user_is_missing():  # U-RES-3
    with pytest.raises(ValueError):
        resolve_user_id(_cursor([]), "clerk_1")


def test_resolve_user_id_binds_the_id_as_a_parameter():  # U-RES-4
    db = FakeDB().on("FROM users", rows=[{"user_id": 7}])
    hostile_id = "x' OR '1'='1"
    resolve_user_id(db.get_connection().cursor(), hostile_id)
    assert db.calls[0]["params"] == (hostile_id,)
    assert hostile_id not in db.calls[0]["sql"]


@pytest.mark.parametrize("alias", ["ps5", "playstation 5"])
def test_platform_aliases_map_to_one_id(alias):  # U-PLAT-1
    assert get_platform_id(alias) == 167


@pytest.mark.parametrize("name", ["PS4", " ps4 ", "  PlayStation 4"])
def test_platform_lookup_ignores_case_and_whitespace(name):  # U-PLAT-2
    assert get_platform_id(name) == 48


@pytest.mark.parametrize("name", [None, "", "commodore 64000"])
def test_unknown_platforms_return_none(name):  # U-PLAT-3
    assert get_platform_id(name) is None


def test_supported_platforms_are_sorted_and_unique():  # U-PLAT-4
    platforms = get_supported_platforms()
    assert platforms == sorted(set(platforms))
    assert "ps5" in platforms


def test_get_if_useful_returns_truthy_values():  # U-GIF-1
    assert getIfUseful({"a": "value"}, "a", "default") == "value"


def test_get_if_useful_defaults_missing_keys():  # U-GIF-2
    assert getIfUseful({}, "a", "default") == "default"
    assert getIfUseful({}, "a") is None


@pytest.mark.parametrize("falsy", [0, "", [], None])
def test_get_if_useful_defaults_falsy_values(falsy):  # U-GIF-3
    assert getIfUseful({"a": falsy}, "a", "default") == "default"


def test_get_if_useful_follows_key_paths():  # U-GIF-4
    assert getIfUseful({"a": {"b": {"c": 1}}}, ["a", "b", "c"], "default") == 1


@pytest.mark.parametrize("data", [{}, {"a": {}}, {"a": {"b": 0}}, {"a": None}])
def test_get_if_useful_defaults_when_a_path_step_is_missing_or_falsy(data):  # U-GIF-5
    assert getIfUseful(data, ["a", "b"], "default") == "default"
