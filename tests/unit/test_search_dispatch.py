import datetime
from unittest import mock

import pytest

from Workers.SearchWorker import SearchWorker

from tests.helpers import MEDIA_TYPES

LOOKUP_METHODS = {
    "book": "lookup_book",
    "movie": "lookup_movie",
    "video_game": "lookup_video_game",
    "board_game": "lookup_board_game",
    "rpg": "lookup_rpg",
    "anime": "lookup_anime",
    "album": "lookup_music",
}


@pytest.mark.parametrize("media_type", MEDIA_TYPES)
def test_each_media_type_calls_its_lookup(search_worker, media_type):  # U-SD-1
    lookup = mock.Mock(return_value={"passed": True, "items": []})
    setattr(search_worker, LOOKUP_METHODS[media_type], lookup)
    assert search_worker.search_item("dune", media_type, 2, {"a": "b"}) == {"passed": True, "items": []}
    lookup.assert_called_once_with("dune", 2, {"a": "b"})


def test_unknown_media_type_lists_valid_types(search_worker):  # U-SD-2
    result = search_worker.search_item("dune", "not_a_type")
    assert result["passed"] is False
    assert result["step_failed"] == "dispatch"
    for media_type in MEDIA_TYPES:
        assert media_type in result["exception"]["error_message"]


def test_page_and_options_have_defaults(search_worker):  # U-SD-3
    search_worker.lookup_book = mock.Mock(return_value={"passed": True, "items": []})
    search_worker.search_item("dune", "book")
    search_worker.lookup_book.assert_called_once_with("dune", 1, {})


def test_crashing_lookup_is_logged_and_propagates(search_worker, caplog):  # U-SD-4
    search_worker.lookup_book = mock.Mock(side_effect=RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        search_worker.search_item("dune", "book")
    assert "Search crashed" in caplog.text


@pytest.mark.parametrize("response, expected", [
    ({"passed": True, "items": [1, 2], "next_page": 2}, "Search succeeded"),
    ({"passed": False, "exception": {"error_type": "ValueError", "error_message": "bad"}}, "error_type=ValueError"),
    ({"passed": False, "exception": "plain string failure"}, "plain string failure"),
])
def test_search_result_logging_handles_each_outcome(search_worker, caplog, response, expected):  # U-SD-5
    caplog.set_level("INFO")
    search_worker._log_search_result("dune", "book", 1, {}, response, 0.1)
    assert expected in caplog.text


def test_init_fetches_a_token_and_sets_headers(search_worker):  # U-SD-6
    assert search_worker.IGDB_headers == {
        "Client-ID": "fake-igdb-id",
        "Authorization": "Bearer fake-igdb-token",
    }


def test_init_raises_on_bad_credentials():  # U-SD-7
    response = mock.Mock()
    response.json.return_value = {"status": 403, "message": "invalid client"}
    with mock.patch("requests.post", return_value=response):
        with pytest.raises(KeyError):
            SearchWorker()


@pytest.mark.xfail(reason="B20: the IGDB token's expiry is recorded but never checked")
def test_expired_token_is_refreshed_before_searching(search_worker, rsps):  # U-SD-8
    rsps.post("https://id.twitch.tv/oauth2/token", json={"access_token": "new-token", "expires_in": 3600})
    rsps.post("https://api.igdb.com/v4/games", json=[])
    search_worker.IGDB_Token_Last_Set = datetime.datetime.now() - datetime.timedelta(seconds=7200)
    search_worker.IGDB_Time_Until_Token_Refresh = 3600
    search_worker.lookup_video_game("dune", 1)
    assert rsps.calls[-1].request.headers["Authorization"] == "Bearer new-token"
