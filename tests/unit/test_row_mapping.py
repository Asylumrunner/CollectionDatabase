"""U-ROW and U-EXC. `_row_to_item` is copy-pasted between workers, so each case runs
against every copy to catch them drifting apart. `_failure_response` lives on BaseWorker
and is checked through every worker to make sure none of them overrides it."""
import pytest

from Workers.ItemWorker import ItemWorker
from Workers.ListWorker import ListWorker
from Workers.SearchWorker import SearchWorker
from Workers.UserWorker import UserWorker

from tests.helpers import view_row


@pytest.fixture(params=[ItemWorker, ListWorker], ids=["ItemWorker", "ListWorker"])
def mapper(request):
    return request.param()


@pytest.mark.parametrize("media_type, columns, expected", [
    ("book", {"book_isbn": "123", "book_printing_year": 1990}, {"isbn": "123", "printing_year": 1990}),
    ("movie", {"movie_lang": "en", "movie_duration": 155}, {"lang": "en", "duration": 155}),
    ("board_game", {"boardgame_min_players": 3, "boardgame_max_players": 4, "boardgame_duration": 90},
     {"min_players": 3, "max_players": 4, "duration": 90}),
    ("rpg", {"rpg_isbn": "456"}, {"isbn": "456"}),
    ("anime", {"anime_episodes": 26}, {"episodes": 26}),
    ("video_game", {"videogame_platforms": '["PC", "Dreamcast"]', "videogame_platform_igdb_ids": '{"PC": 6, "Dreamcast": 23}'},
     {"platforms": ["PC", "Dreamcast"], "platform_igdb_ids": {"PC": 6, "Dreamcast": 23}}),
    ("album", {"album_tracks": '["One", "Two"]'}, {"tracklist": ["One", "Two"]}),
])
def test_each_media_type_maps_its_own_columns(mapper, media_type, columns, expected):  # U-ROW-1 to 7
    item = mapper._row_to_item(view_row(media_type=media_type, **columns))
    assert item.media_type == media_type
    for field, value in expected.items():
        assert getattr(item, field) == value


def test_other_types_columns_do_not_leak_in(mapper):  # U-ROW-8
    item = mapper._row_to_item(view_row(media_type="book", movie_duration=155, anime_episodes=26, rpg_isbn="456"))
    assert item.duration is None
    assert item.episodes is None
    assert item.isbn is None


def test_null_aggregates_map_to_their_empty_values(mapper):  # U-ROW-9
    item = mapper._row_to_item(view_row())
    assert item.created_by == []
    assert item.genres == []
    assert item.platforms is None
    assert item.platform_igdb_ids is None
    assert item.tracklist is None


def test_creators_and_genres_are_parsed_from_json(mapper):
    item = mapper._row_to_item(view_row(creators='["A", "B"]', genres='["Jazz"]'))
    assert item.created_by == ["A", "B"]
    assert item.genres == ["Jazz"]


def test_id_is_stringified(mapper):  # U-ROW-10
    assert mapper._row_to_item(view_row(item_id=42)).id == "42"


@pytest.mark.parametrize("worker_class", [ItemWorker, ListWorker, UserWorker, SearchWorker])
def test_failure_response(worker_class):  # U-EXC-1
    # __new__ skips SearchWorker.__init__, which would request an IGDB token
    worker = worker_class.__new__(worker_class)
    try:
        raise ValueError("boom", "extra")
    except ValueError as e:
        caught = e
    # Built outside the except block on purpose: the traceback must come from the exception itself
    result = worker._failure_response(caught, "probe", "probe_step", list_id=3)

    assert set(result) == {"passed", "step_failed", "exception"}
    assert result["passed"] is False
    assert result["step_failed"] == "probe_step"
    exception = result["exception"]
    assert exception["error_type"] == "ValueError"
    assert "boom" in exception["error_message"]
    assert exception["context"] == {"function": "probe", "step": "probe_step", "list_id": 3}
    assert exception["exception_args"] == ("boom", "extra")
    assert "ValueError" in exception["traceback"]
    assert exception["traceback_lines"]


def test_failure_response_without_a_traceback():  # U-EXC-2
    # SearchWorker reports an unknown media type with an exception that was never raised
    result = ItemWorker()._failure_response(ValueError("bad"), "probe", "probe_step")
    assert result["exception"]["error_message"] == "bad"
    assert result["exception"]["traceback_lines"] == []
