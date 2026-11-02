import dataclasses
import datetime
import json
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
import requests
from responses import matchers

from DataClasses.item import Item

from tests.helpers import MEDIA_TYPES

OPENLIBRARY = "https://openlibrary.org/search.json"
TMDB = "https://api.themoviedb.org/3"
IGDB = "https://api.igdb.com/v4/games"
BGG = "https://boardgamegeek.com/xmlapi2"
RPGGEEK = "https://rpggeek.com/xmlapi2"


def query_of(call):
    return {k: v[0] for k, v in parse_qs(urlparse(call.request.url).query).items()}


def body_of(call):
    body = call.request.body
    return body.decode() if isinstance(body, bytes) else body


# ---- Books

BOOK_DOC = {
    "key": "/works/OL1W",
    "title": "Dune",
    "first_publish_year": 1965,
    "author_name": ["Frank Herbert"],
    "cover_i": 55,
    "editions": {"docs": [{"isbn": ["9780441013593"]}]},
}


def book_query(worker, rsps, options):
    rsps.get(OPENLIBRARY, json={"docs": []})
    worker.lookup_book("dune", 1, options)
    return query_of(rsps.calls[0])["q"]


@pytest.mark.parametrize("option", [
    "author", "subject", "place", "person", "language", "publisher", "edition_count", "author_key",
])
def test_book_filters_are_anded_into_the_query(search_worker, rsps, option):  # U-BOOK-1
    assert book_query(search_worker, rsps, {option: "x"}) == f"dune AND {option}:x"


@pytest.mark.parametrize("options, clause", [
    ({"earliest_publish_year": "1960"}, "publish_year:[1960 TO *]"),
    ({"latest_publish_year": "1970"}, "publish_year:[* TO 1970]"),
    ({"earliest_first_publish_year": "1960"}, "first_publish_year:[1960 TO *]"),
    ({"latest_first_publish_year": "1970"}, "first_publish_year:[* TO 1970]"),
    ({"min_number_of_pages": "100"}, "number_of_pages:[100 TO *]"),
    ({"max_number_of_pages": "900"}, "number_of_pages:[* TO 900]"),
    ({"min_number_of_pages": "100", "max_number_of_pages": "900"}, "number_of_pages:[100 TO 900]"),
])
def test_book_range_filters(search_worker, rsps, options, clause):  # U-BOOK-2
    assert book_query(search_worker, rsps, options) == f"dune AND {clause}"


def test_book_unknown_options_are_ignored(search_worker, rsps):  # U-BOOK-3
    assert book_query(search_worker, rsps, {"nonsense": "x"}) == "dune"


def test_book_fields_are_mapped(search_worker, rsps):  # U-BOOK-4
    rsps.get(OPENLIBRARY, json={"docs": [BOOK_DOC]})
    result = search_worker.lookup_book("dune", 1)
    item = result["items"][0]
    assert result["passed"]
    assert (item.id, item.original_api_id) == ("/works/OL1W", "/works/OL1W")
    assert (item.title, item.media_type, item.release_year) == ("Dune", "book", 1965)
    assert item.created_by == ["Frank Herbert"]
    assert item.isbn == "9780441013593"
    assert item.printing_year == 1965
    assert "55-M.jpg" in item.img_link


@pytest.mark.parametrize("removed, field, expected", [
    ("cover_i", "img_link", ""),
    ("editions", "isbn", ""),
])
def test_book_missing_fields_become_empty_strings(search_worker, rsps, removed, field, expected):  # U-BOOK-5
    doc = {k: v for k, v in BOOK_DOC.items() if k != removed}
    rsps.get(OPENLIBRARY, json={"docs": [doc]})
    assert getattr(search_worker.lookup_book("dune", 1)["items"][0], field) == expected


def test_book_edition_without_isbn_becomes_an_empty_string(search_worker, rsps):  # U-BOOK-5
    rsps.get(OPENLIBRARY, json={"docs": [{**BOOK_DOC, "editions": {"docs": [{"publish_date": ["1990"]}]}}]})
    assert search_worker.lookup_book("dune", 1)["items"][0].isbn == ""


def test_book_invalid_json_reports_request_context(search_worker, rsps):  # U-BOOK-6
    rsps.get(OPENLIBRARY, body="<html>not json</html>", status=502)
    result = search_worker.lookup_book("dune", 1)
    assert result["passed"] is False
    context = result["exception"]["context"]
    assert context["response_status"] == 502
    assert "not json" in context["response_text"]
    assert context["url"].startswith(OPENLIBRARY)


# ---- Movies

def movie_detail(movie_id=1, **overrides):
    return {"id": movie_id, "title": f"Movie {movie_id}", "release_date": "1999-03-31",
            "poster_path": "/p.jpg", "original_language": "en", "overview": "Summary", "runtime": 136, **overrides}


def register_movie(rsps, detail, crew=None):
    movie_id = detail["id"]
    rsps.get(f"{TMDB}/movie/{movie_id}", json=detail)
    rsps.get(f"{TMDB}/movie/{movie_id}/credits", json={"crew": crew or []})


def register_movie_search(rsps, *movie_ids):
    rsps.get(f"{TMDB}/search/movie", json={"results": [{"id": i} for i in movie_ids]})


def test_movie_options_are_filtered(search_worker, rsps):  # U-MOV-1
    register_movie_search(rsps)
    options = {"include_adult": "true", "language": "en", "primary_release_year": "1999",
               "region": "US", "year": "1999", "nonsense": "x"}
    search_worker.lookup_movie("matrix", 2, options)
    query = query_of(rsps.calls[0])
    assert query["query"] == "matrix"
    assert query["page"] == "2"
    assert query["api_key"] == "fake-tmdb-key"
    assert {k: query[k] for k in options if k != "nonsense"} == {k: v for k, v in options.items() if k != "nonsense"}
    assert "nonsense" not in query


def test_movie_fetches_detail_and_credits_keeping_order(search_worker, rsps):  # U-MOV-2
    register_movie_search(rsps, 2, 1)
    register_movie(rsps, movie_detail(2))
    register_movie(rsps, movie_detail(1))
    result = search_worker.lookup_movie("x", 1)
    assert [item.id for item in result["items"]] == [2, 1]
    assert len(rsps.calls) == 5


def test_movie_fields_and_directors_are_mapped(search_worker, rsps):  # U-MOV-3
    register_movie_search(rsps, 1)
    register_movie(rsps, movie_detail(1), crew=[
        {"job": "Director", "name": "Lana"},
        {"job": "Writer", "name": "Someone Else"},
        {"job": "Director", "name": "Lilly"},
    ])
    item = search_worker.lookup_movie("x", 1)["items"][0]
    assert item.created_by == ["Lana", "Lilly"]
    assert (item.title, item.release_year, item.lang, item.duration) == ("Movie 1", "1999", "en", 136)
    assert item.summary == "Summary"
    assert item.img_link.endswith("/p.jpg")


def test_movie_missing_poster_and_date_use_defaults(search_worker, rsps):  # U-MOV-4
    detail = movie_detail(1)
    del detail["poster_path"], detail["release_date"]
    register_movie_search(rsps, 1)
    register_movie(rsps, detail)
    item = search_worker.lookup_movie("x", 1)["items"][0]
    assert item.img_link is None
    assert item.release_year == "0000"


@pytest.mark.xfail(reason="B19b: a null poster_path is formatted into the image URL")
def test_movie_null_poster_gives_no_image(search_worker, rsps):  # U-MOV-5
    register_movie_search(rsps, 1)
    register_movie(rsps, movie_detail(1, poster_path=None))
    assert search_worker.lookup_movie("x", 1)["items"][0].img_link is None


@pytest.mark.xfail(reason="B19c: an empty release_date becomes an empty-string year")
def test_movie_empty_release_date_gives_no_year(search_worker, rsps):  # U-MOV-6
    register_movie_search(rsps, 1)
    register_movie(rsps, movie_detail(1, release_date=""))
    assert search_worker.lookup_movie("x", 1)["items"][0].release_year is None


def test_movie_failed_detail_call_fails_the_search(search_worker, rsps):  # U-MOV-7
    register_movie_search(rsps, 1)
    rsps.get(f"{TMDB}/movie/1", body="not json", status=500)
    assert search_worker.lookup_movie("x", 1)["passed"] is False


# ---- Video games

def igdb_body(worker, rsps, title="zelda", page=1, options=None):
    rsps.post(IGDB, json=[])
    worker.lookup_video_game(title, page, options or {})
    return body_of(rsps.calls[0])


def utc_timestamp(*date_parts):
    return int(datetime.datetime(*date_parts, tzinfo=datetime.timezone.utc).timestamp())


def test_igdb_body_has_search_limit_and_offset(search_worker, rsps):  # U-VG-1
    body = igdb_body(search_worker, rsps, page=3)
    assert 'search "zelda";' in body
    assert "limit 25;" in body
    assert "offset 50;" in body
    assert "fields " in body
    assert rsps.calls[0].request.headers["Authorization"] == "Bearer fake-igdb-token"


def test_igdb_title_is_escaped(search_worker, rsps):  # U-VG-2
    body = igdb_body(search_worker, rsps, title='a"b\\c')
    assert 'search "a\\"b\\\\c";' in body


def test_igdb_known_platform_adds_a_where_clause(search_worker, rsps):  # U-VG-3
    assert "where platforms = 167;" in igdb_body(search_worker, rsps, options={"platform": "PS5"})


def test_igdb_unknown_platform_is_omitted(search_worker, rsps):  # U-VG-3
    assert "where" not in igdb_body(search_worker, rsps, options={"platform": "nope"})


def test_igdb_date_filters_become_timestamps(search_worker, rsps):  # U-VG-4
    body = igdb_body(search_worker, rsps, options={"release_date_before": "01/02/2020", "release_date_after": "01/02/2010"})
    assert (f"where first_release_date < {utc_timestamp(2020, 1, 2)} "
            f"& first_release_date > {utc_timestamp(2010, 1, 2)};") in body


@pytest.mark.parametrize("option", ["release_date_before", "release_date_after"])
def test_igdb_invalid_date_is_skipped_with_a_warning(search_worker, rsps, caplog, option):  # U-VG-5
    body = igdb_body(search_worker, rsps, options={option: "2020-01-02"})
    assert "where" not in body
    assert f"Invalid {option}" in caplog.text


def test_igdb_fields_are_mapped(search_worker, rsps):  # U-VG-6
    rsps.post(IGDB, json=[{
        "id": 7, "name": "Zelda", "first_release_date": utc_timestamp(2001, 9, 9), "cover": {"image_id": "abc"},
        "involved_companies": [{"company": {"name": "Nintendo"}}], "summary": "Summary", "platforms": [{"name": "N64"}],
    }])
    item = search_worker.lookup_video_game("zelda", 1)["items"][0]
    assert (item.id, item.original_api_id, item.title, item.release_year) == (7, 7, "Zelda", 2001)
    assert (item.img_link, item.created_by, item.platforms) == ("abc", ["Nintendo"], ["N64"])
    assert item.summary == "Summary"


def test_igdb_missing_optional_fields_use_empty_values(search_worker, rsps):  # U-VG-6
    rsps.post(IGDB, json=[{"id": 7, "name": "Zelda", "first_release_date": utc_timestamp(2001, 9, 9)}])
    item = search_worker.lookup_video_game("zelda", 1)["items"][0]
    assert (item.img_link, item.created_by, item.platforms, item.summary) == ("", [], [], "")


def test_igdb_error_object_fails_with_request_body_in_context(search_worker, rsps):  # U-VG-7
    rsps.post(IGDB, json={"message": "Authorization Failure"}, status=401)
    result = search_worker.lookup_video_game("zelda", 1)
    assert result["passed"] is False
    assert 'search "zelda"' in result["exception"]["context"]["request_body"]


@pytest.mark.xfail(reason="B19f: a missing release date is reported as 1970 (1969 in US timezones)")
def test_igdb_missing_date_gives_no_year(search_worker, rsps):  # U-VG-8
    rsps.post(IGDB, json=[{"id": 7, "name": "Zelda"}])
    assert search_worker.lookup_video_game("zelda", 1)["items"][0].release_year is None


# ---- Board games and RPGs

def search_xml(*ids):
    return "<items>" + "".join(f'<item id="{i}"/>' for i in ids) + "</items>"


def thing_xml(item_id=1, link_type="boardgamedesigner", include=("image", "yearpublished", "players")):
    image = "<image>https://example.test/i.jpg</image>" if "image" in include else ""
    year = '<yearpublished value="1995"/>' if "yearpublished" in include else ""
    players = '<minplayers value="3"/><maxplayers value="4"/><playingtime value="90"/>' if "players" in include else ""
    return f"""<items><item id="{item_id}">
        {image}
        <name type="alternate" value="Alternate {item_id}"/>
        <name type="primary" value="Title {item_id}"/>
        <description>Summary {item_id}</description>
        {year}{players}
        <link type="{link_type}" value="Klaus"/>
        <link type="publisher" value="Not A Designer"/>
    </item></items>"""


def register_things(rsps, base_url, things):
    for item_id, body in things.items():
        rsps.get(f"{base_url}/thing", body=body, match=[matchers.query_param_matcher({"id": str(item_id)})])


def test_board_game_search_request_and_detail_calls(search_worker, rsps):  # U-BGG-1
    rsps.get(f"{BGG}/search", body=search_xml(1, 2))
    register_things(rsps, BGG, {1: thing_xml(1), 2: thing_xml(2)})
    result = search_worker.lookup_board_game("catan", 1)
    search_call = rsps.calls[0]
    assert query_of(search_call) == {"query": "catan", "type": "boardgame"}
    assert search_call.request.headers["Authorization"] == "Bearer fake-bgg-key"
    assert [item.title for item in result["items"]] == ["Title 1", "Title 2"]
    assert len(rsps.calls) == 3


def test_board_game_fields_are_mapped(search_worker, rsps):  # U-BGG-2
    rsps.get(f"{BGG}/search", body=search_xml(1))
    register_things(rsps, BGG, {1: thing_xml(1)})
    item = search_worker.lookup_board_game("catan", 1)["items"][0]
    assert (item.id, item.original_api_id, item.title, item.media_type) == ("1", "1", "Title 1", "board_game")
    assert item.created_by == ["Klaus"]
    assert (item.release_year, item.min_players, item.max_players, item.duration) == ("1995", "3", "4", "90")
    assert (item.img_link, item.summary) == ("https://example.test/i.jpg", "Summary 1")


def test_board_game_without_image_has_none(search_worker, rsps):  # U-BGG-3
    rsps.get(f"{BGG}/search", body=search_xml(1))
    register_things(rsps, BGG, {1: thing_xml(1, include=("yearpublished", "players"))})
    assert search_worker.lookup_board_game("catan", 1)["items"][0].img_link is None


def test_board_game_missing_detail_is_dropped(search_worker, rsps):  # U-BGG-3
    rsps.get(f"{BGG}/search", body=search_xml(1, 2))
    register_things(rsps, BGG, {1: "<items></items>", 2: thing_xml(2)})
    assert [item.title for item in search_worker.lookup_board_game("catan", 1)["items"]] == ["Title 2"]


def test_board_game_no_results(search_worker, rsps):  # U-BGG-4
    rsps.get(f"{BGG}/search", body='<items total="0"></items>')
    result = search_worker.lookup_board_game("catan", 1)
    assert result["passed"] and result["items"] == []


def test_board_game_malformed_xml_fails(search_worker, rsps):  # U-BGG-4
    rsps.get(f"{BGG}/search", body="<items><oops")
    assert search_worker.lookup_board_game("catan", 1)["passed"] is False


@pytest.mark.xfail(reason="B19i: one malformed record fails the whole search")
def test_board_game_malformed_record_is_skipped(search_worker, rsps):  # U-BGG-5
    rsps.get(f"{BGG}/search", body=search_xml(1, 2))
    register_things(rsps, BGG, {1: thing_xml(1, include=("image",)), 2: thing_xml(2)})
    result = search_worker.lookup_board_game("catan", 1)
    assert result["passed"]
    assert [item.title for item in result["items"]] == ["Title 2"]


@pytest.mark.xfail(reason="B19h: BGG lookups ignore the page, so every page is identical")
def test_board_game_pages_differ(search_worker, rsps):  # U-BGG-6
    ids = list(range(1, 31))
    rsps.get(f"{BGG}/search", body=search_xml(*ids))
    register_things(rsps, BGG, {i: thing_xml(i) for i in ids})
    first = [item.title for item in search_worker.lookup_board_game("catan", 1)["items"]]
    second = [item.title for item in search_worker.lookup_board_game("catan", 2)["items"]]
    assert first != second


def field(item, name):
    # RPG results are plain dicts today (B19e); read them either way so these tests survive the fix
    return item[name] if isinstance(item, dict) else getattr(item, name)


def test_rpg_uses_rpggeek_and_maps_fields(search_worker, rsps):  # U-RPG-1
    rsps.get(f"{RPGGEEK}/search", body=search_xml(1))
    register_things(rsps, RPGGEEK, {1: thing_xml(1, link_type="rpgdesigner")})
    item = search_worker.lookup_rpg("dnd", 1)["items"][0]
    assert query_of(rsps.calls[0]) == {"query": "dnd", "type": "rpgitem"}
    assert field(item, "title") == "Title 1"
    assert field(item, "media_type") == "rpg"
    assert field(item, "created_by") == ["Klaus"]
    assert field(item, "release_year") == "1995"
    assert field(item, "original_api_id") == "1"
    assert field(item, "summary") == "Summary 1"
    assert field(item, "img_link") == "https://example.test/i.jpg"


@pytest.mark.xfail(reason="B19e: RPG search returns dicts without an id, unlike every other type")
def test_rpg_results_have_the_same_shape_as_other_types(search_worker, rsps):  # U-RPG-2
    rsps.get(f"{RPGGEEK}/search", body=search_xml(1))
    register_things(rsps, RPGGEEK, {1: thing_xml(1, link_type="rpgdesigner")})
    item = search_worker.lookup_rpg("dnd", 1)["items"][0]
    assert isinstance(item, Item)
    assert dataclasses.asdict(item)["id"] == "1"


@pytest.mark.xfail(reason="B19i: one malformed record fails the whole search")
def test_rpg_malformed_record_is_skipped(search_worker, rsps):  # U-RPG-3
    rsps.get(f"{RPGGEEK}/search", body=search_xml(1, 2))
    register_things(rsps, RPGGEEK, {
        1: thing_xml(1, link_type="rpgdesigner", include=("image",)),
        2: thing_xml(2, link_type="rpgdesigner"),
    })
    result = search_worker.lookup_rpg("dnd", 1)
    assert result["passed"]
    assert len(result["items"]) == 1


# ---- Anime

def anime_entry(**overrides):
    return {
        "mal_id": 1, "title_english": "Cowboy Bebop", "title": "Kaubooi Bibappu",
        "aired": {"prop": {"from": {"year": 1998}}}, "images": {"jpg": {"image_url": "https://example.test/a.jpg"}},
        "studios": [{"name": "Sunrise"}, {"name": "Bones"}], "synopsis": "Space", "episodes": 26, **overrides,
    }


def stub_jikan(worker, data=None, error=None):
    worker.jikan_client = mock.Mock()
    worker.jikan_client.search.return_value = {"data": data or []}
    worker.jikan_client.search.side_effect = error


def test_anime_options_are_filtered_and_page_forwarded(search_worker):  # U-ANI-1
    stub_jikan(search_worker)
    search_worker.lookup_anime("bebop", 2, {"type": "tv", "nonsense": "x"})
    search_worker.jikan_client.search.assert_called_once_with("anime", "bebop", 2, parameters={"type": "tv"})


def test_anime_without_options_passes_none(search_worker):  # U-ANI-1
    stub_jikan(search_worker)
    search_worker.lookup_anime("bebop", 1)
    search_worker.jikan_client.search.assert_called_once_with("anime", "bebop", 1, parameters=None)


def test_anime_fields_are_mapped(search_worker):  # U-ANI-2
    stub_jikan(search_worker, [anime_entry()])
    item = search_worker.lookup_anime("bebop", 1)["items"][0]
    assert (item.id, item.original_api_id, item.title, item.release_year) == (1, 1, "Cowboy Bebop", 1998)
    assert (item.created_by, item.episodes) == (["Sunrise", "Bones"], 26)
    assert (item.img_link, item.summary) == ("https://example.test/a.jpg", "Space")


def test_anime_no_results(search_worker):  # U-ANI-2
    stub_jikan(search_worker)
    result = search_worker.lookup_anime("bebop", 1)
    assert result["passed"] and result["items"] == []


def test_anime_client_error_fails(search_worker):  # U-ANI-3
    stub_jikan(search_worker, error=RuntimeError("rate limited"))
    assert search_worker.lookup_anime("bebop", 1)["passed"] is False


@pytest.mark.xfail(reason="B19d: anime with no English title get a null title")
def test_anime_null_english_title_falls_back(search_worker):  # U-ANI-4
    stub_jikan(search_worker, [anime_entry(title_english=None)])
    assert search_worker.lookup_anime("bebop", 1)["items"][0].title == "Kaubooi Bibappu"


# ---- Music. SimpleNamespace, not MagicMock: lookup_music branches on hasattr, which
# is always true on a MagicMock.

def full_master(**attributes):
    return SimpleNamespace(**{"title": "Kind of Blue", **attributes})


def stub_discogs(worker, *masters, search_error=None):
    results = mock.Mock()
    results.page.return_value = [SimpleNamespace(id=i + 1) for i in range(len(masters))]
    client = mock.Mock()
    client.search.return_value = results
    client.search.side_effect = search_error
    client.master.side_effect = list(masters)
    worker.discogs_client = client
    return client, results


def test_music_search_parameters_and_page(search_worker):  # U-MUS-1
    client, results = stub_discogs(search_worker)
    search_worker.lookup_music("kind of blue", 3, {"artist": "Miles", "year": "1959", "nonsense": "x"})
    client.search.assert_called_once_with(release_title="kind of blue", type="master", artist="Miles", year="1959")
    results.page.assert_called_once_with(3)


def test_music_prefers_main_release_artists(search_worker):  # U-MUS-2
    stub_discogs(search_worker, full_master(
        main_release=SimpleNamespace(artists=[SimpleNamespace(name="Miles Davis")]),
        data={"artists": [{"name": "Should Not Be Used"}]},
    ))
    assert search_worker.lookup_music("x", 1)["items"][0].created_by == ["Miles Davis"]


def test_music_falls_back_to_raw_artist_data(search_worker):  # U-MUS-2
    stub_discogs(search_worker, full_master(data={"artists": [{"name": "Miles Davis"}, {"id": 5}]}))
    assert search_worker.lookup_music("x", 1)["items"][0].created_by == ["Miles Davis"]


def test_music_fields_are_mapped(search_worker):  # U-MUS-3
    stub_discogs(search_worker, full_master(
        year=1959, images=[{"uri": "https://example.test/first.jpg"}, {"uri": "second"}], notes="Notes",
        genres=["Jazz"], tracklist=[SimpleNamespace(title="So What"), SimpleNamespace(title="Freddie")],
    ))
    item = search_worker.lookup_music("x", 1)["items"][0]
    assert (item.id, item.original_api_id, item.title, item.media_type) == (1, 1, "Kind of Blue", "album")
    assert (item.release_year, item.img_link, item.summary) == (1959, "https://example.test/first.jpg", "Notes")
    assert (item.genres, item.tracklist) == (["Jazz"], ["So What", "Freddie"])


def test_music_absent_attributes_become_none(search_worker):  # U-MUS-3
    stub_discogs(search_worker, full_master())
    item = search_worker.lookup_music("x", 1)["items"][0]
    assert (item.release_year, item.img_link, item.summary, item.genres, item.tracklist) == (None,) * 5
    assert item.created_by == []


def test_music_failed_master_is_skipped(search_worker, caplog):  # U-MUS-4
    stub_discogs(search_worker, RuntimeError("404"), full_master(title="Survivor"))
    result = search_worker.lookup_music("x", 1)
    assert result["passed"]
    assert [item.title for item in result["items"]] == ["Survivor"]
    assert "Could not fetch details for master 1" in caplog.text


def test_music_search_error_fails(search_worker):  # U-MUS-5
    stub_discogs(search_worker, search_error=RuntimeError("rate limited"))
    assert search_worker.lookup_music("x", 1)["passed"] is False


# ---- Paging behaviour shared by all seven lookups

def register_results(worker, rsps, media_type, empty=False):
    """Stubs one media type's upstream to return either one result or none."""
    if media_type == "book":
        rsps.get(OPENLIBRARY, json={"docs": [] if empty else [BOOK_DOC]})
    elif media_type == "movie":
        register_movie_search(rsps, *([] if empty else [1]))
        if not empty:
            register_movie(rsps, movie_detail(1))
    elif media_type == "video_game":
        rsps.post(IGDB, json=[] if empty else [{"id": 7, "name": "Zelda", "first_release_date": 1000000000}])
    elif media_type == "board_game":
        rsps.get(f"{BGG}/search", body=search_xml(*([] if empty else [1])))
        register_things(rsps, BGG, {} if empty else {1: thing_xml(1)})
    elif media_type == "rpg":
        rsps.get(f"{RPGGEEK}/search", body=search_xml(*([] if empty else [1])))
        register_things(rsps, RPGGEEK, {} if empty else {1: thing_xml(1, link_type="rpgdesigner")})
    elif media_type == "anime":
        stub_jikan(worker, [] if empty else [anime_entry()])
    elif media_type == "album":
        if empty:
            stub_discogs(worker)
        else:
            stub_discogs(worker, full_master())


@pytest.mark.parametrize("media_type", MEDIA_TYPES)
def test_results_present_advance_the_page(search_worker, rsps, media_type):  # U-PAGE-1
    register_results(search_worker, rsps, media_type)
    result = search_worker.search_item("x", media_type, 2)
    assert result["passed"] and len(result["items"]) == 1
    assert result["next_page"] == 3


@pytest.mark.xfail(reason="B19g: next_page keeps incrementing even with no results")
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
def test_no_results_end_paging(search_worker, rsps, media_type):  # U-PAGE-2
    register_results(search_worker, rsps, media_type, empty=True)
    assert search_worker.search_item("x", media_type, 2)["next_page"] is None


B21 = pytest.mark.xfail(reason="B21: book and movie set passed=True before parsing the page, so a bad page reports success")


@pytest.mark.parametrize("media_type", [
    pytest.param(media_type, marks=B21) if media_type in ("book", "movie") else media_type
    for media_type in MEDIA_TYPES
])
def test_non_numeric_page_fails_cleanly(search_worker, rsps, media_type):  # U-PAGE-3
    register_results(search_worker, rsps, media_type)
    assert search_worker.search_item("x", media_type, "abc")["passed"] is False
