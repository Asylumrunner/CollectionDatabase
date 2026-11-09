"""U-ROW and U-EXC. `_row_to_item` and `_build_exception_dict` are copy-pasted between
workers, so each case runs against every copy to catch them drifting apart."""
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
def test_build_exception_dict(worker_class):  # U-EXC-1
    # __new__ skips SearchWorker.__init__, which would request an IGDB token
    worker = worker_class.__new__(worker_class)
    try:
        raise ValueError("boom", "extra")
    except ValueError as e:
        result = worker._build_exception_dict(e, {"function": "probe"})

    assert result["error_type"] == "ValueError"
    assert "boom" in result["error_message"]
    assert result["context"] == {"function": "probe"}
    assert result["exception_args"] == ("boom", "extra")
    assert "ValueError" in result["traceback"]
    assert result["traceback_lines"]
