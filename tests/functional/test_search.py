"""The real client libraries run here; `responses` stubs the third-party APIs beneath them.

Only tests/fixtures/openlibrary/search.json is a recorded response. The rest are hand-written
from each API's documented shape and need checking against the live APIs.
"""
import re
from urllib.parse import parse_qs, urlparse

import pytest
import requests
from responses import matchers

from tests.functional_support import load_fixture, load_json_fixture
from tests.helpers import MEDIA_TYPES

OPENLIBRARY = "https://openlibrary.org/search.json"
TMDB = "https://api.themoviedb.org/3"
IGDB = "https://api.igdb.com/v4/games"
BGG = "https://boardgamegeek.com/xmlapi2"
RPGGEEK = "https://rpggeek.com/xmlapi2"
JIKAN = re.compile(r"https://api\.jikan\.moe/v4/anime.*")
DISCOGS = "https://api.discogs.com"
DISCOGS_SEARCH = re.compile(r"https://api\.discogs\.com/database/search.*")

# The first upstream request each search makes, used to simulate outages
FIRST_CALL = {
    "book": ("GET", OPENLIBRARY),
    "movie": ("GET", f"{TMDB}/search/movie"),
    "video_game": ("POST", IGDB),
    "board_game": ("GET", f"{BGG}/search"),
    "rpg": ("GET", f"{RPGGEEK}/search"),
    "anime": ("GET", JIKAN),
    "album": ("GET", DISCOGS_SEARCH),
}

EXPECTED = {
    "book": {"title": "Dune", "created_by": ["Frank Herbert"], "release_year": 1965, "original_api_id": "/works/OL893414W"},
    "movie": {"title": "The Matrix", "created_by": ["Lana Wachowski", "Lilly Wachowski"], "release_year": "1999",
              "lang": "en", "duration": 136, "original_api_id": 603},
    "video_game": {"title": "The Legend of Zelda: Ocarina of Time", "created_by": ["Nintendo EAD"], "release_year": 1998,
                   "platforms": ["Nintendo 64"], "original_api_id": 1029},
    "board_game": {"title": "CATAN", "created_by": ["Klaus Teuber"], "release_year": "1995", "min_players": "3",
                   "max_players": "4", "duration": "120", "original_api_id": "13"},
    "rpg": {"title": "Blades in the Dark", "created_by": ["John Harper"], "release_year": "2017", "original_api_id": "4321"},
    "anime": {"title": "Cowboy Bebop", "created_by": ["Sunrise"], "release_year": 1998, "episodes": 26, "original_api_id": 1},
    "album": {"title": "Kind Of Blue", "created_by": ["Miles Davis"], "genres": ["Jazz"],
              "tracklist": ["So What", "Freddie Freeloader"], "original_api_id": 5460},
}


def stub_upstream(rsps, media_type):
    if media_type == "book":
        rsps.get(OPENLIBRARY, json=load_json_fixture("openlibrary/search.json"))
    elif media_type == "movie":
        rsps.get(f"{TMDB}/search/movie", json=load_json_fixture("tmdb/search.json"))
        rsps.get(f"{TMDB}/movie/603", json=load_json_fixture("tmdb/movie.json"))
        rsps.get(f"{TMDB}/movie/603/credits", json=load_json_fixture("tmdb/credits.json"))
    elif media_type == "video_game":
        rsps.post(IGDB, json=load_json_fixture("igdb/games.json"))
    elif media_type == "board_game":
        rsps.get(f"{BGG}/search", body=load_fixture("bgg/search.xml"))
        rsps.get(f"{BGG}/thing", body=load_fixture("bgg/thing.xml"))
    elif media_type == "rpg":
        rsps.get(f"{RPGGEEK}/search", body=load_fixture("rpggeek/search.xml"))
        rsps.get(f"{RPGGEEK}/thing", body=load_fixture("rpggeek/thing.xml"))
    elif media_type == "anime":
        rsps.get(JIKAN, json=load_json_fixture("jikan/search.json"))
    elif media_type == "album":
        rsps.get(DISCOGS_SEARCH, json=load_json_fixture("discogs/search.json"))
        rsps.get(f"{DISCOGS}/masters/5460", json=load_json_fixture("discogs/master.json"))
        rsps.get(f"{DISCOGS}/releases/1234", json=load_json_fixture("discogs/release.json"))


def search(client, media_type, title="dune", **filters):
    query = "&".join(f"{k}={v}" for k, v in {"media_type": media_type, **filters}.items())
    return client.get(f"/search/{title}?{query}")


@pytest.fixture
def client(client_as):
    # Search never resolves the user, so no users row (and no DB) is needed
    return client_as("user_a")


@pytest.mark.parametrize("media_type", MEDIA_TYPES)
def test_search_returns_normalized_items(client, rsps, media_type):  # F-SRCH-1 to 7
    stub_upstream(rsps, media_type)
    response = search(client, media_type)
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "SUCCESS"
    assert body["next_page"] == 2
    item = body["data"][0]
    assert item["media_type"] == media_type
    for field, expected in EXPECTED[media_type].items():
        assert item[field] == expected, field


@pytest.mark.xfail(reason="B22: the installed Discogs Master model has no year or notes, so albums lose both")
@pytest.mark.parametrize("field, expected", [("release_year", 1959), ("summary", "A landmark record.")])
def test_album_search_keeps_year_and_notes(client, rsps, field, expected):  # F-SRCH-7
    stub_upstream(rsps, "album")
    assert search(client, "album").get_json()["data"][0][field] == expected


@pytest.mark.parametrize("media_type, url_fragment", [
    ("book", "openlibrary.org/search.json"),
    ("movie", "api.themoviedb.org/3/search/movie"),
    ("board_game", "boardgamegeek.com/xmlapi2/search"),
    ("rpg", "rpggeek.com/xmlapi2/search"),
    ("anime", "api.jikan.moe/v4/anime"),
    ("album", "api.discogs.com/database/search"),
])
def test_search_calls_the_right_upstream(client, rsps, media_type, url_fragment):  # F-SRCH-1 to 7
    stub_upstream(rsps, media_type)
    search(client, media_type)
    assert url_fragment in rsps.calls[0].request.url


def test_igdb_gets_its_token(client, rsps):  # F-SRCH-3
    stub_upstream(rsps, "video_game")
    search(client, "video_game")
    headers = rsps.calls[0].request.headers
    assert headers["Authorization"] == "Bearer fake-igdb-token"
    assert headers["Client-ID"] == "fake-igdb-id"


@pytest.mark.parametrize("media_type, filters, query_param, expected", [
    ("book", {"author": "herbert"}, "q", "dune AND author:herbert"),
    ("movie", {"year": "1999"}, "year", "1999"),
    ("anime", {"type": "tv"}, "type", "tv"),
    ("album", {"artist": "miles"}, "artist", "miles"),
])
def test_filters_reach_the_upstream(client, rsps, media_type, filters, query_param, expected):  # F-SRCH-8
    stub_upstream(rsps, media_type)
    search(client, media_type, **filters)
    query = parse_qs(urlparse(rsps.calls[0].request.url).query)
    assert query[query_param] == [expected]


def test_video_game_filter_reaches_the_upstream(client, rsps):  # F-SRCH-8
    stub_upstream(rsps, "video_game")
    search(client, "video_game", platform="ps5")
    body = rsps.calls[0].request.body
    assert "where platforms = 167;" in (body.decode() if isinstance(body, bytes) else body)


def assert_failure_json(response):
    assert response.status_code == 500
    assert response.get_json()["status"] == "FAILURE"


@pytest.mark.parametrize("media_type", MEDIA_TYPES)
def test_upstream_non_json_error_page_is_a_500(client, rsps, media_type):  # F-SRCH-9
    method, url = FIRST_CALL[media_type]
    rsps.add(method, url, body="Bad Gateway", status=502)
    assert_failure_json(search(client, media_type))


@pytest.mark.parametrize("media_type", MEDIA_TYPES)
def test_upstream_connection_error_is_a_500(client, rsps, media_type):  # F-SRCH-10
    method, url = FIRST_CALL[media_type]
    rsps.add(method, url, body=requests.exceptions.ConnectionError("upstream down"))
    assert_failure_json(search(client, media_type))


def test_no_results_is_a_200_with_empty_data(client, rsps):  # F-SRCH-11
    rsps.get(OPENLIBRARY, json={"docs": []})
    response = search(client, "book")
    assert response.status_code == 200
    assert response.get_json()["data"] == []


# Search result -> PUT -> GET: the path a real user takes

@pytest.mark.parametrize("media_type", MEDIA_TYPES)
def test_search_results_can_be_added_as_is(user_a, rsps, media_type):  # F-SRCH-12 to 18
    stub_upstream(rsps, media_type)
    found = search(user_a, media_type).get_json()["data"][0]

    assert user_a.put("/collection/item", json=found).status_code == 200

    stored = user_a.get("/collection").get_json()["data"]
    assert len(stored) == 1
    assert stored[0]["title"] == found["title"]
    assert stored[0]["media_type"] == media_type
    assert stored[0]["original_api_id"] == str(found["original_api_id"])
    assert stored[0]["created_by"] == found["created_by"]


@pytest.mark.xfail(reason="B17: summaries over 1024 characters fail with a 500, and BGG descriptions can be longer")
def test_board_game_with_a_long_description_can_be_added(user_a, rsps):  # F-SRCH-19
    rsps.get(f"{BGG}/search", body=load_fixture("bgg/search.xml"))
    thing = load_fixture("bgg/thing.xml").replace("Trade and build.", "x" * 3000)
    rsps.get(f"{BGG}/thing", body=thing, match=[matchers.query_param_matcher({"id": "13"})])
    found = search(user_a, "board_game").get_json()["data"][0]
    assert user_a.put("/collection/item", json=found).status_code == 200


@pytest.mark.xfail(reason="B19c: an empty release_date becomes an empty-string year, which a SMALLINT column rejects")
def test_movie_with_an_empty_release_date_can_be_added(user_a, rsps):  # F-SRCH-20
    rsps.get(f"{TMDB}/search/movie", json=load_json_fixture("tmdb/search.json"))
    rsps.get(f"{TMDB}/movie/603", json={**load_json_fixture("tmdb/movie.json"), "release_date": ""})
    rsps.get(f"{TMDB}/movie/603/credits", json=load_json_fixture("tmdb/credits.json"))
    found = search(user_a, "movie").get_json()["data"][0]
    assert user_a.put("/collection/item", json=found).status_code == 200
